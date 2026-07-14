import { getNextRecommendedDocument, type DocumentTrack } from './documentClassification'

type ClydeContext = {
  route?: string
  track?: DocumentTrack
  clientState?: {
    documents?: Array<{ category?: string; title?: string; filename?: string; goclear_review_status?: string; status?: string }>
    missingRequirements?: string[]
    profileComplete?: boolean
    pendingReview?: boolean
    creditReadinessStatus?: string
    tier1Status?: string
    tier2Status?: string
    utilizationHigh?: boolean
    evidenceNeeded?: boolean
    reportItemsToReview?: number
  }
}

function trackFromRoute(route?: string, fallback?: DocumentTrack): DocumentTrack {
  if (fallback) return fallback
  if (/credit-profile|credit-utilization/.test(route || '')) return 'credit_profile'
  if (/credit-repair|dispute-review/.test(route || '')) return 'credit_repair'
  if (/profile|business-setup/.test(route || '')) return 'business_profile'
  if (/funding-readiness/.test(route || '')) return 'business_funding'
  if (/documents/.test(route || '')) return 'documents'
  if (/request-review/.test(route || '')) return 'request_review'
  return 'general'
}

export function getClydePageContext({ route, track, clientState }: ClydeContext) {
  const currentTrack = trackFromRoute(route, track)
  const nextDocument = getNextRecommendedDocument({
    track: currentTrack,
    uploadedDocuments: clientState?.documents || [],
    missingRequirements: clientState?.missingRequirements || [],
  })
  const pageGoalMap: Record<DocumentTrack, string> = {
    credit_profile: 'Understand what may be affecting your funding readiness and optimize your Credit Profile.',
    business_profile: 'Complete your Business Profile foundation.',
    business_funding: 'Prepare your Credit Profile and Business Profile for Tier 1 and Tier 2 funding positioning.',
    request_review: 'Package the right support for GoClear Review.',
    credit_repair: 'Review report items and organize possible documentation options.',
    documents: 'Keep Documents Vault organized for GoClear Review.',
    general: 'Move to the next best client action.',
  }
  return {
    currentTrack,
    pageGoal: pageGoalMap[currentTrack],
    whatClydeShouldFocusOn: `Next recommended document: ${nextDocument}`,
    availableActions: generateClydeQuickActions({ track: currentTrack, clientState }),
    nextDocument,
  }
}

export function generateClydeRecommendations(context: ClydeContext) {
  const page = getClydePageContext(context)
  const base = [
    {
      title: `Upload ${page.nextDocument}`,
      reason: 'Upload one document and Clyde will organize it for GoClear Review.',
      actionLabel: 'Upload Document',
      actionType: 'upload',
      uploadContext: { track: page.currentTrack, suggestedCategory: undefined },
      priority: 'high',
      status: 'next',
    },
    {
      title: 'Request GoClear Review',
      reason: 'Use this when you want a specialist to review your current file.',
      actionLabel: 'Request Review',
      actionType: 'route',
      route: '/client/request-review',
      priority: 'medium',
      status: 'available',
    },
    {
      title: 'Open Documents Vault',
      reason: 'Documents is your vault. Uploads from any page are organized there.',
      actionLabel: 'View Vault',
      actionType: 'route',
      route: '/client/documents',
      priority: 'low',
      status: 'available',
    },
  ]
  if (page.currentTrack === 'credit_profile') {
    base.splice(1, 0, { title: 'Review Report Items', reason: 'Review items that may affect funding readiness and see documentation options.', actionLabel: 'Show Options', actionType: 'route', route: '/client/credit-repair-journey', priority: 'medium', status: 'available' })
  }
  if (page.currentTrack === 'business_funding') {
    base.splice(1, 0, { title: 'Review Missing Requirements', reason: 'Funding review depends on missing documents and profile blockers.', actionLabel: 'Review Readiness', actionType: 'route', route: '/client/funding-readiness', priority: 'medium', status: 'available' })
  }
  return base.slice(0, 5)
}

export function generateClydeQuickActions(context: ClydeContext) {
  const currentTrack = trackFromRoute(context.route, context.track)
  const actions = [
    { label: 'Upload Document', actionType: 'upload', uploadContext: { track: currentTrack } },
    { label: 'Ask GoClear to Review', actionType: 'route', route: '/client/request-review' },
    { label: 'Show Missing Items', actionType: 'focus', target: 'missing' },
    { label: 'Continue My Next Step', actionType: 'next' },
    { label: 'Open Documents Vault', actionType: 'route', route: '/client/documents' },
  ]
  if (currentTrack === 'credit_profile' || currentTrack === 'credit_repair') actions.push({ label: 'Review Letters', actionType: 'route', route: '/client/dispute-review' })
  return actions
}

export function generateClydeAnswer(question: string, context: ClydeContext) {
  const page = getClydePageContext(context)
  const lower = question.toLowerCase()
  if (lower.includes('next')) return `Here is your next best action: upload ${page.nextDocument}. It will show as Pending GoClear Review after upload.`
  if (lower.includes('document')) return `Upload one document at a time. For this page, the next useful document is ${page.nextDocument}. Suggested categories are based on context and filename; GoClear will verify.`
  if (lower.includes('credit')) return 'I’ll help you understand what may be affecting your funding readiness. Start with a credit report, review utilization and report items, then let GoClear review any documentation options before approval.'
  if (lower.includes('business profile')) return 'Complete business basics, EIN/entity status, address, banking status, and required business documents. Do not enter full EIN or account numbers.'
  if (lower.includes('tier 1') || lower.includes('tier1')) return `Tier 1 readiness is ${context.clientState?.tier1Status || 'still being evaluated'}. Review Credit Profile utilization, inquiries, major funding-impact items, and Business Profile completeness. This is readiness guidance, not an approval decision.`
  if (lower.includes('tier 2') || lower.includes('tier2')) return `Tier 2 readiness is ${context.clientState?.tier2Status || 'still being evaluated'}. Tier 2 also needs operating history, revenue, banking, and supporting documents. Lenders make final decisions.`
  if (lower.includes('funding')) return 'Your next step is to improve your Credit Profile and Business Profile readiness. The goal is stronger Tier 1 and Tier 2 funding positioning; lenders make final decisions and readiness does not guarantee approval.'
  if (lower.includes('reviewing')) return 'GoClear reviews uploaded documents, selected dispute items, support evidence, and review requests. Pending items stay marked as Pending GoClear Review.'
  if (lower.includes('utilization')) return context.clientState?.utilizationHigh ? 'Your available readiness data indicates utilization needs attention. Review payoff timing and balance reduction options; no score change is guaranteed.' : 'No approved high-utilization flag is available yet. Upload a current report or wait for GoClear review before relying on a recommendation.'
  if (lower.includes('evidence')) return context.clientState?.evidenceNeeded ? 'An approved review item needs supporting evidence. Upload only the requested document with sensitive fields redacted.' : 'No approved evidence request is available yet. GoClear may request one after reviewing system recommendations.'
  if (lower.includes('report item')) return `${context.clientState?.reportItemsToReview || 0} approved report items are currently available for client review. A parsed flag is not a finding that an item is inaccurate.`
  if (lower.includes('credit profile complete')) return `Your Credit Profile status is ${context.clientState?.creditReadinessStatus || 'still being evaluated'}. Complete the current report review, utilization steps, and requested evidence.`
  if (lower.includes('challenge') || lower.includes('dispute')) return 'Some report items may be worth reviewing if they appear inaccurate, outdated, duplicated, unfamiliar, incomplete, or unverifiable. I can organize documents and show options, but GoClear does not guarantee removals, score increases, or funding approval.'
  if (lower.includes('waiting')) return 'Waiting on you usually means a missing document, profile field, selected dispute reason, or letter approval. Waiting on GoClear means Pending GoClear Review.'
  return `For this page, focus on: ${page.pageGoal} ${page.whatClydeShouldFocusOn}.`
}

export function getClydeNextBestAction(context: ClydeContext) {
  return generateClydeRecommendations(context)[0]
}
