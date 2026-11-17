/** Options-specific analysis contracts inside Mercury; never grants trade authority. */
export const OPTIONS_STRATEGY_FEEDER = `
PURPOSE: Extract an options strategy from a supplied source. Treat creator statements as SOURCE_CLAIM; never present creator claims as lender/exchange or verified trading facts. Identify exact evidence gaps.
A. STRATEGY IDENTITY: STRATEGY_NAME=; STRATEGY_FAMILY=WHEEL|CASH_SECURED_PUT|COVERED_CALL|VERTICAL|IRON_CONDOR|BUTTERFLY|CALENDAR|DIAGONAL|STRADDLE|STRANGLE|RATIO_SPREAD|BACKSPREAD|CUSTOM_MULTI_LEG|OTHER; MARKET_OUTLOOK=; VOLATILITY_OUTLOOK=
B. UNDERLYING: UNDERLYING_SELECTION_RULES=; EXAMPLE_TICKER=; ASSET_CLASS=; FUNDAMENTAL_REQUIREMENTS=; TREND_REQUIREMENTS=; VOLATILITY_REQUIREMENTS=; LIQUIDITY_REQUIREMENTS=
C. OPTION LEGS: for each BUY_OR_SELL, CALL_OR_PUT, QUANTITY, STRIKE_SELECTION_RULE, DELTA_RULE, DTE_RULE, EXPIRATION_RELATIONSHIP.
D. TRADE ECONOMICS: DEBIT_OR_CREDIT, MAX_LOSS, THEORETICAL_MAX_PROFIT, BREAK_EVEN, CAPITAL_REQUIRED, BUYING_POWER_REQUIRED.
E. GREEKS/VOLATILITY: DELTA, GAMMA, THETA, VEGA, IV_REQUIREMENT, IV_RANK_OR_PERCENTILE, VOLATILITY_ASSUMPTION.
F. LIQUIDITY: BID_ASK_SPREAD, OPEN_INTEREST, OPTION_VOLUME, UNDERLYING_VOLUME.
G. MANAGEMENT: ENTRY_RULES, PROFIT_TAKE_RULE, STOP_RULE, TIME_EXIT, ROLL_RULE, ASSIGNMENT_RULE, EXERCISE_RULE, EXPIRATION_RULE.
H. PORTFOLIO: RISK_PER_TRADE, MAX_POSITION_ALLOCATION, CASH_RESERVE_RULE, MAX_CONCURRENT_POSITIONS.
I. RISKS: ASSIGNMENT, EARLY_EXERCISE, PIN, EXPIRATION, LIQUIDITY, SLIPPAGE, EVENT, EARNINGS, VOLATILITY, GAP.
J. SOURCE CLAIMS: classify each major claim SOURCE_CLAIM|CROSS_SUPPORTED|VERIFIED|CONTRADICTED|RESEARCH_REQUIRED.
K. TEST QUESTIONS: exact questions covering DTE, delta, strike spacing, underlying, IV regime, management, assignment, capital lockup, money management and portfolio allocation. Do not recommend real-money deployment.
`;

export const OPTIONS_FAMILIES = ['WHEEL','CASH_SECURED_PUT','COVERED_CALL','VERTICAL','IRON_CONDOR','BUTTERFLY','CALENDAR','DIAGONAL','STRADDLE','STRANGLE','RATIO_SPREAD','BACKSPREAD','CUSTOM_MULTI_LEG'] as const;
export type OptionFamily = typeof OPTIONS_FAMILIES[number];

export type SourceClaim = { claim: string; evidence_state: 'SOURCE_CLAIM'|'CROSS_SUPPORTED'|'VERIFIED'|'CONTRADICTED'|'RESEARCH_REQUIRED'; source_reference?: string };
export type OptionLeg = { side: 'BUY'|'SELL'; right: 'CALL'|'PUT'; quantity: number; strike: number; premium_per_share: number; delta?: number };
export type OptionPracticeInput = { experiment_id:string; strategy_id:string; strategy_family:OptionFamily; underlying?:string; asset_class?:string; dte?:number; legs:OptionLeg[]; spot_at_expiry:number; multiplier?:number; fixture?:boolean; claims?:SourceClaim[]; bid_ask?:Record<string,number>; open_interest?:number[]; volume?:number[]; assignment_occurred?:boolean; capital_lockup_days?:number; underlying_pnl?:number; covered_call_pnl?:number; max_drawdown?:number };
export function calculateOptionPayoff(input:OptionPracticeInput) {
  const multiplier=input.multiplier??100;
  const premium=input.legs.reduce((sum,l)=>sum+(l.side==='BUY'?-1:1)*l.quantity*l.premium_per_share*multiplier,0);
  const intrinsic=input.legs.reduce((sum,l)=>sum+(l.side==='BUY'?1:-1)*l.quantity*Math.max(0,l.right==='PUT'?l.strike-input.spot_at_expiry:input.spot_at_expiry-l.strike)*multiplier,0);
  const optionPnl=premium+intrinsic;
  const total=optionPnl+(input.underlying_pnl??0)+(input.covered_call_pnl??0);
  const spread=input.bid_ask?.spread;
  const oi=input.open_interest?.length?Math.min(...input.open_interest):undefined;
  const vol=input.volume?.length?Math.min(...input.volume):undefined;
  const executable=spread===undefined||oi===undefined||vol===undefined ? 'RESEARCH_REQUIRED' : spread<=0.05&&oi>=100&&vol>=10 ? 'POTENTIALLY_FEASIBLE' : 'LOW_FEASIBILITY';
  return { premium_pnl:premium, option_pnl:optionPnl, underlying_pnl:input.underlying_pnl??0, covered_call_pnl:input.covered_call_pnl??0, total_strategy_pnl:total, return_on_capital:null, theoretical_edge_score:null, execution_feasibility:executable, missing_execution_evidence:[...(spread===undefined?['bid_ask_spread']:[]),...(oi===undefined?['open_interest']:[]),...(vol===undefined?['volume']:[])], result:'INCONCLUSIVE' as const, confidence:'LOW' as const, sample_quality:'SINGLE_DETERMINISTIC_FIXTURE', test_fixture:input.fixture??false, live_trading_enabled:false, material_loop_incremented:false };
}

export function classifyOptionEvidence(claims:SourceClaim[]) {
  return { source_claims:claims.map(c=>({...c,evidence_state:'SOURCE_CLAIM' as const})), verification_gaps:claims.map(c=>`Verify independently: ${c.claim}`), current_requirements_verified:false, live_trading_enabled:false };
}

/** One-axis-at-a-time bounded design. Candidates remain untested without dated chains. */
export function generateOptionPracticeCandidates(strategyId:string, maxCandidates=6) {
  const axes=[
    {change_type:'DTE',values:[14,45]},
    {change_type:'STRIKE_SPACING_RATIO',values:[1.5,2.5]},
    {change_type:'IV_REGIME',values:['LOW','HIGH']},
  ] as const;
  const candidates=axes.flatMap(axis=>axis.values.map(value=>({strategy_id:strategyId,experiment_class:'PRACTICE_EXPERIMENT' as const,change_type:axis.change_type,value,result:'INCONCLUSIVE' as const,confidence:'LOW' as const,requires_historical_chain:true,required_evidence:['option_chain','bid_ask','open_interest','volume','IV','greeks','expiration_calendar'],lesson_eligible:false,material_loop_incremented:false,live_trading_enabled:false}))).slice(0,Math.max(0,Math.min(6,maxCandidates)));
  return {candidates,generated:candidates.length,practice_limit:Math.max(0,Math.min(6,maxCandidates)),status:'WAITING_ON_EXTERNAL_RESEARCH' as const,next_owner:'TRADING',reason:'Candidate design is bounded; measured option outcomes require dated historical option-chain evidence.'};
}

export function optionsExecutionFeasibility(evidence:{bidAskSpread?:number;openInterest?:number;optionVolume?:number;fillModel?:string;slippageModel?:string;feesKnown?:boolean;assignmentModel?:boolean}) {
  const gaps=[...(!Number.isFinite(evidence.bidAskSpread)?['BID_ASK_SPREAD']:[]),...(!Number.isFinite(evidence.openInterest)?['OPEN_INTEREST']:[]),...(!Number.isFinite(evidence.optionVolume)?['OPTION_VOLUME']:[]),...(!evidence.fillModel?['FILL_MODEL']:[]),...(!evidence.slippageModel?['SLIPPAGE_MODEL']:[]),...(evidence.feesKnown!==true?['FEES']:[]),...(evidence.assignmentModel!==true?['ASSIGNMENT_MODEL']:[])];
  return {status:gaps.length?'RESEARCH_REQUIRED':'READY_FOR_PAPER_FEASIBILITY_REVIEW',gaps,theoretical_edge_is_executable:false,live_trading_enabled:false};
}

export function wheelTotalEconomics(input:{premiumPnl:number;underlyingPnl:number;coveredCallPnl:number;capital:number;lockupDays:number;assignmentOccurred:boolean}) {
  return { premium_pnl:input.premiumPnl, underlying_pnl:input.underlyingPnl, covered_call_pnl:input.coveredCallPnl, total_strategy_pnl:input.premiumPnl+input.underlyingPnl+input.coveredCallPnl, return_on_capital:input.capital>0?(input.premiumPnl+input.underlyingPnl+input.coveredCallPnl)/input.capital:null, capital_lockup_days:input.lockupDays, assignment_occurred:input.assignmentOccurred, result:'INCONCLUSIVE' as const, confidence:'LOW' as const, test_fixture:true, live_trading_enabled:false };
}

export const OPTIONS_LAB_AUTHORITY = { owner:'TRADING', analyst:'MERCURY', liveTradingEnabled:false, practiceCountsAsMaterial:false, autonomousMaterialLoopLimit:2, finalDecision:'RAY_DECISION_REQUIRED' } as const;
