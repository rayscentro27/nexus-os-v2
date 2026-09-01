"""Bounded multi-market Trading Lab contracts and deterministic tournament.

Nexus remains authority. This module supplies contracts, bounded generation,
signal/risk separation, replay records, and evidence persistence. It never
places live orders and never imports the legacy Vibe executors.
"""
from __future__ import annotations
import hashlib, json, math, os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Iterable
from nexus_agent_platform.governed import persistence
from .contracts import authority_allows, dependency_state, validate_trading_safety

MARKETS = {"FOREX": {"hours":"session_based","paper":True,"live_authority":"NONE","venue":"OANDA_PRACTICE"}, "CRYPTO": {"hours":"24/7","paper":True,"live_authority":"NONE","venue":"UNCONNECTED"}, "OPTIONS": {"hours":"exchange","paper":True,"live_authority":"NONE","venue":"UNCONNECTED"}}
FAMILIES = ("TREND_FOLLOWING","BREAKOUT","MEAN_REVERSION","MOMENTUM","VOLATILITY","SESSION_BASED","EVENT_DRIVEN","MULTI_TIMEFRAME")
MONEY_MODELS = ("FIXED_NOTIONAL_BASELINE","FIXED_FRACTIONAL","ATR_RISK_SIZING","VOLATILITY_NORMALIZED")
EXIT_MODELS = ("FIXED_STOP","ATR_STOP","VOLATILITY_STOP","TRAILING_STOP","TIME_EXIT","SIGNAL_EXIT")

def _now(): return datetime.now(timezone.utc).isoformat()
def _fp(v): return hashlib.sha256(json.dumps(v,sort_keys=True,default=str).encode()).hexdigest()[:24]

@dataclass(frozen=True)
class MarketAdapter:
    market_type: str; venue: str; instrument: str; hours: str; quote_model: str; price_precision: int; transaction_cost_model: str; position_model: str; risk_model: str; execution_model: str; paper_capability: bool; live_authority: str

@dataclass(frozen=True)
class ExperimentSpec:
    market_type: str; venue: str; instrument: str; strategy_family: str; strategy_id: str; strategy_version: str; timeframe: str; regime: str; parameters: dict[str,Any]; risk_model: str; money_management_model: str; data_period: dict[str,str]
    @property
    def experiment_id(self): return "exp_" + _fp(asdict(self))

def adapters():
    return {"FOREX":MarketAdapter("FOREX","OANDA_PRACTICE","EUR_USD","session_based","bid_ask",5,"spread_plus_slippage","single_currency_pair","pip_and_fractional","next_completed_bar",True,"NONE"),"CRYPTO":MarketAdapter("CRYPTO","UNCONNECTED","BTC_USD","24/7","bid_ask",8,"fee_plus_spread","spot","volatility_and_fractional","paper_simulation",True,"NONE"),"OPTIONS":MarketAdapter("OPTIONS","UNCONNECTED","SPY","exchange","bid_ask",2,"bid_ask_and_multiplier","multi_leg","premium_at_risk_defined_risk","paper_simulation",True,"NONE")}

def options_position(underlying: str, legs: list[dict[str,Any]]) -> dict[str,Any]:
    required={"action","call_put","strike","expiration","quantity","premium"}
    if not legs or any(not required <= set(leg) for leg in legs): raise ValueError("invalid_multi_leg_position")
    return {"strategy_position_id":"pos_"+_fp({"underlying":underlying,"legs":legs}),"underlying":underlying,"legs":legs,"live_authority":"NONE","paper_only":True}

def regime(closes: list[float]) -> str:
    if len(closes)<30: return "UNKNOWN"
    mean=sum(closes[-30:])/30; drift=(closes[-1]-closes[-30])/mean if mean else 0
    vol=(sum((x-mean)**2 for x in closes[-30:])/30)**0.5/mean if mean else 0
    return "HIGH_VOLATILITY" if vol>.01 else "TRENDING" if abs(drift)>.004 else "RANGING"

def _series(rows): return [float(x.get("mid",{}).get("c")) for x in rows if x.get("mid",{}).get("c") is not None]
def signal_returns(rows, *, fast=10, slow=30, cost=0.00015, money_model="FIXED_FRACTIONAL"):
    closes=_series(rows); risk=0.01 if money_model=="FIXED_FRACTIONAL" else .005 if money_model=="VOLATILITY_NORMALIZED" else .01
    rets=[]; entries=[]
    for i in range(max(slow+1,1),len(closes)-1):
        pf=sum(closes[i-slow:i-1][-fast:])/fast; ps=sum(closes[i-slow:i-1])/slow
        f=sum(closes[i-slow+1:i][-fast:])/fast; s=sum(closes[i-slow+1:i])/slow
        if pf<=ps and f>s:
            change=(closes[i+1]*(1-cost)-closes[i]*(1+cost))/closes[i]; rets.append(change*risk); entries.append({"entry_index":i,"exit_index":i+1,"entry_price":closes[i],"exit_price":closes[i+1],"return":change*risk,"signal":"SMA_CROSS_UP","regime":regime(closes[:i+1])})
    return rets,entries

def metrics(returns, *, equity=10000.0):
    curve=[equity];
    for r in returns: curve.append(curve[-1]*(1+r))
    peak=curve[0]; dd=0
    for x in curve: peak=max(peak,x); dd=max(dd,(peak-x)/peak*100)
    avg=sum(returns)/len(returns) if returns else 0; wins=[x for x in returns if x>0]; losses=[x for x in returns if x<0]; pf=sum(wins)/abs(sum(losses)) if losses else (math.inf if wins else 0)
    mean=avg; variance=sum((x-mean)**2 for x in returns)/(len(returns)-1) if len(returns)>1 else 0; sd=variance**.5
    downside=(sum(min(0,x)**2 for x in returns)/(len(returns)-1))**.5 if len(returns)>1 else 0
    return {"trade_count":len(returns),"net_return_pct":round((curve[-1]/equity-1)*100,5),"expectancy_pct":round(avg*100,5),"win_rate_pct":round(len(wins)/len(returns)*100,2) if returns else 0,"profit_factor":round(pf,5) if math.isfinite(pf) else "INF","max_drawdown_pct":round(dd,5),"sharpe":round(avg/sd*math.sqrt(252),5) if sd else None,"sortino":round(avg/downside*math.sqrt(252),5) if downside else None,"equity_curve":[round(x,4) for x in curve]}

def bounded_specs(instrument="EUR_USD", timeframe="H1", data_period=None):
    period=data_period or {"start":"","end":""}; out=[]
    for family,fast,slow in (("TREND_FOLLOWING",10,30),("BREAKOUT",20,50),("MEAN_REVERSION",5,20)):
        out.append(ExperimentSpec("FOREX","OANDA_PRACTICE",instrument,family,"nexus_"+family.lower()+"_v1","1.0",timeframe,"UNKNOWN",{"fast":fast,"slow":slow,"cost":.00015},"bounded_fractional", "FIXED_FRACTIONAL",period))
    return out

def run_tournament(rows: list[dict[str,Any]], *, instrument="EUR_USD", timeframe="H1"):
    if len(rows)<120: raise ValueError("insufficient_data")
    specs=bounded_specs(instrument,timeframe,{"start":rows[0].get("time"),"end":rows[-1].get("time")}); n=len(rows); cut1=n*60//100; cut2=n*80//100; results=[]
    for spec in specs:
        p=spec.parameters; is_r,is_e=signal_returns(rows[:cut1],fast=p["fast"],slow=p["slow"],cost=p["cost"]); val_r,val_e=signal_returns(rows[cut1:cut2],fast=p["fast"],slow=p["slow"],cost=p["cost"]); oos_r,oos_e=signal_returns(rows[cut2:],fast=p["fast"],slow=p["slow"],cost=p["cost"])
        mm={m:metrics(*signal_returns(rows[cut2:],fast=p["fast"],slow=p["slow"],cost=p["cost"],money_model=m)[0:1]) for m in MONEY_MODELS}; oos=metrics(oos_r); score=max(0,min(100,round(25+oos["expectancy_pct"]*100+min(float(oos["profit_factor"]) if oos["profit_factor"]!="INF" else 3,3)*10-oos["max_drawdown_pct"]+min(oos["trade_count"],30))))
        results.append({"experiment_id":spec.experiment_id,"spec":asdict(spec),"data":{"bar_count":n,"split":[cut1,cut2,n]},"in_sample":metrics(is_r),"validation":metrics(val_r),"oos":oos,"oos_entries":oos_e,"money_management":mm,"parameter_stability":[{"fast":x,"slow":y,"oos":metrics(signal_returns(rows[cut2:],fast=x,slow=y,cost=p["cost"])[0])} for x,y in ((p["fast"]-2,p["slow"]),(p["fast"]+2,p["slow"]),(p["fast"],p["slow"]+10))],"score":score,"decision":"PAPER_RESEARCH" if oos["trade_count"]<5 and oos["expectancy_pct"]>=0 else "REJECT","created_at":_now()})
    return sorted(results,key=lambda x:x["score"],reverse=True)

def replay_record(experiment: dict[str,Any]) -> dict[str,Any]:
    oos=experiment["oos"]; trades=[]
    for i,t in enumerate(experiment.get("oos_entries",[])): trades.append({"type":"FILL","sequence":i,"entry_index":t["entry_index"],"exit_index":t["exit_index"],"entry_price":t["entry_price"],"exit_price":t["exit_price"],"risk_model":experiment["spec"]["risk_model"],"money_management_model":experiment["spec"]["money_management_model"]})
    return {"replay_id":"replay_"+_fp(experiment["experiment_id"]),"experiment_id":experiment["experiment_id"],"strategy_id":experiment["spec"]["strategy_id"],"strategy_version":experiment["spec"]["strategy_version"],"market_type":experiment["spec"]["market_type"],"instrument":experiment["spec"]["instrument"],"timeframe":experiment["spec"]["timeframe"],"mode":"BACKTEST","signals":trades,"current_bar_index":0,"metrics":oos,"lookahead_protected":True,"execution_authority":"NONE","created_at":_now()}

def persist_tournament(results, loop_id=None):
    for row in results: persistence.append_record("trading_experiments",{"type":"WP8.5_TOURNAMENT","loop_id":loop_id,"experiment_id":row["experiment_id"],**row})
    persistence.append_record("trading_mcp_audits",{"audit_id":persistence.new_id("mcp"),"resource":"VIBE_TRADING_MCP","status":"UNAVAILABLE","tools":[],"allowlist":[],"denied":["ORDER_PLACEMENT","BROKER_WRITE","LIVE_EXECUTION","SHELL","SYSTEM_MUTATION"],"created_at":_now()})
    return {"persisted":len(results),"status":"PASS"}
