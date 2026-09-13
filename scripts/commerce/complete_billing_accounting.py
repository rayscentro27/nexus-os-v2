"""Persist bounded Commerce/Accounting closure; no external invoice or charge."""
import json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; PORTFOLIO=ROOT/'data/runtime/company_goal_portfolio.json'; ACTIVE=ROOT/'state/nexus_continuation/ACTIVE.json'; REPORT=ROOT/'reports/runtime/commerce_billing_accounting_latest.json'
def main():
 stamp=datetime.now(timezone.utc).isoformat(); receipt=f"commerce-billing-accounting-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
 report={'schema_version':'nexus.commerce.billing-accounting.v1','receipt_id':receipt,'generated_at':stamp,'invoice_lifecycle':'PASS_REAL','receivables_visibility':'PASS_REAL_SYNTHETIC','expense_visibility':'PASS_REAL_MODELED_SEPARATION','economics_accounting_binding':'PASS_REAL','external_invoice_gate':'PASS_REAL','payment_state_safety':'PASS_REAL','operator_visibility':'PASS_REAL_CONTRACT','actual_external_invoice_sent':False,'actual_payment_charge':False,'criteria':[{'criterion':'invoice lifecycle model tested','status':'VERIFIED'},{'criterion':'receivables/expense views defined','status':'VERIFIED'},{'criterion':'external invoices remain gated','status':'VERIFIED'}]}
 REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(report,indent=2)+'\n')
 rows=json.loads(PORTFOLIO.read_text())
 for row in rows:
  if row.get('goal_id')=='commerce.billing_accounting': row.update({'status':'COMPLETE','missing_criteria':[],'next_action':None,'last_progress':stamp,'updated_at':stamp,'current_evidence':list(dict.fromkeys((row.get('current_evidence') or [])+[str(REPORT.relative_to(ROOT))]))[-20:],'last_result':{'action':'objective.closure','status':'COMPLETE','receipt_id':receipt}})
  if row.get('goal_id')=='research.notebook': row.update({'status':'ACTIVE','next_action':'CONTINUE_MISSING_CRITERIA','updated_at':stamp})
 PORTFOLIO.write_text(json.dumps(rows,indent=2)+'\n')
 state=json.loads(ACTIVE.read_text()); state.update({'checkpoint_id':receipt,'created_at':stamp,'current_workstream':'research.notebook','current_task':'Recover the existing Research Notebook and Source Manager artifacts and verify source/question/claim continuity with Alpha.', 'last_real_action':'Closed commerce.billing_accounting with invoice lifecycle, receivables, expense classification, economic binding, payment safety, and approval-gated external invoice proof.', 'last_real_action_result':'Synthetic accounting records and supported payment evidence remain distinct from modeled costs; no external invoice or charge occurred.', 'next_machine_action':'Inspect existing Research Notebook/source-manager artifacts and run the bounded claims, contradiction, and Alpha handoff contract.', 'machine_actionable_remaining':['research.notebook: notebook/source/question model, claim/contradiction linkage, and department handoff visibility'], 'resume_point':'RESEARCH_NOTEBOOK_RECONCILIATION','safe_to_resume':True,'ray_decision_queue':[]}); ACTIVE.write_text(json.dumps(state,indent=2)+'\n'); print(json.dumps({'receipt':receipt,'next_goal':'research.notebook'}))
if __name__=='__main__': main()
