"""Python-first Finance ledger and economic preflight engine.

Accounting state, budgets, deduplication, scenarios, and circuit breakers are
deterministic. Unknown values stay unknown; estimates retain provenance.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Mapping
from nexus_agent_platform.governed import persistence

COST_CLASSES = {'FIXED','VARIABLE','EXPERIMENTAL','ONE_TIME','RECURRING','METERED','FREE_CREDIT','FREE_QUOTA','COMPUTE','STORAGE','NETWORK','SOFTWARE','MODEL','GPU','DATA','TRADING_FRICTION','OTHER'}
SCARCITY = {'ABUNDANT','RENEWABLE_DAILY','RENEWABLE_WEEKLY','RENEWABLE_MONTHLY','LIMITED_CREDIT','PAID_METERED','FIXED_INFRASTRUCTURE','UNKNOWN'}
ECONOMIC_STATES = {'UNKNOWN','ESTIMATED','VALIDATION_WORTHY','TESTING','INSUFFICIENT_DATA','BREAK_EVEN_NOT_REACHED','BREAK_EVEN_REACHED','PROFITABLE','UNPROFITABLE','ECONOMICS_DEGRADED'}

def now() -> str: return datetime.now(timezone.utc).isoformat()
def _latest(collection: str, key: str, value: Any) -> dict[str, Any] | None:
    return next((r for r in persistence.read_records(collection) if r.get(key) == value), None)

def record_resource(resource_id: str, provider: str, resource_type: str, department: str, *, consumed: float = 0, starting_balance: float | str = 'UNKNOWN', unit: str = 'units', cash_cost_usd: float | str = 0, estimated_equivalent_cost_usd: float | str = 'UNKNOWN', scarcity_class: str = 'UNKNOWN', source_of_measurement: str = 'UNKNOWN', measurement_confidence: str = 'UNKNOWN', **refs: Any) -> dict[str, Any]:
    row = {'resource_id': resource_id, 'provider': provider, 'resource_type': resource_type, 'department': department, 'consumed': consumed, 'starting_balance': starting_balance, 'remaining_balance': 'UNKNOWN' if starting_balance == 'UNKNOWN' else starting_balance - consumed, 'unit': unit, 'cash_cost_usd': cash_cost_usd, 'estimated_equivalent_cost_usd': estimated_equivalent_cost_usd, 'scarcity_class': scarcity_class, 'source_of_measurement': source_of_measurement, 'measurement_confidence': measurement_confidence, 'started_at': now(), 'completed_at': now(), **refs}
    return persistence.append_record('finance_resource_ledger', row)

def record_cost(receipt_id: str, *, work_order_id: str | None = None, department: str = 'UNKNOWN', initiative_id: str | None = None, money_spent_usd: float = 0, free_credit_consumed: float = 0, quota_consumed: float = 0, compute_consumed: float = 0, storage_consumed: float = 0, estimated_replacement_cost_usd: float | str = 'UNKNOWN', provenance: str = 'ACTUAL', confidence: str = 'UNKNOWN', **refs: Any) -> dict[str, Any]:
    prior = _latest('finance_cost_receipts', 'receipt_id', receipt_id)
    if prior: return {**prior, 'idempotent': True}
    return persistence.append_record('finance_cost_receipts', {'receipt_id': receipt_id, 'work_order_id': work_order_id, 'department': department, 'initiative_id': initiative_id, 'money_spent_usd': money_spent_usd, 'free_credit_consumed': free_credit_consumed, 'quota_consumed': quota_consumed, 'compute_consumed': compute_consumed, 'storage_consumed': storage_consumed, 'estimated_replacement_cost_usd': estimated_replacement_cost_usd, 'provenance': provenance, 'confidence': confidence, 'created_at': now(), **refs})

def record_revenue(receipt_id: str, amount_usd: float | str, state: str, *, provenance: str = 'ACTUAL', confidence: str = 'UNKNOWN', **refs: Any) -> dict[str, Any]:
    prior = _latest('finance_revenue', 'receipt_id', receipt_id)
    if prior: return {**prior, 'idempotent': True}
    if state not in {'PROJECTED','PENDING','INVOICED','RECEIVED','REFUNDED','REVERSED','UNKNOWN'}: raise ValueError('invalid revenue state')
    return persistence.append_record('finance_revenue', {'receipt_id': receipt_id, 'amount_usd': amount_usd, 'state': state, 'provenance': provenance, 'confidence': confidence, 'created_at': now(), **refs})

def break_even(fixed_cost: float, unit_contribution: float) -> dict[str, Any]:
    if not isinstance(unit_contribution, (int, float)) or unit_contribution <= 0:
        return {'break_even_quantity': 'UNKNOWN', 'fixed_cost': fixed_cost, 'unit_contribution': unit_contribution, 'provenance': 'ESTIMATED'}
    return {'break_even_quantity': __import__('math').ceil(fixed_cost / unit_contribution), 'fixed_cost': fixed_cost, 'unit_contribution': unit_contribution, 'provenance': 'ESTIMATED'}

def campaign_preflight(*, campaign_id: str, price: float | str, variable_cost: float | str, upfront_cost: float, continuous_cost: float, max_validation_cost_usd: float, conversion: float | str = 'UNKNOWN', cac: float | str = 'UNKNOWN', scenarios: Mapping[str, Mapping[str, Any]] | None = None) -> dict[str, Any]:
    def scenario(row: Mapping[str, Any]) -> dict[str, Any]:
        raw_p, raw_v = row.get('price', price), row.get('variable_cost', variable_cost)
        p = float(raw_p) if isinstance(raw_p, (int, float)) else 'UNKNOWN'
        v = float(raw_v) if isinstance(raw_v, (int, float)) else 'UNKNOWN'
        customers = int(row.get('customers', 0)); contribution = p-v if p != 'UNKNOWN' and v != 'UNKNOWN' else 'UNKNOWN'
        return {**row, 'revenue': p * customers if contribution != 'UNKNOWN' else 'UNKNOWN', 'contribution': contribution * customers - float(row.get('fixed_cost', upfront_cost)) if contribution != 'UNKNOWN' else 'UNKNOWN', 'break_even': break_even(float(row.get('fixed_cost', upfront_cost)), contribution) if contribution != 'UNKNOWN' else {'break_even_quantity':'UNKNOWN'}}
    result = {'campaign_id': campaign_id, 'price': price, 'variable_cost': variable_cost, 'upfront_cost': upfront_cost, 'continuous_cost': continuous_cost, 'max_validation_cost_usd': max_validation_cost_usd, 'conversion': conversion, 'cac': cac, 'scenarios': {k: scenario(v) for k,v in (scenarios or {'DOWNSIDE':{},'BASE':{},'UPSIDE':{}}).items()}, 'state': 'ESTIMATED', 'recommendation': 'VALIDATE_WITH_NO_SPEND_FIRST', 'provenance': 'ESTIMATED_WITH_UNKNOWN_CAC_CONVERSION_RETENTION', 'created_at': now()}
    persistence.append_record('finance_learning', {'type':'campaign_preflight','created_at':now(),**result}); return result

def trading_preflight(strategy_id: str, *, research_cost: float = 0, data_cost: float = 0, compute_cost: float = 0, spread: float = 0, commission: float = 0, slippage: float = 0, financing: float = 0, gross_expectancy: float | str = 'UNKNOWN', trade_count: int = 0, capital: float | str = 'UNKNOWN') -> dict[str, Any]:
    friction = spread + commission + slippage + financing; net = 'UNKNOWN' if gross_expectancy == 'UNKNOWN' else float(gross_expectancy) - friction
    return {'strategy_id':strategy_id,'research_cost':research_cost,'data_cost':data_cost,'compute_cost':compute_cost,'friction_per_trade':friction,'gross_expectancy':gross_expectancy,'net_expectancy':net,'trade_count':trade_count,'capital':capital,'win_rate_not_used_as_decision':'PASS','economic_state':'INSUFFICIENT_DATA' if trade_count < 30 or net == 'UNKNOWN' else ('PROFITABLE' if net > 0 else 'UNPROFITABLE'),'provenance':'PAPER_OR_ESTIMATED','created_at':now()}

def budget_check(used: Mapping[str, float], budget: Mapping[str, float]) -> dict[str, Any]:
    exceeded = [k for k,v in budget.items() if k.startswith('MAX_') and k.removeprefix('MAX_').lower() in used and float(used[k.removeprefix('MAX_').lower()]) > float(v)]
    status = 'PAUSE_OPTIONAL_CONSUMPTION' if exceeded else 'WITHIN_ENVELOPE'
    return {'status':status,'state':status,'exceeded':exceeded,'overages':exceeded,'preserve_state':True,'escalate_to':'FINANCE_PLUS_OWNER'}

def daily_ledger() -> dict[str, Any]:
    costs = persistence.read_records('finance_cost_receipts'); revenue = persistence.read_records('finance_revenue')
    actual = lambda key: sum(float(r.get(key,0) or 0) for r in costs if isinstance(r.get(key,0),(int,float)))
    received = sum(float(r.get('amount_usd',0) or 0) for r in revenue if r.get('state') == 'RECEIVED' and isinstance(r.get('amount_usd'),(int,float)))
    return {'cash_spent':actual('money_spent_usd'),'free_credit_consumed':actual('free_credit_consumed'),'quota_consumed':actual('quota_consumed'),'compute_consumed':actual('compute_consumed'),'storage_added':actual('storage_consumed'),'replacement_cost_estimate':sum(float(r.get('estimated_replacement_cost_usd',0) or 0) for r in costs if isinstance(r.get('estimated_replacement_cost_usd'),(int,float))),'revenue_received':received,'net_contribution':received-actual('money_spent_usd'),'provenance':'ACTUAL_RECEIPTS_ONLY','generated_at':now()}

def finance_preflight(work_order_id: str, *, department: str, initiative_id: str | None = None,
                      campaign_id: str | None = None, strategy_id: str | None = None,
                      envelope: Mapping[str, Any] | None = None, estimated: Mapping[str, Any] | None = None,
                      authority: str = 'INTERNAL_ONLY', resource_state: str = 'UNKNOWN') -> dict[str, Any]:
    """Governed preflight boundary used before an autonomous work order."""
    envelope = dict(envelope or {}); estimated = dict(estimated or {})
    if authority not in {'INTERNAL_ONLY', 'ADVISORY_ONLY'}:
        decision = 'BLOCK_AUTHORITY'
    else:
        check = budget_check({k: v for k, v in estimated.items() if isinstance(v, (int, float))}, envelope)
        decision = 'BLOCK_BUDGET' if check['exceeded'] else ('UNKNOWN_REQUIRES_REVIEW' if resource_state == 'UNKNOWN' and envelope.get('require_known_resource') else 'ALLOW')
    receipt = {'type': 'FINANCE_PREFLIGHT', 'work_order_id': work_order_id, 'department': department, 'initiative_id': initiative_id, 'campaign_id': campaign_id, 'strategy_id': strategy_id, 'envelope': envelope, 'estimated': estimated, 'authority': authority, 'resource_state': resource_state, 'decision': decision, 'created_at': now()}
    persistence.append_record('finance_learning', receipt)
    return receipt

def finance_postrun(work_order_id: str, *, department: str, initiative_id: str | None = None,
                    estimated: Mapping[str, Any] | None = None, actual: Mapping[str, Any] | None = None,
                    status: str = 'COMPLETED', attempt: int = 1, retry_of: str | None = None) -> dict[str, Any]:
    """Persist a post-run cost receipt, including failed and retry attempts."""
    actual = dict(actual or {}); estimated = dict(estimated or {})
    receipt_id = f'finance-postrun:{work_order_id}:{attempt}'
    receipt = record_cost(receipt_id, work_order_id=work_order_id, department=department, initiative_id=initiative_id,
                          money_spent_usd=float(actual.get('cash_cost_usd', actual.get('money_spent_usd', 0)) or 0),
                          free_credit_consumed=float(actual.get('free_credit_consumed', 0) or 0),
                          quota_consumed=float(actual.get('quota_consumed', 0) or 0),
                          compute_consumed=float(actual.get('compute_minutes', actual.get('compute_consumed', 0)) or 0),
                          storage_consumed=float(actual.get('storage_bytes', actual.get('storage_consumed', 0)) or 0),
                          estimated_replacement_cost_usd=actual.get('estimated_replacement_cost_usd', 'UNKNOWN'),
                          provenance='ACTUAL', confidence='HIGH', status=status, attempt=attempt, retry_of=retry_of,
                          model_tokens=actual.get('model_tokens', 0), gpu_minutes=actual.get('gpu_minutes', 0))
    variance = {key: {'estimated': estimated.get(key, 'UNKNOWN'), 'actual': actual.get(key, 0), 'difference': (actual.get(key, 0) - estimated[key]) if isinstance(actual.get(key), (int, float)) and isinstance(estimated.get(key), (int, float)) else 'UNKNOWN'} for key in set(estimated) | set(actual)}
    return {'receipt': receipt, 'status': status, 'attempt': attempt, 'variance': variance, 'failed_work_still_accounted': status not in {'COMPLETED', 'PASS'}}

def finance_rollup(*, department: str | None = None, initiative_id: str | None = None) -> dict[str, Any]:
    rows = persistence.read_records('finance_cost_receipts')
    if department: rows = [r for r in rows if r.get('department') == department]
    if initiative_id: rows = [r for r in rows if r.get('initiative_id') == initiative_id]
    numeric = lambda key: sum(float(r.get(key, 0) or 0) for r in rows if isinstance(r.get(key, 0), (int, float)))
    return {'department': department, 'initiative_id': initiative_id, 'work_orders': sorted({r.get('work_order_id') for r in rows if r.get('work_order_id')}), 'cash_cost_usd': numeric('money_spent_usd'), 'free_credit_consumed': numeric('free_credit_consumed'), 'quota_consumed': numeric('quota_consumed'), 'compute_consumed': numeric('compute_consumed'), 'storage_consumed': numeric('storage_consumed'), 'estimated_replacement_cost_usd': numeric('estimated_replacement_cost_usd'), 'provenance': 'ACTUAL_RECEIPTS_ONLY'}

def run_bounded_dry_run() -> dict[str, Any]:
    """Run a local, no-spend proof across the scheduler's department boundary."""
    jobs = [('alpha-dry-run', 'ALPHA'), ('creative-dry-run', 'CREATIVE'), ('growth-dry-run', 'GROWTH'), ('trading-dry-run', 'TRADING'), ('finance-dry-run', 'FINANCE')]
    results = []
    for work_order_id, department in jobs:
        pre = finance_preflight(work_order_id, department=department, initiative_id='wp8_14b_dry_run', envelope={'MAX_CASH_COST_USD': 0}, estimated={'cash_cost_usd': 0}, resource_state='UNKNOWN')
        post = finance_postrun(work_order_id, department=department, initiative_id='wp8_14b_dry_run', estimated={'cash_cost_usd': 0}, actual={'cash_cost_usd': 0}, status='COMPLETED')
        results.append({'work_order_id': work_order_id, 'department': department, 'preflight': pre, 'postrun': post})
    summary = {'type': 'FINANCE_DRY_RUN', 'jobs': results, 'daily_ledger': daily_ledger(), 'company_rollup': finance_rollup(initiative_id='wp8_14b_dry_run'), 'authority': 'INTERNAL_ONLY', 'publication': False, 'created_at': now()}
    persistence.append_record('finance_learning', summary)
    return summary
