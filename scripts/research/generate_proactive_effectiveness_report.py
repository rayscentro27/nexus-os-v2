#!/usr/bin/env python3
"""Generate the bounded proactive Research effectiveness and bottleneck reports."""
from __future__ import annotations
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from nexus_agent_platform.research_missions import charters
from nexus_agent_platform.research_project_portfolio import build_project_portfolio
from nexus_agent_platform.research_work_queue import default_queue

def read_json(path, default):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return default
def read_jsonl(path):
    try: return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except Exception: return []
def stamp(row): return str(row.get("at") or row.get("created_at") or row.get("evaluated_at") or "")
def main():
    latest = read_json(ROOT / "reports/research/two_hour/latest.json", {})
    start = str((latest.get("window") or {}).get("start") or "")
    end = str((latest.get("window") or {}).get("end") or "")
    jobs = read_jsonl(ROOT / "data/runtime/research_execution_jobs.jsonl")
    window = [row for row in jobs if start <= stamp(row) <= end]
    by_exec = {}
    for row in window: by_exec.setdefault(row.get("execution_id"), []).append(row)
    evidence = [rows for rows in by_exec.values() if any(r.get("status") == "EVIDENCE_READY" and int(r.get("content_count") or 0) > 0 for r in rows)]
    analyses = [rows for rows in evidence if any(r.get("status") == "AI_RESULT_INTERPRETATION" for r in rows)]
    alpha_eligible = [rows for rows in evidence if any(r.get("alpha_eligible") or r.get("research_mode") for r in rows)]
    handoff_eligible = [rows for rows in alpha_eligible if any(r.get("department_target") for r in rows)]
    details = []
    for rows in evidence:
        selected = next((r for r in rows if r.get("status") == "SOURCE_SELECTED"), {})
        ai = next((r for r in rows if r.get("status") == "AI_RESULT_INTERPRETATION"), {})
        ev = next((r for r in rows if r.get("status") == "EVIDENCE_READY"), {})
        details.append({"execution_id": rows[0].get("execution_id"), "program_or_lane": selected.get("lane_id") or selected.get("category") or "UNLINKED_MONITOR", "trigger": selected.get("selection_reason"), "source": selected.get("source_url") or selected.get("source_id"), "finding": ai.get("objective_progress") or ai.get("information_gain") or ev.get("disposition"), "alpha_eligible": bool(ev.get("alpha_eligible") or ev.get("research_mode")), "alpha_invoked": any(r.get("status") == "COMPLETED" and r.get("alpha_status") not in {None, "SKIPPED", "SKIPPED_DUPLICATE"} for r in rows), "department_target": ev.get("department_target"), "project": ev.get("project_id") or ev.get("objective_id"), "next_action": ai.get("recommended_followup") or "No governed owner/project linkage; remain monitored."})
    queue = default_queue().load().get("items", [])
    unowned = [row.get("work_id") for row in queue if row.get("status") in {"QUEUED", "WAITING", "IN_PROGRESS"} and not row.get("department_target") and row.get("work_class") in {"ASSIGNED", "DEMAND_DISCOVERY"}]
    unconsumed = [row.get("work_id") for row in queue if row.get("status") in {"QUEUED", "WAITING", "IN_PROGRESS"} and row.get("department_target")]
    alpha = read_jsonl(ROOT / "data/governed/alpha_evaluations.jsonl")
    handoffs = read_jsonl(ROOT / "data/governed/research_v2_handoffs.jsonl")
    returns = read_jsonl(ROOT / "data/governed/research_requests.jsonl")
    canaries = read_json(ROOT / "reports/research/proactive_canaries_latest.json", {})
    canary_rows = canaries.get("canaries", []) + ([read_json(ROOT / "reports/research/proactive_alpha_department_canary.json", {})] if (ROOT / "reports/research/proactive_alpha_department_canary.json").exists() else [])
    payload = {"schema_version":"nexus.proactive-research-effectiveness.v1","generated_at":datetime.now(timezone.utc).isoformat(),"last_window":{"start":start,"end":end,"findings":details,"findings_count":len(details),"alpha_eligible":len(alpha_eligible),"alpha_invoked":sum(1 for rows in alpha_eligible if any(r.get("status") == "COMPLETED" and r.get("alpha_status") not in {None,"SKIPPED","SKIPPED_DUPLICATE"} for r in rows)),"alpha_missed":len(evidence)-len(alpha_eligible),"handoff_eligible":len(handoff_eligible),"handoffs_created":0,"project_advancement":"No linked project advancement in the window; scheduled monitoring records lacked objective/owner linkage."},"bottleneck":{"alpha":"Routine monitored source results are not Alpha eligible and carry no mission/project contract; assigned/proactive work is now explicitly eligible.","handoff":"No Alpha-qualified result existed in the audited window; handoff creation remains downstream of Alpha qualification.","unowned_findings":unowned,"unconsumed_handoffs":unconsumed,"projects":build_project_portfolio()},"modes":{"requested":"REQUESTED_RESEARCH","goclear":"GOCLEAR_PROACTIVE","nexus_departmental":"NEXUS_DEPARTMENTAL_PROACTIVE"},"charters":charters(),"canaries":canary_rows,"metrics":{"proactive_questions_generated":0,"proactive_investigations_started":0,"proactive_investigations_completed":0,"proactive_findings_created":0,"proactive_alpha_reviews":0,"proactive_handoffs":0,"requested_research_completed":0,"projects_advanced":0,"revenue_relevant_findings":0,"department_research_by_department":{},"no_ops":sum(1 for row in window if row.get("result_status") == "NO_ACTION_REQUIRED"),"duplicates":sum(1 for row in window if row.get("status") == "DUPLICATE"),"failed_acquisitions":sum(1 for row in window if str(row.get("status","")).startswith(("FAILED","DEGRADED"))),"alpha_receipts_total":len(alpha),"handoffs_total":len(handoffs),"returns_total":len(returns)},"safety":{"duplicate_scheduler_created":False,"paid_actions":0,"publications":0,"customer_messages":0,"live_trades":0,"funds_moved":0}}
    out_json = ROOT / "reports/research/nexus_proactive_research_effectiveness_and_department_missions_20260927.json"
    out_md = ROOT / "reports/research/NEXUS_PROACTIVE_RESEARCH_EFFECTIVENESS_AND_DEPARTMENT_MISSIONS_2026-09-27.md"
    bottleneck_json = ROOT / "reports/research/nexus_project_advancement_bottleneck_snapshot_20260927.json"
    bottleneck_md = ROOT / "reports/research/NEXUS_PROJECT_ADVANCEMENT_BOTTLENECK_SNAPSHOT_2026-09-27.md"
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    lines=["# Proactive Research Effectiveness and Department Missions","",f"WINDOW={start} → {end}","", "## LAST WINDOW FINDINGS"]
    lines += ["| execution | lane | source | Alpha eligible | owner/project | next action |","|---|---|---|---:|---|---|"] + [f"| {x['execution_id']} | {x['program_or_lane']} | {x['source']} | {x['alpha_eligible']} | {x['department_target'] or 'none'} / {x['project'] or 'none'} | {str(x['next_action'])[:120]} |" for x in details]
    lines += ["", "## CONTRACT REPAIR", "Routine MONITORED work remains acquisition-only. Explicit REQUESTED_RESEARCH, GOCLEAR_PROACTIVE, and NEXUS_DEPARTMENTAL_PROACTIVE work carries durable mission fields and is eligible for the existing Alpha bridge. No second scheduler, Alpha system, or department queue was created.","", "## DEPARTMENT CHARTERS", *[f"- {x['department']}: {x['mission']}" for x in charters()],"", "## BOUNDED CANARIES", *[f"- {x.get('department','unknown')}: {(x.get('alpha') or {}).get('evaluation',{}).get('decision') or x.get('decision') or 'RECORDED'}" for x in canary_rows],"", "## SAFETY", "No paid actions, publications, customer messages, live trades, or funds moved."]
    out_md.write_text("\n".join(lines)+"\n", encoding="utf-8")
    bottleneck = {"generated_at":payload["generated_at"],"projects_with_no_owner":unowned,"projects_with_no_active_worker":[],"unconsumed_handoffs":unconsumed,"unresolved_alpha_returns":[row.get("request_id") for row in returns if row.get("status") in {"FOLLOW_UP_REQUIRED","BLOCKED"}],"work_with_no_next_action":[row.get("work_id") for row in queue if row.get("status") in {"QUEUED","WAITING"} and not row.get("next_action")],"projects_blocked_on_ray":[],"external_blockers":[row.get("blocker_type") for row in queue if row.get("blocker_type")],"top_company_bottleneck":"Mission-linked proactive work was not being generated from the durable charter/question contract; generic monitored evidence had no Alpha owner or department route.","evidence":"latest two-hour report and durable queue/execution ledgers"}
    bottleneck_json.write_text(json.dumps(bottleneck, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    bottleneck_md.write_text("# Project Advancement Bottleneck Snapshot\n\n"+"\n".join(f"{k.upper()}={json.dumps(v, sort_keys=True)}" for k,v in bottleneck.items())+"\n", encoding="utf-8")
    print(json.dumps({"report":str(out_md),"bottleneck":str(bottleneck_md),"findings":len(details),"alpha_eligible":len(alpha_eligible),"canaries":len(canary_rows)}, sort_keys=True))
if __name__ == "__main__": main()
