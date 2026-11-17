export const BUSINESS_INTELLIGENCE_PROMPTS = {
  BUSINESS_OPPORTUNITY_FEEDER: `PURPOSE: Evaluate a newly added source as a potential business opportunity. Answer as many questions as current sources support. Do not invent numbers or approve/reject projects. Label important claims SOURCE_CLAIM, CROSS_SUPPORTED, VERIFIED, CONTRADICTED, or RESEARCH_REQUIRED.
A CLASSIFICATION: IS_THIS_A_BUSINESS_OPPORTUNITY=YES/NO; if no classify MARKETING_TACTIC/SOFTWARE_TOOL/AFFILIATE_OPPORTUNITY/BUSINESS_COMPONENT/EDUCATIONAL_CONTENT/DUPLICATE/OTHER. Capture BUSINESS_MODEL, PRIMARY_PRODUCT_OR_SERVICE, TARGET_CUSTOMER, CUSTOMER_PROBLEM, VALUE_PROPOSITION, PRIMARY_REVENUE_MODEL.
B DEMAND: CUSTOMER_DEMAND_EVIDENCE_PRESENT, INDEPENDENT_DEMAND_SUPPORT, CUSTOMER_COMPLAINTS_OR_UNMET_NEEDS_IDENTIFIED (YES/NO), EVIDENCE, and exact research question for every NO.
C ECONOMICS: pricing, revenue, margin, unit economics, break-even presence; source claims; independent support; financial gaps. Never invent costs.
D MARKETING: defined customer, channels, hook, acquisition, conversion; channels SEO/YOUTUBE/SHORT_FORM/PAID_ADS/EMAIL/OUTBOUND/AFFILIATE/MARKETPLACE/PARTNERSHIP/OTHER; evidence.
E COMPETITION: competitor names, prices, positioning, customer, offer, strengths, weaknesses, observable gaps; research requirement.
F ENTRY TIERS: multi-cost entry YES/NO; LEAN_BOOTSTRAP, MODERATE, ACCELERATED capital/tools/labor/time/pros/cons, only when supported.
G AFFILIATE/WHITE LABEL: existing product, affiliate, white-label, referral, partner options.
H OPERATIONS: fulfillment, suppliers, software, staffing, automation, support, time requirements.
I RISKS: market, platform, capital, supplier, regulatory, acquisition, margin, fulfillment, competition.
J NEXUS FIT: reusable capability, similar prior projects, affiliate/partner resource, reusable marketing asset, one improvement and why.
K REUSABLE COMPONENTS: customer problem, audience, offer, pricing, monetization, traffic/content, fulfillment/supplier/automation model, affiliate option, scaling method.
L COMPLETENESS YES/NO: model, customer, problem, demand, revenue, competitor review, cost structure, marketing path, risks, affiliate check. Exact research question for each NO.
M INITIAL RECOMMENDATION (not a decision): PROMOTE_TO_DEDICATED_OPPORTUNITY_NOTEBOOK / ADDITIONAL_RESEARCH_REQUIRED / ATTACH_TO_EXISTING_OPPORTUNITY / SAVE_AS_REUSABLE_COMPONENT / NOT_A_BUSINESS_OPPORTUNITY. Include recommendation, action, next owner.` ,
  BUSINESS_FUNDING_FEEDER: `PURPOSE: Evaluate a funding technique, lender, grant, credit product, banking strategy, or capital opportunity. Original-source statements begin SOURCE_CLAIM; creator claims are not lender policy. Identify verification gaps; do not guarantee approval.
A PRODUCT IDENTITY: specific lender/product YES/NO, lender, product, type (BUSINESS_LINE_OF_CREDIT/TERM_LOAN/BUSINESS_CREDIT_CARD/SBA/EQUIPMENT/VENDOR_CREDIT/GRANT/BANK_RELATIONSHIP/OTHER), claimed limit/minimum, secured status, documentation claim.
B CREDIT: personal credit required, claimed score, bureaus, hard pull, business credit required, lender verified.
C BUSINESS REQUIREMENTS: entity, time in business, revenue, bank account/relationship/account age/deposits/average balance, state, industry/NAICS, DUNS, business plan.
D DOCUMENTATION: tax returns, bank/financial statements, revenue proof, EIN, formation documents, ID, PG, collateral, UCC.
E PRICING: APR/rate, fees, term, payment structure, draw/annual/prepayment/other costs. F APPLICATION: online/branch/manager/phone/referral/other. G GEOGRAPHY: states, national/local.
H For every material claim record CLAIM, evidence level SOURCE_CLAIM/LENDER_VERIFIED/CROSS_SUPPORTED/CONTRADICTED/RESEARCH_REQUIRED and source.
I For every qualification: requirement, binary, improvable, time/relationship/credit/financial/business-age basis; can condition change, action, completion verification. No future approval guarantee.
J Alternatives: requirement differences to search if missed (lower score, no relationship, shorter time, lower revenue, different state, no PG, other).
K Completeness YES/NO for product existence, current requirements, credit/business requirements, documentation, pricing, application, geography; exact question for each NO.
L Recommend PROMOTE_TO_FUNDING_PRODUCT_BANK / ADDITIONAL_VERIFICATION_REQUIRED / ATTACH_TO_EXISTING_PRODUCT / SAVE_AS_FUNDING_TECHNIQUE / STALE_OR_DISCONTINUED. Include next action and owner.` ,
  BUSINESS_CREATION_BANKABILITY: `PURPOSE: Determine whether a NEW_BUSINESS or EXISTING_BUSINESS is established, operationally credible, and positioned for funding. First BUSINESS_EXISTS=YES/NO and WORKFLOW_TYPE=NEW_BUSINESS_CREATION/EXISTING_BUSINESS_AUDIT.
A ENTITY: legal name/type/state/formation/good standing/EIN/agent/address/type/licenses required/present. B IDENTITY: domain/website/pro email/phone/Google Business/listing consistency. C BANKING: bank/type/open date/age/current and 30/90 day average balances/monthly deposits/consistency/operating account.
D ACTIVITY: actual product/service, primary customer/revenue activity, what customers pay for, delivery. E NAICS: determine actual primary activity; list all truthfully defensible candidates with description, primary activity/revenue/operating model match, funding risk, licensing/compliance implications. Accuracy first; compare funding implications only among truthful candidates; never change activity to obtain financing. Recommend code and why.
F IDENTITY/CREDIT FILE: DUNS, business credit file, bureaus. G BUSINESS CREDIT: tradelines, vendor/revolving/reporting accounts, payment history, building needed. H PLAN: present/current/stale/consistent; required if missing. I OPERATIONS: time in business, monthly/annual revenue, employees/contractors/products/services/history.
J PERSONAL CREDIT: availability and appropriately available score/range, bureaus, utilization, derogatories, inquiries, age; whether it affects funding. PERSONAL_CREDIT_REPAIR_WORKFLOW=NOT_YET_GOVERNED; do not execute repair.
K classify each ENTITY/GOOD_STANDING/EIN/ADDRESS/DOMAIN/WEBSITE/EMAIL/PHONE/BANK_ACCOUNT/BANK_AGE/BALANCE/DEPOSITS/NAICS/DUNS/GOOGLE_BUSINESS/PLAN/LICENSES/BUSINESS_CREDIT/PERSONAL_CREDIT_READINESS as COMPLETE/MISSING/NEEDS_CORRECTION/NOT_APPLICABLE.
L ordered actions with owner and measurable completion criteria. M BUSINESS_CREATION_COMPLETE_ENOUGH_FOR_FUNDING_REVIEW=YES/NO; if no next action; if yes next owner CLYDE. Recommendations do not authorize entity formation or bank changes.`
} as const

export const BI_NOTEBOOK_TYPES = Object.keys(BUSINESS_INTELLIGENCE_PROMPTS) as Array<keyof typeof BUSINESS_INTELLIGENCE_PROMPTS>
export const BI_BANK_TYPES = ['BUSINESS_HUB','OPPORTUNITY_BANK','OPPORTUNITY_COMPONENT_BANK','FUNDING_PRODUCT_BANK','BUSINESS_CREDIT_PRODUCT_BANK'] as const
export const BI_HANDOFF_CONTRACT = ['SUMMARY','SUPPORTING_DATA','WHAT_WAS_COMPLETED','WHAT_REMAINS','RECOMMENDATION','ACTION','NEXT_OWNER','EXPECTED_OUTPUT'] as const
export const BUSINESS_DECISION_AUTHORITY = { ATLAS_CAN_RECOMMEND:true, ATLAS_CAN_APPROVE_BUSINESS:false, CLYDE_CAN_RECOMMEND_FUNDING:true, CLYDE_CAN_ACCEPT_FUNDING:false, CLIENT_IS_FINAL_CLIENT_DECISION_AUTHORITY:true, RAY_IS_FINAL_NEXUS_DECISION_AUTHORITY:true } as const

export type BusinessSourceInput = {
  SOURCE_TYPE: string
  SOURCE_TITLE: string
  SOURCE_URL_OR_REFERENCE: string
  SOURCE_TRANSCRIPT: string
  NOTEBOOK_OUTPUT: Record<string, unknown>
  SOURCE_CLAIMS: Array<{ claim: string; value: unknown; evidence_level?: 'SOURCE_CLAIM'|'CROSS_SUPPORTED'|'VERIFIED'|'CONTRADICTED'|'RESEARCH_REQUIRED' }>
  RESEARCH_GAPS: Array<{ question: string; owner?: string; reason?: string }>
}

export function validateBusinessSourceInput(input: Partial<BusinessSourceInput>) {
  return (['SOURCE_TYPE','SOURCE_TITLE','SOURCE_URL_OR_REFERENCE','SOURCE_TRANSCRIPT','NOTEBOOK_OUTPUT','SOURCE_CLAIMS','RESEARCH_GAPS'] as const)
    .filter(key => input[key] === undefined || input[key] === null || input[key] === '')
}

export function allFundingClaimsRemainUnverified(claims: BusinessSourceInput['SOURCE_CLAIMS']) {
  return claims.every(claim => (claim.evidence_level || 'SOURCE_CLAIM') === 'SOURCE_CLAIM')
}

export function evaluateNaicsCandidates<T extends { code:string; truthfulActivityFit:boolean; primaryActivityFit:boolean }>(candidates:T[]) {
  const defensible = candidates.filter(candidate => candidate.truthfulActivityFit)
  const recommended = defensible.find(candidate => candidate.primaryActivityFit) || defensible[0] || null
  return { defensible, recommended, accuracyFirst:true as const, falseOptimizationAllowed:false as const }
}

export function canPromoteBusinessOpportunity(gates: Record<string, boolean>) {
  return ['BUSINESS_MODEL_DEFINED','CUSTOMER_DEFINED','PROBLEM_DEFINED','REVENUE_MODEL_DEFINED','DEMAND_EVIDENCE_PRESENT','COMPETITOR_REVIEW_COMPLETE','BASIC_COST_STRUCTURE_PRESENT','RISKS_IDENTIFIED'].every(key => gates[key] === true)
}

export function fundingMatchState(input: { met: number; unmet: number; unverified: number; alternative?: boolean }): 'CURRENT_MATCH'|'NEAR_MATCH'|'PATH_TO_ELIGIBILITY'|'ALTERNATIVE_PRODUCT_MATCH'|'NOT_APPROPRIATE' {
  if (input.met === 0 && input.unmet > 0 && !input.alternative) return 'NOT_APPROPRIATE'
  if (input.alternative) return 'ALTERNATIVE_PRODUCT_MATCH'
  if (input.unmet === 0 && input.unverified === 0) return 'CURRENT_MATCH'
  if (input.met > 0 && input.unmet === 0) return 'NEAR_MATCH'
  return 'PATH_TO_ELIGIBILITY'
}

export type DepartmentHandoff = { case_id:string; handoff_type:string; from_department:string; next_owner:string; summary:string; supporting_data:unknown; what_was_completed:string[]; what_remains:string[]; recommendation:string; action:string; expected_output:string }
export function validateDepartmentHandoff(packet: Partial<DepartmentHandoff>) {
  const required: Array<keyof DepartmentHandoff> = ['case_id','handoff_type','from_department','next_owner','summary','supporting_data','what_was_completed','what_remains','recommendation','action','expected_output']
  return required.filter(key => packet[key] === undefined || packet[key] === null || packet[key] === '')
}

export function fundingLaneAllowed(caseType: string, ownerLane: string) {
  return caseType === ownerLane && ['CLIENT_GOCLEAR','NEXUS_INTERNAL'].includes(caseType)
}

export function rayDecisionRequired(workflow: 'BUSINESS_OPPORTUNITY'|'NEXUS_FUNDING'|'CLIENT_FUNDING') {
  return workflow === 'CLIENT_FUNDING' ? 'CLIENT_DECISION_REQUIRED' : 'RAY_DECISION_REQUIRED'
}
