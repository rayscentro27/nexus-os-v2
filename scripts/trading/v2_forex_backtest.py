#!/usr/bin/env python3
"""Small-sample, assumption-labeled EURUSD M30 research harness. No broker calls."""
import argparse, json, math
from datetime import datetime
from pathlib import Path

def ema(xs, n):
    out=[]; alpha=2/(n+1); prev=None
    for x in xs:
        prev=x if prev is None else alpha*x+(1-alpha)*prev; out.append(prev)
    return out
def atr(rows,n=14):
    trs=[]; prev=None
    for r in rows:
        h,l,c=r["h"],r["l"],r["c"]; trs.append(max(h-l,abs(h-(prev if prev is not None else c)),abs(l-(prev if prev is not None else c)))); prev=c
    out=[]
    for i in range(len(trs)): out.append(sum(trs[max(0,i-n+1):i+1])/min(n,i+1))
    return out
def load(path):
    d=json.loads(Path(path).read_text()); raw=d.get("candles",[]); rows=[]
    for c in raw:
        if not c.get("complete"): continue
        m=c.get("mid") or c.get("bid") or {}; rows.append({"t":c["time"],"o":float(m["o"]),"h":float(m["h"]),"l":float(m["l"]),"c":float(m["c"])})
    # Resample contiguous M15 pairs to M30. The source snapshot is OANDA practice data.
    bars=[]
    for i in range(0,len(rows)-1,2):
        a,b=rows[i:i+2]
        if (datetime.fromisoformat(b["t"].replace("Z","+00:00"))-datetime.fromisoformat(a["t"].replace("Z","+00:00"))).total_seconds()!=900: continue
        bars.append({"t":a["t"],"o":a["o"],"h":max(a["h"],b["h"]),"l":min(a["l"],b["l"]),"c":b["c"]})
    return bars
def run(path):
    bars=load(path); closes=[r["c"] for r in bars]; e=ema(closes,20); av=atr(bars,14); trades=[]
    # Explicit working signal assumption: %R(14) leaves oversold/overbought in EMA20 direction.
    wr=[]
    for i in range(len(bars)):
        w=bars[max(0,i-13):i+1]; hi=max(x["h"] for x in w); lo=min(x["l"] for x in w)
        wr.append(-100*(hi-closes[i])/(hi-lo) if hi>lo else -50)
    for i in range(20,len(bars)-1):
        if wr[i-1] <= -80 < wr[i] and closes[i]>e[i]: side=1
        elif wr[i-1] >= -20 > wr[i] and closes[i]<e[i]: side=-1
        else: continue
        entry=bars[i+1]["o"]; stop=entry-side*1.5*av[i]; target=entry+side*3*av[i]
        # One-position, deterministic OHLC stop/target; if both touch same bar, assume stop first.
        exit_px=None; outcome="DATA_END"
        for j in range(i+1,len(bars)):
            r=bars[j]
            stop_hit=(r["l"]<=stop if side==1 else r["h"]>=stop)
            target_hit=(r["h"]>=target if side==1 else r["l"]<=target)
            if stop_hit: exit_px=stop; outcome="STOP"; break
            if target_hit: exit_px=target; outcome="TARGET"; break
        if exit_px is None: exit_px=bars[-1]["c"]
        # 1.5 pip round-trip spread/slippage proxy; swap excluded.
        pips=(exit_px-entry)*side*10000-1.5
        trades.append({"entry_time":bars[i+1]["t"],"side":"LONG" if side==1 else "SHORT","entry":entry,"exit":exit_px,"exit_reason":outcome,"net_pips_proxy":round(pips,2)})
    positives=sum(t["net_pips_proxy"]>0 for t in trades)
    return {"strategy":"EURUSD M30 EMA20 + Williams %R(14) exhaustion re-entry (assumption)","source_file":str(path),"bars":len(bars),"trade_count":len(trades),"trades":trades,"win_rate":round(positives/len(trades),4) if trades else None,"net_pips_proxy":round(sum(t["net_pips_proxy"] for t in trades),2),"live_trading":False,"broker_orders":0,"limitations":["only short OANDA practice snapshot; not a robust historical sample","EMA20 is an explicit test assumption replacing source's unspecified trend baseline; no 200-period warmup","OHLC fills and 1.5-pip spread/slippage are proxies; swaps and event filters not represented","no out-of-sample or statistical edge claim"]}
if __name__=="__main__":
 p=argparse.ArgumentParser(); p.add_argument("--input",required=True); p.add_argument("--output"); a=p.parse_args(); r=run(a.input); s=json.dumps(r,indent=2); Path(a.output).write_text(s+chr(10)) if a.output else print(s)
