export type JourneyStageId = 'credit_profile' | 'credit_improvement' | 'business_foundation' | 'business_bankability' | 'funding_readiness' | 'review_plan'

export type StageStatus = 'not_started' | 'action_needed' | 'in_progress' | 'ready_to_review' | 'complete' | 'blocked' | 'insufficient_information'

export interface JourneyRequirement {
  id: string
  label: string
  description: string
  status: 'complete' | 'missing' | 'in_progress' | 'pending_review' | 'not_applicable'
  documentCategory?: string
  whyItMatters: string
  readinessImpact: 'high' | 'medium' | 'low'
  partnerOffer?: string
}

export interface JourneyStage {
  id: JourneyStageId
  displayName: string
  description: string
  status: StageStatus
  score: number
  completedRequirements: string[]
  missingRequirements: string[]
  blockingRequirements: string[]
  nextAction: string
  nextActionRoute: string
  requiredDocuments: string[]
  optionalResources: string[]
  readinessImpact: string
  previousStage: JourneyStageId | null
  nextStage: JourneyStageId | null
}

export interface ClientJourneyState {
  currentStage: JourneyStageId
  stages: Record<JourneyStageId, JourneyStage>
  overallScore: number
  completedCount: number
  totalCount: number
  primaryBlocker: string | null
  nextBestAction: string
  nextBestActionRoute: string
  reviewEligible: boolean
  lastActivity: string | null
}

function scoreToStatus(score: number, missing: string[], blocking: string[]): StageStatus {
  if (blocking.length > 0) return 'blocked'
  if (missing.length === 0 && score >= 90) return 'complete'
  if (missing.length === 0) return 'ready_to_review'
  if (score >= 60) return 'in_progress'
  if (score > 0) return 'action_needed'
  return 'not_started'
}

const STAGE_DEFINITIONS: Record<JourneyStageId, Omit<JourneyStage, 'status' | 'score' | 'completedRequirements' | 'missingRequirements' | 'blockingRequirements'>> = {
  credit_profile: {
    id: 'credit_profile',
    displayName: 'Credit Profile',
    description: 'Understand your current credit standing across all three bureaus.',
    nextAction: 'Upload your credit report for analysis',
    nextActionRoute: '/client/credit-profile',
    requiredDocuments: ['Credit Report (PDF)'],
    optionalResources: ['SmartCredit monitoring', 'AnnualCreditReport.com'],
    readinessImpact: 'Credit profile score directly impacts Tier 1 and Tier 2 funding eligibility.',
    previousStage: null,
    nextStage: 'credit_improvement',
  },
  credit_improvement: {
    id: 'credit_improvement',
    displayName: 'Credit Improvement',
    description: 'Address discrepancies and optimize your credit profile.',
    nextAction: 'Review strategy recommendations and select actions',
    nextActionRoute: '/client/credit-profile',
    requiredDocuments: ['Dispute evidence (if applicable)'],
    optionalResources: ['Credit education resources'],
    readinessImpact: 'Improved credit scores unlock better funding terms and higher approval odds.',
    previousStage: 'credit_profile',
    nextStage: 'business_foundation',
  },
  business_foundation: {
    id: 'business_foundation',
    displayName: 'Business Foundation',
    description: 'Establish your business identity and core documentation.',
    nextAction: 'Complete your business profile',
    nextActionRoute: '/client/business-setup',
    requiredDocuments: ['Business formation documents', 'EIN confirmation', 'Business address verification'],
    optionalResources: ['Business banking setup', 'Domain registration'],
    readinessImpact: 'A complete business foundation is required for all funding applications.',
    previousStage: 'credit_improvement',
    nextStage: 'business_bankability',
  },
  business_bankability: {
    id: 'business_bankability',
    displayName: 'Business Bankability',
    description: 'Demonstrate business stability and revenue readiness.',
    nextAction: 'Add revenue documentation and banking details',
    nextActionRoute: '/client/business-bankability',
    requiredDocuments: ['Bank statements (3 months)', 'Revenue documentation', 'Business phone/email'],
    optionalResources: ['Bookkeeping setup', 'Business banking partners'],
    readinessImpact: 'Bankability signals determine lender confidence and funding amounts.',
    previousStage: 'business_foundation',
    nextStage: 'funding_readiness',
  },
  funding_readiness: {
    id: 'funding_readiness',
    displayName: 'Funding Readiness',
    description: 'Final readiness check before funding applications.',
    nextAction: 'Complete remaining requirements and request review',
    nextActionRoute: '/client/funding-readiness',
    requiredDocuments: ['All prior stage documents'],
    optionalResources: ['Funding preparation guides'],
    readinessImpact: 'Funding readiness score determines which funding tiers you qualify for.',
    previousStage: 'business_bankability',
    nextStage: 'review_plan',
  },
  review_plan: {
    id: 'review_plan',
    displayName: 'Review & Funding Plan',
    description: 'Expert review of your complete funding readiness package.',
    nextAction: 'Request your personalized review',
    nextActionRoute: '/client/request-review',
    requiredDocuments: [],
    optionalResources: [],
    readinessImpact: 'The review produces your personalized funding roadmap.',
    previousStage: 'funding_readiness',
    nextStage: null,
  },
}

export function computeJourneyState(data: {
  creditScore?: number
  creditReportUploaded?: boolean
  hasDiscrepancies?: boolean
  strategySelected?: boolean
  businessProfileComplete?: boolean
  entityEstablished?: boolean
  einAvailable?: boolean
  businessAddress?: boolean
  bankAccountReady?: boolean
  revenueDocumented?: boolean
  timeInBusiness?: number
  documentsComplete?: number
  documentsMissing?: number
  reviewRequested?: boolean
  lastActivity?: string | null
  utilizationHigh?: boolean
}): ClientJourneyState {
  const stages: Record<JourneyStageId, JourneyStage> = {} as any

  const creditMissing: string[] = []
  const creditBlocking: string[] = []
  if (!data.creditReportUploaded) creditMissing.push('Credit Report')
  if (data.utilizationHigh) creditMissing.push('Utilization reduction')
  const creditScore = data.creditScore || 0
  const creditCompleted: string[] = []
  if (data.creditReportUploaded) creditCompleted.push('Credit Report')
  if (!data.strategySelected && data.creditReportUploaded) creditMissing.push('Strategy selection')

  stages.credit_profile = {
    ...STAGE_DEFINITIONS.credit_profile,
    status: scoreToStatus(data.creditReportUploaded ? Math.max(creditScore, 50) : 0, creditMissing, creditBlocking),
    score: data.creditReportUploaded ? Math.max(creditScore, 50) : 0,
    completedRequirements: creditCompleted,
    missingRequirements: creditMissing,
    blockingRequirements: creditBlocking,
  }

  const improvementMissing: string[] = []
  const improvementCompleted: string[] = []
  if (data.strategySelected) improvementCompleted.push('Strategy selected')
  else if (data.creditReportUploaded) improvementMissing.push('Strategy selection')

  stages.credit_improvement = {
    ...STAGE_DEFINITIONS.credit_improvement,
    status: scoreToStatus(data.strategySelected ? 80 : (data.creditReportUploaded ? 30 : 0), improvementMissing, []),
    score: data.strategySelected ? 80 : (data.creditReportUploaded ? 30 : 0),
    completedRequirements: improvementCompleted,
    missingRequirements: improvementMissing,
    blockingRequirements: [],
  }

  const bizMissing: string[] = []
  const bizCompleted: string[] = []
  const bizBlocking: string[] = []
  if (data.entityEstablished) bizCompleted.push('Entity')
  else bizMissing.push('Business entity')
  if (data.einAvailable) bizCompleted.push('EIN')
  else bizMissing.push('EIN')
  if (data.businessAddress) bizCompleted.push('Address')
  else bizMissing.push('Business address')

  stages.business_foundation = {
    ...STAGE_DEFINITIONS.business_foundation,
    status: scoreToStatus(bizCompleted.length / 3 * 100, bizMissing, bizBlocking),
    score: Math.round(bizCompleted.length / 3 * 100),
    completedRequirements: bizCompleted,
    missingRequirements: bizMissing,
    blockingRequirements: bizBlocking,
  }

  const bankMissing: string[] = []
  const bankCompleted: string[] = []
  if (data.bankAccountReady) bankCompleted.push('Bank account')
  else bankMissing.push('Business bank account')
  if (data.revenueDocumented) bankCompleted.push('Revenue docs')
  else bankMissing.push('Revenue documentation')
  if (data.timeInBusiness && data.timeInBusiness >= 6) bankCompleted.push('6+ months in business')
  else bankMissing.push('Time in business (6+ months)')

  stages.business_bankability = {
    ...STAGE_DEFINITIONS.business_bankability,
    status: scoreToStatus(bankCompleted.length / 3 * 100, bankMissing, []),
    score: Math.round(bankCompleted.length / 3 * 100),
    completedRequirements: bankCompleted,
    missingRequirements: bankMissing,
    blockingRequirements: [],
  }

  const allStages = ['credit_profile', 'credit_improvement', 'business_foundation', 'business_bankability'] as JourneyStageId[]
  const allComplete = allStages.every(s => stages[s].status === 'complete' || stages[s].status === 'ready_to_review')
  const docsOk = (data.documentsComplete || 0) > 0 && (data.documentsMissing || 0) === 0

  stages.funding_readiness = {
    ...STAGE_DEFINITIONS.funding_readiness,
    status: allComplete && docsOk ? 'ready_to_review' : (allComplete ? 'action_needed' : 'not_started'),
    score: allComplete ? (docsOk ? 90 : 70) : Math.round(allStages.reduce((sum, s) => sum + stages[s].score, 0) / allStages.length * 0.5),
    completedRequirements: allComplete ? ['All prior stages'] : [],
    missingRequirements: allComplete ? (docsOk ? [] : ['Complete document set']) : ['Complete credit and business stages first'],
    blockingRequirements: [],
  }

  stages.review_plan = {
    ...STAGE_DEFINITIONS.review_plan,
    status: data.reviewRequested ? 'complete' : (stages.funding_readiness.status === 'ready_to_review' ? 'ready_to_review' : 'not_started'),
    score: data.reviewRequested ? 100 : (stages.funding_readiness.status === 'ready_to_review' ? 80 : 0),
    completedRequirements: data.reviewRequested ? ['Review requested'] : [],
    missingRequirements: data.reviewRequested ? [] : ['Complete funding readiness'],
    blockingRequirements: [],
  }

  const stageOrder: JourneyStageId[] = ['credit_profile', 'credit_improvement', 'business_foundation', 'business_bankability', 'funding_readiness', 'review_plan']
  let currentStage: JourneyStageId = 'credit_profile'
  for (const sid of stageOrder) {
    if (stages[sid].status === 'not_started' || stages[sid].status === 'action_needed' || stages[sid].status === 'blocked') {
      currentStage = sid
      break
    }
    currentStage = sid
  }

  const totalReqs = stageOrder.reduce((sum, s) => sum + stages[s].completedRequirements.length + stages[s].missingRequirements.length, 0)
  const completedReqs = stageOrder.reduce((sum, s) => sum + stages[s].completedRequirements.length, 0)
  const overallScore = Math.round(stageOrder.reduce((sum, s) => sum + stages[s].score, 0) / stageOrder.length)

  const blockers: string[] = []
  for (const s of stageOrder) {
    for (const b of stages[s].blockingRequirements) blockers.push(b)
    if (stages[s].status === 'blocked') blockers.push(`${stages[s].displayName} is blocked`)
  }

  const current = stages[currentStage]
  return {
    currentStage,
    stages,
    overallScore,
    completedCount: completedReqs,
    totalCount: totalReqs,
    primaryBlocker: blockers[0] || null,
    nextBestAction: current.nextAction,
    nextBestActionRoute: current.nextActionRoute,
    reviewEligible: stages.funding_readiness.status === 'ready_to_review' || stages.funding_readiness.status === 'complete',
    lastActivity: data.lastActivity || null,
  }
}

export function getStageIndex(id: JourneyStageId): number {
  const order: JourneyStageId[] = ['credit_profile', 'credit_improvement', 'business_foundation', 'business_bankability', 'funding_readiness', 'review_plan']
  return order.indexOf(id)
}

export function getPreviousStage(id: JourneyStageId): JourneyStageId | null {
  const idx = getStageIndex(id)
  const order: JourneyStageId[] = ['credit_profile', 'credit_improvement', 'business_foundation', 'business_bankability', 'funding_readiness', 'review_plan']
  return idx > 0 ? order[idx - 1] : null
}

export function getNextStage(id: JourneyStageId): JourneyStageId | null {
  const idx = getStageIndex(id)
  const order: JourneyStageId[] = ['credit_profile', 'credit_improvement', 'business_foundation', 'business_bankability', 'funding_readiness', 'review_plan']
  return idx < order.length - 1 ? order[idx + 1] : null
}
