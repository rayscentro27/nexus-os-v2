import { describe, expect, it } from 'vitest'
import { allFundingClaimsRemainUnverified, BUSINESS_DECISION_AUTHORITY, canPromoteBusinessOpportunity, evaluateNaicsCandidates, fundingLaneAllowed, fundingMatchState, rayDecisionRequired, validateBusinessSourceInput, validateDepartmentHandoff } from '../src/lib/businessIntelligenceWorkflows'

describe('business intelligence workflow v1', () => {
  it('keeps the existing detailing draft in research until all material promotion gates pass', () => {
    const gates = { BUSINESS_MODEL_DEFINED:true, CUSTOMER_DEFINED:true, PROBLEM_DEFINED:true, REVENUE_MODEL_DEFINED:false, DEMAND_EVIDENCE_PRESENT:false, COMPETITOR_REVIEW_COMPLETE:false, BASIC_COST_STRUCTURE_PRESENT:false, RISKS_IDENTIFIED:true }
    expect(canPromoteBusinessOpportunity(gates)).toBe(false)
    expect(canPromoteBusinessOpportunity({...gates,REVENUE_MODEL_DEFINED:true,DEMAND_EVIDENCE_PRESENT:true,COMPETITOR_REVIEW_COMPLETE:true,BASIC_COST_STRUCTURE_PRESENT:true})).toBe(true)
  })
  it('uses multi-state funding matches and keeps client and Nexus lanes separate', () => {
    expect(fundingMatchState({met:3,unmet:0,unverified:0})).toBe('CURRENT_MATCH')
    expect(fundingMatchState({met:2,unmet:1,unverified:0})).toBe('PATH_TO_ELIGIBILITY')
    expect(fundingMatchState({met:1,unmet:0,unverified:2})).toBe('NEAR_MATCH')
    expect(fundingMatchState({met:0,unmet:2,unverified:0,alternative:true})).toBe('ALTERNATIVE_PRODUCT_MATCH')
    expect(fundingLaneAllowed('CLIENT_GOCLEAR','CLIENT_GOCLEAR')).toBe(true)
    expect(fundingLaneAllowed('CLIENT_GOCLEAR','NEXUS_INTERNAL')).toBe(false)
  })
  it('requires every field in a formal handoff and preserves human decision gates', () => {
    expect(validateDepartmentHandoff({case_id:'case-1'} as never)).not.toHaveLength(0)
    expect(rayDecisionRequired('BUSINESS_OPPORTUNITY')).toBe('RAY_DECISION_REQUIRED')
    expect(rayDecisionRequired('CLIENT_FUNDING')).toBe('CLIENT_DECISION_REQUIRED')
    expect(BUSINESS_DECISION_AUTHORITY.ATLAS_CAN_RECOMMEND).toBe(true)
    expect(BUSINESS_DECISION_AUTHORITY.ATLAS_CAN_APPROVE_BUSINESS).toBe(false)
    expect(BUSINESS_DECISION_AUTHORITY.CLYDE_CAN_RECOMMEND_FUNDING).toBe(true)
    expect(BUSINESS_DECISION_AUTHORITY.CLYDE_CAN_ACCEPT_FUNDING).toBe(false)
    expect(BUSINESS_DECISION_AUTHORITY.CLIENT_IS_FINAL_CLIENT_DECISION_AUTHORITY).toBe(true)
    expect(BUSINESS_DECISION_AUTHORITY.RAY_IS_FINAL_NEXUS_DECISION_AUTHORITY).toBe(true)
  })
  it('requires a structured safe source fixture and preserves original claims as claims', () => {
    const source = {SOURCE_TYPE:'YOUTUBE',SOURCE_TITLE:'Funding claim',SOURCE_URL_OR_REFERENCE:'fixture://first-citizens',SOURCE_TRANSCRIPT:'Source excerpt',NOTEBOOK_OUTPUT:{},SOURCE_CLAIMS:[{claim:'limit',value:25000}],RESEARCH_GAPS:[]}
    expect(validateBusinessSourceInput(source)).toEqual([])
    expect(allFundingClaimsRemainUnverified(source.SOURCE_CLAIMS)).toBe(true)
    expect(allFundingClaimsRemainUnverified([{claim:'x',value:'y',evidence_level:'VERIFIED'}])).toBe(false)
  })
  it('selects only truthful NAICS candidates and favors actual primary activity', () => {
    const result=evaluateNaicsCandidates([{code:'811192',truthfulActivityFit:true,primaryActivityFit:false},{code:'561790',truthfulActivityFit:false,primaryActivityFit:true},{code:'561720',truthfulActivityFit:true,primaryActivityFit:true}])
    expect(result.recommended?.code).toBe('561720')
    expect(result.defensible.map(x=>x.code)).toEqual(['811192','561720'])
    expect(result.falseOptimizationAllowed).toBe(false)
  })
  it('covers every non-binary funding recommendation state', () => {
    expect(fundingMatchState({met:8,unmet:0,unverified:0})).toBe('CURRENT_MATCH')
    expect(fundingMatchState({met:8,unmet:0,unverified:1})).toBe('NEAR_MATCH')
    expect(fundingMatchState({met:6,unmet:2,unverified:0})).toBe('PATH_TO_ELIGIBILITY')
    expect(fundingMatchState({met:0,unmet:2,unverified:0,alternative:true})).toBe('ALTERNATIVE_PRODUCT_MATCH')
    expect(fundingMatchState({met:0,unmet:2,unverified:0})).toBe('NOT_APPROPRIATE')
  })
})
