import { getNextRecommendedDocument, type DocumentTrack } from './documentClassification'

type ClydeContext = {
  route?: string
  track?: DocumentTrack
  clientState?: {
    documents?: Array<{ category?: string; title?: string; filename?: string; goclear_review_status?: string; status?: string }>
    missingRequirements?: string[]
    profileComplete?: boolean
    pendingReview?: boolean
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
    credit_profile: 'Improve and repair your Credit Profile.',
    business_profile: 'Complete your Business Profile foundation.',
    business_funding: 'Prepare for Business Funding review.',
    request_review: 'Package the right support for GoClear Review.',
    credit_repair: 'Choose items, reasons, evidence, and approval steps.',
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
    base.splice(1, 0, { title: 'Choose Items to Challenge', reason: 'Pick what you want reviewed and why.', actionLabel: 'Show Options', actionType: 'route', route: '/client/credit-repair-journey', priority: 'medium', status: 'available' })
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
  if (lower.includes('credit')) return 'Start with a credit report, then choose items you want challenged, upload evidence, and let GoClear review dispute options before approval.'
  if (lower.includes('business profile')) return 'Complete business basics, EIN/entity status, address, banking status, and required business documents. Do not enter full EIN or account numbers.'
  if (lower.includes('funding')) return 'Business Funding depends on Credit Profile, Business Profile, and funding documents. GoClear review is required before any funding recommendation.'
  if (lower.includes('reviewing')) return 'GoClear reviews uploaded documents, selected dispute items, support evidence, and review requests. Pending items stay marked as Pending GoClear Review.'
  if (lower.includes('utilization')) return 'High utilization may be improved with payoff timing, balance reduction, limit increase prep, or consolidation review. GoClear should review before action.'
  if (lower.includes('challenge')) return 'Tell me which items you want challenged and why. Nexus prepares options, then specialist review and client approval are required.'
  if (lower.includes('waiting')) return 'Waiting on you usually means a missing document, profile field, selected dispute reason, or letter approval. Waiting on GoClear means Pending GoClear Review.'
  return `For this page, focus on: ${page.pageGoal} ${page.whatClydeShouldFocusOn}.`
}

export function getClydeNextBestAction(context: ClydeContext) {
  return generateClydeRecommendations(context)[0]
}
