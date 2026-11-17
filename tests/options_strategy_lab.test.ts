import { describe, expect, it } from 'vitest'
import { calculateOptionPayoff, classifyOptionEvidence, generateOptionPracticeCandidates, optionsExecutionFeasibility, OPTIONS_FAMILIES, OPTIONS_LAB_AUTHORITY, wheelTotalEconomics } from '../src/lib/optionsStrategyLab'

describe('Mercury Options Strategy Lab contracts',()=>{
  it('classifies all requested families and keeps decision authority with Ray',()=>{
    expect(OPTIONS_FAMILIES).toHaveLength(13)
    expect(OPTIONS_LAB_AUTHORITY).toMatchObject({owner:'TRADING',liveTradingEnabled:false,practiceCountsAsMaterial:false,autonomousMaterialLoopLimit:2,finalDecision:'RAY_DECISION_REQUIRED'})
  })
  it('keeps source assertions unverified with exact research questions',()=>{
    const out=classifyOptionEvidence([{claim:'Creator says $7 debit yields $492 max profit',evidence_state:'VERIFIED'}])
    expect(out.source_claims[0].evidence_state).toBe('SOURCE_CLAIM')
    expect(out.verification_gaps[0]).toContain('Verify independently')
    expect(out.current_requirements_verified).toBe(false)
  })
  it('calculates option PnL and refuses to infer executable edge without quote evidence',()=>{
    const out=calculateOptionPayoff({experiment_id:'synthetic-spread-fixture',strategy_id:'fixture',strategy_family:'CUSTOM_MULTI_LEG',spot_at_expiry:120,fixture:true,legs:[
      {side:'SELL',right:'PUT',quantity:3,strike:100,premium_per_share:0.1},
      {side:'BUY',right:'PUT',quantity:2,strike:95,premium_per_share:0.2},
      {side:'BUY',right:'PUT',quantity:1,strike:110,premium_per_share:0.5},
    ]})
    expect(out.option_pnl).toBe(-60)
    expect(out.execution_feasibility).toBe('RESEARCH_REQUIRED')
    expect(out.live_trading_enabled).toBe(false)
    expect(out.material_loop_incremented).toBe(false)
  })
  it('includes underlying loss and covered-call PnL in Wheel total economics',()=>{
    const out=wheelTotalEconomics({premiumPnl:400,underlyingPnl:-1200,coveredCallPnl:250,capital:10000,lockupDays:40,assignmentOccurred:true})
    expect(out.total_strategy_pnl).toBe(-550)
    expect(out.capital_lockup_days).toBe(40)
    expect(out.result).toBe('INCONCLUSIVE')
  })
  it('generates a bounded one-axis-at-a-time options test matrix',()=>{
    const out=generateOptionPracticeCandidates('fixture_custom_put')
    expect(out.generated).toBe(6)
    expect(new Set(out.candidates.map(x=>x.change_type))).toEqual(new Set(['DTE','STRIKE_SPACING_RATIO','IV_REGIME']))
    expect(out.candidates.every(x=>x.result==='INCONCLUSIVE'&&x.material_loop_incremented===false&&x.requires_historical_chain)).toBe(true)
    expect(generateOptionPracticeCandidates('fixture',99).generated).toBe(6)
  })
  it('does not equate theoretical payoff with executable edge when quotes or fill inputs are missing',()=>{
    const out=optionsExecutionFeasibility({})
    expect(out.status).toBe('RESEARCH_REQUIRED')
    expect(out.theoretical_edge_is_executable).toBe(false)
    expect(out.gaps).toContain('BID_ASK_SPREAD')
  })
})
