export type CustomerGoal =
  | 'improve_credit_profile'
  | 'build_business_profile'
  | 'get_business_funding'
  | 'buy_home_or_personal_goal'
  | 'not_sure'

export type CustomerTrackStatus = {
  label: string
  percentComplete: number
  status: 'missing' | 'in_progress' | 'needs_review' | 'ready' | 'completed'
  missingItems: string[]
  nextBestAction: string
  primaryCTA: string
  route: string
}

export function getCustomerGoalOptions() {
  return [
    { id: 'improve_credit_profile' as const, label: 'Improve my Credit Profile' },
    { id: 'build_business_profile' as const, label: 'Build my Business Profile' },
    { id: 'get_business_funding' as const, label: 'Get ready for Business Funding' },
    { id: 'buy_home_or_personal_goal' as const, label: 'Buy a home or reach another financial goal' },
    { id: 'not_sure' as const, label: 'I am not sure yet' },
  ]
}

export function calculateCustomerFlowStatus(context: {
  scores?: { credit?: number; business?: number; funding?: number }
  documents?: Array<{ category?: string; title?: string; status?: string; goclear_review_status?: string }>
  profileComplete?: { percent?: number; complete?: boolean } | null
  lettersReady?: boolean
  reviewPending?: boolean
}): {
  creditProfileStatus: CustomerTrackStatus
  businessProfileStatus: CustomerTrackStatus
  businessFundingStatus: CustomerTrackStatus
  documentsStatus: CustomerTrackStatus
  reviewStatus: CustomerTrackStatus
  monthlyProgressStatus: CustomerTrackStatus
} {
  const docs = context.documents || []
  const hasCreditReport = docs.some(d => /credit/i.test(`${d.category || ''} ${d.title || ''}`))
  const hasBank = docs.some(d => /bank/i.test(`${d.category || ''} ${d.title || ''}`))
  const profilePercent = context.profileComplete?.percent ?? 55
  const creditScore = context.scores?.credit ?? 40
  const businessScore = Math.max(context.scores?.business ?? 45, profilePercent)
  const fundingScore = context.scores?.funding ?? 35

  return {
    creditProfileStatus: {
      label: 'Credit Profile',
      percentComplete: hasCreditReport ? Math.max(creditScore, 68) : Math.min(creditScore, 45),
      status: hasCreditReport ? 'in_progress' : 'missing',
      missingItems: hasCreditReport ? ['Choose items to challenge', 'Review utilization options'] : ['Credit report'],
      nextBestAction: hasCreditReport ? 'Choose items to challenge or review utilization options.' : 'Upload your credit report.',
      primaryCTA: hasCreditReport ? 'Choose Items to Challenge' : 'Upload Credit Report',
      route: hasCreditReport ? '/client/credit-repair-journey' : '/client/credit-profile',
    },
    businessProfileStatus: {
      label: 'Business Profile',
      percentComplete: Math.min(100, businessScore),
      status: businessScore >= 80 ? 'ready' : 'in_progress',
      missingItems: businessScore >= 80 ? [] : ['Business basics', 'EIN/entity status', 'business profile documents'],
      nextBestAction: 'Complete business basics and upload business documents.',
      primaryCTA: 'Complete Business Profile',
      route: '/client/profile',
    },
    businessFundingStatus: {
      label: 'Business Funding',
      percentComplete: hasBank ? Math.max(fundingScore, 70) : fundingScore,
      status: hasBank && fundingScore >= 70 ? 'needs_review' : 'missing',
      missingItems: hasBank ? ['GoClear funding review'] : ['Bank statement', 'tax return or P&L if needed'],
      nextBestAction: hasBank ? 'Request GoClear funding review.' : 'Upload funding documents.',
      primaryCTA: hasBank ? 'Request Funding Review' : 'Upload Funding Docs',
      route: hasBank ? '/client/request-review' : '/client/funding-readiness',
    },
    documentsStatus: {
      label: 'Documents',
      percentComplete: Math.min(100, docs.length * 12),
      status: docs.length ? 'in_progress' : 'missing',
      missingItems: docs.length ? ['Review status for pending files'] : ['Credit report', 'ID', 'proof of address', 'bank statement'],
      nextBestAction: 'Upload missing documents from the page you are on.',
      primaryCTA: 'Open Document Vault',
      route: '/client/documents',
    },
    reviewStatus: {
      label: 'GoClear Review',
      percentComplete: context.reviewPending ? 70 : 25,
      status: context.reviewPending ? 'needs_review' : 'missing',
      missingItems: context.reviewPending ? ['GoClear response'] : ['Submit review request'],
      nextBestAction: context.reviewPending ? 'Wait for GoClear review or add missing documents.' : 'Request GoClear review when your key items are ready.',
      primaryCTA: 'Request GoClear Review',
      route: '/client/request-review',
    },
    monthlyProgressStatus: {
      label: 'Monthly Progress',
      percentComplete: Math.round((creditScore + businessScore + fundingScore) / 3),
      status: 'in_progress',
      missingItems: ['Next milestone', 'GoClear review queue updates'],
      nextBestAction: 'Complete this month’s next best action and review what GoClear is working on.',
      primaryCTA: 'View Next Action',
      route: hasCreditReport ? '/client/funding-readiness' : '/client/credit-profile',
    },
  }
}

export function generateNextBestActions(context: Parameters<typeof calculateCustomerFlowStatus>[0]) {
  const status = calculateCustomerFlowStatus(context)
  const actions = [
    status.creditProfileStatus,
    status.businessProfileStatus,
    status.businessFundingStatus,
    status.reviewStatus,
  ].map(s => ({ title: s.primaryCTA, description: s.nextBestAction, route: s.route, track: s.label }))
  return actions.slice(0, 5)
}

export function generateSubscriptionValueSummary(context: Parameters<typeof calculateCustomerFlowStatus>[0]) {
  const status = calculateCustomerFlowStatus(context)
  return {
    workingOn: ['Credit Profile review', 'Business Profile readiness', 'Business Funding next steps'],
    completedThisMonth: context.documents?.length ? ['Documents uploaded and routed to review'] : ['Portal access and guided flow started'],
    waitingOnClient: [...status.creditProfileStatus.missingItems, ...status.businessFundingStatus.missingItems].slice(0, 4),
    waitingOnGoClear: context.reviewPending ? ['Specialist review queue'] : ['Submit a review request when ready'],
    nextMonthFocus: status.monthlyProgressStatus.nextBestAction,
  }
}

export function groupRecommendationsByOutcome(context: Parameters<typeof calculateCustomerFlowStatus>[0]) {
  const status = calculateCustomerFlowStatus(context)
  return {
    'Credit Profile': [status.creditProfileStatus.nextBestAction, 'Review dispute options', 'Review utilization improvement options'],
    'Business Profile': [status.businessProfileStatus.nextBestAction, 'Confirm EIN/entity status', 'Upload business documents'],
    'Business Funding': [status.businessFundingStatus.nextBestAction, 'Review missing requirements', 'Request GoClear funding review'],
  }
}
