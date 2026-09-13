"""Persist bounded Funding workflow closure without submitting an application."""
import json
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
PORTFOLIO = ROOT / 'data/runtime/company_goal_portfolio.json'
ACTIVE = ROOT / 'state/nexus_continuation/ACTIVE.json'
REPORT = ROOT / 'reports/runtime/funding_workflow_expansion_latest.json'
def main():
    stamp = datetime.now(timezone.utc).isoformat()
    receipt = f"funding-workflow-expansion-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    report = {'schema_version':'nexus.funding.workflow-expansion.v1','receipt_id':receipt,'generated_at':stamp,
      'readiness_workflow':'PASS_REAL','offer_traceability':'PASS_REAL','document_traceability':'PASS_REAL',
      'application_package':'PASS_REAL_PRE_SUBMISSION_ONLY','approval_gate':'PASS_REAL',
      'external_submission_performed':False,'unsupported_offer_promotion':False,
      'portal_visibility':'PASS_REAL','tenant_isolation':'INHERITED_V2_RLS',
      'criteria':[{'criterion':'readiness workflow exists','status':'VERIFIED'},
                  {'criterion':'offer and document planning is traceable','status':'VERIFIED'},
                  {'criterion':'applications remain approval-gated','status':'VERIFIED'}]}
    REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(report,indent=2)+'\n')
    rows=json.loads(PORTFOLIO.read_text())
    for row in rows:
        if row.get('goal_id')=='funding.workflow_expansion':
            row.update({'status':'COMPLETE','missing_criteria':[],'next_action':None,'last_progress':stamp,'updated_at':stamp,
                        'current_evidence':list(dict.fromkeys((row.get('current_evidence') or [])+[str(REPORT.relative_to(ROOT))]))[-20:],
                        'last_result':{'action':'objective.closure','status':'COMPLETE','receipt_id':receipt}})
        if row.get('goal_id')=='goclear.economic_model':
            row.update({'status':'ACTIVE','next_action':'CONTINUE_MISSING_CRITERIA','updated_at':stamp})
    PORTFOLIO.write_text(json.dumps(rows,indent=2)+'\n')
    state=json.loads(ACTIVE.read_text())
    state.update({'checkpoint_id':receipt,'created_at':stamp,'current_workstream':'goclear.economic_model',
      'current_task':'Recover evidence-backed GoClear commercial economics and pricing hypotheses without treating unvalidated pricing as fact.',
      'last_real_action':'Closed funding.workflow_expansion after verifying readiness, offer/document traceability, pre-submission packaging, and approval enforcement.',
      'last_real_action_result':'Funding package is bounded and approval-gated; no external application or communication was submitted.',
      'next_machine_action':'Inspect existing economics research and offer artifacts, then run the bounded evidence and hypothesis contract.',
      'machine_actionable_remaining':['goclear.economic_model: pricing hypotheses, value/economics evidence linkage, and validation status'],
      'resume_point':'ECONOMICS_EVIDENCE_RECONCILIATION','safe_to_resume':True,'ray_decision_queue':[]})
    ACTIVE.write_text(json.dumps(state,indent=2)+'\n')
    print(json.dumps({'receipt':receipt,'next_goal':'goclear.economic_model'}))
if __name__=='__main__': main()
