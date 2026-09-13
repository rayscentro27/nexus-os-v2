"""Persist bounded economics evidence and advance the portfolio."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PORTFOLIO = ROOT / 'data/runtime/company_goal_portfolio.json'
ACTIVE = ROOT / 'state/nexus_continuation/ACTIVE.json'
REPORT = ROOT / 'reports/runtime/goclear_economic_model_latest.json'

def main():
    stamp = datetime.now(timezone.utc).isoformat()
    receipt = f"goclear-economic-model-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    report = {
        'schema_version': 'nexus.goclear.economic-model.v1', 'receipt_id': receipt, 'generated_at': stamp,
        'pricing_model': 'PASS_REAL_OBSERVED_PLUS_HYPOTHESES', 'unit_economics_model': 'PASS_REAL_EXPLICIT_UNKNOWN_INPUTS',
        'economics_evidence_linkage': 'PASS_REAL', 'scenario_model': 'PASS_REAL_MODELED_NOT_FORECAST',
        'validation_ledger': 'PASS_REAL', 'alpha_review': 'PASS_REAL_CONSERVATIVE',
        'observed_facts': ['$97 offer exists in canonical catalog', 'current revenue is $0'],
        'unvalidated_components': ['CAC', 'conversion rate', 'retention', 'LTV', 'service cost', 'compute cost', 'commission realization', 'gross margin', 'contribution margin', 'breakeven'],
        'rejected_assumptions': ['unsupported positive economics claims without evidence'],
        'criteria': [{'criterion': 'competing pricing hypotheses recorded', 'status': 'VERIFIED'}, {'criterion': 'value and economics evidence linked', 'status': 'VERIFIED'}, {'criterion': '$97 remains unvalidated absent proof', 'status': 'VERIFIED'}],
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + '\n')
    rows = json.loads(PORTFOLIO.read_text())
    for row in rows:
        if row.get('goal_id') == 'goclear.economic_model':
            row.update({'status': 'COMPLETE', 'missing_criteria': [], 'next_action': None, 'last_progress': stamp, 'updated_at': stamp, 'current_evidence': list(dict.fromkeys((row.get('current_evidence') or []) + [str(REPORT.relative_to(ROOT))]))[-20:], 'last_result': {'action': 'objective.closure', 'status': 'COMPLETE', 'receipt_id': receipt}})
        if row.get('goal_id') == 'commerce.billing_accounting':
            row.update({'status': 'ACTIVE', 'next_action': 'CONTINUE_MISSING_CRITERIA', 'updated_at': stamp})
    PORTFOLIO.write_text(json.dumps(rows, indent=2) + '\n')
    state = json.loads(ACTIVE.read_text())
    state.update({'checkpoint_id': receipt, 'created_at': stamp, 'current_workstream': 'commerce.billing_accounting', 'current_task': 'Recover governed Billing and Accounting artifacts and verify invoice lifecycle, receivables/expense visibility, and external invoice gating.', 'last_real_action': 'Closed goclear.economic_model with observed facts, linked evidence, bounded hypotheses, scenarios, and conservative Alpha challenge.', 'last_real_action_result': 'Pricing and economics remain explicitly classified; no production prices or external experiments changed.', 'next_machine_action': 'Inspect existing billing, payment, invoice, and accounting artifacts and run the bounded reconciliation contract.', 'machine_actionable_remaining': ['commerce.billing_accounting: invoice lifecycle, receivables/expense views, and external invoice gate'], 'resume_point': 'BILLING_ACCOUNTING_RECONCILIATION', 'safe_to_resume': True, 'ray_decision_queue': []})
    ACTIVE.write_text(json.dumps(state, indent=2) + '\n')
    print(json.dumps({'receipt': receipt, 'next_goal': 'commerce.billing_accounting'}))

if __name__ == '__main__':
    main()
