import type { ClientJourneyState, JourneyStageId } from './clientJourneyModel'

export type GuidedReadinessState = 'ready_to_review' | 'almost_ready' | 'action_needed' | 'insufficient_information'
export type GuidedRequirementStatus = 'complete' | 'missing' | 'processing' | 'attention' | 'not_applicable'

export interface GuidedRequirement {
  id: string
  label: string
  status: GuidedRequirementStatus
  whyItMatters: string
  missing: string
  documentCategory?: string
  impact: 'high' | 'medium' | 'low'
  route: string
}

export interface GuidedStage {
  id: JourneyStageId
  label: string
  contribution: number
  status: GuidedReadinessState | 'complete'
  requirements: GuidedRequirement[]
}

export interface GuidedFundingReadiness {
  state: GuidedReadinessState
  overallScore: number
  primaryBlocker: string | null
  nextBestAction: string
  nextBestActionRoute: string
  reviewEligible: boolean
  processingDocuments: string[]
  missingDocuments: string[]
  completedRequirements: string[]
  outstandingRequirements: string[]
  readinessHistory: Array<{ label: string; status: string; date: string }>
  tier1: { status: GuidedReadinessState; relevance: string; blockers: string[] }
  tier2: { status: GuidedReadinessState; relevance: string; blockers: string[] }
  stages: Record<'credit' | 'business_foundation' | 'business_bankability' | 'funding', GuidedStage>
}

const clean = (value: unknown) => String(value || '').trim()
const lower = (value: unknown) => clean(value).toLowerCase()
const documentText = (doc: any) => lower(`${doc?.category || ''} ${doc?.title || ''} ${doc?.filename || ''} ${doc?.doc_type || ''}`)
const profileText = (profile: any) => lower(JSON.stringify(profile || {}))

function docMatches(docs: any[], patterns: RegExp[]) {
  return docs.find(doc => patterns.some(pattern => pattern.test(documentText(doc))))
}

function docStatus(doc: any): GuidedRequirementStatus {
  if (!doc) return 'missing'
  if (doc.exception_review_status === 'required') return 'attention'
  if (/processing|queued|pending|review/.test(lower(`${doc.analysis_status || ''} ${doc.goclear_review_status || ''} ${doc.status || ''}`))) return 'processing'
  return 'complete'
}

function documentRequirement(input: {
  id: string
  label: string
  category: string
  patterns: RegExp[]
  whyItMatters: string
  impact: GuidedRequirement['impact']
  route: string
  missing?: string
}, docs: any[]): GuidedRequirement {
  const doc = docMatches(docs, input.patterns)
  const status = docStatus(doc)
  return {
    id: input.id,
    label: input.label,
    status,
    whyItMatters: input.whyItMatters,
    missing: status === 'missing' ? (input.missing || `Upload ${input.label.toLowerCase()}.`) : status === 'processing' ? 'Document is processing or awaiting review.' : status === 'attention' ? 'Specialist review is required before this can be completed.' : 'No additional document is required right now.',
    documentCategory: input.category,
    impact: input.impact,
    route: input.route,
  }
}

function fieldRequirement(input: {
  id: string
  label: string
  value: unknown
  whyItMatters: string
  impact: GuidedRequirement['impact']
  route: string
  missing?: string
}): GuidedRequirement {
  const present = Boolean(clean(input.value))
  return {
    id: input.id,
    label: input.label,
    status: present ? 'complete' : 'missing',
    whyItMatters: input.whyItMatters,
    missing: present ? 'No additional information is required right now.' : (input.missing || `Add ${input.label.toLowerCase()}.`),
    impact: input.impact,
    route: input.route,
  }
}

function stageStatus(requirements: GuidedRequirement[], contribution: number): GuidedReadinessState | 'complete' {
  if (requirements.some(req => req.status === 'attention')) return 'action_needed'
  if (requirements.every(req => req.status === 'complete' || req.status === 'not_applicable')) return contribution >= 90 ? 'complete' : 'ready_to_review'
  if (contribution >= 65) return 'almost_ready'
  if (contribution > 0) return 'action_needed'
  return 'insufficient_information'
}

function stage(id: JourneyStageId, label: string, requirements: GuidedRequirement[], contribution: number): GuidedStage {
  return { id, label, requirements, contribution, status: stageStatus(requirements, contribution) }
}

function missing(requirements: GuidedRequirement[]) {
  return requirements.filter(req => req.status === 'missing' || req.status === 'attention').map(req => req.label)
}

export function buildClientFundingReadiness(input: {
  profile?: Record<string, any> | null
  documents?: any[]
  tasks?: any[]
  scores?: { credit?: number; business?: number; funding?: number }
  systemReviews?: any[]
  strategyRecommendations?: any[]
  strategyDecisions?: any[]
  journey?: ClientJourneyState | null
}): GuidedFundingReadiness {
  const profile = input.profile || {}
  const docs = Array.isArray(input.documents) ? input.documents : []
  const reviews = Array.isArray(input.systemReviews) ? input.systemReviews : []
  const tasks = Array.isArray(input.tasks) ? input.tasks : []
  const strategies = Array.isArray(input.strategyRecommendations) ? input.strategyRecommendations : []
  const decisions = Array.isArray(input.strategyDecisions) ? input.strategyDecisions : []
  const pText = profileText(profile)
  const creditReport = docMatches(docs, [/credit_report|credit report|transunion|experian|equifax/])
  const creditReview = reviews[0]
  const exception = docs.find(doc => doc.exception_review_status === 'required') || (Array.isArray(creditReview?.specialist_exceptions) && creditReview.specialist_exceptions.length ? creditReview.specialist_exceptions[0] : null)
  const pendingReview = docs.filter(doc => docStatus(doc) === 'processing')
  const hasStrategy = strategies.length > 0 || decisions.length > 0
  const creditRequirements = [
    documentRequirement({ id: 'credit_report_status', label: 'Current credit report', category: 'credit_report', patterns: [/credit_report|credit report|transunion|experian|equifax/], whyItMatters: 'A current report gives Nexus the source evidence needed to describe credit readiness accurately.', impact: 'high', route: '/client/credit-profile' }, docs),
    fieldRequirement({ id: 'bureau_coverage', label: 'Bureau coverage', value: creditReview?.summary?.bureauCoverage || (creditReview ? 'Reviewed' : ''), whyItMatters: 'Coverage determines how much of the credit profile can be reviewed.', impact: 'high', route: '/client/credit-profile', missing: 'Upload a recent report that identifies the available bureaus.' }),
    fieldRequirement({ id: 'canonical_accounts', label: 'Canonical accounts', value: creditReview?.report_item_reviews?.length || creditReview?.summary?.canonicalAccountCount, whyItMatters: 'Canonical matching keeps account observations separate from unsupported conclusions.', impact: 'medium', route: '/client/credit-profile', missing: 'Wait for report processing or request specialist review.' }),
    fieldRequirement({ id: 'discrepancies', label: 'Discrepancy review', value: creditReview?.report_item_reviews?.length || creditReview?.summary?.discrepancyCount, whyItMatters: 'Discrepancies are reviewed as observations and are not treated as proven errors.', impact: 'medium', route: '/client/credit-profile', missing: 'Complete report processing before reviewing discrepancies.' }),
    fieldRequirement({ id: 'utilization_summary', label: 'Utilization summary', value: creditReview?.utilization_actions?.length || creditReview?.summary?.utilizationStatus || (creditReport ? 'Available' : ''), whyItMatters: 'Utilization is a readiness factor to understand, not a guaranteed outcome.', impact: 'high', route: '/client/credit-profile', missing: 'Upload a current report for utilization review.' }),
    fieldRequirement({ id: 'approved_strategy', label: 'Approved Strategy Cards', value: hasStrategy ? 'Available' : '', whyItMatters: 'Strategy Cards summarize bounded options and preserve uncertainty for client decisions.', impact: 'medium', route: '/client/credit-profile', missing: 'Strategy Cards appear after report review.' }),
    fieldRequirement({ id: 'client_decisions', label: 'Client decisions', value: decisions.length, whyItMatters: 'Your decision tells Nexus which education or evidence path to keep visible.', impact: 'medium', route: '/client/credit-profile', missing: 'Review a Strategy Card and choose a factual next step.' }),
    documentRequirement({ id: 'credit_evidence', label: 'Credit evidence', category: 'credit_evidence', patterns: [/credit_evidence|dispute|bureau_response|evidence/], whyItMatters: 'Evidence helps a specialist understand a discrepancy without inventing facts.', impact: 'medium', route: '/client/credit-profile', missing: 'Upload supporting evidence only when a requirement requests it.' }, docs),
    fieldRequirement({ id: 'safe_drafts', label: 'Safe drafts', value: creditReview?.recommended_next_steps?.length || (docs.some(doc => doc.client_action_status === 'ready') ? 'Available' : ''), whyItMatters: 'Drafts remain review-only and are never mailed or submitted automatically.', impact: 'low', route: '/client/dispute-review', missing: 'No safe draft is currently available.' }),
  ]

  const foundationRequirements = [
    fieldRequirement({ id: 'entity_registration', label: 'Entity registration', value: profile.entity_type || profile.state_registration_status || docMatches(docs, [/business_formation|formation|incorporation|entity/]), whyItMatters: 'Entity identity gives funding reviewers a consistent business record.', impact: 'high', route: '/client/business-setup' }),
    fieldRequirement({ id: 'ein', label: 'EIN status', value: profile.ein_status || docMatches(docs, [/ein_confirmation|\bein\b|tax/]), whyItMatters: 'An EIN status supports business identity checks; Nexus never asks for a full EIN in the portal.', impact: 'high', route: '/client/business-setup' }),
    fieldRequirement({ id: 'business_address', label: 'Business address', value: profile.business_address_line1 || docMatches(docs, [/proof_of_address|address|utility|lease/]), whyItMatters: 'Consistent address evidence reduces avoidable identity mismatches.', impact: 'high', route: '/client/business-setup' }),
    fieldRequirement({ id: 'business_phone', label: 'Business phone', value: profile.business_phone || profile.phone, whyItMatters: 'A stable contact method is part of a lender-facing business profile.', impact: 'medium', route: '/client/business-setup' }),
    fieldRequirement({ id: 'business_email', label: 'Business email', value: profile.business_email || profile.email, whyItMatters: 'Consistent email and domain details support business identity review.', impact: 'medium', route: '/client/business-setup' }),
    fieldRequirement({ id: 'website_domain', label: 'Website or domain', value: profile.business_domain || profile.website, whyItMatters: 'A domain can help explain business identity and operating presence when available.', impact: 'low', route: '/client/business-setup' }),
    fieldRequirement({ id: 'naics_sic', label: 'NAICS / SIC', value: profile.naics_code || profile.industry, whyItMatters: 'Industry classification helps identify lender-facing questions without predicting approval.', impact: 'medium', route: '/client/business-setup' }),
    documentRequirement({ id: 'business_formation', label: 'Business formation documents', category: 'business_formation', patterns: [/business_formation|formation|incorporation|entity/], whyItMatters: 'Formation documents support the legal business identity record.', impact: 'high', route: '/client/business-setup' }, docs),
    documentRequirement({ id: 'business_license', label: 'Licenses where applicable', category: 'business_license', patterns: [/business_license|license|permit/], whyItMatters: 'Applicable licenses can resolve lender-facing questions about the operating activity.', impact: 'medium', route: '/client/business-setup' }, docs),
    documentRequirement({ id: 'supporting_documents', label: 'Supporting business documents', category: 'other', patterns: [/business_formation|business_license|proof_of_address|ein_confirmation/], whyItMatters: 'A complete document set reduces review delays.', impact: 'medium', route: '/client/documents' }, docs),
  ]

  const bankabilityRequirements = [
    fieldRequirement({ id: 'identity_consistency', label: 'Identity consistency', value: profile.legal_name || docMatches(docs, [/government_id|identification|passport/]), whyItMatters: 'Nexus compares records for consistency and surfaces uncertainty for review.', impact: 'high', route: '/client/business-setup' }),
    fieldRequirement({ id: 'address_consistency', label: 'Address consistency', value: profile.business_address_line1 || profile.mailing_address_line1 || docMatches(docs, [/address|utility|lease/]), whyItMatters: 'Address consistency is a lender-facing readiness signal, not an approval prediction.', impact: 'high', route: '/client/business-setup' }),
    fieldRequirement({ id: 'contact_consistency', label: 'Phone, email, and domain consistency', value: profile.business_phone || profile.business_email || profile.business_domain, whyItMatters: 'Consistent contact details help reviewers reconcile the business profile.', impact: 'medium', route: '/client/business-setup' }),
    fieldRequirement({ id: 'industry_risk', label: 'Industry-risk considerations', value: profile.industry || profile.naics_code, whyItMatters: 'Industry context may create additional questions; it does not determine approval.', impact: 'medium', route: '/client/business-bankability' }),
    fieldRequirement({ id: 'bank_account', label: 'Business bank account', value: profile.business_bank_account_status || docMatches(docs, [/bank_statement|bank|statement/]), whyItMatters: 'Banking evidence helps organize lender-facing readiness information.', impact: 'high', route: '/client/business-bankability' }),
    fieldRequirement({ id: 'account_age', label: 'Account age when available', value: profile.account_age || profile.time_in_business, whyItMatters: 'Time context is shown only when persisted or client-provided.', impact: 'medium', route: '/client/business-bankability', missing: 'Add time-in-business information when available.' }),
    fieldRequirement({ id: 'time_in_business', label: 'Time in business', value: profile.time_in_business, whyItMatters: 'Operating history is a readiness factor and is not a guaranteed lender result.', impact: 'high', route: '/client/business-bankability' }),
    documentRequirement({ id: 'revenue_documentation', label: 'Revenue documentation', category: 'revenue_financials', patterns: [/revenue|income|profit|loss|tax|statement/], whyItMatters: 'Revenue evidence lets a reviewer understand the documented operating picture.', impact: 'high', route: '/client/business-bankability' }, docs),
    fieldRequirement({ id: 'bookkeeping_readiness', label: 'Bookkeeping and statement readiness', value: profile.bookkeeping_status || docMatches(docs, [/bookkeeping|bank_statement|statement|profit|loss/]), whyItMatters: 'Organized records make a controlled readiness review more useful.', impact: 'medium', route: '/client/business-bankability' }),
    fieldRequirement({ id: 'lender_gaps', label: 'Lender-facing gaps', value: exception ? '' : (profile.industry || profile.business_bank_account_status || creditReview), whyItMatters: 'Gaps are surfaced for corrective action and never presented as a guaranteed approval outcome.', impact: 'medium', route: '/client/business-bankability', missing: exception ? 'Resolve the genuine exception through specialist review.' : 'Complete profile and document inputs to identify remaining gaps.' }),
  ]

  const fundingRequirements = [
    fieldRequirement({ id: 'complete_documents', label: 'Complete documents', value: docs.length && !pendingReview.length ? docs.length : '', whyItMatters: 'Funding readiness uses the documents that are actually persisted and visible to the client.', impact: 'high', route: '/client/documents', missing: 'Complete required documents for the active journey stages.' }),
    documentRequirement({ id: 'funding_application_package', label: 'Funding application support', category: 'funding_applications', patterns: [/funding_application|funding support|application/], whyItMatters: 'A funding application support document is linked to the readiness snapshot for controlled review.', impact: 'medium', route: '/client/funding-readiness', missing: 'Upload an application support document when one is requested.' }, docs),
    documentRequirement({ id: 'purchased_debt_documentation', label: 'Purchased-debt documentation', category: 'funding_applications', patterns: [/purchased.?debt|debt.?purchase|acquisition/], whyItMatters: 'Purchased-debt documentation lets a reviewer distinguish client-provided obligations from Nexus observations.', impact: 'high', route: '/client/funding-readiness', missing: 'Upload purchased-debt documentation if this applies to your funding package.' }, docs),
    fieldRequirement({ id: 'missing_documents', label: 'Missing documents', value: missing([...foundationRequirements, ...bankabilityRequirements]).length === 0 ? 'None' : '', whyItMatters: 'Missing items are explicit next actions, not hidden score deductions.', impact: 'high', route: '/client/documents' }),
    fieldRequirement({ id: 'processing_documents', label: 'Processing documents', value: pendingReview.length ? '' : 'None', whyItMatters: 'Processing documents are not treated as complete until their status changes.', impact: 'high', route: '/client/documents' }),
    fieldRequirement({ id: 'readiness_blockers', label: 'Primary blockers', value: exception ? '' : (creditReport || profile.business_name || profile.title), whyItMatters: 'A blocker identifies the next safe action and does not predict an approval decision.', impact: 'high', route: exception ? '/client/request-review' : '/client/funding-readiness' }),
    fieldRequirement({ id: 'tier_1_relevance', label: 'Tier 1 relevance', value: creditReport && foundationRequirements.filter(req => req.impact === 'high' && req.status === 'complete').length >= 3 ? 'Relevant inputs present' : '', whyItMatters: 'Tier 1 relevance describes inputs to review; lenders make final decisions.', impact: 'high', route: '/client/funding-readiness' }),
    fieldRequirement({ id: 'tier_2_relevance', label: 'Tier 2 relevance', value: bankabilityRequirements.filter(req => req.status === 'complete').length >= 5 ? 'Relevant inputs present' : '', whyItMatters: 'Tier 2 relevance adds operating history, revenue, banking, and documentation context.', impact: 'medium', route: '/client/funding-readiness' }),
    fieldRequirement({ id: 'review_eligibility', label: 'Review eligibility', value: !exception && !pendingReview.length && creditReport && foundationRequirements.filter(req => req.status === 'missing').length < 3 ? 'Eligible to request review' : '', whyItMatters: 'Eligibility is a controlled workflow state, not an approval prediction.', impact: 'high', route: '/client/request-review' }),
    fieldRequirement({ id: 'readiness_history', label: 'Readiness history', value: input.scores?.funding || tasks.find(task => /readiness|review/i.test(`${task.category || ''} ${task.title || ''}`)), whyItMatters: 'History shows persisted progress over time instead of implying a guaranteed result.', impact: 'low', route: '/client/funding-readiness' }),
  ]

  const creditScore = Math.max(0, Math.min(100, Number(input.scores?.credit || 0)))
  const foundationScore = Math.round(foundationRequirements.filter(req => req.status === 'complete').length / foundationRequirements.length * 100)
  const bankabilityScore = Math.round(bankabilityRequirements.filter(req => req.status === 'complete').length / bankabilityRequirements.length * 100)
  const fundingScore = Math.round((creditScore + foundationScore + bankabilityScore) / 3)
  const stages = {
    credit: stage('credit_profile', 'Credit', creditRequirements, creditScore || Math.round(creditRequirements.filter(req => req.status === 'complete').length / creditRequirements.length * 100)),
    business_foundation: stage('business_foundation', 'Business Foundation', foundationRequirements, foundationScore),
    business_bankability: stage('business_bankability', 'Business Bankability', bankabilityRequirements, bankabilityScore),
    funding: stage('funding_readiness', 'Funding Readiness', fundingRequirements, fundingScore),
  }
  const allRequirements = Object.values(stages).flatMap(item => item.requirements)
  const missingRequirements = allRequirements.filter(req => req.status === 'missing' || req.status === 'attention')
  const processingDocuments = pendingReview.map(doc => doc.title || doc.filename || doc.category || 'Document')
  const missingDocuments = allRequirements.filter(req => req.documentCategory && req.status === 'missing').map(req => req.label)
  const completedRequirements = allRequirements.filter(req => req.status === 'complete').map(req => req.label)
  const outstandingRequirements = missingRequirements.map(req => req.label)
  const profileSufficient = Boolean(pText && Object.keys(profile).some(key => Boolean(profile[key])))
  const state: GuidedReadinessState = exception ? 'action_needed' : !profileSufficient && !creditReport ? 'insufficient_information' : !processingDocuments.length && missingRequirements.length <= 2 && fundingScore >= 75 ? 'ready_to_review' : fundingScore >= 55 ? 'almost_ready' : 'action_needed'
  const primaryBlocker = exception ? 'Genuine exception requires specialist review' : missingRequirements[0]?.label || processingDocuments[0] || null
  const currentStage: GuidedStage = stages.credit.contribution < 50 ? stages.credit : stages.business_foundation.contribution < 70 ? stages.business_foundation : stages.business_bankability.contribution < 70 ? stages.business_bankability : stages.funding
  const tier1Blockers = [!creditReport && 'Current credit report', foundationScore < 70 && 'Business Foundation requirements', exception && 'Specialist exception review'].filter(Boolean) as string[]
  const tier2Blockers = [...tier1Blockers, bankabilityScore < 70 && 'Business Bankability requirements', processingDocuments.length > 0 && 'Processing documents'].filter(Boolean) as string[]
  const readinessHistory = tasks.filter(task => /readiness|review/i.test(`${task.category || ''} ${task.title || ''}`)).slice(0, 5).map(task => ({ label: task.title || 'Readiness activity', status: String(task.status || 'observed'), date: task.created_at || task.updated_at || '' }))

  return {
    state,
    overallScore: fundingScore,
    primaryBlocker,
    nextBestAction: exception ? 'Request specialist review for the genuine exception' : currentStage.requirements.find(req => req.status === 'missing' || req.status === 'attention')?.missing || (processingDocuments.length ? 'Check processing documents in the vault' : 'Request a controlled readiness review'),
    nextBestActionRoute: exception ? '/client/request-review' : currentStage.requirements.find(req => req.status === 'missing' || req.status === 'attention')?.route || '/client/request-review',
    reviewEligible: state === 'ready_to_review' && !exception && processingDocuments.length === 0,
    processingDocuments,
    missingDocuments,
    completedRequirements,
    outstandingRequirements,
    readinessHistory,
    tier1: { status: tier1Blockers.length ? (tier1Blockers.length > 2 ? 'action_needed' : 'almost_ready') : 'ready_to_review', relevance: 'Credit Profile and Business Foundation inputs are relevant to Tier 1 review. This is not an approval decision.', blockers: tier1Blockers },
    tier2: { status: tier2Blockers.length ? (tier2Blockers.length > 3 ? 'action_needed' : 'almost_ready') : 'ready_to_review', relevance: 'Tier 2 review additionally considers operating history, revenue, banking, and organized records. Lenders make final decisions.', blockers: tier2Blockers },
    stages,
  }
}
