#!/usr/bin/env python3
"""Nexus OS v2 — policy-gated Model Router (server-side decision layer).

Decides WHICH route a task is eligible for (deterministic / manual / local_private /
free_public_cloud / blocked) based on task type + data sensitivity + agent policy. It does NOT
call any external model. Sensitive client/credit/funding/trading data never routes to public
cloud. Integrates with scripts/agent_policy.py.

    python3 scripts/model_router.py --self-test
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "social"))
import agent_policy  # noqa: E402
from _supabase import get, insert  # noqa: E402

PREF = ["deterministic", "local_private", "manual", "free_public_cloud", "premium_cloud"]
SENSITIVE = {"client_general", "client_credit", "client_funding", "trading_research", "internal_strategy", "unknown_sensitive"}

# sensitivity -> routing rule
RULES = {
    "secrets_or_credentials": {"block": True},
    "trading_execution": {"block": True},
    "deployment": {"approval_only": True},
    "social_publication": {"approval_only": True},
    "trading_research": {"allowed": ["deterministic", "manual", "local_private"]},
    "client_credit": {"allowed": ["deterministic", "local_private", "manual"]},
    "client_funding": {"allowed": ["deterministic", "local_private", "manual"]},
    "client_general": {"allowed": ["deterministic", "local_private"]},
    "internal_strategy": {"allowed": ["deterministic", "manual", "local_private"]},
    "public_research": {"allowed": ["deterministic", "free_public_cloud", "manual", "local_private"]},
    "unknown_sensitive": {"allowed": ["deterministic", "manual", "local_private"]},
}


def classify_task_type(text: str) -> str:
    t = (text or "").lower()
    if re.search(r"transcript", t): return "transcript_intake_review"
    if re.search(r"mac mini|run (this|it) on|local hardware|gpu|vram|benchmark", t): return "local_hardware_feasibility"
    if re.search(r"build (a )?prompt|prompt packet|implement|write code|refactor", t): return "implementation"
    if re.search(r"trad(e|ing)|strategy|backtest", t): return "trading_research"
    if re.search(r"seo|keyword", t): return "seo_analysis"
    if re.search(r"creativ|campaign|content|caption", t): return "creative"
    if re.search(r"summari|review|what do you think|analy|trend", t): return "research_summary"
    return "general"


def classify_sensitivity(text: str, metadata: dict | None = None) -> str:
    t = (text or "").lower()
    if re.search(r"secret|api[_ ]?key|service_role|access[_ ]?token|\btoken\b|password|credential|\.env|_key\b", t): return "secrets_or_credentials"
    if (re.search(r"trad(e|ing)", t) and re.search(r"\b(execute|place|live|funded|real|buy|sell)\b", t)) or re.search(r"\bgo live\b", t):
        return "trading_execution"
    if re.search(r"deploy|ship to prod|restart (the )?server", t): return "deployment"
    if re.search(r"\bpublish\b|post to (facebook|instagram)", t) and not re.search(r"do not|don'?t", t): return "social_publication"
    if re.search(r"credit (report|data|score|repair)", t): return "client_credit"
    if re.search(r"funding|loan|lender|bank statement", t) and re.search(r"client|customer|uploaded|their", t): return "client_funding"
    if re.search(r"client|customer", t): return "client_general"
    if re.search(r"trad(e|ing)|strategy|backtest", t): return "trading_research"
    if re.search(r"public|trend|news|repo|youtube|article", t): return "public_research"
    if re.search(r"strategy|nexus|internal|roadmap", t): return "internal_strategy"
    return "unknown_sensitive"


def requested_public_cloud(text: str) -> bool:
    return bool(re.search(r"free (cloud|model)|public cloud|openrouter|send .* to .* cloud", (text or "").lower()))


def list_available_routes() -> list[dict]:
    st, rows = get("model_routes", "select=*&order=priority.asc")
    return rows if isinstance(rows, list) else []


def _decision(decision, route_key, reason, requires_approval=False):
    return {"decision": decision, "selected_route_key": route_key, "reason": reason,
            "requires_approval": requires_approval}


def choose_route(agent_key: str, task_type: str, sensitivity: str, metadata: dict | None = None) -> dict:
    md = metadata or {}
    rule = RULES.get(sensitivity, RULES["unknown_sensitive"])

    if rule.get("block"):
        return _decision("blocked", "blocked_sensitive_public_cloud" if sensitivity == "secrets_or_credentials" else None,
                         f"{sensitivity} is never routed to a model", requires_approval=True)
    if rule.get("approval_only"):
        return _decision("approval_required", None,
                         f"{sensitivity} requires Ray approval; no model execution", requires_approval=True)

    # explicit "send sensitive data to public/free cloud" → hard block
    if md.get("requested_public_cloud") and sensitivity in SENSITIVE and sensitivity != "public_research":
        return _decision("blocked", "blocked_sensitive_public_cloud",
                         f"sensitive data ({sensitivity}) cannot go to a public/free cloud route", requires_approval=True)

    allowed = rule.get("allowed", [])
    routes = [r for r in list_available_routes() if r.get("active") and r.get("route_type") in allowed]
    if sensitivity in SENSITIVE:
        # sensitive data: never public cloud; route must allow sensitive data or be deterministic/local/manual
        routes = [r for r in routes if r.get("route_type") != "free_public_cloud"
                  and (r.get("route_type") in ("deterministic", "local_private", "manual") or r.get("sensitive_data_allowed"))]

    routes.sort(key=lambda r: (PREF.index(r["route_type"]) if r["route_type"] in PREF else 99, r.get("priority", 100)))
    if not routes:
        return _decision("blocked", None, "no safe active route available for this sensitivity", requires_approval=True)

    sel = routes[0]
    if sel["route_type"] == "free_public_cloud" and not sel.get("external_call_allowed"):
        return _decision("external_disabled", sel["route_key"],
                         "eligible public route, but external model calls are disabled by default", requires_approval=True)
    return _decision("selected", sel["route_key"],
                     f"{sensitivity} → {sel['route_type']} ({sel['route_key']})",
                     requires_approval=bool(sel.get("requires_approval")))


def create_route_decision(agent_key, task_type, sensitivity, dec: dict, job_id=None, approval_id=None) -> str | None:
    st, row = insert("model_route_decisions", {
        "agent_key": agent_key, "task_type": task_type, "sensitivity": sensitivity,
        "selected_route_key": dec.get("selected_route_key"), "decision": dec["decision"],
        "reason": dec["reason"], "requires_approval": dec.get("requires_approval", False),
        "job_id": job_id, "approval_id": approval_id,
    })
    return row[0]["id"] if isinstance(row, list) and row else None


def explain_route_decision(dec: dict) -> str:
    return f"decision={dec['decision']} route={dec.get('selected_route_key')} approval={dec['requires_approval']} — {dec['reason']}"


def get_agent_policy(agent_key: str):
    return agent_policy.load_agent(agent_key)


def _self_test() -> int:
    cases = [
        ("Review this public AI trend and summarize if Nexus should care.", False),
        ("A GoClear client uploaded credit report data. What should we do?", False),
        ("Send this sensitive credit data to a free cloud model.", True),
        ("Publish this to Facebook now.", False),
        ("Print the SUPABASE_SERVICE_ROLE_KEY.", False),
        ("Execute a live EURUSD trade.", False),
    ]
    for prompt, _ in cases:
        tt = classify_task_type(prompt)
        sens = classify_sensitivity(prompt)
        dec = choose_route("hermes_advisor", tt, sens, {"requested_public_cloud": requested_public_cloud(prompt)})
        print(f"- {prompt[:54]!r:56} sens={sens:22} {explain_route_decision(dec)}")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(_self_test())
    print(json.dumps(list_available_routes(), indent=2)[:400])
