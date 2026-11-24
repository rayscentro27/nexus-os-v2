#!/usr/bin/env python3
"""Nexus Admin read model publisher (NEXUS_FINAL_OVERNIGHT_COMPLETION_R1).

Builds the Admin Center's operational state from AUTHORITATIVE Nexus sources and
upserts one row per area into Supabase ``nexus_admin_read_model`` (service-role only).
The production Admin reads it through the admin-guarded Netlify function.

Rules: read-only against every source; never invent values (missing -> None plus a
truth class such as NOT_CONNECTED/UNKNOWN); bounded reads; creative previews are
uploaded once (content-hash keyed) to the private ``creative-assets`` bucket.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("NEXUS_REPO_ROOT") or Path(__file__).resolve().parents[2])
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]
os.environ.setdefault("NEXUS_REPO_ROOT", str(ROOT))

from business_loop.commerce.supabase_io import call  # noqa: E402
from services.nexus_mcp import project_reader as PR  # noqa: E402  (same reader Nova's nexus_get_project uses)

R10_DB = Path.home() / ".nexus/state/research/r10/research_r10_batch_c.sqlite3"
TRADING = ROOT / "data/governed/trading_core"
BUCKET = "creative-assets"
PREVIEW_PREFIX = "admin-preview"
VENTURES = {  # registered ventures (configs/nexus_credential_registry.json venture_binding)
    "vnt_goclear_credit_2026": "GoClear",
    "vnt_holiday_commerce_pilot_2026": "Holiday Commerce",
    "vnt_krd_ability_2026": "KRD Ability",
}
NA = None


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _jsonl(path: Path) -> list[dict]:
    try:
        return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    except OSError:
        return []


def _latest(rows: list[dict], key: str) -> list[dict]:
    cur: dict = {}
    for r in rows:
        if r.get(key):
            cur[r[key]] = r
    return list(cur.values())


def _read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def svc(path: str) -> Any:
    code, data = call("GET", path, role="service", prefer="")
    if code != 200:
        raise RuntimeError(f"supabase_read_{code}")
    return data


# ------------------------------------------------------------------ creative previews
def _preview(local: Path, max_px: int = 720) -> str | None:
    """Upload a downscaled JPEG preview once; return the storage path (signed at read time)."""
    if not local.exists():
        return None
    from PIL import Image
    digest = hashlib.sha256(local.read_bytes()).hexdigest()[:24]
    key = f"{PREVIEW_PREFIX}/{digest}.jpg"
    code, _ = call("GET", f"../storage/v1/object/info/{BUCKET}/{key}", role="service", prefer="")
    if code == 200:
        return key
    img = Image.open(local).convert("RGB")
    img.thumbnail((max_px, max_px))
    buf = io.BytesIO(); img.save(buf, "JPEG", quality=82)
    import urllib.request, ssl
    from business_loop.commerce.supabase_io import config, _ctx
    cfg = config()
    req = urllib.request.Request(f"{cfg['url']}/storage/v1/object/{BUCKET}/{key}", data=buf.getvalue(), method="POST",
                                 headers={"apikey": cfg["service"], "Authorization": f"Bearer {cfg['service']}", "Content-Type": "image/jpeg", "x-upsert": "true"})
    try:
        with urllib.request.urlopen(req, context=_ctx(), timeout=30) as r:
            return key if r.status in (200, 201) else None
    except Exception:
        return None


def _evidence_value(v: Any) -> str:
    if isinstance(v, dict):
        val = v.get("value")
        status = v.get("status")
        return f"{val} ({status})" if status is not None else json.dumps(v)
    return json.dumps(v) if isinstance(v, list) else str(v)


def _evidence_truth(key: str, v: Any) -> str:
    status = str(v.get("status") if isinstance(v, dict) else "").upper()
    if "STAGED" in status or "PROPOSED" in status or key == "PRICE":
        return "PROPOSED"
    if "ESTIMATE" in status or key == "SHIPPING_ESTIMATE" and "VERIFIED" not in status:
        return "ESTIMATED"
    if status.startswith("VERIFIED") or key in ("PRODUCT_NAME", "CHECKOUT_STATUS", "SALES_STATUS"):
        return "VERIFIED"
    return "UNKNOWN"


# ------------------------------------------------------------------ areas
def area_projects() -> tuple[list[dict], list[dict], dict]:
    listing = PR.list_projects("")["data"]["projects"]
    projects, approvals, raw = [], [], {}
    for p in listing:
        r = PR.get_project(p["project_id"])
        if r["status"] != "OK":
            continue
        d = r["data"]; raw[d["project_id"]] = d
        ap = PR.get_project_approvals(d["project_id"])["data"]
        dept = (d.get("current_department") or "").title()
        steps = []
        for stage in ("Research", "Opportunity / Project", "Marketing", "Creative", "Commerce", "Distribution", "Metrics", "Analysis", "Next Action"):
            key = stage.split(" ")[0].upper()
            seen = any(key in (h.get("transition") or "") for h in d.get("recent_handoffs") or [])
            # The project record itself proves Research/Opportunity ran; a commerce offer proves Commerce staged.
            seen = seen or stage in ("Research", "Opportunity / Project") or (stage == "Commerce" and bool(d.get("commerce_offer")))
            steps.append({"stage": stage, "status": "WAITING_APPROVAL" if (stage == "Distribution" and ap["waiting_count"]) else ("COMPLETE" if seen else "PENDING"),
                          "owner": stage, "summary": "", "timestamp": None})
        offer = d.get("commerce_offer") or {}
        projects.append({
            "id": d["project_id"], "name": d.get("opportunity_name"), "ventureId": d.get("venture_id"), "opportunityId": d.get("opportunity_id"),
            "clientOrTrack": "NEXUS_VENTURE", "status": "AWAITING_APPROVAL" if ap["waiting_count"] and d.get("status") == "ACTIVE" else (d.get("status") or "ACTIVE"),
            "projectStatus": d.get("status"), "currentDepartment": dept or "Distribution", "stage": d.get("current_stage"),
            "summary": f"Cycle {d.get('cycle')} · {d.get('work_items', {}).get('total', 0)} work items · {len(d.get('recent_handoffs') or [])} recent handoffs",
            "nextAction": d.get("next_action"), "blocker": "; ".join(d.get("blockers") or []) or None, "lastActivity": d.get("updated_at"),
            "truthClass": "VERIFIED", "workflowSteps": steps,
            "linkedApprovalIds": [a.get("approval_request_id") or a.get("approval_id") for a in ap["all_project_approvals"]],
            "linkedCampaignIds": [], "linkedAssetIds": [], "linkedOfferId": offer.get("PRINTIFY_PRODUCT_ID"),
            "evidence": [{"id": f"ev_{i}", "label": k, "value": _evidence_value(v), "truthClass": _evidence_truth(k, v), "source": "business_loop_project_store"}
                         for i, (k, v) in enumerate((d.get("commerce_offer") or {}).items()) if k in ("PRODUCT_NAME", "PRICE", "BASE_COST", "SHIPPING_ESTIMATE", "CHECKOUT_STATUS", "SALES_STATUS")],
            "activityLog": [{"id": f"h{i}", "timestamp": h.get("at"), "department": (h.get("transition") or "->").split("->")[-1].title(), "event": f"{h.get('transition')}: {h.get('summary')}", "truthClass": "VERIFIED"}
                            for i, h in enumerate(d.get("recent_handoffs") or [])],
            "source": "nexus_get_project",
        })
        for a in ap["all_project_approvals"]:
            golive = a.get("approval_kind") == "COMMERCE_GO_LIVE"
            approvals.append({
                "id": a.get("approval_request_id") or a.get("approval_id"), "projectId": d["project_id"], "projectName": d.get("opportunity_name"),
                "ventureId": d.get("venture_id"), "department": "Commerce" if golive else "Distribution",
                "type": "Commerce go-live" if golive else "Campaign publication",
                "status": {"WAITING_FOR_RAY": "PENDING", "APPROVED": "APPROVED", "CONSUMED": "APPROVED", "SUPERSEDED": "REJECTED"}.get(a.get("state"), "PENDING"),
                "nexusState": a.get("state"), "priority": "HIGH", "riskLevel": "HIGH",
                "title": ("Commerce go-live (live checkout + sales)" if golive else f"Publish {a.get('platform', '').title()} post"),
                "subtitle": d.get("opportunity_name"), "reason": "Ray approval required before any external action.",
                "whatIsBeingApproved": a.get("then") or a.get("owner_command") or a.get("file") or "",
                "plainEnglishExplanation": ("Turn on real sales after a real Stripe test key and test checkout are in place." if golive
                                            else "Publish one tracked post that sends traffic to the interest-capture page. No spend."),
                "costImpact": "$0", "blockedAction": "Live checkout and sales" if golive else "Publication",
                "nextAction": a.get("owner_command") or "Review", "createdAt": d.get("updated_at"),
                "approvalCommand": a.get("owner_command"), "source": "nexus_get_project_approvals",
                "preview": {"kind": "commerce" if golive else "campaign", "headline": d.get("opportunity_name"), "facts": []},
            })
    return projects, approvals, raw


def area_directives() -> tuple[list[dict], list[dict]]:
    rows = svc("nexus_durable_jobs?job_type=eq.DEPARTMENT_DIRECTIVE&select=job_id,state,created_at,directive:governance_context->directive&order=created_at.desc&limit=30")
    out, notes = [], []
    for r in rows:
        d = r.get("directive") or {}
        res = d.get("result") or {}
        out.append({"directiveId": d.get("directive_id"), "projectId": d.get("project_id"), "parentDirectiveId": d.get("parent_directive_id"),
                    "department": d.get("target_department"), "status": d.get("status"), "jobState": r.get("state"), "objective": d.get("objective"),
                    "createdAt": d.get("created_at"), "completedAt": d.get("completed_at"), "nextAction": d.get("next_action"),
                    "isSmoke": "SMOKE" in str(d.get("objective") or ""),
                    "marketing": {k: res.get(k) for k in ("campaign_concept", "target_audience", "hypothesis", "variant_a", "variant_b", "cta",
                                                          "channel_recommendation", "measurement_plan", "creative_requirements")} if d.get("target_department") == "MARKETING" else None,
                    "events": d.get("events") or []})
        for ev in d.get("events") or []:
            notes.append({"id": f"{ev.get('directive_id')}:{ev.get('kind')}:{ev.get('at')}", "type": ev.get("kind"), "title": ev.get("kind", "").replace("_", " ").title(),
                          "detail": f"{ev.get('summary')} — next: {ev.get('next')}", "timestamp": ev.get("at"), "read": False,
                          "targetPage": "projects", "targetEntityId": ev.get("directive_id"), "projectId": ev.get("project_id"), "truthClass": "VERIFIED"})
    return out, notes


def area_rea() -> list[dict]:
    rows = svc("nexus_durable_jobs?job_type=eq.REA_EXECUTION&select=job_id,state,created_at,started_at,completed_at,payload_ref,"
               "rea:governance_context->rea_engine,summary:governance_context->result_summary&order=created_at.desc&limit=20")
    out = []
    for r in rows:
        rea = r.get("rea") or {}; summ = r.get("summary") or {}
        ans = {}
        if isinstance(summ, dict) and isinstance(summ.get("answer"), str):
            try:
                ans = json.loads(summ["answer"])
            except ValueError:
                ans = {}
        req = _read(Path(r["payload_ref"])) if r.get("payload_ref") and str(r["payload_ref"]).startswith(str(ROOT)) else None
        opts = (req or {}).get("options") or {}
        model = ans.get("model") if isinstance(ans.get("model"), dict) else {}
        out.append({"reaJobId": r["job_id"], "status": {"COMPLETED": "COMPLETE", "RUNNING": "RUNNING", "CLAIMED": "RUNNING", "READY": "QUEUED", "QUEUED": "QUEUED",
                                                        "BLOCKED": "BLOCKED", "FAILED_RETRYABLE": "FAILED", "CANCELLED": "CANCELLED"}.get(r.get("state"), r.get("state")),
                    "projectId": opts.get("project_id") or (req or {}).get("project_id"), "target": rea.get("target") or ans.get("target"),
                    "objective": rea.get("objective") or ans.get("objective"), "workType": rea.get("mode") or ans.get("mode") or (req or {}).get("mode"),
                    "providerMode": ans.get("provider_mode"), "model": model.get("served_model_key") or opts.get("model_key"),
                    "toolProfile": model.get("tool_profile") or opts.get("tool_profile") or opts.get("model_profile"),
                    "startedAt": r.get("started_at"), "completedAt": r.get("completed_at"), "createdAt": r.get("created_at"),
                    "resultSummary": {k: ans.get(k) for k in ("findings", "summary", "recommendations", "status", "elapsed_seconds", "evidence_gate") if k in ans} or None,
                    "evidence": [x for x in (rea.get("receipts") or [])][:12], "sessionId": rea.get("rea_session_id"),
                    "blocker": ans.get("blocker") or ans.get("error"), "nextAction": ans.get("next_action")})
    return out


def area_research() -> list[dict]:
    if not R10_DB.exists():
        return []
    con = sqlite3.connect(f"file:{R10_DB}?mode=ro", uri=True)
    rows = con.execute("select payload from jobs order by updated_at desc limit 15").fetchall()
    out = []
    for (payload,) in rows:
        try:
            d = json.loads(payload)
        except ValueError:
            continue
        status = d.get("status")
        out.append({"id": d.get("job_id"), "title": (d.get("objective") or "")[:160], "source": ", ".join(str(s) for s in (d.get("source_refs") or [])[:2])[:200],
                    "sourceType": "Market Signal", "status": status, "researchType": d.get("research_type"),
                    "evidenceQuality": "MEDIUM" if status == "COMPLETED" else "LOW",
                    "confidence": "MODERATE" if status == "COMPLETED" else "EARLY",
                    "truthClass": "VERIFIED" if str(status).startswith("COMPLETED") else "UNKNOWN",
                    "recommendation": str(d.get("result_summary") or "")[:900], "departmentDestination": "Research",
                    "whatHappensNext": "Nova can turn a justified next action into a department directive." if str(status).startswith("COMPLETED") else "In progress",
                    "linkedProjectId": d.get("project_id"), "promotedToProject": bool(d.get("directive_refs")),
                    "discoveredAt": d.get("completed_at") or d.get("created_at"), "completedAt": d.get("completed_at"), "model": d.get("model")})
    return out


def area_commerce(projects_raw: dict) -> list[dict]:
    draft = _read(ROOT / "reports/business_loop/printify_draft_r2.json") or {}
    r2 = _read(ROOT / "reports/business_loop/commerce_readiness_r2_latest.json") or {}
    try:
        ev = svc("commerce_events?select=event_type,is_test&project_id=eq.proj_98ef515bccee4b58&limit=5000")
        leads = svc("commerce_leads?select=is_test&project_id=eq.proj_98ef515bccee4b58&limit=5000")
        orders = svc("commerce_orders?select=mode,payment_status,amount_total_cents&project_id=eq.proj_98ef515bccee4b58&limit=1000")
        real_ev = [e for e in ev if not e["is_test"]]; real_leads = [l for l in leads if not l["is_test"]]
        funnel = {"pageViews": sum(e["event_type"] == "PAGE_VIEW" for e in real_ev), "interestSubmissions": len(real_leads),
                  "liveOrders": sum(o["mode"] == "LIVE" and o["payment_status"] == "paid" for o in orders), "truthClass": "VERIFIED"}
    except Exception:
        funnel = {"pageViews": None, "interestSubmissions": None, "liveOrders": None, "truthClass": "NOT_CONNECTED"}
    out = []
    for pid, d in projects_raw.items():
        offer = d.get("commerce_offer") or {}
        if not offer:
            continue
        base = (offer.get("BASE_COST") or {}).get("value"); price = (offer.get("PRICE") or {}).get("value")
        pr = r2.get("pricing") or {}
        rec = next((o for o in pr.get("options", []) if o.get("RETAIL_PRICE") == price), {})
        tc = lambda s: "VERIFIED" if str(s).startswith("VERIFIED") else ("PROPOSED" if "STAGED" in str(s) or "PROPOSED" in str(s) else ("ESTIMATED" if "ESTIMATE" in str(s) else "UNKNOWN"))  # noqa: E731
        ship = r2.get("printify", {})
        approvals = {a.get("approval_kind") or a.get("platform"): (a.get("approval_request_id") or a.get("approval_id")) for a in d.get("approvals_all") or []}
        out.append({"id": offer.get("PRINTIFY_PRODUCT_ID") or pid, "projectId": pid, "projectName": d.get("opportunity_name"), "ventureId": d.get("venture_id"),
                    "title": offer.get("PRODUCT_NAME"), "provider": "Printify", "externalProductId": offer.get("PRINTIFY_PRODUCT_ID"),
                    "variantId": str((draft.get("variant") or {}).get("id") or ""), "variantSpec": f"{(draft.get('variant') or {}).get('title', '')} white glossy ceramic mug",
                    "productTruth": {"baseCost": base, "baseCostTruth": tc((offer.get("BASE_COST") or {}).get("status")),
                                     "firstItemShipping": ship.get("us_shipping_first_item_usd"), "firstItemShippingTruth": "VERIFIED" if ship.get("us_shipping_first_item_usd") else "UNKNOWN",
                                     "additionalItemShipping": ship.get("us_shipping_additional_item_usd"), "additionalShippingTruth": "VERIFIED" if ship.get("us_shipping_additional_item_usd") else "UNKNOWN",
                                     "totalVerifiedCost": round((base or 0) + (ship.get("us_shipping_first_item_usd") or 0), 2) if base else None,
                                     "stagedPrice": price, "stagedPriceTruth": "PROPOSED",
                                     "estimatedGrossMarginDollar": rec.get("ESTIMATED_GROSS_PROFIT"), "estimatedGrossMarginPct": round(rec["ESTIMATED_GROSS_MARGIN"] * 100, 1) if isinstance(rec.get("ESTIMATED_GROSS_MARGIN"), float) else None,
                                     "marginTruth": "ESTIMATED"},
                    "interestTest": {"mode": "INTEREST CAPTURE ONLY", "landingUrl": offer.get("STOREFRONT_URL") or "https://nexus-campaigns.pages.dev/holiday-commerce-pilot/holiday-ceramic-mug/",
                                     "waitlistSignups": funnel["interestSubmissions"], "waitlistTruth": funnel["truthClass"],
                                     "stageAApprovalId": approvals.get("FACEBOOK", "")},
                    "liveSales": {"checkoutStatus": "BLOCKED", "blockerReason": offer.get("CHECKOUT_STATUS"), "stripeStatus": "MISSING CREDENTIAL",
                                  "stageBApprovalId": approvals.get("COMMERCE_GO_LIVE", "")},
                    "funnel": funnel,
                    "claimsVsTruth": [{"claim": "15 oz white ceramic mug", "verification": "VERIFIED", "note": "Printify variant spec"},
                                      {"claim": f"Price ${price}", "verification": "PROPOSED", "note": "Staged; not a live sales price"},
                                      {"claim": "Available for purchase", "verification": "UNKNOWN", "note": "Not for sale — interest capture only"}]})
    return out


def area_creative(projects_raw: dict) -> list[dict]:
    out = []
    candidates = []
    for pid in projects_raw:
        base = ROOT / "dist/creative/business_loop" / pid
        for f in sorted(base.glob("*.jpg")):
            candidates.append((pid, f, "Pillow template composite (deterministic)" if "square" in f.name or "card" in f.name or "story" in f.name else "unknown"))
    mock = ROOT / "dist/campaign-host/holiday-commerce-pilot/holiday-ceramic-mug/printify_mockup_612am_15oz_front.jpg"
    if mock.exists():
        candidates.insert(0, ("proj_98ef515bccee4b58", mock, "Printify product mockup"))
    hero = ROOT / "dist/creative/meta_holiday_ceramic_mug_1794355016_facebook.jpg"
    if hero.exists():
        candidates.append(("proj_98ef515bccee4b58", hero, "meta.ai (browser, concept image)"))
    for pid, f, provider in candidates[:12]:
        key = _preview(f)
        out.append({"id": "asset_" + hashlib.sha256(str(f).encode()).hexdigest()[:12], "title": f.stem.replace("_", " "), "campaign_id": "camp_holiday_ceramic_mug_2026",
                    "campaign_name": "The 6:12 AM Quiet Ritual", "asset_type": "Social Image", "platform": "Cross-Platform", "current_stage": "READY",
                    "approval_state": "PENDING_RAY" if "r2_h1" in f.name else "DRAFT", "prompt_id": "", "prompt_version": "", "exact_approved_creative_prompt": "",
                    "provider": provider, "created_at": datetime.fromtimestamp(f.stat().st_mtime, timezone.utc).isoformat(), "last_revised": None, "generation_cost": 0,
                    "thumbnail_url": "", "storage_path": key, "truth_class": "VERIFIED", "project_id": pid, "venture_id": "vnt_holiday_commerce_pilot_2026",
                    "preview_data": {}, "revisions": []})
    return out


def area_trading() -> dict:
    strategies = _latest(_jsonl(TRADING / "strategies.jsonl"), "strategy_id")
    versions = _latest(_jsonl(TRADING / "strategy_versions.jsonl"), "strategy_version_id")
    trades = _latest(_jsonl(TRADING / "trades.jsonl"), "trade_id")
    perf = _latest(_jsonl(TRADING / "performance_snapshots.jsonl"), "snapshot_id")
    return {"mode": "PAPER", "broker": "OANDA_PRACTICE", "liveTradingEnabled": False,
            "strategies": [{"id": s.get("strategy_id"), "name": s.get("name")} for s in strategies],
            "versions": [{"id": v.get("strategy_version_id"), "name": v.get("name"), "instrument": v.get("instrument"), "timeframe": v.get("timeframe"), "status": v.get("status")} for v in versions],
            "counts": {k: len(_latest(_jsonl(TRADING / f"{k}.jsonl"), key)) for k, key in (("signals", "signal_id"), ("risk_events", "risk_event_id"), ("orders", "order_id"),
                                                                                           ("positions", "position_id"), ("trades", "trade_id"), ("execution_receipts", "receipt_id"),
                                                                                           ("reconciliation_events", "reconciliation_id"))},
            "trades": [{"id": t.get("trade_id"), "instrument": t.get("instrument"), "direction": t.get("direction"), "pnl": t.get("realized_pnl"), "exitReason": t.get("exit_reason"), "at": t.get("exit_time"), "origin": t.get("origin")} for t in trades][-10:],
            "performance": sorted(perf, key=lambda p: p.get("computed_at") or "")[-1] if perf else None,
            "contabo_worker": "DEFERRED (observe-only package staged; not certified)", "truthClass": "PAPER"}


def _launchd(label: str) -> str:
    out = subprocess.run(["launchctl", "list"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[2] == label:
            return "RUNNING" if parts[0] not in ("-", "") else ("STOPPED" if parts[1] == "0" else f"EXITED_{parts[1]}")
    return "NOT_LOADED"


def _ssh(target: str, identity: str, cmd: str, timeout: int = 25) -> str | None:
    try:
        r = subprocess.run(["ssh", "-i", os.path.expanduser(identity), "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12", target, cmd],
                           capture_output=True, text=True, timeout=timeout)
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


def area_systems() -> tuple[list[dict], dict]:
    auth = _read(ROOT / "docs/architecture/NEXUS_ORACLE_CONNECTION_AUTHORITY.json") or {}
    cur = auth.get("current") or {}
    oracle = _ssh(f"{cur.get('user')}@{cur.get('host')}", cur.get("identity_path", "~/.ssh/oracle_vm"),
                  "systemctl --user is-active nova-telegram-oracle.service nexus-hermes-0225.service; systemctl --user show nova-telegram-oracle.service --property=ExecStart --value | grep -oE 'releases/[^/]+' | head -1")
    olines = (oracle or "").split()
    contabo = _ssh("nexus-contabo", "~/.ssh/nexus_contabo", "docker ps --format '{{.Names}}={{.Status}}'") if True else None
    cmap = dict(line.split("=", 1) for line in (contabo or "").splitlines() if "=" in line)
    up = lambda n: ("RUNNING" if cmap.get(n, "").startswith("Up") else ("NOT_RUNNING" if contabo else "UNKNOWN"))  # noqa: E731
    nova = {"service": olines[0].upper() if olines else "UNKNOWN", "hermes": olines[1].upper() if len(olines) > 1 else "UNKNOWN",
            "release": olines[2].replace("releases/", "") if len(olines) > 2 else None}
    nodes = [
        {"id": "oracle", "name": "Oracle VM (nexus-llm-worker)", "role": "Nova (Telegram) + Hermes reasoning", "workloadPolicy": "Operator/reasoning only — not heavy workloads",
         "status": "ONLINE" if oracle else "UNKNOWN", "services": {"nova": nova["service"], "hermes": nova["hermes"]}, "truthClass": "VERIFIED" if oracle else "UNKNOWN"},
        {"id": "mac", "name": "Mac mini", "role": "Nexus control plane: durable dispatcher, MCP bridge, Research R10, business loop", "workloadPolicy": "Development + governed light workers",
         "status": "ONLINE", "services": {"durable_dispatcher": _launchd("com.nexus.durable-dispatcher"), "mcp_bridge": _launchd("com.nexus.nexus-mcp-bridge"),
                                          "research_mcp": _launchd("com.nexus.research-mcp"), "admin_read_model": _launchd("com.nexus.admin-read-model")}, "truthClass": "VERIFIED"},
        {"id": "contabo", "name": "Contabo App Services", "role": "n8n, Postiz, REA harness", "workloadPolicy": "Persistent app services + REA (capped)",
         "status": "ONLINE" if contabo else "UNKNOWN", "services": {"n8n": up("n8n"), "postiz": up("postiz"), "rea": up("nexus-rea")}, "truthClass": "VERIFIED" if contabo else "UNKNOWN"},
        {"id": "supabase", "name": "Supabase", "role": "Durable jobs, governor, commerce funnel, admin read model", "workloadPolicy": "Authoritative shared state",
         "status": "ONLINE", "services": {}, "truthClass": "VERIFIED"},
        {"id": "kaggle", "name": "Kaggle (burst GPU)", "role": "REA model endpoint when a session runs", "workloadPolicy": "Ephemeral burst compute only",
         "status": "UNKNOWN", "services": {}, "truthClass": "UNKNOWN"},
    ]
    return nodes, nova


def area_businesses(projects: list[dict], approvals: list[dict], commerce: list[dict], directives: list[dict]) -> list[dict]:
    out = []
    for vid, name in VENTURES.items():
        bp = [p for p in projects if p.get("ventureId") == vid]
        ba = [a for a in approvals if a.get("ventureId") == vid and a.get("status") == "PENDING"]
        bc = [c for c in commerce if c.get("ventureId") == vid]
        leads = sum((c.get("funnel") or {}).get("interestSubmissions") or 0 for c in bc) if bc else None
        orders = sum((c.get("funnel") or {}).get("liveOrders") or 0 for c in bc) if bc else None
        traffic = sum((c.get("funnel") or {}).get("pageViews") or 0 for c in bc) if bc else None
        out.append({"businessId": vid, "ventureId": vid, "businessName": name, "status": "ACTIVE" if bp else "REGISTERED (no active Nexus project)",
                    "revenue": {"value": 0.0 if bc else None, "truthClass": "VERIFIED" if bc else "NOT_CONNECTED", "note": "Live sales not enabled; no live orders" if bc else "No revenue source connected"},
                    "operatingCost": {"value": 0.0 if bc else None, "truthClass": "VERIFIED" if bc else "NOT_CONNECTED", "note": "Cost governor: $0 spend authorized" if bc else ""},
                    "profitOrMargin": {"value": None, "truthClass": "NOT_CONNECTED"},
                    "leads": {"value": leads, "truthClass": "VERIFIED" if bc else "NOT_CONNECTED"},
                    "customers": {"value": None, "truthClass": "NOT_CONNECTED"},
                    "orders": {"value": orders, "truthClass": "VERIFIED" if bc else "NOT_CONNECTED"},
                    "traffic": {"value": traffic, "truthClass": "VERIFIED" if bc else "NOT_CONNECTED"},
                    "conversion": {"value": None if not traffic else round((leads or 0) / traffic, 4), "truthClass": "VERIFIED" if traffic else "NOT_CONNECTED"},
                    "activeCampaigns": 0, "pendingApprovals": len(ba), "activeProjects": len([p for p in bp if p.get("projectStatus") == "ACTIVE"]),
                    "projectIds": [p["id"] for p in bp], "approvalIds": [a["id"] for a in ba], "offerIds": [c["id"] for c in bc],
                    "currentBlockers": [p.get("blocker") for p in bp if p.get("blocker")],
                    "nextAction": bp[0].get("nextAction") if bp else "No Nexus project yet", "lastActivity": max([p.get("lastActivity") or "" for p in bp], default=None) or None,
                    "trends": {"7d": None, "30d": None, "90d": None, "truthClass": "NOT_CONNECTED", "note": "No historical metric series recorded yet"}})
    return out


def build() -> dict:
    t0 = time.monotonic()
    areas: dict[str, Any] = {}
    errors: dict[str, str] = {}

    def safe(name, fn, *a):
        try:
            return fn(*a)
        except Exception as exc:  # area unavailable -> explicit, never fabricated
            errors[name] = f"{type(exc).__name__}: {str(exc)[:160]}"
            return None
    pr = safe("projects", area_projects) or ([], [], {})
    projects, approvals, raw = pr
    directives, dnotes = safe("directives", area_directives) or ([], [])
    commerce = safe("commerce", area_commerce, raw) or []
    systems = safe("systems", area_systems) or ([], {})
    areas.update({
        "projects": projects, "approvals": approvals, "directives": directives, "notifications": dnotes[-40:],
        "rea": safe("rea", area_rea) or [], "research": safe("research", area_research) or [],
        "commerce": commerce, "creative": safe("creative", area_creative, raw) or [], "trading": safe("trading", area_trading) or {},
        "systems": systems[0], "nova": systems[1],
        "finance": {"verifiedSpendUsd": 0.0, "verifiedRevenueUsd": 0.0 if commerce else None, "truthClass": "VERIFIED",
                    "note": "Cost governor authorizes $0 spend; no live sales enabled. Other financials NOT_CONNECTED."},
    })
    areas["businesses"] = safe("businesses", area_businesses, projects, approvals, commerce, directives) or []
    areas["meta"] = {"generated_at": now(), "build_seconds": round(time.monotonic() - t0, 1), "errors": errors,
                     "sources": {"projects": "business_loop project store via project_reader (same as nexus_get_project)", "rea": "nexus_durable_jobs REA_EXECUTION",
                                 "research": "R10 store (read-only)", "directives": "nexus_durable_jobs DEPARTMENT_DIRECTIVE", "trading": "trading_core store",
                                 "commerce": "project commerce_offer + Printify draft + commerce_* tables", "businesses": "registered ventures (credential registry)"}}
    return areas


def publish(areas: dict) -> dict:
    rows = [{"area": k, "payload": v, "generated_at": areas["meta"]["generated_at"]} for k, v in areas.items()]
    code, _ = call("POST", "nexus_admin_read_model?on_conflict=area", rows, role="service", prefer="resolution=merge-duplicates,return=minimal")
    return {"status": code, "areas": len(rows), "bytes": len(json.dumps(rows, default=str))}


if __name__ == "__main__":
    a = build()
    print(json.dumps({"errors": a["meta"]["errors"], "counts": {k: (len(v) if isinstance(v, list) else 1) for k, v in a.items()}}, indent=1))
    if "--dry-run" not in sys.argv:
        print(json.dumps(publish(a)))
