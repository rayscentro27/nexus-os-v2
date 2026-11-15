#!/usr/bin/env python3
"""Business Loop R1 orchestrator.

  loop.py run   - one full cycle for the selected opportunity (idempotent project)
  loop.py tick  - continuation: execute READY work items routed by the last cycle
  loop.py summary - Nova/operator summary

Nexus is authoritative (data/governed/business_loop). n8n may call `tick` on a
schedule; it holds no project state.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

from business_loop import departments as D  # noqa: E402
from business_loop.project_state import ProjectStore, new_id, now  # noqa: E402
from nexus_agent_platform.company_workflow import build_handoff, nonterminal_next_action, result_contract, validate_actionable_handoff  # noqa: E402

VENTURE_ID = "vnt_holiday_commerce_pilot_2026"
OPPORTUNITY_ID = "opp_holiday_ceramic_mug_2026"
OPPORTUNITY_NAME = "The 6:12 AM Quiet Ritual - holiday ceramic mug (Holiday Commerce Pilot)"
SUMMARY_PATH = ROOT / "reports/business_loop/business_loop_r1_nova_summary_latest.json"


def ensure_project(store: ProjectStore) -> dict:
    existing = [p for p in store._latest("projects", "project_id").values() if p["opportunity_id"] == OPPORTUNITY_ID and p["status"] == "ACTIVE"]
    if existing:
        return existing[0]
    return store.save_project({
        "project_id": new_id("proj"), "venture_id": VENTURE_ID, "opportunity_id": OPPORTUNITY_ID, "opportunity_name": OPPORTUNITY_NAME,
        "status": "ACTIVE", "current_department": "RESEARCH", "current_stage": "RESEARCH", "owner_engine": "NEXUS_BUSINESS_LOOP_R1",
        "next_action": "Research handoff", "blockers": [], "approvals_required": [], "artifacts": [], "metrics": {}, "handoff_history": [],
        "cost_ledger": {"ai_model": 0.0, "media": 0.0, "platform": 0.0, "ad_spend": 0.0, "other": 0.0, "unauthorized": 0.0},
        "cycle": 0, "created_at": now()})


def _handoff(store: ProjectStore, project: dict, src_item: dict, dst_dept: str, dst_stage: str, *, summary: str, data: Any,
             artifacts: list, next_action: str) -> tuple[dict, dict]:
    dst = store.open_work_item(project, dst_dept, dst_stage, next_action)
    case = {"case_id": project["project_id"], "objective": project["opportunity_name"], "status": project["status"],
            "current_phase": dst_stage, "findings": [{"summary": summary}], "expected_output": f"{dst_stage} output"}
    env = build_handoff(case=case, request_id=new_id("ho"), to_department=dst_dept, work=next_action, why=summary,
                        from_department=src_item["department"], return_to="ANALYSIS", expected_output=f"{dst_stage} output")
    env.update({"handoff_id": env["directive_id"], "project_id": project["project_id"], "venture_id": project["venture_id"],
                "opportunity_id": project["opportunity_id"], "SOURCE_WORK_ITEM": src_item["work_item_id"], "DESTINATION_WORK_ITEM": dst["work_item_id"],
                "SUMMARY": summary, "DATA": data, "ARTIFACTS": artifacts, "NEXT_ACTION": next_action, "STATUS": "DELIVERED",
                "TIMESTAMP": now(), "manual_ray_handoff": False, "transition": f"{src_item['department']}->{dst_dept}"})
    env["contract_validation"] = validate_actionable_handoff(env)
    store.save_handoff(env)
    dst = store.save_work_item(dst, source_handoff_id=env["handoff_id"])
    project = store.save_project(project, current_department=dst_dept, current_stage=dst_stage, next_action=next_action,
                                 handoff_history=list(project.get("handoff_history") or []) + [env["handoff_id"]])
    return project, dst


def _run(store: ProjectStore, project: dict, item: dict, fn: Callable[[], dict]) -> tuple[dict, dict | None, dict]:
    """Run one department step. Recoverable failures are recorded + routed; the project stays ACTIVE."""
    item = store.save_work_item(item, status="RUNNING", attempts=int(item.get("attempts", 0)) + 1)
    try:
        res = fn()
    except D.DepartmentFailure as exc:
        route = nonterminal_next_action({"NOT_ENOUGH_EVIDENCE": "INSUFFICIENT_DATA"}.get(exc.code, "PROVIDER_FAILURE"), exc.detail)
        store.event(project, "RECOVERABLE_FAILURE", department=item["department"], code=exc.code, detail=exc.detail, route=route)
        item = store.save_work_item(item, status="RETRY_SCHEDULED", failure=exc.code, reroute=route)
        project = store.save_project(project, blockers=list(project.get("blockers") or []) + [f"{item['department']}:{exc.code}"])
        return project, None, item
    for issue in res.get("issues", []):
        store.event(project, "ISSUE_RECORDED", department=item["department"], **issue)
    ledger = dict(project["cost_ledger"])
    for k, v in (res.get("cost") or {}).items():
        ledger[k] = round(ledger.get(k, 0.0) + float(v or 0), 6)
    item = store.save_work_item(item, status="DONE", outputs=res["output"], artifacts=res.get("artifacts", []))
    project = store.save_project(project, cost_ledger=ledger, artifacts=list(dict.fromkeys((project.get("artifacts") or []) + res.get("artifacts", []))))
    return project, res, item


def _add_approvals(project: dict, new: list[dict]) -> list[dict]:
    merged = {a.get("approval_request_id") or a.get("approval_kind"): a for a in (project.get("approvals_required") or [])}
    for a in new:
        merged[a.get("approval_request_id") or a.get("approval_kind")] = a
    return list(merged.values())


def run_cycle(store: ProjectStore | None = None, *, hooks: dict | None = None) -> dict:
    """Full Research->...->Next Action cycle. ``hooks`` injects department callables (tests/failure injection)."""
    store = store or ProjectStore(); h = hooks or {}
    project = ensure_project(store)
    project = store.save_project(project, cycle=int(project.get("cycle", 0)) + 1)
    for old in store.work_items(project["project_id"]):  # a new cycle re-plans: earlier open continuations are superseded
        if old["status"] in {"READY", "WAITING"} and old["stage"] != "RESEARCH_RETRY":
            store.save_work_item(old, status="SUPERSEDED", superseded_by_cycle=project["cycle"])
    item = store.open_work_item(project, "RESEARCH", "RESEARCH", "Produce structured opportunity handoff")
    project, r, item = _run(store, project, item, lambda: h.get("research", D.research)(project))
    if r is None:  # insufficient evidence: route back to Research with a different method, continue with what is known
        retry_route = item["reroute"]
        project, item = _handoff(store, project, item, "RESEARCH", "RESEARCH_RETRY", summary="Research evidence insufficient; rerouted",
                                 data={"failure": item.get("failure"), "route": retry_route}, artifacts=[], next_action=retry_route["next_action"])
        return {"project": project, "halted_stage": None, "note": "research rerouted; project ACTIVE"}
    rh = r["output"]
    for stale in store.work_items(project["project_id"]):  # an earlier insufficient-evidence retry is now satisfied
        if stale["stage"] == "RESEARCH_RETRY" and stale["status"] in {"READY", "WAITING"}:
            store.save_work_item(stale, status="SUPERSEDED", superseded_by=item["work_item_id"])
    project, mk_item = _handoff(store, project, item, "MARKETING", "MARKETING", summary="Research handoff: opportunity, evidence, directives",
                                data=rh, artifacts=r["artifacts"], next_action="Build bounded campaign brief from research handoff")
    project, m, mk_item = _run(store, project, mk_item, lambda: h.get("marketing", D.marketing)(project, rh))
    brief = m["output"]
    project, cr_item = _handoff(store, project, mk_item, "CREATIVE", "CREATIVE", summary="Creative production brief + hooks + captions plan",
                                data={k: brief[k] for k in ("HOOKS", "CTA", "CREATIVE_PRODUCTION_BRIEF", "CONTENT_PLAN")}, artifacts=[],
                                next_action="Produce primary image + 2 formats + captions; QA with truth validator")
    project, co_item = _handoff(store, project, mk_item, "COMMERCE", "COMMERCE", summary="Product page brief + offer + pricing directives",
                                data={"PRODUCT_PAGE_BRIEF": brief["PRODUCT_PAGE_BRIEF"], "OFFER": brief["OFFER"], "COMMERCE_DIRECTIVES": rh["COMMERCE_DIRECTIVES"]},
                                artifacts=[], next_action="Stage one sellable offer on existing storefront path")
    project, c, cr_item = _run(store, project, cr_item, lambda: h.get("creative", D.creative)(project, brief))
    cout = c["output"] if c else None
    project, co, co_item = _run(store, project, co_item, lambda: h.get("commerce", D.commerce)(project, rh, brief, cout))
    project, back = _handoff(store, project, cr_item, "MARKETING", "MARKETING_REVIEW", summary="Creative assets + QA returned to Marketing",
                             data={"qa": (cout or {}).get("CREATIVE_QA"), "assets": [a["asset_id"] for a in (cout or {}).get("ASSETS", [])]},
                             artifacts=c["artifacts"] if c else [], next_action="Accept assets for distribution")
    store.save_work_item(back, status="DONE", outputs={"decision": "ACCEPTED_FOR_DISTRIBUTION" if cout and cout["CREATIVE_QA"]["status"] == "PASS" else "COPY_FIX_REQUIRED"})
    project, di_item = _handoff(store, project, cr_item, "DISTRIBUTION", "DISTRIBUTION", summary="Approved creative for channel packaging",
                                data={"captions": (cout or {}).get("CAPTIONS"), "assets": (cout or {}).get("ASSETS")}, artifacts=c["artifacts"] if c else [],
                                next_action="Prepare posts; create approval card")
    project, _di2 = _handoff(store, project, co_item, "DISTRIBUTION", "DISTRIBUTION", summary="Offer + purchase URL for posts",
                             data=co["output"]["OFFER"], artifacts=[], next_action="Use offer URL in all posts")
    store.save_work_item(_di2, status="MERGED", merged_into=di_item["work_item_id"])
    project = store.save_project(project, approvals_required=_add_approvals(project, [co["output"]["APPROVAL_REQUEST"]]))
    project, d, di_item = _run(store, project, di_item, lambda: h.get("distribution", D.distribution)(project, brief, cout, co["output"]))
    if d:
        project = store.save_project(project, approvals_required=_add_approvals(project, d["output"]["APPROVAL_REQUIRED"]))
    dout = d["output"] if d else {"PUBLICATION_STATUS": "DISTRIBUTION_RETRY_SCHEDULED", "APPROVAL_REQUIRED": []}
    project, me_item = _handoff(store, project, di_item, "METRICS", "METRICS", summary=f"Publication {dout['PUBLICATION_STATUS']}; measure existing live posts",
                                data={"publication": dout["PUBLICATION_STATUS"]}, artifacts=d["artifacts"] if d else [],
                                next_action="Ingest real platform + store metrics")
    project, me, me_item = _run(store, project, me_item, lambda: h.get("metrics", D.metrics)(project))
    if me:
        project = store.save_project(project, metrics=me["output"]["SOCIAL_SUMMARY"] | {"store": me["output"]["STORE"]})
    project, an_item = _handoff(store, project, me_item, "ANALYSIS", "ANALYSIS", summary="Metrics ready" if me else "Metrics unavailable; analyse with gap",
                                data=me["output"] if me else {"metrics": "UNAVAILABLE"}, artifacts=[], next_action="Evidence-only analysis + next best action")
    project, a, an_item = _run(store, project, an_item, lambda: h.get("analysis", D.analysis)(project, me["output"] if me else None, dout, co["output"]))
    nba = a["output"]["NEXT_BEST_ACTION"]
    directive = result_contract(result="CYCLE_COMPLETE", interpretation=a["output"]["WHAT_HAPPENED"], what_changed="Cycle 1 executed end to end",
                                why_changed="Business loop R1", learned="; ".join(a["output"]["WHAT_IS_UNKNOWN"]), recommendation=nba["why"],
                                recommended_changes=a["output"]["WHAT_SHOULD_CHANGE"], next_owner=nba["owner"], next_directive=nba["action"],
                                return_to="ANALYSIS", ray_required=False, case_status="ACTIVE")
    project, nx = _handoff(store, project, an_item, nba["owner"], f"CONTINUATION:{nba['action']}", summary=nba["why"],
                           data={"directive": directive, "analysis": a["output"]}, artifacts=[], next_action=nba["action"])
    project = store.save_project(project, status="ACTIVE", continuation_work_item=nx["work_item_id"], last_analysis=a["output"])
    if me is None:  # metrics outage: schedule a retry in parallel with the continuation
        store.open_work_item(project, "METRICS", "METRICS_RETRY", "Retry metric ingestion next cycle")
    return {"project": project, "continuation": nx}


# ---------------------------------------------------------------- continuation
def _marketing_variant(store, project, item) -> dict:
    last = project["last_analysis"]
    plan = {"variant_hook": "H2", "variant_text": "Zero snowflakes. Zero Santas. Just a quiet ceramic mug for slow winter mornings.",
            "control_hook": "H1", "measurement": "UTM utm_content=H1 vs H2 on equal square format", "based_on": last["NEXT_BEST_ACTION"]["evidence"]}
    return {"output": plan, "next": ("CREATIVE", "CREATIVE_VARIANT", "Render H2 square variant for A/B")}


def _creative_variant(store, project, item) -> dict:
    handoff = next((h for h in store.handoffs(project["project_id"]) if h["handoff_id"] == item.get("source_handoff_id")), {})
    text = (handoff.get("DATA") or {}).get("variant_text") or "A quiet ceramic mug for slow winter mornings."
    out = D.ROOT / "dist/creative/business_loop" / project["project_id"] / "variant_h2_square_1080.jpg"
    D._render(D.HERO_JPG, out, (1080, 1080), text, "The 6:12 AM Ritual - studio preview")
    from product_truth_validator import ProductTruthValidator as Truth
    return {"output": {"asset": D._rel(out), "sha256": D.sha256(out), "qa": Truth.audit_copy(text)},
            "next": ("DISTRIBUTION", "DISTRIBUTION_VARIANT", "Queue H2 variant post behind its own approval card (paused)")}


HANDLERS = {"MARKETING": _marketing_variant, "CREATIVE": _creative_variant}


def tick(store: ProjectStore | None = None, max_items: int = 3) -> dict:
    store = store or ProjectStore()
    project = ensure_project(store)
    done = []
    for item in sorted([w for w in store.work_items(project["project_id"]) if w["status"] == "READY"], key=lambda w: w["created_at"])[:max_items]:
        fn = HANDLERS.get(item["department"])
        if not fn:
            store.save_work_item(item, status="WAITING", wait_reason="approval-gated or no autonomous handler (paused action only)")
            continue
        item = store.save_work_item(item, status="RUNNING")
        res = fn(store, project, item)
        item = store.save_work_item(item, status="DONE", outputs=res["output"])
        dept, stage, action = res["next"]
        project, nxt = _handoff(store, project, item, dept, stage, summary=f"{item['department']} continuation complete", data=res["output"],
                                artifacts=[res["output"].get("asset")] if res["output"].get("asset") else [], next_action=action)
        done.append({"from": item["department"], "to": dept, "work_item": nxt["work_item_id"]})
    return {"project_status": store.project(project["project_id"])["status"], "routed": done}


# --------------------------------------------------------------------- summary
def summary(store: ProjectStore | None = None) -> dict:
    store = store or ProjectStore()
    p = ensure_project(store)
    items = store.work_items(p["project_id"])
    by = lambda dept, stage=None: next((w for w in sorted(items, key=lambda w: w["created_at"], reverse=True)  # noqa: E731
                                        if w["department"] == dept and (stage is None or w["stage"] == stage) and w["status"] == "DONE"), {})
    rs, mk, cr, co, di = by("RESEARCH").get("outputs", {}), by("MARKETING", "MARKETING").get("outputs", {}), by("CREATIVE", "CREATIVE").get("outputs", {}), by("COMMERCE").get("outputs", {}), by("DISTRIBUTION", "DISTRIBUTION").get("outputs", {})
    s = {
        "PROJECT": {k: p.get(k) for k in ("project_id", "venture_id", "opportunity_id", "opportunity_name", "status", "cycle")},
        "CURRENT_STAGE": {"department": p["current_department"], "stage": p["current_stage"]},
        "WHAT_RESEARCH_FOUND": {"summary": rs.get("OPPORTUNITY_SUMMARY"), "evidence_sufficiency": rs.get("EVIDENCE_SUFFICIENCY"),
                                "demand_evidence": rs.get("DEMAND_EVIDENCE"), "questions": rs.get("QUESTIONS_TO_VALIDATE")},
        "MARKETING_PLAN": {"positioning": mk.get("POSITIONING"), "hooks": [h["text"] for h in mk.get("HOOKS", [])], "cta": mk.get("CTA"),
                           "spend": mk.get("SPEND_RECOMMENDATION")},
        "CREATIVE_ASSETS": [{"path": a["path"], "size": a["size"], "hook": a["hook_id"]} for a in cr.get("ASSETS", [])] + ([{"qa": cr["CREATIVE_QA"]["status"]}] if cr else []),
        "COMMERCE_OFFER": {k: (co.get("OFFER") or {}).get(k) for k in ("PRODUCT_NAME", "PRICE", "COST", "MARGIN", "STATUS", "PURCHASE_URL")},
        "DISTRIBUTION_STATUS": {"publication": di.get("PUBLICATION_STATUS"), "channels": di.get("CHANNELS")},
        "METRICS": p.get("metrics"),
        "BLOCKERS": p.get("blockers"),
        "APPROVALS_REQUIRED": p.get("approvals_required"),
        "NEXT_ACTION": {"owner": p["current_department"], "action": p["next_action"]},
        "COSTS": p["cost_ledger"],
        "HANDOFFS": len(store.handoffs(p["project_id"])),
        "generated_at": now(),
    }
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(s, indent=2, default=str) + "\n")
    return s


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["run", "tick", "summary"])
    cmd = ap.parse_args().cmd
    out = run_cycle() if cmd == "run" else tick() if cmd == "tick" else summary()
    print(json.dumps(out if cmd != "run" else {"project_id": out["project"]["project_id"], "status": out["project"]["status"],
                                                "continuation": (out.get("continuation") or {}).get("work_item_id")}, indent=2, default=str))
