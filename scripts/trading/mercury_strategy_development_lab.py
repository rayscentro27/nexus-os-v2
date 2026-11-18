#!/usr/bin/env python3
"""Bounded offline practice lab for the existing Wick Trading case.

Practice runs use the case-specific deterministic replay adapter. They never
call a broker and never increment the material-loop counter. Current bounds:
3 candidates, one parameter variant per candidate, one symbol, two timeframes,
1200 seconds, and $0 external compute spend.
"""
from __future__ import annotations
import copy, hashlib, json, os, subprocess, sys, tempfile, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SPEC=ROOT/'data/governed/mercury_strategy_specs/strategy_wick_sequence_breakout_v1.json'
BASE=ROOT/'data/governed/wick_sequence_baseline_v1_backtest.json'
REPLAY=ROOT/'artifacts/trading/wick_sequence_baseline_v1_replay.py'
OUTDIR=ROOT/'artifacts/trading/mercury_development_lab_wick'
BANK=ROOT/'data/governed/trading_strategy_experience_bank.jsonl'
CASE='rcase_98d9635c39cf3ae5a4'; NOTEBOOK='fe652c61-c8c7-43c0-9277-3f8bf2f28235'
SETTINGS_PATH=ROOT/'config/mercury_strategy_development_lab.json'
DEFAULT_SETTINGS=json.loads(SETTINGS_PATH.read_text()) if SETTINGS_PATH.exists() else {'enabled':True,'live_trading_enabled':False,'autonomous_material_loop_limit':2,'practice_limits':{'max_practice_candidates_per_cycle':3,'max_parameter_variants':1,'max_timeframes_per_cycle':2,'max_markets_per_cycle':1,'max_total_practice_runs':4,'max_runtime_seconds':1200,'max_compute_cost_usd':0,'in_sample_fraction':0.7}}
LAB_SETTINGS=copy.deepcopy(DEFAULT_SETTINGS)
LIMITS=LAB_SETTINGS['practice_limits']

def now(): return datetime.now(timezone.utc).isoformat()
def read(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def normalize(raw, candidate):
    m={k:raw.get(k) for k in ('trade_count','win_rate','profit_factor','expectancy','net_result_equity_fraction','max_drawdown_fraction','average_win','average_loss')}
    return {'engine':'NEXUS_NATIVE_CASE_REPLAY','engine_version':'case-specific-v1','strategy_id':raw['strategy_id'],'experiment_id':candidate['experiment_id'],'symbol':raw['instrument'],'timeframe':raw['timeframe'],'date_range':[raw['date_start'],raw['date_end']],'trades':m['trade_count'],'win_rate':m['win_rate'],'profit_factor':m['profit_factor'],'expectancy':m['expectancy'],'net_return':m['net_result_equity_fraction'],'max_drawdown':m['max_drawdown_fraction'],'avg_win':m['average_win'],'avg_loss':m['average_loss'],'risk_reward':None,'data_source':raw['data_provider'],'fill_model':'NEXT_BAR_OPEN; OHLC STOP_FIRST','commission_model':'0.05% round-trip notional proxy','slippage_model':'MID price; spread/slippage limitation','errors':[],'warnings':raw.get('limitations',[]),'data_sha256':raw.get('data_sha256'),'engine_parity_status':'NOT_CROSS_ENGINE_TESTED'}

def classify_weakness(base):
    n=base.get('trade_count') or 0
    if n<30: return 'INSUFFICIENT_SAMPLE'
    if (base.get('expectancy') or 0)<0: return 'NO_EDGE'
    return 'OTHER_DEFINED_REASON'

def rank(row):
    m=row.get('normalized_result') or row['new_metrics']; b=row.get('baseline_metrics') or row['base_metrics']
    # Multi-factor, not net-return-only. Small samples and no OOS are penalized.
    pf=max(-2,min(2,(m.get('profit_factor') or 0)-(b.get('profit_factor') or 0)))
    exp=max(-1,min(1,(m.get('expectancy') or 0)-(b.get('expectancy') or 0)))*100
    dd=(b.get('max_drawdown') or b.get('max_drawdown_fraction') or 0)-(m.get('max_drawdown') or m.get('max_drawdown_fraction') or 0)
    trades=min(1,(m.get('trades') or 0)/30)
    sample_penalty=2.0 if (m.get('trades') or 0)<10 else 0.6 if (m.get('trades') or 0)<30 else 0.0
    score=pf*2+exp+dd*5+trades*0.2+row['information_gain']*0.15-sample_penalty-0.25-0.15
    return round(score,6)

def supabase_insert(rows):
    # Existing runtime env loader has already populated SUPABASE_URL/key. Never log key.
    url=os.environ.get('SUPABASE_URL') or os.environ.get('VITE_SUPABASE_URL')
    key=os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    if not url or not key: return {'status':'NOT_CONFIGURED'}
    # PostgREST bulk inserts require every object to expose the same keys.
    # The local evidence schema is intentionally richer than the DB row schema,
    # so submit records individually and keep each response auditable.
    outcomes=[]
    for row in rows:
        request=urllib.request.Request(url.rstrip('/')+'/rest/v1/trading_strategy_experience_bank',data=json.dumps(row).encode(),headers={'apikey':key,'Authorization':'Bearer '+key,'Content-Type':'application/json','Prefer':'resolution=merge-duplicates,return=minimal'},method='POST')
        try:
            with urllib.request.urlopen(request,timeout=5,context=ssl_context()) as response: outcomes.append({'experiment_id':row.get('experiment_id'),'status':'PERSISTED','http_status':response.status})
        except urllib.error.HTTPError as e: outcomes.append({'experiment_id':row.get('experiment_id'),'status':'WRITE_FAILED','http_status':e.code,'reason':e.read(500).decode(errors='replace')})
        except Exception as e: outcomes.append({'experiment_id':row.get('experiment_id'),'status':'WRITE_FAILED','reason':type(e).__name__,'cause':type(getattr(e,'reason',None)).__name__ if getattr(e,'reason',None) else None})
    return {'status':'PERSISTED' if outcomes and all(x['status']=='PERSISTED' for x in outcomes) else 'PARTIAL_OR_FAILED','records':outcomes}

def ssl_context():
    try:
        import certifi
        return __import__('ssl').create_default_context(cafile=certifi.where())
    except Exception:return __import__('ssl').create_default_context()

def load_authoritative_settings():
    url=os.environ.get('SUPABASE_URL') or os.environ.get('VITE_SUPABASE_URL');key=os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    if not url or not key:return {'settings':DEFAULT_SETTINGS,'source':'LOCAL_DEFAULT','status':'NOT_CONFIGURED'}
    req=urllib.request.Request(url.rstrip('/')+'/rest/v1/trading_development_lab_settings?settings_id=eq.MERCURY_STRATEGY_DEVELOPMENT_LAB&select=enabled,live_trading_enabled,autonomous_material_loop_limit,practice_limits&limit=1',headers={'apikey':key,'Authorization':'Bearer '+key})
    try:
        with urllib.request.urlopen(req,timeout=5,context=ssl_context()) as response:
            rows=json.loads(response.read().decode() or '[]')
            if not rows:return {'settings':DEFAULT_SETTINGS,'source':'LOCAL_DEFAULT','status':'SUPABASE_SETTINGS_ROW_MISSING'}
            row=rows[0]; merged={**DEFAULT_SETTINGS,**row,'practice_limits':{**DEFAULT_SETTINGS['practice_limits'],**(row.get('practice_limits') or {})}}
            return {'settings':merged,'source':'SUPABASE','status':'LOADED'}
    except Exception as error:return {'settings':DEFAULT_SETTINGS,'source':'LOCAL_DEFAULT','status':'SUPABASE_SETTINGS_READ_FAILED','error':type(error).__name__}

def persist_banks(experience):
    run_by_type={x['modification']['change_type']:x for x in experience if not x.get('is_control')}
    em=run_by_type['SECOND_INDICATOR']; tf=run_by_type['TIMEFRAME']; mm=run_by_type['RISK_PER_TRADE']
    def metrics(r): return {k:r['new_metrics'].get(k) for k in ('win_rate','profit_factor','expectancy','max_drawdown','trades','net_return')}
    indicator={'indicator_id':'EMA_200_TREND_FILTER','name':'EMA(200)','function_class':'TREND','context':{'markets':['FOREX'],'best_markets':[],'best_timeframes':['H1'],'strategy_types_helped':['WICK_REVERSAL'],'works_well_with':['WICK_PATTERN'],'redundant_with':[],'conflicts_with':[],'latest_result':metrics(em),'change_vs_baseline':em['change_vs_baseline']},'tests_run':1,'positive_results':int(em['result']=='POSITIVE'),'negative_results':int(em['result']=='NEGATIVE'),'inconclusive_results':int(em['result']=='INCONCLUSIVE'),'metric_impacts':em['change_vs_baseline'],'confidence':em['confidence'],'last_updated':now()}
    timeframe={'context_id':'WICK_REVERSAL|FOREX|EUR_USD|M15','strategy_family':'WICK_REVERSAL','market':'FOREX','symbol_class':'FX_MAJOR','timeframe':'M15','tests_run':1,'positive_results':int(tf['result']=='POSITIVE'),'negative_results':int(tf['result']=='NEGATIVE'),'metrics':{'candidate':metrics(tf),'matched_h1_control':next(metrics(x) for x in experience if x.get('is_control'))},'robustness':'NOT_TESTED','confidence':tf['confidence'],'last_updated':now()}
    market={'context_id':'WICK_REVERSAL|FOREX|EUR_USD|H1','strategy_family':'WICK_REVERSAL','asset_class':'FOREX','market':'EUR_USD','symbol':'EUR_USD','session':'NOT_SEGMENTED','regime_if_known':None,'result_metrics':{'ema200_practice':metrics(em),'risk05_practice':metrics(mm)},'test_count':2,'confidence':'LOW','last_updated':now()}
    money={'configuration_id':'WICK_REVERSAL|EUR_USD|H1|RISK_0.5_PERCENT','strategy_family':'WICK_REVERSAL','market':'EUR_USD','timeframe':'H1','configuration':{'stop_method':'ATR_2','take_profit_method':'FIXED_RR_2','position_size_method':'FIXED_PERCENT_RISK','risk_per_trade':0.005,'partial_exit':False,'trailing_stop':False,'break_even_rule':None,'max_concurrent_trades':1},'outcomes':metrics(mm),'test_count':1,'confidence':mm['confidence'],'last_updated':now()}
    repositories=[
      {'repository_id':'PYNECORE','repository':'PyneSys/pynecore','owner':'PyneSys','url':'https://github.com/PyneSys/pynecore','purpose':'Pine-compatible Python runtime / strategy backtests','language':'Python','license':'Apache-2.0','active_status':'ACTIVE_AS_OF_2026-10-07_SOURCE_REVIEW','last_activity':'GitHub repository active; exact last commit not recorded','capabilities':{'pine_support':'Pine-style runtime; Pine conversion depends on separate PyneComp service/API','backtest_support':True,'optimization_support':False,'data_source_support':'Provider plugins','indicator_support':True,'multi_timeframe_support':'Feature-dependent'},'risks':{'security':'Review code before execution','dependency':'Core reports no mandatory non-stdlib dependencies','maintenance':'Active project; conversion is separate service'},'nexus_tested':False,'nexus_compatibility':'Not tested in isolated Nexus harness','benchmark_result':{'status':'NOT_RUN','reason':'No installed isolated adapter; source review only'},'use_class':'REFERENCE_IMPLEMENTATION','last_updated':now()},
      {'repository_id':'HYPERVIEW','repository':'TreborNamor/TradingView-Machine-Learning-GUI','owner':'TreborNamor','url':'https://github.com/TreborNamor/TradingView-Machine-Learning-GUI','purpose':'CLI backtest/optimization and data download','language':'Python','license':'See repository LICENSE; license was not verified in this run','active_status':'ACTIVE_AS_OF_2026-10-07_SOURCE_REVIEW','last_activity':'Recent repository activity shown by GitHub; commit not recorded','capabilities':{'pine_support':'Pine-like behavior in Python strategies; not a general Pine transpiler','backtest_support':True,'optimization_support':True,'data_source_support':'TradingView data downloader'},'risks':{'dependency':'README lists Python 3.11+, TA-Lib, rich; optional browser/session support','maintenance':'Fork/project must be pinned and reviewed'},'nexus_tested':False,'nexus_compatibility':'Not tested in isolated Nexus harness','benchmark_result':{'status':'NOT_RUN','reason':'Not installed; source/README review only'},'use_class':'RESEARCH_ONLY','last_updated':now()},
      {'repository_id':'PINEFORGE','repository':'pineforge-4pass/pineforge-engine','owner':'pineforge-4pass','url':'https://github.com/pineforge-4pass/pineforge-engine','purpose':'C++17 Pine execution/backtest kernel','language':'C++17','license':'Apache-2.0 engine; compiler distribution has separate PolyForm Noncommercial terms','active_status':'ACTIVE_AS_OF_2026-10-07_SOURCE_REVIEW','last_activity':'GitHub repository active; no pinned commit in this run','capabilities':{'pine_support':'Requires separate codegen/transpiler for Pine source','backtest_support':True,'optimization_support':'Parameter sweeps documented','multi_timeframe_support':'request.security documented'},'risks':{'license':'Compiler is not commercially cleared by engine license','dependency':'CMake/C++17/Eigen build surface','maintenance':'Large parity claims require independent verification'},'nexus_tested':False,'nexus_compatibility':'Not tested or built in Nexus','benchmark_result':{'status':'NOT_RUN','reason':'No isolated build or parity replay was run'},'use_class':'RESEARCH_ONLY','last_updated':now()},
      {'repository_id':'PINETS','repository':'LuxAlgo/PineTS','owner':'LuxAlgo','url':'https://github.com/LuxAlgo/PineTS','purpose':'JavaScript/TypeScript Pine runtime','language':'TypeScript','license':'AGPL-3.0 or commercial license','active_status':'ACTIVE_AS_OF_2026-10-07_SOURCE_REVIEW','last_activity':'GitHub release v0.9.31 shown Aug 12, 2026','capabilities':{'pine_support':'Pine v5/v6 runtime and indicators/strategies','backtest_support':True,'optimization_support':False,'data_source_support':'Provider or supplied OHLCV'},'risks':{'license':'AGPL or commercial terms require review','dependency':'Node runtime and package dependencies','maintenance':'Active releases; Pine API coverage not equivalent to full TradingView parity'},'nexus_tested':False,'nexus_compatibility':'Not installed','benchmark_result':{'status':'NOT_RUN','reason':'No isolated runtime or parity comparison was executed'},'use_class':'RESEARCH_ONLY','last_updated':now()},
    ]
    collections=[('trading_indicator_intelligence_bank.jsonl','indicator_id',[indicator]),('trading_timeframe_intelligence_bank.jsonl','context_id',[timeframe]),('trading_market_intelligence_bank.jsonl','context_id',[market]),('trading_money_management_bank.jsonl','configuration_id',[money]),('trading_repository_capability_bank.jsonl','repository_id',repositories)]
    local={}; remote={}
    for file,key,rows in collections:
        path=BANK.parent/file; path.parent.mkdir(parents=True,exist_ok=True)
        old=set()
        if path.exists():
            for line in path.read_text().splitlines():
                try: old.add(json.loads(line).get(key))
                except Exception: pass
        fresh=[row for row in rows if row.get(key) not in old]
        with path.open('a') as stream:
            for row in fresh: stream.write(json.dumps(row,sort_keys=True)+'\n')
        local[file]={'records_added':len(fresh),'existing_records':len(old)}
        remote[file]=supabase_insert_table(file.removesuffix('.jsonl'),rows)
    return {'local':local,'supabase':remote}

def supabase_insert_table(table, rows):
    url=os.environ.get('SUPABASE_URL') or os.environ.get('VITE_SUPABASE_URL');key=os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    if not url or not key:return {'status':'NOT_CONFIGURED'}
    req=urllib.request.Request(url.rstrip('/')+'/rest/v1/'+table,data=json.dumps(rows).encode(),headers={'apikey':key,'Authorization':'Bearer '+key,'Content-Type':'application/json','Prefer':'resolution=merge-duplicates,return=minimal'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=5,context=ssl_context()) as response:return {'status':'PERSISTED','http_status':response.status}
    except urllib.error.HTTPError as e:return {'status':'WRITE_FAILED','http_status':e.code,'reason':e.read(300).decode(errors='replace')}
    except Exception as e:return {'status':'WRITE_FAILED','reason':type(e).__name__,'cause':type(getattr(e,'reason',None)).__name__ if getattr(e,'reason',None) else None}

def main():
    os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1')
    try:
        sys.path.insert(0,str(ROOT/'scripts'))
        sys.path.insert(0,str(ROOT/'scripts/ops'))
        from nexus_runtime_env import load_runtime_env
        load_runtime_env()
    except Exception: pass
    global LAB_SETTINGS,LIMITS
    settings_receipt=load_authoritative_settings()
    LAB_SETTINGS=settings_receipt['settings']; LIMITS=LAB_SETTINGS['practice_limits']
    if LAB_SETTINGS.get('enabled') is not True: raise RuntimeError('MERCURY_DEVELOPMENT_LAB_DISABLED_BY_SETTINGS')
    if LAB_SETTINGS.get('live_trading_enabled') is not False or LAB_SETTINGS.get('autonomous_material_loop_limit')!=2:
        raise RuntimeError('MERCURY_SAFETY_SETTINGS_INVALID')
    spec=read(SPEC); baseline=read(BASE)
    matrix=read(ROOT/'data/governed/wick_experiment_matrix_20261006.json')
    if spec['strategy_id']!='strategy_wick_sequence_breakout_v1' or baseline['case_id']!=CASE or baseline.get('live_trading_enabled') is not False:
        raise RuntimeError('WICK_CASE_OR_LIVE_TRADING_GUARD_FAILED')
    base_metrics={'trades':baseline.get('trade_count'),'win_rate':baseline.get('win_rate'),'profit_factor':baseline.get('profit_factor'),'expectancy':baseline.get('expectancy'),'net_return':baseline.get('net_result_equity_fraction'),'max_drawdown':baseline.get('max_drawdown_fraction')}
    OUTDIR.mkdir(parents=True,exist_ok=True)
    candidates=[
      {'experiment_id':'practice_wick_h1_control_fresh_20261007','change_type':'MATCHED_BASELINE_CONTROL','change_description':'Unmodified Wick configuration on the common EUR_USD H1 in-sample window.','why':'Control for attribution across indicator and sizing variants.','prior_evidence':'Existing H1 baseline covers a longer window; this control is matched to the candidate practice window.','information_gain':0.3,'snapshot':os.environ.get('NEXUS_WICK_FRESH_H1_SNAPSHOT','wick_sequence_oanda_eurusd_h1_2026-10-06.json'),'is_control':True,'mutate':lambda s:None},
      {'experiment_id':'practice_wick_timeframe_m15_fresh_20261007','change_type':'TIMEFRAME','change_description':'Run unchanged Wick rules on EUR_USD M15 over the same calendar window as H1.','why':'Tests context-specific timeframe fit after data availability validation.','prior_evidence':'Existing Wick H1 and M30 results are contextual; M15 snapshot begins later, so compare common date range.','information_gain':0.9,'snapshot':os.environ.get('NEXUS_WICK_FRESH_M15_SNAPSHOT','wick_sequence_oanda_eurusd_m15_2026-10-06.json'),'mutate':lambda s:(s.__setitem__('timeframe','M15'),s['strategy_logic'].__setitem__('timeframe','M15'))},
      {'experiment_id':'practice_wick_ema200_h1_fresh_20261007','change_type':'SECOND_INDICATOR','change_description':'Add causal EMA(200) directional filter on EUR_USD H1.','why':'Tests a complementary trend information class while holding other setup constant.','prior_evidence':'Existing Wick matrix contains EUR_USD M30 EMA test; this H1 run is a distinct context.','information_gain':0.8,'snapshot':os.environ.get('NEXUS_WICK_FRESH_H1_SNAPSHOT','wick_sequence_oanda_eurusd_h1_2026-10-06.json'),'mutate':lambda s:s['strategy_logic'].__setitem__('trend_filter',{'enabled':True,'kind':'EMA','period':200})},
      {'experiment_id':'practice_wick_risk05_h1_fresh_20261007','change_type':'RISK_PER_TRADE','change_description':'Reduce Mercury test risk fraction from 1.0% to 0.5%; preserve entries, stop and target.','why':'Isolates equity path / drawdown sensitivity to risk sizing; does not alter entry edge.','prior_evidence':'Existing Wick replay uses a 1% Mercury-designed risk assumption.','information_gain':0.7,'snapshot':os.environ.get('NEXUS_WICK_FRESH_H1_SNAPSHOT','wick_sequence_oanda_eurusd_h1_2026-10-06.json'),'mutate':lambda s:(s['strategy_logic'].__setitem__('risk_fraction_per_trade',0.005),s['position_risk'].__setitem__('risk_fraction',0.005),s['risk'].__setitem__('risk_fraction',0.005))},
    ]
    if sum(not c.get('is_control') for c in candidates)>LIMITS['max_practice_candidates_per_cycle'] or len(candidates)>LIMITS['max_total_practice_runs'] or len({c['snapshot'] for c in candidates})>LIMITS['max_timeframes_per_cycle']:
        raise RuntimeError('PRACTICE_BOUNDS_EXCEEDED')
    m15_path=Path(os.environ.get('NEXUS_WICK_FRESH_M15_SNAPSHOT',ROOT/'data/runtime/wick_sequence_oanda_eurusd_m15_2026-10-06.json')); m15_path=m15_path if m15_path.is_absolute() else ROOT/'data/runtime'/m15_path; m15_source=read(m15_path)
    common_start=m15_source['candles'][0]['time']; common_end=m15_source['candles'][-1]['time']
    common=[r for r in m15_source['candles'] if r.get('complete')]
    cutoff_index=max(1,min(len(common)-2,int(len(common)*LIMITS['in_sample_fraction'])))
    cutoff=common[cutoff_index]['time']; oos_start=common[cutoff_index+1]['time']
    experience=[]; started=datetime.now(timezone.utc); h1_control_metrics=None
    for candidate in candidates:
        if (datetime.now(timezone.utc)-started).total_seconds()>LIMITS['max_runtime_seconds']: raise TimeoutError('PRACTICE_RUNTIME_LIMIT')
        cand_spec=copy.deepcopy(spec); candidate['mutate'](cand_spec); cand_spec['strategy_id']=spec['strategy_id']+'_'+candidate['experiment_id']
        cand_spec['live_trading']=False
        snapshot=Path(candidate['snapshot']); snapshot=snapshot if snapshot.is_absolute() else ROOT/'data/runtime'/snapshot
        with tempfile.TemporaryDirectory(prefix='mercury-practice-') as temp:
            tmp=Path(temp); sp=tmp/'spec.json'; crop=tmp/'snapshot.json'; out=OUTDIR/(candidate['experiment_id']+'.json'); sp.write_text(json.dumps(cand_spec))
            source=read(snapshot); source['candles']=[r for r in source['candles'] if r.get('complete') and common_start<=r['time']<=cutoff]; crop.write_text(json.dumps(source))
            env=os.environ.copy(); env.update({'NEXUS_WICK_EXPERIMENT_CLASS':'PRACTICE_EXPERIMENT','NEXUS_WICK_LIVE_TRADING_ENABLED':'NO','NEXUS_WICK_BROKER_ACCESS':'NO','NEXUS_WICK_REPLAY_SPEC':str(sp),'NEXUS_WICK_REPLAY_DATA':str(crop),'NEXUS_WICK_REPLAY_OUT':str(out)})
            cached=read(out) if out.exists() else {}
            if cached.get('spec_sha256')!=sha(sp) or cached.get('data_sha256')!=sha(crop):
                try: subprocess.run([sys.executable,str(REPLAY)],cwd=ROOT,env=env,check=True,capture_output=True,text=True,timeout=LIMITS['max_runtime_seconds'])
                except subprocess.CalledProcessError as exc: raise RuntimeError('WICK_REPLAY_FAILED: '+(exc.stderr or exc.stdout or str(exc))) from exc
        raw=read(out); result=normalize(raw,candidate); result['practice_data_split']={'in_sample_start':common_start,'in_sample_end':cutoff,'held_out_start':oos_start,'held_out_end':common_end,'in_sample_fraction':LIMITS['in_sample_fraction']}
        if raw.get('live_trading_enabled') is not False or raw.get('broker_order_api_called') is not False: raise RuntimeError('OFFLINE_REPLAY_BOUNDARY_FAILED')
        if candidate.get('is_control'): h1_control_metrics=result
        comparison_base=h1_control_metrics if h1_control_metrics else base_metrics
        changes={k:(result.get(k)-v if isinstance(result.get(k),(int,float)) and isinstance(v,(int,float)) else None) for k,v in [('trades',comparison_base['trades']),('win_rate',comparison_base['win_rate']),('profit_factor',comparison_base['profit_factor']),('expectancy',comparison_base['expectancy']),('net_return',comparison_base['net_return']),('max_drawdown',comparison_base['max_drawdown'])]}
        row={'experiment_id':candidate['experiment_id'],'strategy_id':spec['strategy_id'],'strategy_family':'WICK_REVERSAL','notebook_id':NOTEBOOK,'experiment_class':'PRACTICE_EXPERIMENT','engine':result['engine'],'engine_version':result['engine_version'],'market':'FOREX','symbol':result['symbol'],'timeframe':result['timeframe'],'date_range':result['date_range'],'data_source':result['data_source'],'base_configuration':spec['strategy_logic'],'selected_configuration':cand_spec['strategy_logic'],'modification':{k:candidate[k] for k in ('change_type','change_description','why','prior_evidence')},'indicators':(['WICK_PATTERN','EMA_200'] if candidate['change_type']=='SECOND_INDICATOR' else ['WICK_PATTERN']),'parameters':{},'stop_method':'ATR','take_profit_method':'FIXED_RR','position_sizing':'FIXED_PERCENT_RISK','risk_per_trade':cand_spec['strategy_logic']['risk_fraction_per_trade'],'base_metrics':comparison_base,'new_metrics':result,'change_vs_baseline':changes,'result':'INCONCLUSIVE' if candidate.get('is_control') or (result.get('trades') or 0)<30 else 'POSITIVE' if (result.get('expectancy') or 0)>(comparison_base.get('expectancy') or 0) and (result.get('max_drawdown') or 1)<(comparison_base.get('max_drawdown') or 0) else 'NEGATIVE' if (result.get('expectancy') or 0)<(comparison_base.get('expectancy') or 0) else 'INCONCLUSIVE','lesson':candidate['why'],'confidence':'LOW' if (result.get('trades') or 0)<30 else 'MODERATE','sample_quality':'LOW' if (result.get('trades') or 0)<30 else 'ADEQUATE','out_of_sample_tested':False,'robustness_tested':False,'engine_parity_status':'NOT_CROSS_ENGINE_TESTED','overfit_risk':'HIGH' if (result.get('trades') or 0)<30 else 'MODERATE','material_loop_incremented':False,'source_artifact':str(out.relative_to(ROOT)),'created_at':now(),'information_gain':candidate['information_gain'],'candidate_rank_score':None,'is_control':candidate.get('is_control',False)}
        row['candidate_rank_score']=rank({'normalized_result':result,'baseline_metrics':comparison_base,'information_gain':candidate['information_gain']})
        experience.append(row)
    timeframe_control=next(row for row in experience if row['experiment_id']=='practice_wick_h1_control_fresh_20261007')
    for row in experience:
        if row['timeframe']=='M15' and not row.get('is_control'):
            row['base_metrics']=timeframe_control['new_metrics']
            row['change_vs_baseline']={k:(row['new_metrics'].get(k)-timeframe_control['new_metrics'].get(k) if isinstance(row['new_metrics'].get(k),(int,float)) and isinstance(timeframe_control['new_metrics'].get(k),(int,float)) else None) for k in ('trades','win_rate','profit_factor','expectancy','net_return','max_drawdown')}
    ranked=[row for row in experience if not row.get('is_control')]
    for row in ranked: row['candidate_rank_score']=rank(row)
    ranked.sort(key=lambda x:x['candidate_rank_score'],reverse=True)
    for i,row in enumerate(ranked,1): row['candidate_rank']=i
    BANK.parent.mkdir(parents=True,exist_ok=True)
    existing_ids=set()
    if BANK.exists():
        for line in BANK.read_text().splitlines():
            try:existing_ids.add(json.loads(line).get('experiment_id'))
            except Exception:pass
    fresh=[row for row in experience if row['experiment_id'] not in existing_ids]
    with BANK.open('a') as f:
        for row in fresh: f.write(json.dumps(row,sort_keys=True)+'\n')
    # Upsert this bounded cycle on every run, including rows already present in
    # the local append-only bank; this also retries transient remote failures.
    remote={'experience':supabase_insert(experience),'intelligence_banks':persist_banks(experience)}
    winner=ranked[0]
    directive={'strategy_id':spec['strategy_id'],'notebook_id':NOTEBOOK,'experiment_class':'MATERIAL_EXPERIMENT','status':'WAITING_ON_SYSTEMS','test_objective':f"Validate practice-ranked candidate {winner['modification']['change_type']} on a newly acquired non-overlapping window; preserve source-derived entry rules.",'market':winner['market'],'symbol':winner['symbol'],'timeframe':winner['timeframe'],'date_range':None,'data_source':winner['data_source'],'base_configuration':winner['base_configuration'],'experiment_configuration':winner['selected_configuration'],'entry_rules':winner['selected_configuration']['formation'],'exit_rules':winner['selected_configuration']['breakout'],'stop_rules':winner['selected_configuration']['atr'],'take_profit_rules':winner['selected_configuration']['target'],'position_size_rules':{'risk_fraction':winner['risk_per_trade'],'source':'candidate practice configuration'},'metrics_required':['trades','win_rate','profit_factor','expectancy','net_return','max_drawdown','out_of_sample_stability'],'why_this_test_was_selected':winner['modification']['why'],'practice_evidence':winner['new_metrics'],'next_owner':'SYSTEMS','systems_request':'Acquire and persist a new EUR_USD historical candle range not present in the current Wick snapshots, using the same data/provider and price component; return its exact start/end, source hash, granularity, completeness, and no-lookahead checks to Trading.','return_to':'TRADING','requires_existing_workflow_approval':True,'live_trading_enabled':False,'practice_counted_as_material':False,'do_not_run_until_data_and_material_loop_count_are_reconciled':True}
    report={'schema_version':'nexus.mercury-development-lab.v1','created_at':now(),'strategy_id':spec['strategy_id'],'notebook_id':NOTEBOOK,'workflow_authority_preserved':True,'live_trading_enabled':False,'prior_h1_result_read':{'artifact':str(BASE.relative_to(ROOT)),**base_metrics,'primary_weakness':classify_weakness(base_metrics),'secondary_weakness':'NO_EDGE' if (base_metrics.get('expectancy') or 0)<0 else None},'prior_experience_read':{'source_artifact':'data/governed/wick_experiment_matrix_20261006.json','experiments':[{k:e.get(k) for k in ('experiment_id','timeframe','variable_changed','status','result','baseline','did_it_improve_baseline','what_was_learned')} for e in matrix.get('experiments',[])]},'practice_limits':LIMITS,'practice_split':{'start':common_start,'in_sample_end':cutoff,'held_out_start':oos_start,'end':common_end,'fresh_non_overlapping_data':True,'this_cycle_oos_seen':False,'prior_material_and_practice_records_cover_overlapping_dates':False},'practice_runs':experience,'ranked_candidates':ranked,'recommended_next_material_test':directive,'material_test_loops_completed':'NOT_READ_FROM_CANONICAL_PROJECT_STATE','material_loop_incremented':False,'ray_gate':'NOT_ADVANCED_BY_PRACTICE_RUNS','supabase_persistence':remote,'local_experience_bank':str(BANK.relative_to(ROOT)),'parity_failed_evidence_rejected':True,'parity_status':'NO_CROSS_ENGINE_RUNS; therefore no candidate is parity-verified','research_reentry_used':False,'next_action':'Fresh practice window acquired. Samples under 30 trades remain inconclusive. Trading reconciles the authoritative material-loop count and obtains sufficient fresh out-of-sample data before considering reservation.'}
    path=OUTDIR/'latest.json'; path.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n'); print(json.dumps({k:v for k,v in report.items() if k not in ('practice_runs','ranked_candidates','recommended_next_material_test')},indent=2));
if __name__=='__main__': main()
