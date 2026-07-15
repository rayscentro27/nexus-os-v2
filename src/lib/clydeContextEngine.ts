import type { ClientJourneyState, JourneyStageId } from './clientJourneyModel'

export interface ClydeContext {
  route: string
  stage: JourneyStageId | null
  journey: ClientJourneyState | null
  documents: Array<{ id: string; category: string; status: string; title: string }>
  profileComplete: boolean
}

export interface ClydeMessage {
  id: string
  type: 'fact' | 'observation' | 'action' | 'warning' | 'uncertainty'
  text: string
  source: 'nexus_observed' | 'client_provided' | 'uploaded_evidence' | 'uncertainty' | 'readiness_implication'
  priority: 'high' | 'medium' | 'low'
}

const ROUTE_CONTEXT: Record<string, { pageGoal: string; focus: string; actions: string[] }> = {
  '/client/dashboard': {
    pageGoal: 'Overview of your funding readiness journey',
    focus: 'Current status, progress, and next best action',
    actions: ['Continue to next step', 'Upload documents', 'View funding readiness'],
  },
  '/client/credit-profile': {
    pageGoal: 'Understand and improve your credit profile',
    focus: 'Credit report analysis, discrepancies, and strategy recommendations',
    actions: ['Upload credit report', 'Review strategies', 'Check utilization'],
  },
  '/client/business-setup': {
    pageGoal: 'Establish your business foundation',
    focus: 'Entity, EIN, address, and core business documentation',
    actions: ['Complete business profile', 'Upload formation docs', 'Set up banking'],
  },
  '/client/business-bankability': {
    pageGoal: 'Demonstrate business stability for lenders',
    focus: 'Revenue, banking, time-in-business, and lender-facing signals',
    actions: ['Upload bank statements', 'Add revenue docs', 'Review bankability score'],
  },
  '/client/funding-readiness': {
    pageGoal: 'Final readiness check before funding applications',
    focus: 'Tier eligibility, blockers, and remaining requirements',
    actions: ['Complete missing items', 'Request review', 'View funding options'],
  },
  '/client/documents': {
    pageGoal: 'Manage your document vault',
    focus: 'Upload, organize, and track document processing status',
    actions: ['Upload document', 'Check processing status', 'View missing documents'],
  },
  '/client/request-review': {
    pageGoal: 'Submit your complete package for expert review',
    focus: 'Review eligibility, missing items, and submission',
    actions: ['Check eligibility', 'Submit review request', 'View open tasks'],
  },
  '/client/resources': {
    pageGoal: 'Access tools and partners to support your journey',
    focus: 'Credit education, business tools, and funding preparation',
    actions: ['Explore tools', 'Connect monitoring', 'View partner offers'],
  },
  '/client/credit-repair-journey': {
    pageGoal: 'Track your credit improvement progress',
    focus: 'Dispute items, draft letters, and case progress',
    actions: ['Review disputes', 'Approve letters', 'Track results'],
  },
  '/client/dispute-review': {
    pageGoal: 'Review and approve dispute letters',
    focus: 'Letter content, supporting evidence, and approval',
    actions: ['Review letter', 'Approve for mailing', 'Request edits'],
  },
}

function getStageInsights(stage: JourneyStageId | null, journey: ClientJourneyState | null): ClydeMessage[] {
  if (!stage || !journey) return []
  const messages: ClydeMessage[] = []
  const stageData = journey.stages[stage]

  if (stageData?.blockingRequirements.length) {
    messages.push({
      id: 'blocking',
      type: 'warning',
      text: `Blocked: ${stageData.blockingRequirements.join(', ')}. These must be resolved before proceeding.`,
      source: 'nexus_observed',
      priority: 'high',
    })
  }

  if (stageData?.missingRequirements.length) {
    messages.push({
      id: 'missing',
      type: 'action',
      text: `Still needed: ${stageData.missingRequirements.join(', ')}.`,
      source: 'nexus_observed',
      priority: 'high',
    })
  }

  if (stageData?.completedRequirements.length) {
    messages.push({
      id: 'completed',
      type: 'fact',
      text: `Completed: ${stageData.completedRequirements.join(', ')}.`,
      source: 'nexus_observed',
      priority: 'low',
    })
  }

  if (stage === 'credit_profile' && journey.overallScore < 50) {
    messages.push({
      id: 'low-score',
      type: 'uncertainty',
      text: 'Your funding readiness score is below 50. Completing credit and business stages will significantly improve this.',
      source: 'readiness_implication',
      priority: 'medium',
    })
  }

  return messages
}

export function generateClydeMessages(ctx: ClydeContext): ClydeMessage[] {
  const messages: ClydeMessage[] = []
  const routeCtx = ROUTE_CONTEXT[ctx.route]

  if (routeCtx) {
    messages.push({
      id: 'page-goal',
      type: 'observation',
      text: routeCtx.pageGoal,
      source: 'nexus_observed',
      priority: 'low',
    })
  }

  messages.push(...getStageInsights(ctx.stage, ctx.journey))

  if (ctx.documents.length === 0) {
    messages.push({
      id: 'no-docs',
      type: 'action',
      text: 'No documents uploaded yet. Start by uploading your credit report or business formation documents.',
      source: 'nexus_observed',
      priority: 'high',
    })
  }

  const pendingDocs = ctx.documents.filter(d => d.status === 'uploaded' || d.status === 'pending_review')
  if (pendingDocs.length > 0) {
    messages.push({
      id: 'pending-docs',
      type: 'observation',
      text: `${pendingDocs.length} document(s) are being processed. Check the Documents vault for updates.`,
      source: 'uploaded_evidence',
      priority: 'medium',
    })
  }

  if (!ctx.profileComplete) {
    messages.push({
      id: 'profile-incomplete',
      type: 'action',
      text: 'Complete your business profile to unlock more funding options.',
      source: 'nexus_observed',
      priority: 'medium',
    })
  }

  messages.push({
    id: 'disclaimer',
    type: 'uncertainty',
    text: 'Nexus observes facts from your data and documents. Outcomes depend on lender criteria and are not guaranteed.',
    source: 'uncertainty',
    priority: 'low',
  })

  return messages
}
