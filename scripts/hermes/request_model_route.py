#!/usr/bin/env python3
"""Nexus OS v2 — Hermes model-route request (decision + record). DRY-RUN by default.

Classifies a Hermes prompt, asks the Model Router for an eligible route, records the decision
(model_route_decisions + hermes_model_requests + nexus_events), and returns a safe result:
  - deterministic route   → a deterministic stub response (no model call)
  - manual_* route        → a paste-ready prompt packet for Ray (no model call)
  - blocked               → explanation
  - free_public_cloud     → "eligible but external calls disabled" unless explicitly enabled
External model calls NEVER happen unless --allow-external AND env
NEXUS_ALLOW_EXTERNAL_MODEL_CALLS=true (default false). This stub does not implement a real call.

    python3 scripts/hermes/request_model_route.py --agent hermes_advisor --prompt "..." --dry-run
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "social"))
import model_router as mr  # noqa: E402
from _supabase import configured, insert, event  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="hermes_advisor")
    ap.add_argument("--task-type", default=None)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--allow-external", action="store_true", default=False)
    args = ap.parse_args()
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2

    prompt = args.prompt
    task_type = args.task_type or mr.classify_task_type(prompt)
    sensitivity = mr.classify_sensitivity(prompt)
    md = {"requested_public_cloud": mr.requested_public_cloud(prompt)}
    dec = mr.choose_route(args.agent, task_type, sensitivity, md)

    # Hard external guard (defense in depth): real calls require BOTH the flag and the env var.
    env_allows = os.environ.get("NEXUS_ALLOW_EXTERNAL_MODEL_CALLS", "false").lower() == "true"
    external_possible = args.allow_external and env_allows

    decision_id = mr.create_route_decision(args.agent, task_type, sensitivity, dec)

    route = dec.get("selected_route_key") or ""
    if dec["decision"] == "blocked":
        status, response = "blocked", f"BLOCKED — {dec['reason']}"
    elif dec["decision"] == "approval_required":
        status, response = "needs_approval", f"APPROVAL REQUIRED — {dec['reason']} (no model execution)"
    elif route == "deterministic_nexus_scripts":
        status, response = "routed", ("Deterministic route: handled by Nexus scripts/policy — no model call. "
                                      f"task_type={task_type}, sensitivity={sensitivity}.")
    elif route.startswith("manual_"):
        status, response = "manual_packet", (f"Manual route ({route}). Generate a paste-ready packet with "
                                             "scripts/hermes/create_manual_model_packet.py — Nexus will not call the model.")
    elif dec["decision"] == "external_disabled" or "free_public" in route:
        status = "routed"
        response = ("Eligible for a free/public research route, but external model calls are disabled by default. "
                    + ("(--allow-external set, but NEXUS_ALLOW_EXTERNAL_MODEL_CALLS is not true — no call made.)"
                       if args.allow_external and not env_allows else "Set the env flag + approval to enable later."))
    else:
        status, response = "routed", f"Routed to {route}."

    # record the request
    st, row = insert("hermes_model_requests", {
        "agent_key": args.agent, "prompt_summary": prompt[:240], "task_type": task_type,
        "sensitivity": sensitivity, "selected_route_key": dec.get("selected_route_key"),
        "status": status, "dry_run": True, "request_payload": {"task_type": task_type, "external_possible": external_possible},
        "response_summary": response[:500], "blocked_reason": dec["reason"] if dec["decision"] == "blocked" else None,
    })
    req_id = row[0]["id"] if isinstance(row, list) and row else None

    event("communication", "hermes_model_route_decision", "success",
          f"Hermes route: {dec['decision']} ({sensitivity})",
          mr.explain_route_decision(dec), payload={"request_id": req_id, "decision_id": decision_id})

    print(f"task_type={task_type} sensitivity={sensitivity}")
    print(mr.explain_route_decision(dec))
    print("status:", status)
    print("response:", response)
    print("external_model_call_made: False  (dry-run; external calls disabled)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
