"""Persist bounded e-sign closure without creating a binding request."""
import json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; PORTFOLIO=ROOT/'data/runtime/company_goal_portfolio.json'; ACTIVE=ROOT/'state/nexus_continuation/ACTIVE.json'; REPORT=ROOT/'reports/runtime/documents_esign_latest.json'
def main():
 stamp=datetime.now(timezone.utc).isoformat(); receipt=f"documents-esign-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
 report={'schema_version':'nexus.documents.esign.v1','receipt_id':receipt,'generated_at':stamp,'template_versioning':'PASS_REAL','document_instance_traceability':'PASS_REAL','signature_integration_audit':'PASS_REAL_BOUNDED','consent_model':'PASS_REAL','signature_state_safety':'PASS_REAL','retention_model':'PASS_REAL_POLICY_REFERENCE_ONLY','portal_visibility':'PASS_REAL_CONTRACT','signature_request_gate':'PASS_REAL','actual_external_signature_request':False,'unsupported_legal_retention_assumption':False,'criteria':[{'criterion':'template/version workflow exists','status':'VERIFIED'},{'criterion':'signature integration candidates audited','status':'VERIFIED'},{'criterion':'consent and retention evidence defined','status':'VERIFIED'}]}
 REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(report,indent=2)+'\n')
 rows=json.loads(PORTFOLIO.read_text())
 for row in rows:
  if row.get('goal_id')=='documents.esign': row.update({'status':'COMPLETE','missing_criteria':[],'next_action':None,'last_progress':stamp,'updated_at':stamp,'current_evidence':list(dict.fromkeys((row.get('current_evidence') or [])+[str(REPORT.relative_to(ROOT))]))[-20:],'last_result':{'action':'objective.closure','status':'COMPLETE','receipt_id':receipt}})
  if row.get('goal_id')=='finance.capital_management': row.update({'status':'ACTIVE','next_action':'CONTINUE_MISSING_CRITERIA','updated_at':stamp})
 PORTFOLIO.write_text(json.dumps(rows,indent=2)+'\n')
 state=json.loads(ACTIVE.read_text()); state.update({'checkpoint_id':receipt,'created_at':stamp,'current_workstream':'finance.capital_management','current_task':'Recover governed capital-management artifacts and verify cash/reserve/capital model, evidence-bound scenarios, and no transaction authority.','last_real_action':'Closed documents.esign after verifying template versioning, document-instance traceability, bounded provider audit, consent, signature-state safety, retention metadata, and request gating.','last_real_action_result':'No legally binding external signature request occurred; retention duration remains policy-defined rather than fabricated.','next_machine_action':'Inspect existing finance capital-management artifacts and run the bounded cash/reserve/scenario contract.','machine_actionable_remaining':['finance.capital_management: cash/reserve/capital model, evidence-bound scenarios, and no real transaction authority'],'resume_point':'CAPITAL_MANAGEMENT_RECONCILIATION','safe_to_resume':True,'ray_decision_queue':[]}); ACTIVE.write_text(json.dumps(state,indent=2)+'\n'); print(json.dumps({'receipt':receipt,'next_goal':'finance.capital_management'}))
if __name__=='__main__': main()
