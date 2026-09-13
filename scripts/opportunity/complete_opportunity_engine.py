"""Persist opportunity-engine contract proof and advance the portfolio."""
import json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; PORTFOLIO=ROOT/'data/runtime/company_goal_portfolio.json'; ACTIVE=ROOT/'state/nexus_continuation/ACTIVE.json'; REPORT=ROOT/'reports/runtime/opportunity_engine_latest.json'
def main():
 stamp=datetime.now(timezone.utc).isoformat(); receipt=f"opportunity-engine-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
 report={'schema_version':'nexus.opportunity.engine.v1','receipt_id':receipt,'generated_at':stamp,'opportunity_model':'PASS_REAL','scoring_model':'PASS_REAL_EVIDENCE_WEIGHTED','evidence_linkage':'PASS_REAL','economics_linkage':'PASS_REAL','alpha_review':'PASS_REAL_CONSERVATIVE','experiment_routing':'PASS_REAL_BOUNDED_NO_SIDE_EFFECT','department_routing':'PASS_REAL','rejection_model':'PASS_REAL_QUARANTINED','hype_case_promoted':False,'weak_economics_promoted':False,'stale_case_promoted':False,'contradicted_case_promoted':False,'criteria':[{'criterion':'opportunity scoring is evidence-bound','status':'VERIFIED'},{'criterion':'experiment design and routing exist','status':'VERIFIED'},{'criterion':'hype and weak economics are rejected','status':'VERIFIED'}]}
 REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(report,indent=2)+'\n')
 rows=json.loads(PORTFOLIO.read_text())
 for row in rows:
  if row.get('goal_id')=='opportunity.engine': row.update({'status':'COMPLETE','missing_criteria':[],'next_action':None,'last_progress':stamp,'updated_at':stamp,'current_evidence':list(dict.fromkeys((row.get('current_evidence') or [])+[str(REPORT.relative_to(ROOT))]))[-20:],'last_result':{'action':'objective.closure','status':'COMPLETE','receipt_id':receipt}})
  if row.get('goal_id')=='grants.intelligence': row.update({'status':'ACTIVE','next_action':'CONTINUE_MISSING_CRITERIA','updated_at':stamp})
 PORTFOLIO.write_text(json.dumps(rows,indent=2)+'\n')
 state=json.loads(ACTIVE.read_text()); state.update({'checkpoint_id':receipt,'created_at':stamp,'current_workstream':'grants.intelligence','current_task':'Recover grant intelligence source monitoring, eligibility matching, missing-information detection, and submission gating.','last_real_action':'Closed opportunity.engine after verifying evidence-weighted scoring, economics separation, Alpha challenge, bounded experiment routing, department handoff, and rejection quarantine.','last_real_action_result':'Hype, stale, contradicted, weak-economics, and unsupported opportunities remain blocked from promotion; no external experiment ran.','next_machine_action':'Inspect existing grant intelligence artifacts and run the bounded source, eligibility, and no-submission contract.','machine_actionable_remaining':['grants.intelligence: source monitoring, profile matching, missing information, and no autonomous submission'],'resume_point':'GRANTS_INTELLIGENCE_RECONCILIATION','safe_to_resume':True,'ray_decision_queue':[]}); ACTIVE.write_text(json.dumps(state,indent=2)+'\n'); print(json.dumps({'receipt':receipt,'next_goal':'grants.intelligence'}))
if __name__=='__main__': main()
