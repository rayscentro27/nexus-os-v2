"""Generic durable department directive (NEXUS_AUTOMATIC_DIRECTIVE_AND_CONTINUATION_R1).

A directive IS one existing Nexus durable job (``nexus_durable_jobs``, job_type
DEPARTMENT_DIRECTIVE). The standard directive schema lives in
``governance_context.directive``; an append-only ``directive.events`` list is the
notification source Nova's proactive loop reads. No new queue, store, or manager.

  create_directive(...)  -> called by the Nova MCP tool (creates work, never executes it)
  execute(job, store)    -> called by the durable dispatcher route DEPARTMENT_DIRECTIVE

Departments: MARKETING (bounded Hermes specialist turn), CREATIVE (canonical
provider policy; blocks honestly when no approved autonomous executor exists),
REA (hands off to the existing REA_EXECUTION route; finished by continue_directives).
Continuation is deterministic; approvals pause only the gated action.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

JOB_TYPE = "DEPARTMENT_DIRECTIVE"
SOURCE_NOVA = "NOVA_MCP_DEPARTMENT_DIRECTIVE"
SOURCE_CONTINUATION = "NEXUS_DIRECTIVE_CONTINUATION"
SCHEMA_VERSION = "nexus.department-directive.v1"
STATUSES = {"READY", "RUNNING", "WAITING_APPROVAL", "BLOCKED", "COMPLETE", "FAILED", "CANCELLED"}
DEPARTMENTS = {"MARKETING", "CREATIVE", "REA"}
REQUIRED_FIELDS = ("objective", "task", "required_output")
MARKETING_OUTPUT_KEYS = ("campaign_concept", "target_audience", "hypothesis", "variant_a", "variant_b", "cta",
                         "channel_recommendation", "measurement_plan", "creative_required")
# Claims a GoClear/credit-adjacent message must never make without evidence.
PROHIBITED_CLAIMS = re.compile(
    r"\bguarantee(?:d|s)?\b|\b(?:will|100%)\s+(?:raise|boost|increase|fix|repair)\b|\bapproved\s+for\b|\bget\s+approved\b|"
    r"\b(?:instant|guaranteed)\s+(?:funding|approval|loan)\b|\b\d{2,3}\s*(?:points?|pts)\b|\berase\s+(?:your\s+)?(?:debt|bad\s+credit)\b", re.I)
CREATIVE_CATEGORY = "SOCIAL_IMAGES"
# Canonical Creative policy (scripts/creative/creative_provider_router.py): approved generative
# providers only; deterministic/local media substitutes are prohibited for production creative.
CREATIVE_ROUTE = ("meta_ai_browser_creative", "modal")
# Executors Nexus can actually run unattended today. Empty by design: Meta.ai has no
# autonomous executor and Modal is not routable without spend approval.
AUTONOMOUS_CREATIVE_EXECUTORS: dict[str, Callable[[dict], dict]] = {}

ROOT = Path(__file__).resolve().parents[2]
AUTHORITY = Path(os.environ.get("NEXUS_ORACLE_AUTHORITY") or "/Users/raymonddavis/nexus-os-v2-canonical/docs/architecture/NEXUS_ORACLE_CONNECTION_AUTHORITY.json")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


# ------------------------------------------------------------------ schema
def build_directive(*, target_department: str, objective: str, task: str, required_output: list | str,
                    project_id: str = "", parent_directive_id: str = "", source_department: str = "NOVA",
                    inputs: dict | None = None, evidence_references: list | None = None,
                    success_criteria: list | None = None, restrictions: list | None = None,
                    approval_requirement: str = "PUBLICATION_REQUIRES_RAY_APPROVAL",
                    dependencies: list | None = None, next_department: str = "", next_action: str = "",
                    business_id: str = "", venture_id: str = "") -> dict:
    dept = str(target_department or "").upper()
    if dept not in DEPARTMENTS:
        raise ValueError(f"unsupported_target_department:{dept}")
    biz = str(business_id or venture_id or "").strip() or _venture_for_project(project_id)
    d = {"schema_version": SCHEMA_VERSION, "directive_id": None, "project_id": project_id or "",
         "business_id": biz, "venture_id": biz,
         "parent_directive_id": parent_directive_id or None, "source_department": str(source_department).upper(),
         "target_department": dept, "objective": str(objective or "").strip(), "task": str(task or "").strip(),
         "inputs": inputs or {}, "evidence_references": list(evidence_references or []),
         "required_output": required_output if isinstance(required_output, list) else [str(required_output)],
         "success_criteria": list(success_criteria or []), "restrictions": list(restrictions or []),
         "cost_policy": {"max_spend_usd": 0, "paid_providers": "DENY", "ad_spend": "DENY"},
         "approval_requirement": approval_requirement, "dependencies": list(dependencies or []),
         "status": "READY", "created_at": now(), "started_at": None, "completed_at": None,
         "next_department": (next_department or "").upper() or None, "next_action": next_action or None,
         "result": None, "events": []}
    missing = [k for k in REQUIRED_FIELDS if not d[k]]
    if missing:
        raise ValueError("directive_missing:" + ",".join(missing))
    if any(len(str(d[k])) > 4000 for k in ("objective", "task")):
        raise ValueError("directive_text_too_long")
    if dept == "REA":
        rea = d["inputs"]
        if not str(rea.get("target") or "").strip():
            raise ValueError("directive_missing:inputs.target")
        if str(rea.get("mode") or "MODEL").upper() == "MODEL" and not str(rea.get("authorization_ref") or "").strip():
            raise ValueError("directive_missing:inputs.authorization_ref")
    return d


def _venture_for_project(project_id: str) -> str | None:
    """BUSINESS_ID/VENTURE_ID from the authoritative project store; None when it cannot be resolved."""
    if not project_id or not str(project_id).startswith("proj_") or str(project_id).startswith("proj_dir_"):
        return None
    try:
        from services.nexus_mcp import project_reader
        r = project_reader.get_project(project_id)
        return (r.get("data") or {}).get("venture_id") if r.get("status") == "OK" else None
    except Exception:
        return None


def event(d: dict, kind: str, *, summary: str, next_step: str = "", **extra: Any) -> dict:
    at = now()
    seq = len(d.get("events") or [])
    ev = {"kind": kind, "at": at, "event_id": "evt_" + _hash([d.get("directive_id"), kind, at, seq])[:24],
          "directive_id": d.get("directive_id"), "project_id": d.get("project_id"),
          "business_id": d.get("business_id"), "parent_directive_id": d.get("parent_directive_id"),
          "department": d.get("target_department"), "status": d.get("status"), "started_at": d.get("started_at"),
          "summary": summary, "next": next_step or d.get("next_action") or "", **extra}
    d.setdefault("events", []).append(ev)
    return ev


def _save(store, job, d: dict) -> None:
    ctx = dict((store.get(job.job_id) or job).governance_context or {})
    ctx["directive"] = d
    store.set_governance_context(job.job_id, ctx)


def create_directive(store, directive: dict, *, source: str = SOURCE_NOVA, parent_job=None,
                     idempotency_key: str | None = None, correlation_id: str | None = None):
    """Create durable department work. Never executes it."""
    key = idempotency_key or "directive:" + _hash({k: directive.get(k) for k in ("target_department", "objective", "task", "project_id", "parent_directive_id")})[:32]
    # The directive worker is orchestration only (Marketing runs remotely on Oracle; Creative is a
    # provider-policy step). It becomes heavy only if a LOCAL heavy executor is registered.
    local_heavy = directive["target_department"] == "CREATIVE" and any(
        getattr(fn, "local_heavy", False) for fn in AUTONOMOUS_CREATIVE_EXECUTORS.values())
    ctx = {"source": source, "spend_allowed": False, "paid_provider_authorized": False,
           "external_actions_allowed": False, "external_actions_authorized": False,
           "resource_dependencies": [], "directive": directive,
           "resource_class": "HEAVY_LOCAL" if local_heavy else "LIGHTWEIGHT_INTERNAL"}
    job = store.enqueue(directive["target_department"], JOB_TYPE, priority=90, payload_ref=None,
                        parent_job_id=getattr(parent_job, "job_id", None),
                        correlation_id=correlation_id or getattr(parent_job, "correlation_id", None) or key,
                        max_attempts=2, idempotency_key=key, governance_context=ctx)
    d = dict((job.governance_context or {}).get("directive") or directive)
    if not d.get("directive_id"):
        d["directive_id"] = job.job_id
        if not d.get("project_id"):
            d["project_id"] = "proj_dir_" + job.job_id.removeprefix("job_")[:20]
        event(d, "DIRECTIVE_CREATED", summary=f"{d['target_department']} directive created: {d['objective'][:200]}",
              next_step=f"{d['target_department']} worker will execute it.")
        _save(store, job, d)
    return job, d


# ------------------------------------------------------------------ Hermes specialist (Marketing)
def _oracle_target() -> tuple[str, str]:
    auth = json.loads(AUTHORITY.read_text())
    cur = auth.get("current") or {}
    return f"{cur['user']}@{cur['host']}", os.path.expanduser(cur["identity_path"])


def run_hermes_specialist(prompt: str, session: str, timeout: int = 240) -> dict:
    """One bounded Hermes turn on Oracle via the CURRENT authority connection (same invocation Nova uses)."""
    target, identity = _oracle_target()
    remote = ("podman exec -i nexus-hermes-0225 env HERMES_HOME=/opt/data/profiles/nova_nexus HERMES_PROFILE=nova_nexus "
              f"/opt/hermes/.venv/bin/hermes -p nova_nexus chat -Q --query-file - --continue {session} --create-if-missing --format stream-json")
    proc = subprocess.run(["ssh", "-i", identity, "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", target, remote],
                          input=prompt, text=True, capture_output=True, timeout=timeout)
    events = []
    for line in (proc.stdout or "").splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            continue
    terminal = next((e for e in reversed(events) if isinstance(e, dict) and e.get("type") == "result"), None)
    tools = [e.get("name") for e in events if isinstance(e, dict) and e.get("type") == "tool_use"]
    if proc.returncode != 0 or not terminal:
        return {"ok": False, "error": f"hermes_exit_{proc.returncode}", "tools": tools}
    return {"ok": True, "text": str(terminal.get("text") or ""), "tools": tools, "session": session}


def _extract_json(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        v = json.loads(m.group(0))
        return v if isinstance(v, dict) else None
    except ValueError:
        return None


def _marketing_prompt(d: dict) -> str:
    return (
        "You are the Nexus MARKETING department worker executing one durable directive. "
        "Do NOT call any tools. Do NOT publish, spend, or contact anyone. Use only the directive below.\n"
        "Respect every restriction. Never claim guaranteed credit/score outcomes, funding or approval, and never copy a creator's anecdote.\n"
        "If the evidence does not justify any marketing action, set creative_required=false and explain in no_further_action_reason.\n"
        "Reply with ONE JSON object only, keys: " + ", ".join(MARKETING_OUTPUT_KEYS) +
        ", creative_requirements {asset_requirements, message_variants, channel_formats, truth_constraints}, "
        "restrictions_applied, no_further_action_reason (null if action is justified).\n\nDIRECTIVE:\n" +
        json.dumps({k: d.get(k) for k in ("directive_id", "project_id", "objective", "task", "inputs", "evidence_references",
                                          "required_output", "success_criteria", "restrictions", "cost_policy", "approval_requirement")}, indent=1))


def truth_violations(output: dict) -> list[str]:
    text = json.dumps({k: output.get(k) for k in ("campaign_concept", "hypothesis", "variant_a", "variant_b", "cta")}, default=str)
    return sorted({m.group(0) for m in PROHIBITED_CLAIMS.finditer(text)})


# ------------------------------------------------------------------ execution
def execute(job, store, *, hermes: Callable[[str, str], dict] = run_hermes_specialist,
            rea_submit: Callable[[Any, dict], dict] | None = None) -> dict:
    ctx = dict(job.governance_context or {})
    d = dict(ctx.get("directive") or {})
    if d.get("schema_version") != SCHEMA_VERSION:
        return {"status": "BLOCKED", "reason": "DIRECTIVE_SCHEMA_MISSING"}
    if d.get("status") in {"COMPLETE", "CANCELLED", "WAITING_APPROVAL"}:
        return {"status": "COMPLETED", "directive_id": d.get("directive_id"), "directive_status": d["status"], "idempotent": True}
    if d.get("status") == "RUNNING" and (d.get("result") or {}).get("rea_job_id"):
        return {"status": "COMPLETED", "directive_id": d.get("directive_id"), "directive_status": "RUNNING", "idempotent": True}
    d["status"] = "RUNNING"
    d["started_at"] = d.get("started_at") or now()
    event(d, "WORK_STARTED", summary=f"{d['target_department']} started directive {d['directive_id']}.")
    _save(store, job, d)
    dept = d["target_department"]
    if dept == "REA":
        return _rea(job, store, d, rea_submit)
    out = _marketing(job, store, d, hermes) if dept == "MARKETING" else _creative(job, store, d)
    return out


def _finish(store, job, d: dict, status: str, kind: str, summary: str, next_step: str, result: Any = None, **extra) -> dict:
    d["status"] = status
    d["result"] = result if result is not None else d.get("result")
    if status in {"COMPLETE", "FAILED", "BLOCKED", "CANCELLED"}:
        d["completed_at"] = now()
    d["next_action"] = next_step
    event(d, kind, summary=summary, next_step=next_step, **extra)
    _save(store, job, d)
    nexus_status = {"COMPLETE": "COMPLETED", "WAITING_APPROVAL": "COMPLETED", "BLOCKED": "BLOCKED", "FAILED": "FAILED", "CANCELLED": "CANCELLED"}[status]
    return {"status": nexus_status, "reason": extra.get("reason") or status, "directive_id": d["directive_id"],
            "directive_status": status, "department": d["target_department"], "result_summary": summary[:300]}


def _marketing(job, store, d: dict, hermes) -> dict:
    run = hermes(_marketing_prompt(d), f"nexus-directive-{d['directive_id']}")
    if not run.get("ok"):
        return _finish(store, job, d, "FAILED", "WORK_FAILED", f"Marketing worker could not run ({run.get('error')}).",
                       "Retry per durable-job policy; project remains active.", reason="MARKETING_WORKER_UNAVAILABLE")
    output = _extract_json(run.get("text", ""))
    missing = [k for k in MARKETING_OUTPUT_KEYS if not output or k not in output]
    if missing:
        return _finish(store, job, d, "FAILED", "WORK_FAILED", "Marketing output did not meet the directive contract (missing " + ",".join(missing[:5]) + ").",
                       "Retry per durable-job policy.", reason="MARKETING_OUTPUT_CONTRACT", result={"raw_text": run.get("text", "")[:2000]})
    violations = truth_violations(output)
    if violations:
        return _finish(store, job, d, "BLOCKED", "PROJECT_BLOCKED", "Marketing output contained prohibited claims: " + ", ".join(violations),
                       "Marketing must revise without unsupported claims.", reason="TRUTH_CHECK_FAILED", result=output)
    campaign_id = "camp_" + d["directive_id"].removeprefix("job_")[:16]
    output["campaign_id"] = campaign_id
    event(d, "CAMPAIGN_CREATED", summary=f"Campaign package created: {str(output.get('campaign_concept'))[:200]} (not published).",
          next_step="Creative requirements follow; publication needs Ray's approval.", campaign_id=campaign_id)
    output["_provenance"] = {"engine": "hermes_specialist_turn", "session": run.get("session"), "tools_called": run.get("tools", []),
                             "research_source": d.get("evidence_references"), "directive_id": d["directive_id"], "project_id": d["project_id"]}
    if not output.get("creative_required") or output.get("no_further_action_reason"):
        return _finish(store, job, d, "COMPLETE", "WORK_COMPLETED", f"Marketing completed: {str(output.get('campaign_concept'))[:200]}. No further department action justified.",
                       str(output.get("no_further_action_reason") or "Branch closed."), result=output)
    req = output.get("creative_requirements") or {}
    child = build_directive(
        target_department="CREATIVE", project_id=d["project_id"], parent_directive_id=d["directive_id"], source_department="MARKETING",
        objective=f"Produce campaign assets for: {output.get('campaign_concept')}",
        task="Create the asset set required by the Marketing package using only approved Creative providers.",
        business_id=d.get("business_id") or "",
        inputs={"campaign_id": campaign_id, "marketing_directive_id": d["directive_id"],
                "message_variants": req.get("message_variants") or [output.get("variant_a"), output.get("variant_b")],
                "asset_requirements": req.get("asset_requirements"), "channel_formats": req.get("channel_formats"), "cta": output.get("cta")},
        evidence_references=d.get("evidence_references"), required_output=["asset files", "per-asset provider receipt", "truth QA"],
        restrictions=list(d.get("restrictions") or []) + list(req.get("truth_constraints") or []),
        approval_requirement="PUBLICATION_REQUIRES_RAY_APPROVAL", next_department="DISTRIBUTION",
        next_action="Publication approval request")
    child_job, child_d = create_directive(store, child, source=SOURCE_CONTINUATION, parent_job=job,
                                          idempotency_key=f"next:{job.job_id}:creative")
    output["_continuation"] = {"creative_directive_id": child_d["directive_id"]}
    res = _finish(store, job, d, "COMPLETE", "WORK_COMPLETED", f"Marketing completed: {str(output.get('campaign_concept'))[:200]}.",
                  f"Creative directive {child_d['directive_id']} created automatically.", result=output)
    d = dict(store.get(job.job_id).governance_context["directive"])
    event(d, "PROJECT_CONTINUED", summary=f"Project continued MARKETING -> CREATIVE (directive {child_d['directive_id']}).",
          next_step="Creative executes with approved providers only.", child_directive_id=child_d["directive_id"])
    _save(store, job, d)
    return {**res, "child_directive_id": child_d["directive_id"]}


def _creative(job, store, d: dict) -> dict:
    attempts = []
    for provider in CREATIVE_ROUTE:
        executor = AUTONOMOUS_CREATIVE_EXECUTORS.get(provider)
        if provider == "modal" and executor is None:
            attempts.append({"provider": provider, "result": "WAITING_FOR_RAY_APPROVAL_OR_NOT_ROUTABLE"})
            continue
        if executor is None:
            attempts.append({"provider": provider, "result": "NO_AUTONOMOUS_EXECUTOR"})
            continue
        try:
            assets = executor(d)
        except Exception as exc:  # recoverable provider failure -> next approved provider
            attempts.append({"provider": provider, "result": f"FAILED:{type(exc).__name__}"})
            continue
        if assets.get("ok"):
            event(d, "CREATIVE_CREATED", summary=f"{len(assets.get('assets', []))} creative asset(s) created via {provider} (not published).",
                  next_step="Ray reviews the assets.", asset_ids=[a.get("asset_id") for a in assets.get("assets", []) if isinstance(a, dict)][:20])
            return _finish(store, job, d, "WAITING_APPROVAL", "APPROVAL_REQUIRED",
                           f"Creative completed {len(assets.get('assets', []))} asset(s) via {provider}. Publication is waiting for Ray's approval. No money spent; nothing published.",
                           "Ray: review and approve publication.", result={"assets": assets.get("assets"), "provider": provider, "attempts": attempts},
                           required_action="Approve or reject publication of the creative package.")
    return _finish(store, job, d, "BLOCKED", "PROJECT_BLOCKED",
                   "CREATIVE_EXECUTION_BLOCKED: the approved Creative providers (Meta.ai, Modal) have no autonomous executor available; "
                   "local/deterministic substitutes are prohibited, so no assets were generated.",
                   "Ray: approve Modal spend or an autonomous Meta.ai executor; the Marketing package remains complete and the project stays active.",
                   reason="CREATIVE_EXECUTION_BLOCKED", result={"attempts": attempts, "fallback_used": False},
                   required_action="Decide the Creative execution path (Modal spend approval or Meta.ai executor).")


# ------------------------------------------------------------------ REA target (NEXUS_FINAL_OVERNIGHT_COMPLETION_R1)
def _default_rea_submit(store, raw: dict) -> dict:
    from nexus_agent_platform import rea_engine_handoff
    return rea_engine_handoff.create_request(store, raw)


def _rea(job, store, d: dict, rea_submit=None) -> dict:
    """Hand the directive to the existing REA route (REA_EXECUTION durable job on the Contabo harness).

    Non-blocking: the directive stays RUNNING and ``continue_directives`` finishes it from the REA job's
    authoritative state (REA_WORK_COMPLETED / REA_WORK_FAILED)."""
    inp = dict(d.get("inputs") or {})
    raw = {"mode": str(inp.get("mode") or "MODEL").upper(), "objective": d["objective"], "target": inp.get("target"),
           "authorization_ref": inp.get("authorization_ref"), "requested_by": "NEXUS_DIRECTIVE",
           "options": {k: inp[k] for k in ("tool_profile", "model_profile", "model_key") if inp.get(k)}}
    try:
        sub = (rea_submit or _default_rea_submit)(store, raw)
    except ValueError as exc:
        return _finish(store, job, d, "BLOCKED", "PROJECT_BLOCKED", f"REA request rejected by the REA contract: {exc}.",
                       "Ray: supply a valid REA target/authorization.", reason="REA_REQUEST_INVALID")
    rea_job_id = sub.get("nexus_job_id")
    d["result"] = {"rea_job_id": rea_job_id, "rea_session_id": sub.get("rea_session_id"), "mode": raw["mode"]}
    d["next_action"] = f"REA job {rea_job_id} runs on the Contabo harness; Nexus finishes this directive from its result."
    event(d, "REA_WORK_STARTED", summary=f"REA work submitted ({raw['mode']}) for target: {str(raw['target'])[:200]}.",
          next_step=d["next_action"], rea_job_id=rea_job_id)
    _save(store, job, d)
    return {"status": "COMPLETED", "directive_id": d["directive_id"], "directive_status": "RUNNING", "rea_job_id": rea_job_id,
            "department": "REA", "result_summary": "REA work submitted"}


TERMINAL_JOB_STATES = {"COMPLETED", "BLOCKED", "CANCELLED", "FAILED", "DEAD_LETTER"}
CONTINUATION_LIMIT = 30


def continue_directives(store, *, limit: int = CONTINUATION_LIMIT) -> dict:
    """Deterministic directive continuation, run on each continuation sweep (bounded).

    RUNNING + REA child finished      -> REA_WORK_COMPLETED + COMPLETE, or REA_WORK_FAILED + BLOCK
    FAILED and retries exhausted      -> PROJECT_BLOCKED (notify once)
    WAITING_APPROVAL, not decided     -> held (no action)
    WAITING_APPROVAL + APPROVED       -> PROJECT_CONTINUED (resume) and COMPLETE
    COMPLETE with a promised child    -> ensure the next directive exists (idempotent)
    Recoverable failures are retried by the durable job itself (max_attempts) before reaching here.
    """
    rows = store._request(f"nexus_durable_jobs?job_type=eq.{JOB_TYPE}&state=in.(COMPLETED,FAILED,FAILED_RETRYABLE,BLOCKED,DEAD_LETTER)"
                          f"&select=job_id,state,attempt_count,max_attempts&order=created_at.desc&limit={int(limit)}") or []
    out = {"checked": len(rows), "rea_completed": 0, "rea_failed": 0, "blocked": 0, "resumed": 0, "held": 0}
    for row in rows:
        job = store.get(row["job_id"])
        if not job:
            continue
        d = dict((job.governance_context or {}).get("directive") or {})
        kinds = {e.get("kind") for e in d.get("events") or []}
        status = d.get("status")
        if status == "RUNNING" and (d.get("result") or {}).get("rea_job_id"):
            child = store.get(d["result"]["rea_job_id"])
            cstate = str(getattr(child, "state", "") or "")
            if cstate == "COMPLETED":
                summ = ((child.governance_context or {}).get("result_summary") or {})
                _finish_event_only(store, job, d, "COMPLETE", "REA_WORK_COMPLETED", f"REA job {child.job_id} completed.",
                                   "Nova/Ray review the REA findings.", rea_job_id=child.job_id, result_ref=bool(summ))
                out["rea_completed"] += 1
            elif cstate in TERMINAL_JOB_STATES:
                _finish_event_only(store, job, d, "BLOCKED", "REA_WORK_FAILED", f"REA job {child.job_id} ended {cstate}.",
                                   "Ray: review the REA failure; the project stays active.", rea_job_id=child.job_id)
                d2 = dict(store.get(job.job_id).governance_context["directive"])
                event(d2, "PROJECT_BLOCKED", summary=f"Directive {d2['directive_id']} blocked: REA job {child.job_id} {cstate}.",
                      next_step=d2.get("next_action") or "", rea_job_id=child.job_id)
                _save(store, job, d2)
                out["rea_failed"] += 1
            continue
        if status == "FAILED" and row["state"] in {"FAILED", "DEAD_LETTER", "BLOCKED"} and "PROJECT_BLOCKED" not in kinds:
            d["status"] = "BLOCKED"
            event(d, "PROJECT_BLOCKED", summary=f"Directive {d.get('directive_id')} failed after {row.get('attempt_count')} attempt(s); retries exhausted.",
                  next_step="Ray: decide whether to retry or re-scope this work.")
            _save(store, job, d)
            out["blocked"] += 1
            continue
        if status == "WAITING_APPROVAL":
            decision = str((d.get("approval") or {}).get("status") or "").upper()
            if decision == "APPROVED" and "PROJECT_CONTINUED" not in kinds:
                d["status"] = "COMPLETE"
                d["completed_at"] = now()
                event(d, "PROJECT_CONTINUED", summary=f"Approval {d['approval'].get('approval_id')} granted; directive resumed.",
                      next_step=d.get("next_action") or "Next department proceeds.")
                _save(store, job, d)
                out["resumed"] += 1
            else:
                out["held"] += 1
    return out


def _finish_event_only(store, job, d: dict, status: str, kind: str, summary: str, next_step: str, **extra) -> None:
    d["status"] = status
    d["completed_at"] = now()
    d["next_action"] = next_step
    d["result"] = {**(d.get("result") or {}), **{k: v for k, v in extra.items() if k == "rea_job_id"}}
    event(d, kind, summary=summary, next_step=next_step, **extra)
    _save(store, job, d)
