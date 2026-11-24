#!/usr/bin/env python3
"""Isolated PyneCore vs Nexus-native SMA3 parity benchmark, indicator-only."""
from __future__ import annotations
import csv,json,math,subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'data/runtime/wick_sequence_oanda_eurusd_m15_fresh_20261007.json'
WORK=Path('/tmp/pyne'); PYNE=Path('/tmp/nexus-mercury-pynecore-venv/bin/pyne')
SCRIPT=WORK/'sma3.py'; CSV=WORK/'eurusd.csv'; PLOT=WORK/'pyne_plot.csv'
REPORT=ROOT/'artifacts/trading/mercury_pynecore_parity_20261007.json'
def main():
 d=json.loads(DATA.read_text()); rows=d['candles']; WORK.mkdir(exist_ok=True)
 with CSV.open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['time','open','high','low','close','volume'])
  for x in rows:
   m=x['mid']; w.writerow([x['time'],m['o'],m['h'],m['l'],m['c'],x.get('volume',0)])
 SCRIPT.write_text('"""\\n@pyne\\n"""\\nfrom pynecore.lib import script, close, ta, plot\\n@script.indicator(title="Nexus SMA3 parity fixture")\\ndef main():\\n    basis = ta.sma(close, 3)\\n    plot(basis, "SMA3")\\n    plot(close > basis, "Above")\\n'.replace('\\n','\n'))
 started=datetime.now(timezone.utc)
 p=subprocess.run([str(PYNE),'run',str(SCRIPT),str(CSV),'--plot',str(PLOT),'--timeframe','15'],cwd=WORK,capture_output=True,text=True,timeout=60)
 elapsed=(datetime.now(timezone.utc)-started).total_seconds()
 if p.returncode: raise RuntimeError('PYNECORE_RUN_FAILED: '+p.stderr[-1200:])
 with PLOT.open(newline='') as f: plotted=list(csv.DictReader(f))
 native=[]
 closes=[float(x['mid']['c']) for x in rows]
 for i,x in enumerate(rows):
  sma=sum(closes[i-2:i+1])/3 if i>=2 else None
  native.append((sma, sma is not None and closes[i]>sma))
 pyne_vals=[None if r['SMA3']=='NaN' else float(r['SMA3']) for r in plotted]
 pyne_signal=[r['Above']=='True' for r in plotted]
 native_signal=[x[1] for x in native]
 diffs=[abs(a-b) for a,b in zip([v for v in pyne_vals if v is not None],[x[0] for x in native if x[0] is not None])]
 entries=[rows[i]['time'] for i in range(1,len(rows)) if native_signal[i] and not native_signal[i-1]]
 exits=[rows[i]['time'] for i in range(1,len(rows)) if not native_signal[i] and native_signal[i-1]]
 trades=min(len(entries),len(exits)); pnls=[]; e=0;x=0
 while e<len(entries) and x<len(exits):
  while x<len(exits) and exits[x]<entries[e]:x+=1
  if x>=len(exits):break
  ei=next(i for i,r in enumerate(rows) if r['time']==entries[e]);xi=next(i for i,r in enumerate(rows) if r['time']==exits[x])
  pnls.append((closes[xi]-closes[ei])/closes[ei]);e+=1;x+=1
 wins=[v for v in pnls if v>0];losses=[v for v in pnls if v<0]
 metrics={'trades':len(pnls),'profit_factor':sum(wins)/abs(sum(losses)) if losses else None,'expectancy':sum(pnls)/len(pnls) if pnls else None,'max_drawdown':None,'net_return':math.prod(1+x for x in pnls)-1 if pnls else 0}
 stream_equal=pyne_signal==native_signal
 value_max_diff=max(diffs) if diffs else None
 report={'benchmark':'PyneCore vs Nexus-native SMA3/close-above signal','experiment_class':'ENGINE_PARITY_BENCHMARK_NOT_STRATEGY_LESSON','symbol':'EUR_USD','timeframe':'M15','data_source':'OANDA_PRACTICE_FRESH_2026-10-07','bars':len(rows),'pinecore_version':'6.10.7','nexus_engine':'NEXUS_NATIVE_SMA3_V1','runtime_seconds':round(elapsed,4),'indicator_values_compared':len(diffs),'indicator_max_abs_difference':value_max_diff,'signal_count_native':sum(1 for i in range(1,len(native_signal)) if native_signal[i]!=native_signal[i-1]),'signal_count_pynecore':sum(1 for i in range(1,len(pyne_signal)) if pyne_signal[i]!=pyne_signal[i-1]),'signal_stream_equal':stream_equal,'entry_timestamps_equal':stream_equal,'exit_timestamps_equal':stream_equal,'entry_timestamps':entries,'exit_timestamps':exits,'trade_metrics':metrics,'engine_parity':'PASS' if stream_equal and value_max_diff is not None and value_max_diff<1e-12 else 'FAIL','lesson_eligible':False,'reason':'SMA3 parity smoke test is a runtime capability benchmark, not Wick strategy evidence or a strategy lesson; no live trading.'}
 REPORT.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('entry_timestamps','exit_timestamps')},indent=2))
if __name__=='__main__':main()
