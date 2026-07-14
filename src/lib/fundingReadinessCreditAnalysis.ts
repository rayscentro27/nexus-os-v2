import type { ParsedCreditAccount, ParsedInquiry, ParsedPersonalInfoVariation, CreditReportConfidence } from './creditReportParserTypes'

export type FundingImpactCategory = 'high_funding_impact' | 'utilization_impact' | 'report_item_review' | 'inquiry_review' | 'personal_info_review' | 'client_evidence_needed' | 'specialist_exception' | 'no_action_suggested'
export type FundingImpactReason = 'inaccurate_balance_possible' | 'duplicate_possible' | 'unfamiliar_account' | 'incorrect_dates_possible' | 'payment_status_review' | 'paid_or_settled_status_review' | 'unauthorized_inquiry_possible' | 'personal_information_mismatch' | 'outdated_information_possible' | 'incomplete_information' | 'unverifiable_information' | 'not_sure'

export interface FundingImpactItem {
  id: string
  creditorFurnisher: string
  maskedAccountReference: string
  bureau: string
  category: FundingImpactCategory
  reason: FundingImpactReason
  issueDetected: string
  fundingImpact: string
  suggestedNextStep: string
  possibleDocumentationOption: string | null
  confidence: CreditReportConfidence
  explanation: string
  clientEvidenceNeeded: string[]
  specialistReviewRequired: boolean
  tier1Impact: 'high' | 'medium' | 'low' | 'none'
  tier2Impact: 'high' | 'medium' | 'low' | 'none'
  letterEligible: boolean
}

export interface FundingReadinessCreditAnalysis {
  creditProfileStatus: 'ready_to_review' | 'almost_ready' | 'action_needed' | 'insufficient_information'
  summary: string
  fundingImpactItems: FundingImpactItem[]
  utilizationActions: FundingImpactItem[]
  reportItemReviews: FundingImpactItem[]
  inquiryReviews: FundingImpactItem[]
  personalInfoReviews: FundingImpactItem[]
  evidenceNeeded: FundingImpactItem[]
  specialistExceptions: FundingImpactItem[]
  noActionItems: FundingImpactItem[]
  recommendedNextSteps: string[]
  confidenceSummary: { overall: CreditReportConfidence; lowConfidenceItems: number; warnings: string[] }
  tier1Impact: { blockerCount: number; summary: string }
  tier2Impact: { blockerCount: number; summary: string }
}

const text = (value: unknown) => String(value || '').toLowerCase()
const stableId = (prefix: string, index: number, bureau: string) => `${prefix}_${bureau || 'other'}_${index + 1}`

function accountItem(account: ParsedCreditAccount, index: number): FundingImpactItem {
  const haystack = text(`${account.itemType} ${account.status} ${account.paymentStatus} ${account.negativeCandidateReason} ${account.notes}`)
  const utilization = Number(account.utilizationPercent || 0)
  const ambiguous = !account.bureau || account.bureau === 'other' || (!account.furnisherName && !account.accountName)
  let category: FundingImpactCategory = 'no_action_suggested'
  let reason: FundingImpactReason = 'not_sure'
  let issue = 'No immediate funding-impact action detected'
  let fundingImpact = 'No material impact identified from available fields.'
  let next = 'Keep monitoring and review when updated information is available.'
  let documentation: string | null = null
  let letterEligible = false
  let evidence: string[] = []
  let tier1: FundingImpactItem['tier1Impact'] = 'none'
  let tier2: FundingImpactItem['tier2Impact'] = 'none'

  if (ambiguous || account.confidence === 'low') {
    category = 'specialist_exception'; reason = 'incomplete_information'; issue = 'Incomplete or ambiguous extracted account information'
    fundingImpact = 'Impact cannot be assessed reliably until the extraction is confirmed.'; next = 'GoClear should compare this item with the source report.'
    evidence = ['Current credit report page showing the complete item']; tier1 = 'medium'; tier2 = 'medium'
  } else if (utilization >= 30 || haystack.includes('utilization')) {
    category = 'utilization_impact'; reason = 'not_sure'; issue = utilization ? `Reported utilization is ${utilization}%` : 'Utilization information needs review'
    fundingImpact = 'Higher revolving utilization may weaken lender readiness.'; next = 'Review payoff timing, balance reduction, and statement-date options.'
    tier1 = utilization >= 70 ? 'high' : 'medium'; tier2 = 'medium'
  } else if (/collection|charge.?off|90 day|60 day|30 day|late/.test(haystack)) {
    category = 'high_funding_impact'; reason = haystack.includes('paid') || haystack.includes('settled') ? 'paid_or_settled_status_review' : 'payment_status_review'
    issue = 'Major derogatory or payment-status indicator detected'; fundingImpact = 'This reported status may materially affect Tier 1 and Tier 2 readiness.'
    next = 'Confirm the reported facts and gather supporting records before choosing an action.'; documentation = 'Possible dispute/documentation option only if the reporting appears inaccurate, outdated, incomplete, or unverifiable.'
    evidence = ['Statements, payment records, settlement records, or bureau correspondence']; letterEligible = true; tier1 = 'high'; tier2 = 'high'
  } else if (/duplicate/.test(haystack)) {
    category = 'report_item_review'; reason = 'duplicate_possible'; issue = 'Possible duplicate reporting indicator detected'
    fundingImpact = 'Duplicate reporting may overstate obligations or negative history.'; next = 'Compare bureau, furnisher, dates, and masked account references.'
    documentation = 'Possible dispute/documentation option if the entries represent the same obligation.'; evidence = ['Report pages showing both entries']; letterEligible = true; tier1 = 'medium'; tier2 = 'medium'
  }
  return { id: stableId('account', index, account.bureau), creditorFurnisher: account.furnisherName || account.accountName || 'Unknown furnisher', maskedAccountReference: account.accountNumberMasked || 'Not available', bureau: account.bureau || 'other', category, reason, issueDetected: issue, fundingImpact, suggestedNextStep: next, possibleDocumentationOption: documentation, confidence: account.confidence || 'low', explanation: 'Deterministic classification from parsed status, type, utilization, bureau, and completeness fields; not a factual verification.', clientEvidenceNeeded: evidence, specialistReviewRequired: category !== 'no_action_suggested', tier1Impact: tier1, tier2Impact: tier2, letterEligible }
}

export function analyzeCreditForFundingReadiness(input: { accounts?: ParsedCreditAccount[]; inquiries?: ParsedInquiry[]; personalInfoVariations?: ParsedPersonalInfoVariation[]; confidence?: CreditReportConfidence; warnings?: Array<{ message?: string }> }): FundingReadinessCreditAnalysis {
  const accounts = input.accounts || []
  const items = accounts.map(accountItem)
  const inquiryItems: FundingImpactItem[] = (input.inquiries || []).map((inquiry, index) => ({ id: stableId('inquiry', index, inquiry.bureau), creditorFurnisher: inquiry.company || 'Unknown inquiry', maskedAccountReference: 'Not applicable', bureau: inquiry.bureau || 'other', category: inquiry.confidence === 'low' ? 'specialist_exception' : 'inquiry_review', reason: 'unauthorized_inquiry_possible', issueDetected: 'Recent inquiry detected for client review', fundingImpact: 'Recent hard inquiries may affect some funding evaluations.', suggestedNextStep: 'Confirm whether the inquiry is familiar and authorized.', possibleDocumentationOption: 'Possible dispute/documentation option only if the inquiry is unfamiliar or lacks permissible purpose.', confidence: inquiry.confidence || 'low', explanation: 'Detection is not verification that an inquiry was unauthorized.', clientEvidenceNeeded: ['Client confirmation and any application records'], specialistReviewRequired: true, tier1Impact: 'medium', tier2Impact: 'low', letterEligible: true }))
  const personalItems: FundingImpactItem[] = (input.personalInfoVariations || []).map((variation, index) => ({ id: stableId('personal', index, variation.bureau || 'other'), creditorFurnisher: 'Personal information', maskedAccountReference: 'Not applicable', bureau: variation.bureau || 'other', category: variation.confidence === 'low' ? 'specialist_exception' : 'personal_info_review', reason: 'personal_information_mismatch', issueDetected: `${variation.field || 'Personal information'} variation detected`, fundingImpact: 'Identity or address inconsistencies can delay report and funding documentation review.', suggestedNextStep: 'Compare the entry with current identity and address documents.', possibleDocumentationOption: 'Possible documentation option if the entry is outdated, unfamiliar, or inaccurate.', confidence: variation.confidence || 'low', explanation: 'A parsed variation is not a verified error.', clientEvidenceNeeded: ['Government ID or current proof of address, with sensitive fields redacted'], specialistReviewRequired: true, tier1Impact: 'low', tier2Impact: 'low', letterEligible: true }))
  const all = [...items, ...inquiryItems, ...personalItems]
  const by = (category: FundingImpactCategory) => all.filter(item => item.category === category)
  const exceptions = by('specialist_exception')
  const blockers = all.filter(item => item.tier1Impact === 'high' || item.tier1Impact === 'medium')
  const status = accounts.length === 0 ? 'insufficient_information' : blockers.some(i => i.tier1Impact === 'high') ? 'action_needed' : blockers.length ? 'almost_ready' : 'ready_to_review'
  return { creditProfileStatus: status, summary: accounts.length ? `${accounts.length} accounts analyzed; ${blockers.length} items may affect funding readiness.` : 'Insufficient parsed account information for a readiness assessment.', fundingImpactItems: all.filter(i => i.category !== 'no_action_suggested'), utilizationActions: by('utilization_impact'), reportItemReviews: [...by('report_item_review'), ...by('high_funding_impact')], inquiryReviews: by('inquiry_review'), personalInfoReviews: by('personal_info_review'), evidenceNeeded: all.filter(i => i.clientEvidenceNeeded.length > 0), specialistExceptions: exceptions, noActionItems: by('no_action_suggested'), recommendedNextSteps: ['Confirm high-impact recommendations', 'Review utilization actions', 'Request only the evidence needed for unresolved items'], confidenceSummary: { overall: input.confidence || 'low', lowConfidenceItems: all.filter(i => i.confidence === 'low').length, warnings: (input.warnings || []).map(w => w.message || '').filter(Boolean) }, tier1Impact: { blockerCount: blockers.length, summary: 'Tier 1 impact emphasizes utilization, recent inquiries, derogatory indicators, and data sufficiency.' }, tier2Impact: { blockerCount: all.filter(i => i.tier2Impact === 'high' || i.tier2Impact === 'medium').length, summary: 'Tier 2 impact carries forward material Credit Profile risks for combined business underwriting preparation.' } }
}
