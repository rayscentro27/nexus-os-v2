"""Common normalization and parity gate for historical strategy experiments."""
from __future__ import annotations
from typing import Any

REQUIRED=('engine','engine_version','strategy_id','experiment_id','symbol','timeframe','date_range','trades','win_rate','profit_factor','expectancy','net_return','max_drawdown','avg_win','avg_loss','risk_reward','data_source','fill_model','commission_model','slippage_model','errors','warnings')

def normalize_result(raw:dict[str,Any], *, engine:str, engine_version:str, experiment_id:str)->dict[str,Any]:
    trades=raw.get('trades',raw.get('trade_count'))
    return {'engine':engine,'engine_version':engine_version,'strategy_id':raw.get('strategy_id'),'experiment_id':experiment_id,'symbol':raw.get('symbol',raw.get('instrument')),'timeframe':raw.get('timeframe'),'date_range':raw.get('date_range',[raw.get('date_start'),raw.get('date_end')]),'trades':trades,'win_rate':raw.get('win_rate'),'profit_factor':raw.get('profit_factor'),'expectancy':raw.get('expectancy'),'net_return':raw.get('net_return',raw.get('net_result_equity_fraction')),'max_drawdown':raw.get('max_drawdown',raw.get('max_drawdown_fraction')),'avg_win':raw.get('avg_win',raw.get('average_win')),'avg_loss':raw.get('avg_loss',raw.get('average_loss')),'risk_reward':raw.get('risk_reward'),'data_source':raw.get('data_source',raw.get('data_provider')),'fill_model':raw.get('fill_model','NOT_REPORTED'),'commission_model':raw.get('commission_model',raw.get('transaction_cost_round_trip_notional_fraction')),'slippage_model':raw.get('slippage_model','NOT_REPORTED'),'errors':raw.get('errors',[]),'warnings':raw.get('warnings',raw.get('limitations',[]))}

def compare_engine_parity(left:dict[str,Any],right:dict[str,Any],*,timestamp_tolerance_seconds:float=0.0,metric_relative_tolerance:float=0.01)->dict[str,Any]:
    """Fail closed: absent signal/indicator streams cannot be presumed equal."""
    reasons=[]
    if not left.get('signal_timestamps') or not right.get('signal_timestamps'):
        reasons.append('SIGNAL_TIMESTAMPS_MISSING')
    elif left['signal_timestamps'] != right['signal_timestamps']:
        reasons.append('SIGNAL_TIMESTAMPS_DIFFER')
    for key in ('entry_timestamps','exit_timestamps','indicator_values'):
        if key in left or key in right:
            if left.get(key)!=right.get(key): reasons.append(f'{key.upper()}_DIFFER')
    for key in ('trades','win_rate','profit_factor','expectancy','net_return','max_drawdown'):
        a,b=left.get(key),right.get(key)
        if a is None or b is None: reasons.append(f'{key.upper()}_MISSING');continue
        if isinstance(a,(int,float)) and isinstance(b,(int,float)):
            scale=max(abs(float(a)),abs(float(b)),1e-12)
            if abs(float(a)-float(b))/scale>metric_relative_tolerance: reasons.append(f'{key.upper()}_OUT_OF_TOLERANCE')
    return {'engine_parity_status':'PASS' if not reasons else 'FAIL','reasons':reasons,'lesson_eligible':not reasons,'timestamp_tolerance_seconds':timestamp_tolerance_seconds,'metric_relative_tolerance':metric_relative_tolerance}
