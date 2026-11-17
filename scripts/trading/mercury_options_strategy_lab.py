#!/usr/bin/env python3
"""Bounded Options Lab fixture runner. No broker API, orders, or live mode exists here."""
from __future__ import annotations
import json, os, ssl, sys, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/trading/mercury_options_lab/latest.json'
WHEEL_URL='https://www.youtube.com/watch?v=7RB1semc_6U'
WHEEL_SOURCE_CLAIMS=[
 'Creator claims an upward chart over about 18 months.',
 'Creator requires profitable/positive P-E company, cash rich, low debt; transcript figures differ and are source-time claims.',
 'Creator says no more than two earnings misses in a row and cites four recent beats at video time.',
 'Creator targets 30-DTE 25-30 delta cash-secured puts with at least 2.5% premium ROI; claims 3.5%+ often.',
 'Creator describes 10-15 delta as a lower-premium safer alternative.',
 'Creator targets 30-delta covered calls 15-25 DTE above assignment cost basis.',
 'Creator VIX/cash claims: 20-25% cash at VIX 15-20 and 50% when VIX below 12.',
 'Creator caps cash allocated to one stock at 10%.',
 'Creator expects assignment and cycles covered calls until shares are called away.',
 'Creator cites 90% of options expiring worthless and personal profits; both remain unverified source claims.'
]
CUSTOM_CLAIMS=[
 {'claim':'Sell 3 middle-strike puts; buy 2 lower-strike puts; buy 1 higher-strike put.','evidence_state':'SOURCE_CLAIM','source_reference':'USER_SUPPLIED_STRATEGY_SPEC'},
 {'claim':'Upper strike distance approximately twice lower-wing distance in the source example.','evidence_state':'SOURCE_CLAIM','source_reference':'USER_SUPPLIED_STRATEGY_SPEC'},
 {'claim':'Sideways / low-volatility outlook.','evidence_state':'SOURCE_CLAIM','source_reference':'USER_SUPPLIED_STRATEGY_SPEC'},
 {'claim':'Example debit $7-$7.50 and maximum profit approximately $492-$493.','evidence_state':'SOURCE_CLAIM','source_reference':'USER_SUPPLIED_STRATEGY_SPEC'}]

def now(): return datetime.now(timezone.utc).isoformat()
def load_env():
    sys.path.insert(0,str(ROOT/'scripts/ops'))
    from nexus_runtime_env import load_runtime_env
    load_runtime_env()
def ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:return ssl.create_default_context()
def request(path,method='GET',body=None,prefer=None):
    base=os.environ.get('SUPABASE_URL') or os.environ.get('VITE_SUPABASE_URL'); key=os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    if not base or not key: raise RuntimeError('SUPABASE_SERVICE_ROLE_CONFIGURATION_REQUIRED')
    headers={'apikey':key,'Authorization':'Bearer '+key,'Content-Type':'application/json'}
    if prefer:headers['Prefer']=prefer
    req=urllib.request.Request(base.rstrip('/')+'/rest/v1/'+path,data=None if body is None else json.dumps(body).encode(),headers=headers,method=method)
    try:
        with urllib.request.urlopen(req,timeout=45,context=ssl_context()) as response:return response.status,json.loads(response.read().decode() or '[]')
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f'SUPABASE_HTTP_{exc.code}:{exc.read().decode(errors="replace")}') from exc

def option_pnl(legs,expiry_spot,multiplier=100):
    premium=sum((1 if x['side']=='SELL' else -1)*x['quantity']*x['premium_per_share']*multiplier for x in legs)
    intrinsic=sum((1 if x['side']=='BUY' else -1)*x['quantity']*max(0,(x['strike']-expiry_spot) if x['right']=='PUT' else (expiry_spot-x['strike']))*multiplier for x in legs)
    return {'synthetic_premium_pnl':premium,'synthetic_intrinsic_pnl':intrinsic,'synthetic_option_pnl':premium+intrinsic,'test_fixture':True,'result':'INCONCLUSIVE','confidence':'LOW'}

def experience_row(experiment_id,strategy_id,family,underlying,source_claims,gaps,lesson,modification=None,**extra):
    return {'experiment_id':experiment_id,'strategy_id':strategy_id,'strategy_family':family,'experiment_class':'PRACTICE_EXPERIMENT','underlying':underlying,'asset_class':'SYNTHETIC' if underlying=='TEST_FIXTURE' else 'EQUITY','legs':[],'strikes':[],'strike_spacing':{},'delta_values':{},'bid_ask_spread':{},'open_interest':{},'volume':{},'break_evens':[],'result':'INCONCLUSIVE','confidence':'LOW','sample_quality':'TEST_FIXTURE_NOT_MARKET_SAMPLE','lesson':lesson,'source_claims':source_claims,'verification_gaps':gaps,'candidate_modification':modification or {},'test_fixture':True,'live_trading_enabled':False,'material_loop_incremented':False,**extra}

def main():
    load_env()
    status,settings=request('options_strategy_lab_settings?settings_id=eq.MERCURY_OPTIONS_STRATEGY_LAB&select=*')
    if len(settings)!=1:raise RuntimeError('AUTHORITATIVE_OPTIONS_LAB_SETTINGS_MISSING')
    cfg=settings[0]
    if cfg.get('enabled') is not True:raise RuntimeError('OPTIONS_LAB_DISABLED_BY_SUPABASE_SETTINGS')
    if cfg.get('live_trading_enabled') is not False or cfg.get('autonomous_material_loop_limit')!=2:raise RuntimeError('OPTIONS_SAFETY_SETTINGS_INVALID')
    limits=cfg['practice_limits'];maxruns=min(6,int(limits['max_total_practice_runs']))
    if limits.get('requires_historical_option_chain') is not True:raise RuntimeError('OPTIONS_HISTORICAL_CHAIN_GATE_MUST_REMAIN_ENABLED')
    gaps=['No timestamped historical option chain supplied.','No executable bid/ask, OI, volume, IV/Greeks, fill, fee, slippage, assignment, or expiration evidence.','Candidate is design-only; do not learn strategy performance from this fixture.']
    candidates=[]
    for key,values in [('DTE',[14,45]),('STRIKE_SPACING_RATIO',[1.5,2.5]),('IV_REGIME',['LOW','HIGH'])]:
        for value in values:candidates.append((key,value))
    candidates=candidates[:maxruns]
    rows=[]
    for i,(axis,value) in enumerate(candidates,1):
        rows.append(experience_row(f'options_custom_put_candidate_{axis.lower()}_{str(value).replace(".","_")}_20261007','fixture_custom_multi_leg_put','CUSTOM_MULTI_LEG','TEST_FIXTURE',CUSTOM_CLAIMS,gaps,'One-axis candidate generated. INCONCLUSIVE until a timestamped option-chain replay supplies quotes, fills, IV, assignment and cost inputs.',{'change_type':axis,'value':value,'baseline':{'DTE':30,'upper_to_lower_wing_ratio':2,'IV_REGIME':'MID'},'candidate_rank':i,'requires_historical_option_chain':True},dte=value if axis=='DTE' else None,strike_spacing={'upper_to_lower_ratio':value} if axis=='STRIKE_SPACING_RATIO' else {},theoretical_edge_score=None,execution_feasibility_score=None))
    # Numeric premiums/strikes below only test payoff arithmetic. They are not market quotes.
    legs=[{'side':'SELL','right':'PUT','quantity':3,'strike':100,'premium_per_share':0.1},{'side':'BUY','right':'PUT','quantity':2,'strike':95,'premium_per_share':0.2},{'side':'BUY','right':'PUT','quantity':1,'strike':110,'premium_per_share':0.5}]
    payoff=option_pnl(legs,120)
    rows.append(experience_row('options_custom_put_payoff_calculator_fixture_20261007','fixture_custom_multi_leg_put','CUSTOM_MULTI_LEG','TEST_FIXTURE',CUSTOM_CLAIMS,gaps,'Synthetic payoff calculation smoke test only; creator debit/profit remain SOURCE_CLAIM and the calculation does not validate those amounts.',{'test':'expiration-payoff-calculator','source_example_values_are_not_inputs':True},legs=legs,strikes=[95,100,110],strike_spacing={'lower_wing':5,'upper_wing':10,'upper_to_lower_ratio':2,'synthetic':True},debit_or_credit='SYNTHETIC_TEST_INPUT',option_pnl=payoff['synthetic_option_pnl'],total_strategy_pnl=payoff['synthetic_option_pnl'],theoretical_edge_score=None,execution_feasibility_score=None))
    wheel_claims=[{'claim':c,'evidence_state':'SOURCE_CLAIM','source_reference':WHEEL_URL} for c in WHEEL_SOURCE_CLAIMS]
    wheel={'premium_pnl':400,'underlying_pnl':-1200,'covered_call_pnl':250,'capital_required':10000,'capital_lockup_days':40,'assignment_occurred':True}
    wheel['total_strategy_pnl']=wheel['premium_pnl']+wheel['underlying_pnl']+wheel['covered_call_pnl'];wheel['return_on_capital']=wheel['total_strategy_pnl']/wheel['capital_required']
    wheelrow=experience_row('options_crdo_wheel_accounting_smoke_fixture_20261007','fixture_crdo_wheel','WHEEL','CRDO',wheel_claims,['CRDO historical stock and option-chain data absent; synthetic values below test arithmetic only.','No assignment, recovery, or cost-basis outcomes measured from market data.'],'Accounting smoke test includes premium, assigned-share loss, covered-call PnL, and capital-lockup days. Synthetic only; no CRDO strategy result.',{'test':'wheel-total-economics-accounting','all_pnl_values_are_synthetic':True},**wheel,theoretical_edge_score=None,execution_feasibility_score=None)
    rows.append(wheelrow)
    written=[]
    for row in rows:
        _,saved=request('options_strategy_experience_bank?on_conflict=experiment_id','POST',row,'resolution=merge-duplicates,return=representation')
        written.extend(saved)
    ids=','.join(json.dumps(x['experiment_id']) for x in rows)
    _,readback=request('options_strategy_experience_bank?experiment_id=in.('+ids+')&select=experiment_id,result,test_fixture,live_trading_enabled,material_loop_incremented,candidate_modification')
    if len(readback)!=len(rows):raise RuntimeError(f'OPTIONS_EXPERIENCE_READBACK_COUNT_MISMATCH:{len(readback)}/{len(rows)}')
    if any(x.get('live_trading_enabled') is not False or x.get('material_loop_incremented') is not False or x.get('result')!='INCONCLUSIVE' for x in readback):raise RuntimeError('OPTIONS_SAFETY_OR_EVIDENCE_CLASSIFICATION_FAILED')
    report={'created_at':now(),'lab_enabled':True,'live_trading_enabled':False,'settings_source':'SUPABASE','practice_limits':limits,'options_feeder_template':'OPTIONS_STRATEGY_FEEDER','custom_multi_leg':{'family':'CUSTOM_MULTI_LEG','classification':'RATIO_LIKE_PUT_STRUCTURE','source_claims_preserved':CUSTOM_CLAIMS,'payoff_fixture':payoff,'execution_feasibility':'RESEARCH_REQUIRED','material_loop_incremented':False},'practice_candidate_count':len(candidates),'practice_candidates':[{ 'change_type':k,'value':v,'result':'INCONCLUSIVE','confidence':'LOW','requires_historical_option_chain':True} for k,v in candidates],'wheel':{'source_url':WHEEL_URL,'source_claims_preserved':len(wheel_claims),'accounting_fixture':wheel,'result':'INCONCLUSIVE','confidence':'LOW','market_performance_tested':False},'persisted_rows':len(readback),'remote_readback':'PASS','material_loop_incremented':False,'ray_decision_required':True,'live_orders_placed':False,'next_action':'Research supplies dated historical option-chain data and verifies exact source transcript details; Trading may then run out-of-sample bounded practice.'}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
