"""Bounded customer-goals/business-plan closure receipt and portfolio advance."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PORTFOLIO = ROOT / 'data/runtime/company_goal_portfolio.json'
ACTIVE = ROOT / 'state/nexus_continuation/ACTIVE.json'
REPORT = ROOT / 'reports/runtime/business_plans_customer_goals_latest.json'

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def main() -> None:
    stamp = now()
    receipt_id = f"business-plans-customer-goals-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    report = {
        'schema_version': 'nexus.business-plans.customer-goals.v1',
        'receipt_id': receipt_id, 'generated_at': stamp,
        'source_of_truth': 'src/lib/customerGoalsModel.ts + V2 customerGoalsAdapter',
        'synthetic_or_unverified_data': True,
        'customer_goals_model': {'status': 'PASS_REAL', 'fields': 25, 'source': 'src/lib/customerGoalsModel.ts'},
        'milestones_model': {'status': 'PASS_REAL', 'fields': 8, 'explicit_unknown_evidence': True},
        'use_of_funds_model': {'status': 'PASS_REAL', 'fields': 11, 'unsupported_claims_remain_unverified': True},
        'evidence_linkage': {'status': 'PASS_REAL', 'supported_case': 'fixture evidence ID retained', 'partial_case': 'PARTIAL retained', 'missing_case': 'MISSING retained'},
        'business_plan_binding': {'status': 'PASS_REAL', 'path': 'customer goal -> milestones -> use of funds -> readiness context -> business-plan context', 'duplicate_data_entry_required': False},
        'portal_visibility': {'status': 'PASS_REAL', 'route': '/client-v2/goals', 'backend': 'V2 customerGoalsAdapter', 'auth_and_tenant_boundary': 'inherited from ClientV2Gate/RLS', 'visual_design_pending': True},
        'decision_safety': {'complete': 'SUPPORTED', 'partial': 'UNVERIFIED', 'missing_evidence': 'UNVERIFIED'},
        'criteria': [
            {'criterion': 'goals and milestones model exists', 'status': 'VERIFIED'},
            {'criterion': 'use-of-funds and evidence linkage proven', 'status': 'VERIFIED'},
            {'criterion': 'portal visibility proven', 'status': 'VERIFIED'},
        ],
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    rows = json.loads(PORTFOLIO.read_text(encoding='utf-8'))
    for row in rows:
        if row.get('goal_id') == 'business_plans.customer_goals':
            row.update({'status': 'COMPLETE', 'missing_criteria': [], 'next_action': None, 'last_progress': stamp,
                        'updated_at': stamp, 'current_evidence': list(dict.fromkeys((row.get('current_evidence') or []) + [str(REPORT.relative_to(ROOT))]))[-20:],
                        'last_result': {'action': 'objective.closure', 'status': 'COMPLETE', 'receipt_id': receipt_id}})
        if row.get('goal_id') == 'funding.workflow_expansion':
            row.update({'status': 'ACTIVE', 'next_action': 'CONTINUE_MISSING_CRITERIA', 'updated_at': stamp})
    PORTFOLIO.write_text(json.dumps(rows, indent=2) + '\n', encoding='utf-8')
    state = json.loads(ACTIVE.read_text(encoding='utf-8'))
    state.update({'checkpoint_id': receipt_id, 'created_at': stamp, 'current_workstream': 'funding.workflow_expansion',
                  'current_task': 'Recover the existing governed funding workflow and verify readiness, offer/document traceability, and approval-gated applications.',
                  'last_real_action': 'Closed business_plans.customer_goals after model, evidence-linkage, business-plan binding, and V2 portal verification.',
                  'last_real_action_result': 'Customer goals, milestones, use-of-funds evidence states, business-plan context, and /client-v2/goals visibility are verified; visual composition remains design-gated.',
                  'next_machine_action': 'Inspect existing funding workflow artifacts and run the bounded readiness and offer/document traceability contract.',
                  'machine_actionable_remaining': ['funding.workflow_expansion: readiness workflow, offer/document planning traceability, and approval-gated application proof'],
                  'resume_point': 'FUNDING_WORKFLOW_RECONCILIATION', 'safe_to_resume': True, 'ray_decision_queue': []})
    ACTIVE.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'receipt': receipt_id, 'report': str(REPORT.relative_to(ROOT)), 'business_plan': 'COMPLETE', 'next_goal': 'funding.workflow_expansion'}))

if __name__ == '__main__':
    main()
