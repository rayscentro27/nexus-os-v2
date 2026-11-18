#!/usr/bin/env python3
"""Postiz provider adapter (LAB) + n8n orchestration client.

Nexus remains the authority: this module routes through the existing
social_provider_router (Postiz is the LAB primary provider), resolves service
credentials through the canonical credential control plane, and writes the
authoritative receipts to the governed store. Postiz and n8n are execution
infrastructure only.

Scope (2026-11 pilot): read-only health/connectivity, a deliberate failure
probe, account/capability discovery against Nexus bindings
(configs/postiz_account_bindings.json), and a DRAFT-only certification (Postiz
never starts its publish workflow for state DRAFT). There is intentionally NO
publish method here; live publishing stays on
the owner-approved bounded publishers until a governed Postiz publish path is
approved.

Flow:  Nexus -> (receipt REQUESTED) -> n8n webhook -> Postiz -> n8n -> Nexus
       -> (receipt COMPLETED/FAILED)
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT / "scripts", ROOT / "scripts" / "distribution"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from nexus_agent_platform import credential_control_plane as ccp  # noqa: E402
from nexus_agent_platform.governed import persistence  # noqa: E402
from nexus_agent_platform.social_provider_router import provider_route  # noqa: E402

POSTIZ_CREDENTIAL_ID = "credential.postiz.nexus_lab.prod.v1"
N8N_CREDENTIAL_ID = "credential.n8n.nexus_control.prod.v1"
POSTIZ_BASE = "http://nexus-app-services.tailb1e262.ts.net:4007/api"
N8N_BASE = "http://nexus-app-services.tailb1e262.ts.net:5678"
N8N_CERT_WEBHOOK = N8N_BASE + "/webhook/nexus-postiz-certification"
LAB_BUSINESS_ID = "nexus_social_lab"
TEST_VENTURE_ID = "test_nexus_internal"
RECEIPTS = "distribution_provider_receipts"
ALLOWED_ACTIONS = ("health_check", "invalid_endpoint_test")
BINDINGS_PATH = ROOT / "configs" / "postiz_account_bindings.json"
PRIORITY_PROVIDERS = ("facebook", "instagram", "youtube", "tiktok", "linkedin", "linkedin-page")


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def resolve_component(credential_id: str, component: str) -> str:
    """Canonical resolver path; the value is never left in the process env."""
    entry = ccp.registry_entry(credential_id)
    res = ccp.resolve(credential_id)
    if res.get("result") != "AVAILABLE":
        raise RuntimeError(f"CREDENTIAL_NOT_AVAILABLE:{credential_id}")
    alias = entry["canonical_aliases"][component]
    before = os.environ.get(alias)
    try:
        ccp.apply_to_process(credential_id)
        value = os.environ.get(alias, "")
    finally:
        for name in entry["canonical_aliases"].values():
            os.environ.pop(name, None)
        if before is not None:
            os.environ[alias] = before
    if not value:
        raise RuntimeError(f"CREDENTIAL_COMPONENT_MISSING:{credential_id}:{component}")
    return value


def _http(method: str, url: str, headers: Dict[str, str], body: Optional[bytes] = None,
          timeout: int = 30) -> Tuple[Optional[int], Any]:
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read() or b"{}"
            return r.status, json.loads(raw)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except Exception:
            return e.code, {}
    except Exception as e:  # transport failure: no secret or message text persisted
        return None, {"transport_error": type(e).__name__}


def lab_route() -> Dict[str, Any]:
    return provider_route(business_id=LAB_BUSINESS_ID, platform="POSTIZ_LAB", account_id="postiz-org-nexus-social-lab",
                          primary="POSTIZ", secondary="NATIVE", native="NATIVE", channel_environment="LAB")


def _receipt(**fields: Any) -> Dict[str, Any]:
    rec = {"id": fields.get("receipt_id") or "prvrcpt_" + uuid.uuid4().hex, "recorded_at": _now(),
           "authority": "NEXUS", "live_publish": False, **fields}
    persistence.append_record(RECEIPTS, rec)
    return rec


# Provider settings Postiz requires on a post (v2.25.3 DTOs). Instagram needs
# post_type; "post" = a feed post (never a Reel/story) - drafts never publish.
DRAFT_PROVIDER_SETTINGS: Dict[str, Dict[str, Any]] = {
    "instagram": {"post_type": "post", "collaborators": []},
    # TikTok: inbox-upload method (never DIRECT_POST), private, every interaction
    # toggle off. A Postiz DRAFT never reaches TikTok; these only satisfy the DTO.
    "tiktok": {"title": "", "privacy_level": "SELF_ONLY", "content_posting_method": "UPLOAD", "duet": False,
               "stitch": False, "comment": False, "autoAddMusic": "no", "brand_content_toggle": False,
               "brand_organic_toggle": False, "video_made_with_ai": False},
}


class PostizAdapter:
    """Direct Nexus -> Postiz read-only health (used by Systems/diagnostics)."""

    def __init__(self, http: Callable = _http, key_provider: Callable[[], str] = lambda: resolve_component(POSTIZ_CREDENTIAL_ID, "api_key")):
        self._http = http
        self._key = key_provider

    def health(self) -> Dict[str, Any]:
        key = self._key()
        h = {"Authorization": key}
        s1, b1 = self._http("GET", POSTIZ_BASE + "/public/v1/is-connected", h, timeout=15)
        s2, b2 = self._http("GET", POSTIZ_BASE + "/public/v1/integrations", h, timeout=15)
        del key
        integrations = b2 if isinstance(b2, list) else []
        return {"provider": "POSTIZ", "api_http_status": s1, "api_connected": s1 == 200,
                "integrations_http_status": s2, "connected_social_integrations": len(integrations),
                "execution": "READY" if s1 == 200 and integrations else ("BLOCKED_BY_AUTH" if s1 == 200 else "UNAVAILABLE"),
                "health": "HEALTHY" if s1 == 200 and s2 == 200 else "DEGRADED"}

    # ---- governed, non-live certification surface (2026-11-13) ----------
    def _get(self, path: str, timeout: int = 15) -> Tuple[Optional[int], Any]:
        key = self._key()
        try:
            return self._http("GET", POSTIZ_BASE + path, {"Authorization": key}, timeout=timeout)
        finally:
            del key

    def discover_accounts(self, bindings_doc: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Read Postiz integrations and classify each against Nexus bindings.
        Postiz grouping (customers) is never treated as venture truth."""
        status, body = self._get("/public/v1/integrations")
        integrations = body if status == 200 and isinstance(body, list) else []
        result = classify_integrations(integrations, bindings_doc or load_bindings())
        return _receipt(state="COMPLETED" if status == 200 else "FAILED", action="account_discovery",
                        provider="POSTIZ", provider_route=lab_route(), postiz_http_status=status, **result)

    def capability_discovery(self, providers: Tuple[str, ...] = PRIORITY_PROVIDERS) -> Dict[str, Any]:
        """Per provider: allowed in this build, app credentials configured, and
        whether the OAuth redirect is HTTPS on Postiz's own origin. The
        generated auth URL itself is discarded (it carries a one-time state)."""
        caps: Dict[str, Any] = {}
        for provider in providers:
            status, body = self._get(f"/public/v1/social/{provider}")
            url = body.get("url") if status == 200 and isinstance(body, dict) else None
            caps[provider] = describe_auth_url(provider, status, url)
            del url
        ready = [p for p, c in caps.items() if c["oauth_ready"]]
        return _receipt(state="COMPLETED", action="capability_discovery", provider="POSTIZ",
                        provider_route=lab_route(), capabilities=caps, oauth_ready_providers=ready)

    def create_certification_draft(self, channel_account_id: str, venture_id: str, text: str, *,
                                   bindings_doc: Optional[Dict[str, Any]] = None, cleanup: bool = True,
                                   request_id: Optional[str] = None,
                                   internal_ids: Optional[Callable[[], list]] = None) -> Dict[str, Any]:
        """Nexus -> router -> Postiz DRAFT (state DRAFT never starts the Postiz
        publish workflow) -> readback -> delete -> Nexus receipts.
        Fails closed unless the account is bound, verified, in-venture, and the
        bound integration's platform account id (Postiz DB, read-only) is the
        binding's expected_external_id. Writes per-stage receipts
        (create/readback/delete); delete always runs once a draft exists and
        is verified by a second readback."""
        request_id = request_id or "nxreq_" + uuid.uuid4().hex[:20]
        doc = bindings_doc or load_bindings()
        binding = next((b for b in doc["bindings"] if b["channel_account_id"] == channel_account_id), None)
        route = provider_route(business_id=LAB_BUSINESS_ID, platform=(binding or {}).get("platform", "UNKNOWN"),
                               account_id=channel_account_id, primary="POSTIZ", secondary="NATIVE",
                               native="NATIVE", channel_environment="LAB")
        base = dict(request_id=request_id, action="certification_draft", provider="POSTIZ", provider_route=route,
                    channel_account_id=channel_account_id, venture_id=venture_id)
        _receipt(state="REQUESTED", **base)
        reason = _draft_block_reason(binding, venture_id, text)
        live = self.discover_accounts(doc) if reason is None else None
        if reason is None:
            row = next((a for a in live["accounts"] if a["postiz_integration_id"] == binding["postiz_integration_id"]), None)
            if not row or not row["usable"]:
                reason = f"POSTIZ_INTEGRATION_NOT_USABLE:{(row or {}).get('binding_status', 'NOT_FOUND')}"
        identity: Dict[str, Any] = {}
        if reason is None and binding.get("expected_external_id"):
            try:
                rows = (internal_ids or read_postiz_internal_ids)()
            except Exception as exc:  # noqa: BLE001 - fail closed on lookup failure
                reason = f"POSTIZ_IDENTITY_LOOKUP_FAILED:{type(exc).__name__}"
            else:
                active = _active(rows)
                db = next((r for r in active if r.get("id") == binding["postiz_integration_id"]), None)
                same_ext = [r for r in rows if r.get("internal_id") == binding["expected_external_id"]]
                identity = {"postiz_integration_id": binding["postiz_integration_id"],
                            "platform_account_id": (db or {}).get("internal_id"), "account_name": (db or {}).get("name"),
                            "username": (db or {}).get("profile") or None,
                            "expected_platform_account_id": binding["expected_external_id"],
                            "expected_username": binding.get("expected_username"),
                            "same_provider_integrations": sum(1 for r in active if r.get("provider") == binding["postiz_provider"]),
                            "rows_for_account_id": len(same_ext),
                            "stale_rows_for_account_id": sum(1 for r in same_ext if r not in active)}
                if (not db or db.get("internal_id") != binding["expected_external_id"]
                        or db.get("provider") != binding["postiz_provider"]):
                    reason = "POSTIZ_PLATFORM_IDENTITY_MISMATCH"
                elif _forbidden(db, doc):
                    reason = "POSTIZ_FORBIDDEN_IDENTITY"
                elif binding.get("expected_username") and db.get("profile") != binding["expected_username"]:
                    reason = "POSTIZ_USERNAME_MISMATCH"
                elif binding.get("expected_account_name") and db.get("name") != binding["expected_account_name"]:
                    reason = "POSTIZ_ACCOUNT_NAME_MISMATCH"
                elif identity["same_provider_integrations"] != 1 or identity["rows_for_account_id"] != 1:
                    reason = "POSTIZ_DUPLICATE_PROVIDER_INTEGRATION"
        if reason:
            return _receipt(state="BLOCKED", outcome=reason, identity=identity or None, **base)
        now = _now()
        payload = {"type": "draft", "shortLink": False, "date": now, "tags": [],
                   "posts": [{"integration": {"id": binding["postiz_integration_id"]},
                              "value": [{"content": text, "image": []}],
                              "settings": {"__type": binding["postiz_provider"],
                                           **DRAFT_PROVIDER_SETTINGS.get(binding["postiz_provider"], {})}}]}
        key = self._key()
        try:
            status, body = self._http("POST", POSTIZ_BASE + "/public/v1/posts",
                                      {"Authorization": key, "Content-Type": "application/json"},
                                      json.dumps(payload).encode(), timeout=30)
        finally:
            del key
        created = body if status in (200, 201) and isinstance(body, list) else []
        post_ids = [p.get("postId") for p in created if p.get("postId")]
        _receipt(state="COMPLETED" if post_ids else "FAILED", **{**base, "action": "certification_draft_create"},
                 postiz_http_status=status, postiz_post_ids=post_ids, type="draft")
        if not post_ids:
            return _receipt(state="FAILED", outcome=f"POSTIZ_DRAFT_CREATE_{status}", postiz_http_status=status, **base)
        from datetime import datetime, timedelta, timezone
        day = datetime.now(timezone.utc)
        window = (f"/public/v1/posts?startDate={(day - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')}"
                  f"&endDate={(day + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')}")

        def _ours(resp: Any) -> list:
            return [p for p in ((resp or {}).get("posts") or []) if isinstance(resp, dict) and p.get("id") in post_ids]

        def _integration_of(p: Dict[str, Any]) -> Any:
            i = p.get("integration")
            return i.get("id") if isinstance(i, dict) else (i or p.get("integrationId"))

        rs, states, found_integrations, deleted, remaining, readback_ok = None, [], [], [], None, False
        try:
            rs, rb = self._get(window)
            found = _ours(rb)
            states = sorted({str(p.get("state") or p.get("status") or "").upper() for p in found})
            found_integrations = sorted({str(_integration_of(p)) for p in found})
            readback_ok = (len(found) == len(post_ids) and states == ["DRAFT"]
                           and found_integrations == [binding["postiz_integration_id"]])
            _receipt(state="COMPLETED" if readback_ok else "FAILED", **{**base, "action": "certification_draft_readback"},
                     readback_http_status=rs, postiz_post_ids=post_ids, readback_states=states,
                     readback_integration_ids=found_integrations, identity=identity or None)
        finally:
            if cleanup:
                key = self._key()
                try:
                    for pid in post_ids:
                        ds, _ = self._http("DELETE", POSTIZ_BASE + f"/public/v1/posts/{pid}", {"Authorization": key}, timeout=15)
                        deleted.append({"post_id": pid, "http_status": ds})
                finally:
                    del key
                vs, vb = self._get(window)
                remaining = len(_ours(vb)) if vs == 200 else None
                _receipt(state="COMPLETED" if remaining == 0 else "FAILED", **{**base, "action": "certification_draft_delete"},
                         postiz_post_ids=post_ids, cleanup=deleted, verify_http_status=vs, remaining_after_delete=remaining)
        ok = readback_ok and (not cleanup or remaining == 0)
        return _receipt(state="COMPLETED" if ok else "FAILED",
                        outcome="POSTIZ_DRAFT_CERTIFIED_NOT_PUBLISHED" if ok else (
                            "POSTIZ_DRAFT_READBACK_MISMATCH" if not readback_ok else "POSTIZ_DRAFT_DELETE_NOT_VERIFIED"),
                        postiz_http_status=status, postiz_post_ids=post_ids, readback_http_status=rs,
                        readback_states=states, readback_integration_ids=found_integrations, identity=identity or None,
                        cleanup=deleted, remaining_after_delete=remaining,
                        postiz_integration_id=binding["postiz_integration_id"], platform=binding["platform"], **base)

    def publish(self, *a: Any, **k: Any) -> None:  # explicit guard
        raise PermissionError("POSTIZ_PUBLISH_NOT_ENABLED: LIVE_POSTIZ_PUBLISHING=BLOCKED_BY_OWNER; use the owner-approved bounded publishers")



def load_bindings(path: Path = BINDINGS_PATH) -> Dict[str, Any]:
    return json.loads(Path(path).read_text())


# No single quotes (the query is wrapped in sh -c '...'); psql -At prints NULL as empty.
_INTERNAL_ID_SQL = ('select id, "providerIdentifier", "internalId", profile, '
                    '("deletedAt" is not null), disabled, "inBetweenSteps", name from "Integration"')
_INTERNAL_ID_FIELDS = ("id", "provider", "internal_id", "profile", "deleted", "disabled", "in_between_steps", "name")


def parse_internal_id_rows(out: str) -> list:
    rows = []
    for line in out.splitlines():
        parts = line.split("|", len(_INTERNAL_ID_FIELDS) - 1)
        if len(parts) != len(_INTERNAL_ID_FIELDS):
            continue
        row = dict(zip(_INTERNAL_ID_FIELDS, parts))
        for k in ("deleted", "disabled", "in_between_steps"):
            row[k] = row[k] == "t"
        rows.append(row)
    return rows


def _active(rows: list) -> list:
    return [r for r in rows if not r.get("deleted") and not r.get("disabled") and not r.get("in_between_steps")]


def read_postiz_internal_ids() -> list:
    """Read-only lookup of every Postiz integration (including deleted /
    disabled / unfinished rows, flagged) -> platform account id + username."""
    import subprocess
    cmd = ("docker exec postiz-postgres sh -c 'psql -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\" -At -F \"|\" -c "
           + json.dumps(_INTERNAL_ID_SQL) + "'")
    out = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "nexus-contabo-ts", cmd],
                         capture_output=True, text=True, timeout=60, check=True, stdin=subprocess.DEVNULL).stdout
    return parse_internal_id_rows(out)


def verify_bindings(rows: list, doc: Dict[str, Any], *, path: Optional[Path] = BINDINGS_PATH) -> Dict[str, Any]:
    """Bind a Postiz integration to a Nexus account only on an exact
    (provider, platform account id) match with the expected external id.
    Everything else stays unbound (quarantined) for owner review."""
    changes, unmatched = [], []
    for row in _active(rows):
        b = next((b for b in doc["bindings"] if b.get("expected_external_id")
                  and b["postiz_provider"] == row["provider"] and b["expected_external_id"] == row["internal_id"]), None)
        if _forbidden(row, doc):
            unmatched.append({**row, "reason": "FORBIDDEN_IDENTITY"})
        elif b:
            b["postiz_integration_id"], b["verified_internal_id_at"] = row["id"], _now()
            changes.append({"channel_account_id": b["channel_account_id"], "postiz_integration_id": row["id"]})
        else:
            unmatched.append({**row, "reason": "NO_EXACT_NEXUS_BINDING"})
    if path is not None and changes:
        Path(path).write_text(json.dumps(doc, indent=2) + "\n")
    return _receipt(state="COMPLETED", action="binding_verification", provider="POSTIZ",
                    bound=changes, unbound=[{k: u.get(k) for k in ("id", "provider", "name", "reason")} for u in unmatched])


def _forbidden(integration: Dict[str, Any], doc: Dict[str, Any]) -> Optional[str]:
    """Forbidden by platform account id (exact) or by name/username pattern."""
    text = " ".join(str(integration.get(k) or "") for k in ("name", "profile")).lower()
    ext = str(integration.get("internal_id") or "")
    for rule in doc.get("forbidden_identities", []):
        if (ext and ext in rule.get("forbidden_external_ids", [])) or any(p in text for p in rule["name_patterns"]):
            return rule["venture_id"]
    return None


def classify_integrations(integrations: list, doc: Dict[str, Any]) -> Dict[str, Any]:
    by_id = {b["postiz_integration_id"]: b for b in doc["bindings"] if b.get("postiz_integration_id")}
    accounts = []
    for i in integrations:
        binding = by_id.get(i.get("id"))
        forbidden_venture = _forbidden(i, doc)
        if forbidden_venture:
            status = "ISOLATION_VIOLATION"
        elif binding and binding.get("verified_internal_id_at") and i.get("identifier") == binding["postiz_provider"] \
                and not i.get("disabled"):
            status = "BOUND_VERIFIED"
        elif binding:
            status = "BOUND_UNVERIFIED"
        else:
            status = "UNBOUND_QUARANTINED"
        accounts.append({"postiz_integration_id": i.get("id"), "postiz_provider": i.get("identifier"),
                         "name": i.get("name"), "profile": i.get("profile"), "disabled": bool(i.get("disabled")),
                         "binding_status": status, "usable": status == "BOUND_VERIFIED",
                         "channel_account_id": (binding or {}).get("channel_account_id"),
                         "venture_id": (binding or {}).get("venture_id"),
                         "forbidden_venture": forbidden_venture})
    violations = [a for a in accounts if a["binding_status"] == "ISOLATION_VIOLATION"]
    return {"connected_integrations": len(accounts), "accounts": accounts,
            "venture_isolation": "FAIL" if violations else "PASS",
            "usable_accounts": [a["channel_account_id"] for a in accounts if a["usable"]]}


def describe_auth_url(provider: str, status: Optional[int], url: Optional[str]) -> Dict[str, Any]:
    from urllib.parse import parse_qs, urlsplit
    if status != 200 or not url:
        return {"allowed_in_build": status not in (400,), "http_status": status, "app_configured": False,
                "redirect_https": None, "third_party_redirect": None, "oauth_ready": False}
    q = parse_qs(urlsplit(url).query)
    client = (q.get("client_id") or q.get("client_key") or q.get("app_id") or [""])[0]
    redirect = (q.get("redirect_uri") or [""])[0]
    configured = bool(client) and client not in ("undefined", "null")
    https = redirect.startswith("https://")
    third_party = "redirectmeto.com" in redirect
    raw_scope = (q.get("scope") or [""])[0]
    scopes = sorted(x for x in raw_scope.replace(" ", ",").split(",") if x)
    return {"allowed_in_build": True, "http_status": status, "app_configured": configured,
            "redirect_https": https, "third_party_redirect": third_party,
            "redirect_origin": urlsplit(redirect).netloc or None,
            "redirect_uri": redirect.split("?", 1)[0] or None,
            "requested_scopes": scopes,
            "publish_scope_requested": "video.publish" in scopes,
            "oauth_ready": configured and https and not third_party}


def _draft_block_reason(binding: Optional[Dict[str, Any]], venture_id: str, text: str) -> Optional[str]:
    if binding is None:
        return "CHANNEL_ACCOUNT_NOT_BOUND_TO_POSTIZ"
    scope = binding.get("venture_scope") or [binding.get("venture_id")]
    if venture_id not in scope:
        return "VENTURE_ACCOUNT_SCOPE_MISMATCH"
    if not binding.get("postiz_integration_id") or not binding.get("verified_internal_id_at"):
        return "POSTIZ_BINDING_NOT_VERIFIED"
    if not text or len(text) > 500:
        return "CERTIFICATION_TEXT_INVALID"
    return None


def run_n8n_certification(action: str = "health_check", *, http: Callable = _http,
                          token_provider: Callable[[], str] = lambda: resolve_component(N8N_CREDENTIAL_ID, "webhook_token"),
                          request_id: Optional[str] = None) -> Dict[str, Any]:
    """Nexus -> n8n -> Postiz -> n8n -> Nexus, with Nexus-owned receipts."""
    if action not in ALLOWED_ACTIONS:
        raise ValueError(f"ACTION_NOT_ALLOWED:{action}")
    request_id = request_id or "nxreq_" + uuid.uuid4().hex[:20]
    route = lab_route()
    _receipt(request_id=request_id, state="REQUESTED", venture_id=TEST_VENTURE_ID, business_id=LAB_BUSINESS_ID,
             workflow="postiz_connectivity_certification", action=action, provider_route=route,
             orchestrator="N8N", provider="POSTIZ")
    payload = {"request_id": request_id, "venture_id": TEST_VENTURE_ID, "workflow": "postiz_connectivity_certification",
               "action": action}
    token = token_provider()
    status, body = http("POST", N8N_CERT_WEBHOOK, {"Content-Type": "application/json", "X-Nexus-Webhook-Token": token},
                        json.dumps(payload).encode(), timeout=60)
    del token
    body = body if isinstance(body, dict) else {}
    echoed = body.get("request_id") == request_id
    if status is None:
        state, outcome = "FAILED", "N8N_CONNECTION_UNAVAILABLE"
    elif status == 200 and body.get("ok") is True and echoed:
        state, outcome = "COMPLETED", "POSTIZ_REACHED_VIA_N8N"
    elif status in (502, 422) and echoed:
        state, outcome = "FAILED", "PROVIDER_FAILURE_REPORTED_BY_N8N" if status == 502 else "REJECTED_BY_N8N_VALIDATION"
    else:
        state, outcome = "FAILED", f"UNEXPECTED_N8N_RESPONSE_{status}"
    return _receipt(request_id=request_id, state=state, outcome=outcome, venture_id=TEST_VENTURE_ID,
                    business_id=LAB_BUSINESS_ID, workflow="postiz_connectivity_certification", action=action,
                    n8n_http_status=status, request_id_echoed=echoed,
                    n8n_execution_id=body.get("n8n_execution_id"), n8n_workflow_id=body.get("n8n_workflow_id"),
                    postiz_http_status=body.get("postiz_http_status"), postiz_connected=body.get("postiz_connected"),
                    provider_live_publish=body.get("live_publish"))


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "n8n-health"
    if cmd == "postiz-health":
        print(json.dumps(PostizAdapter().health(), indent=2))
    elif cmd == "n8n-health":
        print(json.dumps(run_n8n_certification("health_check"), indent=2))
    elif cmd == "discover-accounts":
        print(json.dumps(PostizAdapter().discover_accounts(), indent=2))
    elif cmd == "capability-discovery":
        print(json.dumps(PostizAdapter().capability_discovery(), indent=2))
    elif cmd == "verify-bindings":
        print(json.dumps(verify_bindings(read_postiz_internal_ids(), load_bindings()), indent=2))
    elif cmd == "n8n-failure-test":
        print(json.dumps(run_n8n_certification("invalid_endpoint_test"), indent=2))
    elif cmd == "certify-draft" and len(argv) == 4:
        # Draft-only round trip (never queued/scheduled/published); text is fixed.
        print(json.dumps(PostizAdapter().create_certification_draft(
            argv[2], argv[3], "Nexus Postiz draft certification - not for publishing"), indent=2))
    else:
        print("usage: postiz_provider_adapter.py postiz-health|discover-accounts|capability-discovery|verify-bindings|"
              "n8n-health|n8n-failure-test|certify-draft <channel_account_id> <venture_id>")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
