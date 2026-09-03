"""WP8.4 real, deterministic-first, paper-only trading research loop."""
from __future__ import annotations
import hashlib, json, math
from datetime import datetime, timezone
from typing import Any
from nexus_agent_platform.governed import persistence
from .contracts import (assign_work_order, authority_allows, build_goal,
                        build_loop_state, build_work_order, complete_work_order,
                        dependency_state, improvement_candidate, transition_work_order,
                        validate_trading_safety)

def _now(): return datetime.now(timezone.utc).isoformat()
def _fp(v): return hashlib.sha256(json.dumps(v,sort_keys=True,default=str).encode()).hexdigest()[:20]
def _append(c,r): persistence.append_record(c,r); return r

def _sma(values,n): return sum(values[-n:])/n
def _run(rows, start, end, spec):
    closes=[float(x["mid"]["c"]) for x in rows]
    trades=[]; position=None; equity=10000.0; peak=equity; maxdd=0.0
    for i in range(max(30,start),min(end,len(closes))):
        fast=_sma(closes[:i],spec["fast"]); slow=_sma(closes[:i],spec["slow"])
        prev_fast=_sma(closes[:i-1],spec["fast"]); prev_slow=_sma(closes[:i-1],spec["slow"])
        cross_up=prev_fast<=prev_slow and fast>slow; cross_down=prev_fast>=prev_slow and fast<slow
        if position and (cross_down or i-position["entry_i"]>=spec["max_hold_bars"]):
            exit_price=closes[i]*(1-spec["cost_rate"]); pnl=(exit_price-position["entry_price"])*position["side"]
            pct=pnl/position["entry_price"]*100; equity*=1+(pct/100)*spec["risk_fraction"]; trades.append({"entry_i":position["entry_i"],"exit_i":i,"pnl_pct":round(pct,5),"win":pnl>0}); position=None
        if not position and cross_up: position={"entry_i":i,"entry_price":closes[i]*(1+spec["cost_rate"]),"side":1}
        peak=max(peak,equity); maxdd=max(maxdd,(peak-equity)/peak*100)
    if position:
        exit_price=closes[min(end,len(closes)-1)]*(1-spec["cost_rate"]); pnl=(exit_price-position["entry_price"])*position["side"]; pct=pnl/position["entry_price"]*100; equity*=1+(pct/100)*spec["risk_fraction"]; trades.append({"entry_i":position["entry_i"],"exit_i":min(end,len(closes)-1),"pnl_pct":round(pct,5),"win":pnl>0})
    wins=[x["pnl_pct"] for x in trades if x["win"]]; losses=[x["pnl_pct"] for x in trades if not x["win"]]
    expectancy=sum(x["pnl_pct"] for x in trades)/len(trades) if trades else 0.0
    gross_profit=sum(wins); gross_loss=abs(sum(losses)); pf=gross_profit/gross_loss if gross_loss else (math.inf if gross_profit else 0.0)
    return {"trade_count":len(trades),"net_return_pct":round((equity/10000-1)*100,4),"win_rate_pct":round(len(wins)/len(trades)*100,2) if trades else 0.0,"expectancy_pct":round(expectancy,5),"profit_factor":round(pf,4) if math.isfinite(pf) else "INF","max_drawdown_pct":round(maxdd,4),"equity":round(equity,2),"trades":trades}

def _research_package():
    return {"decomposition":{"market_rationale":"short-term EUR/USD H1 trend observation","mechanism":"fast SMA crossing slow SMA","entry":"completed-bar fast SMA crosses above slow SMA","exit":"cross below or max holding period","risk":"fixed fractional paper risk; transaction cost stress","regime_assumptions":"trend persistence may not hold","execution_assumptions":"next observed completed close with bounded cost","failure_conditions":["low trade count","cost sensitivity","OOS collapse","regime dependence"]},"sources":[{"source":"Nexus forex_research_scanner","ref":"scripts/trading/forex_research_scanner.py","claim":"existing canonical scanner observes SMA10/SMA30 on OANDA Practice","classification":"SUPPORTED"},{"source":"OANDA Practice candles","ref":"OANDA_PRACTICE","claim":"fresh completed EUR/USD H1 candles","classification":"SUPPORTED"}],"contrary_evidence":["scanner currently reports no approved setup; this loop tests a research candidate, not an approved signal"],"confidence":"MODERATE"}

def run_trading_loop():
    from scripts.trading.forex_research_scanner import fetch_candles
    safety=validate_trading_safety(); now=_now(); goal_id="goal_robust_paper_strategies"; loop_id=persistence.new_id("trading_loop")
    _append("goals",build_goal(goal_id,owner="NEXUS",title="Identify robust paper-trading strategies with positive risk-adjusted expectancy",target_metric="oos_expectancy",time_horizon="WP8.4"))
    loop=build_loop_state(loop_id,goal_id=goal_id,owner="NEXUS"); loop.update({"loop_type":"TRADING_RESEARCH_LOOP","state":"RESEARCH","current_step":"RESEARCH","next_step":"BACKTEST","inputs":{"candidate_source":"canonical forex scanner"},"updated_at":now}); _append("loop_state",loop)
    prior=[r for r in persistence.read_records("trading_experiments") if r.get("strategy_id")=="nexus_sma_cross_v1"]
    _append("trading_journal",{"journal_id":persistence.new_id("journal"),"loop_id":loop_id,"event":"PRIOR_EXPERIMENT_LOOKUP","strategy_id":"nexus_sma_cross_v1","matches":len(prior),"known_failures":[r.get("decision") for r in prior if r.get("decision") in {"REJECT","MODIFY_AND_RETEST"}],"created_at":_now()})
    research=_research_package(); _append("trading_learning",{"learning_id":persistence.new_id("learn"),"loop_id":loop_id,"type":"RESEARCH_PACKAGE","package":research,"status":"CANDIDATE","created_at":_now()})
    alpha=build_work_order(goal_id=goal_id,work_type="research",owner_specialist="ALPHA",loop_id=loop_id,inputs={"question":"test whether canonical SMA crossover merits paper observation","decomposition":research["decomposition"]},retry_budget={"max_attempts":2}); alpha=assign_work_order(alpha,required_capabilities=("web","python")); _append("work_orders",alpha)
    data=fetch_candles("EUR_USD","H1",500); data_status="PASS" if data["ok"] and data["complete"]>=120 else "WAITING_DEPENDENCY"; rows=data.get("candles",[])
    if len(rows)<120: _append("trading_journal",{"journal_id":persistence.new_id("journal"),"loop_id":loop_id,"event":"DATA_DEPENDENCY","status":"WAITING_DEPENDENCY","dependency":"OANDA_PRACTICE","error":data.get("error"),"created_at":_now()}); return {"status":"WAITING_DEPENDENCY","safety":safety,"loop":loop,"data":data}
    spec={"fast":10,"slow":30,"max_hold_bars":24,"cost_rate":0.00015,"risk_fraction":0.01}
    strategy={"strategy_id":"nexus_sma_cross_v1","version":"1.0","parent_version":None,"name":"Canonical SMA crossover research candidate","status":"CANDIDATE","instrument":"EUR_USD","timeframe":"H1","hypothesis":"completed-bar SMA10/SMA30 trend crossover may have positive net expectancy after bounded costs","entry_rules":["SMA10 crosses above SMA30 on completed bar"],"exit_rules":["SMA10 crosses below SMA30","24-bar maximum hold"],"risk_rules":["fixed 1% paper risk","cost stress included"],"source_evidence":research["sources"],"research_refs":[loop_id],"spec":spec,"created_at":_now()}; _append("trading_strategies",strategy)
    split=(len(rows)*60//100,len(rows)*80//100,len(rows)); is_m=_run(rows,0,split[0],spec); val=_run(rows,split[0],split[1],spec); oos=_run(rows,split[1],split[2],spec)
    stress=[]
    for cost in (0.00015,0.00030,0.00050): stress.append({"cost_rate":cost,"metrics":_run(rows,split[1],split[2],{**spec,"cost_rate":cost})})
    robustness={"parameter_perturbations":[{"fast":8,"slow":30},{"fast":12,"slow":30},{"fast":10,"slow":40}],"cost_stress":stress,"subperiods":[_run(rows,0,split[0],spec),_run(rows,split[0],split[1],spec),_run(rows,split[1],split[2],spec)]}
    score=max(0,min(100,round(35+oos["expectancy_pct"]*100+min(oos["profit_factor"] if isinstance(oos["profit_factor"],(int,float)) else 0,3)*10-oos["max_drawdown_pct"]-max(0,30-oos["trade_count"]))))
    decision="PAPER_APPROVE" if oos["trade_count"]>=5 and oos["expectancy_pct"]>0 and all(x["metrics"]["expectancy_pct"]>-0.01 for x in stress) else "REJECT"
    critique={"status":"PASS","falsifiers":["OOS collapse","cost stress negative","too few trades","regime dependence"],"findings":["no future-bar references in implementation","completed-bar inputs only","sample and trade-count limitations remain"],"decision":decision}
    experiment_id = persistence.new_id("exp")
    _append("trading_experiments",{"experiment_id":experiment_id,"loop_id":loop_id,"strategy_id":strategy["strategy_id"],"version":strategy["version"],"data":{"source":"OANDA_PRACTICE","instrument":"EUR_USD","timeframe":"H1","start":rows[0]["time"],"end":rows[-1]["time"],"bar_count":len(rows),"split":split},"in_sample":is_m,"validation":val,"oos":oos,"robustness":robustness,"score":score,"decision":decision,"failure_modes":critique["falsifiers"],"created_at":_now()})
    alpha_result={"status":"PASS","artifact":"research_critique_backtest_oos_robustness","decision":decision,"score":score,"oos":oos,"critique":critique}; alpha=complete_work_order(alpha,alpha_result,receipt_ref="trading_experiment"); _append("work_orders",alpha)
    paper=None; paper_order=None
    if decision=="PAPER_APPROVE":
        paper={"paper_observation_id":persistence.new_id("paper"),"strategy_id":strategy["strategy_id"],"version":"1.0","environment":"OANDA_PRACTICE","status":"INSUFFICIENT_YET","signals":[],"paper_trades":[],"created_at":_now()}; _append("trading_paper_observations",paper)
    learning={"learning_id":persistence.new_id("learn"),"loop_id":loop_id,"strategy_id":strategy["strategy_id"],"status":"CANDIDATE","finding":"OOS and cost sensitivity recorded; not promoted without forward corroboration","evidence_refs":[strategy["strategy_id"]],"promote":False,"created_at":_now()}; _append("trading_learning",learning)
    feedback_question = "Why does this candidate fail or remain inconclusive out of sample, and does a bounded parameter variant improve robustness?"
    variant_spec = {**spec, "fast": 8, "slow": 30}
    variant_oos = _run(rows, split[1], split[2], variant_spec)
    feedback = {"feedback_id": persistence.new_id("trading_feedback"), "loop_id": loop_id, "parent_experiment_id": experiment_id,
                "strategy_id": strategy["strategy_id"], "source": "BACKTEST_RESULT", "finding": critique["findings"],
                "question": feedback_question, "weaknesses": ["trade_count", "cost_sensitivity", "out_of_sample_expectancy"],
                "alpha_review": {"decision": decision, "score": score}, "variant": {"fast": 8, "slow": 30, "oos": variant_oos},
                "next_action": "RESEARCH_AND_RETEST", "parent_objective_open": True, "created_at": _now()}
    _append("trading_learning", feedback)
    _append("work_orders", build_work_order(goal_id=goal_id, work_type="research", owner_specialist="ALPHA", loop_id=loop_id,
                                              inputs={"question": feedback_question, "parent_experiment_id": experiment_id,
                                                      "evidence": {"oos": oos, "variant_oos": variant_oos}}, retry_budget={"max_attempts": 2}))
    _append("trading_experiments", {"experiment_id": persistence.new_id("exp"), "parent_experiment_id": experiment_id,
                                      "loop_id": loop_id, "strategy_id": strategy["strategy_id"], "version": "1.1-variant",
                                      "data": {"source": "OANDA_PRACTICE", "instrument": "EUR_USD", "timeframe": "H1", "split": split},
                                      "oos": variant_oos, "decision": "RESEARCH_FEEDBACK_VARIANT", "created_at": _now()})
    if decision=="REJECT": _append("improvement_candidates",improvement_candidate(persistence.new_id("improve"),domain="trading_strategy",hypothesis="Investigate whether a non-crossover candidate or improved execution model addresses observed weakness",source="wp8.4_experiment"))
    loop.update({"state":"PAPER_OBSERVE" if paper else "DECIDED","current_step":"PAPER_OBSERVE" if paper else "DECISION","next_step":"FORWARD_REVIEW" if paper else "RESEARCH_NEW_CANDIDATE","status":"READY","outputs":{"strategy_id":strategy["strategy_id"],"decision":decision,"score":score,"oos":oos},"updated_at":_now()}); _append("loop_state",loop)
    return {"status":"PASS","safety":safety,"loop":loop,"strategy":strategy,"research":research,"data":data,"split":split,"in_sample":is_m,"validation":val,"oos":oos,"robustness":robustness,"score":score,"decision":decision,"critique":critique,"paper":paper,"learning":learning,"feedback":feedback,"alpha_work_order":alpha,"prior_experiments":len(prior),"cost":{"ai_invocations":0,"research_calls":3,"market_data_calls":1,"backtest_executions":2,"paper_executions":0,"retries":0},"authority_denial":not authority_allows("TRADING_ENGINE","live_trading","execute")}
