import { useCallback, useEffect, useMemo, useState } from 'react'
import { loadClientPortalLiveData } from '../../lib/clientPortalDataAdapter'
import { computeJourneyState, type ClientJourneyState } from '../../lib/clientJourneyModel'
import { buildClientFundingReadiness, type GuidedFundingReadiness } from '../../lib/clientFundingReadiness'
import {
  calculateCustomerFlowStatus,
  generateNextBestActions,
  generateSubscriptionValueSummary,
} from '../../lib/customerFlowEngine'
import { getClydePageContext, generateClydeRecommendations, generateClydeQuickActions } from '../../lib/clydeActionEngine'
import { generateClydeMessages } from '../../lib/clydeContextEngine'
import { CLIENT_FIVE_STAGES, type ClientStageId } from '../../lib/clientStageModel'
import { clientDataMode } from '../../data/clientDataMode'
import { clientPortalData } from '../../data/clientPortalData'
import { isSupabaseConfigured } from '../../lib/supabaseClient'
import type {
  V2CreditRepairView,
  V2DataMode,
  V2DocumentRequirement,
  V2DocumentView,
  V2FlowView,
  V2HermesView,
  V2ProfileView,
  V2RailStage,
  V2Scores,
  V2ViewData,
  V2WorkflowStage,
} from '../types/v2-models'

interface NormalizedSource {
  profile: Record<string, any>
  documents: Array<Record<string, any>>
  businessProfile: Array<Record<string, any>>
  creditItems: Array<Record<string, any>>
  scores: Partial<V2Scores>
  fundingScores: Array<Record<string, any>>
  tasks: Array<Record<string, any>>
  systemReviews: Array<Record<string, any>>
  strategies: Array<Record<string, any>>
  decisions: Array<Record<string, any>>
}

const docText = (d: Record<string, any>) =>
  `${d.category || ''} ${d.title || ''} ${d.filename || ''} ${d.doc_type || ''} ${d.item_type || ''}`.toLowerCase()

const isPresent = (d: Record<string, any>) => {
  const status = `${d.status || ''} ${d.document_status || ''} ${d.client_action_status || ''}`.toLowerCase()
  return !/missing|pending|needs|in_progress|processing|queued|under_review|attention/.test(status)
}

const matches = (docs: Array<Record<string, any>>, patterns: RegExp[]) =>
  docs.some((d) => isPresent(d) && patterns.some((p) => p.test(docText(d))))

const statusOf = (d: Record<string, any>) => {
  const s = `${d.status || ''} ${d.document_status || ''} ${d.client_action_status || ''}`.toLowerCase()
  if (/processing|queued|under_review|pending|review/.test(s)) return 'processing'
  if (/attention|required|exception/.test(s)) return 'attention'
  if (/missing|needs/.test(s)) return 'missing'
  if (/complete|approved|uploaded|active/.test(s)) return 'complete'
  return 'missing'
}

function normalizeLive(source: {
  profile: Record<string, any> | null
  documents: any[]
  businessProfile: any[]
  creditItems: any[]
  scores: any[]
  fundingScores: any[]
  tasks: any[]
  systemReviews: any[]
  strategyRecommendations: any[]
  strategyDecisions: any[]
}): NormalizedSource {
  const docs = (source.documents || []).map((d: any) => ({
    id: d?.id,
    category: d?.doc_type || d?.category || '',
    title: d?.filename || d?.title || d?.doc_type || '',
    filename: d?.filename,
    doc_type: d?.doc_type,
    status: d?.status,
    document_status: d?.document_status,
    client_action_status: d?.client_action_status,
    goclear_review_status: d?.goclear_review_status,
  }))
  const score = (type: string) =>
    (source.scores || []).find((s: any) => String(s?.score_type || '').toLowerCase() === type)?.score || 0
  return {
    profile: source.profile || {},
    documents: docs,
    businessProfile: source.businessProfile || [],
    creditItems: source.creditItems || [],
    scores: {
      credit: score('credit'),
      business: score('business'),
      funding: score('funding'),
      overall: score('overall'),
    },
    fundingScores: source.fundingScores || [],
    tasks: source.tasks || [],
    systemReviews: source.systemReviews || [],
    strategies: source.strategyRecommendations || [],
    decisions: source.strategyDecisions || [],
  }
}

function normalizeDemo(): NormalizedSource {
  const demo = clientPortalData
  const docs: Array<Record<string, any>> = [
    ...(demo.documents?.requiredDocuments || []).map((title: string) => ({ category: 'required', title, status: 'missing' })),
    ...(demo.documents?.uploadedDocuments || []).map((title: string) => ({ category: 'uploaded', title, status: 'uploaded' })),
    ...(demo.documents?.missingDocuments || []).map((title: string) => ({ category: 'missing', title, status: 'missing' })),
    ...(demo.documents?.underReviewDocuments || []).map((title: string) => ({ category: 'under_review', title, status: 'under_review' })),
  ]
  const businessProfile = (demo.businessProfileReadiness?.fundabilityChecklist || []).map((row: string[]) => ({
    requirement_type: row[0],
    status: row[1],
  }))
  const scores = demo.readinessScores || {}
  return {
    profile: demo.clientProfile || {},
    documents: docs,
    businessProfile,
    creditItems: demo.creditRepair?.negativeItems || [],
    scores: {
      credit: scores.creditProfileReadiness,
      business: scores.businessProfileReadiness,
      funding: scores.fundingReadiness,
      overall: Math.round(
        ((scores.creditProfileReadiness || 0) + (scores.businessProfileReadiness || 0) + (scores.fundingReadiness || 0)) / 3
      ),
    },
    fundingScores: [],
    tasks: demo.clientTasks || [],
    systemReviews: [],
    strategies: [],
    decisions: [],
  }
}

function deriveJourney(src: NormalizedSource): ClientJourneyState {
  const profile = src.profile || {}
  const utilization = Number(profile?.utilization_pct ?? profile?.utilization_factor ?? 0)
  const strategySelected = src.decisions.some((d) => ['selected', 'authorized', 'saved'].includes(String(d?.decision).toLowerCase()))
  const timeInBusiness = Number(profile?.time_in_business_months ?? profile?.months_in_business ?? 0) || undefined
  return computeJourneyState({
    creditScore: src.scores.credit || 0,
    creditReportUploaded: matches(src.documents, [/credit report/i, /bureau/i, /credit_profile/i]) || src.creditItems.length > 0,
    hasDiscrepancies: src.creditItems.length > 0,
    strategySelected,
    businessProfileComplete: (src.scores.business || 0) >= 80,
    entityEstablished: matches(src.documents, [/formation/i, /entity/i, /operating agreement/i]) || src.businessProfile.some((b) => /entity/i.test(b.requirement_type) && statusOf(b) === 'complete'),
    einAvailable: matches(src.documents, [/ein/i]),
    businessAddress: matches(src.documents, [/address/i]),
    bankAccountReady: matches(src.documents, [/bank statement/i, /banking/i, /bank/i]),
    revenueDocumented: matches(src.documents, [/revenue/i]),
    timeInBusiness,
    documentsComplete: src.documents.filter((d) => isPresent(d)).length,
    documentsMissing: src.documents.filter((d) => statusOf(d) === 'missing').length,
    reviewRequested: false,
    lastActivity: profile?.updated_at || profile?.next_review_date || null,
    utilizationHigh: utilization > 65,
  })
}

function deriveReadiness(src: NormalizedSource, journey: ClientJourneyState): GuidedFundingReadiness {
  return buildClientFundingReadiness({
    profile: src.profile,
    documents: src.documents,
    tasks: src.tasks,
    scores: src.scores as { credit?: number; business?: number; funding?: number },
    systemReviews: src.systemReviews,
    strategyRecommendations: src.strategies,
    strategyDecisions: src.decisions,
    journey,
  })
}

function deriveRailStages(journey: ClientJourneyState): V2RailStage[] {
  const order: Array<{ stage: ClientStageId; journeyKey: keyof ClientJourneyState['stages'] }> = [
    { stage: 'credit_review', journeyKey: 'credit_profile' },
    { stage: 'credit_improvement', journeyKey: 'credit_improvement' },
    { stage: 'business_foundation', journeyKey: 'business_foundation' },
    { stage: 'funding_readiness', journeyKey: 'funding_readiness' },
    { stage: 'funding_access', journeyKey: 'review_plan' },
  ]
  const journeyOrder = ['credit_profile', 'credit_improvement', 'business_foundation', 'business_bankability', 'funding_readiness', 'review_plan'] as const
  const currentIdx = journeyOrder.indexOf(journey.currentStage)
  return order.map(({ stage, journeyKey }) => {
    const def = CLIENT_FIVE_STAGES.find((s) => s.id === stage)!
    const js = journey.stages[journeyKey]
    const idx = journeyOrder.indexOf(journeyKey as (typeof journeyOrder)[number])
    let state: V2RailStage['state'] = 'locked'
    if (js.status === 'blocked' && idx !== currentIdx) state = 'blocked'
    else if (js.status === 'complete' || js.status === 'ready_to_review' || idx < currentIdx) state = 'completed'
    else if (idx === currentIdx) state = 'current'
    return {
      id: stage,
      label: def.label,
      shortLabel: def.shortLabel,
      path: `/client-v2/${stage.replace(/_/g, '-')}`,
      description: def.description,
      nextStep: js.nextAction || def.nextStep,
      state,
      score: js.score,
    }
  })
}

function deriveDocuments(readiness: GuidedFundingReadiness): V2DocumentView {
  const stages = Object.values(readiness.stages)
  const requirements = stages.flatMap((s) => s.requirements || [])
  const uploaded = requirements.filter((r) => r.status === 'complete').map((r) => r.label)
  const missing = requirements.filter((r) => r.status === 'missing' || r.status === 'attention').map((r) => r.label)
  const processing = requirements.filter((r) => r.status === 'processing').map((r) => r.label)
  const required = requirements.map((r) => r.label)
  const detail: V2DocumentRequirement[] = requirements.map((r) => ({
    label: r.label,
    status: statusOf(r) === 'processing' ? 'processing' : r.status === 'attention' ? 'attention' : r.status === 'complete' ? 'complete' : 'missing',
    whyItMatters: String(r.whyItMatters || ''),
    impact: String((r as any)?.impact || ''),
  }))
  return {
    required,
    uploaded,
    missing,
    underReview: processing,
    processingCount: processing.length,
    requiredCount: required.length,
    uploadedCount: uploaded.length,
    requirements: detail,
  }
}

function deriveWorkflowStages(src: NormalizedSource, creditRepair: Record<string, any>): V2WorkflowStage[] {
  const items = src.creditItems || []
  const submitted = items.length > 0
  const pendingReview = items.some((i) => /pending|review|needs/.test(`${i.goclear_review_status || ''} ${i.status || ''}`.toLowerCase()))
  if (creditRepair?.workflowStages?.length) {
    return creditRepair.workflowStages.map((row: [string, string]) => {
      const raw = String(row[1] || '').toLowerCase()
      const state: V2WorkflowStage['state'] =
        raw === 'complete' ? 'complete' : raw === 'in_progress' ? 'in_progress' : raw === 'blocked' ? 'blocked' : raw === 'pending' ? 'pending' : 'upcoming'
      return { label: String(row[0]), state }
    })
  }
  return [
    { label: 'Intake', state: submitted ? 'complete' : 'in_progress' },
    { label: 'Report connected / uploaded', state: submitted ? 'complete' : 'pending' },
    { label: 'Negative items identified', state: submitted ? 'complete' : 'pending' },
    { label: 'Item classification', state: submitted ? 'complete' : 'pending' },
    { label: 'Document request', state: pendingReview ? 'in_progress' : 'pending' },
    { label: 'Draft letters prepared', state: 'upcoming' },
    { label: 'GoClear review', state: pendingReview ? 'in_progress' : 'upcoming' },
    { label: 'Client approval if needed', state: 'upcoming' },
    { label: 'Manual send after approval', state: 'upcoming' },
    { label: 'Track update', state: 'upcoming' },
  ]
}

function deriveCreditRepair(src: NormalizedSource): V2CreditRepairView {
  const items = src.creditItems || []
  const underReview = items.filter((i) => /in_review|needs_documents|pending_review/.test(String(i.status || '').toLowerCase())).length
  const creditRepair = clientPortalData.creditRepair || {}
  const progress =
    src.profile?.membership_tier === 'trial'
      ? creditRepair?.progressPercent || 0
      : items.length
        ? Math.round((items.filter((i) => /complete|sent|verified|removed|draft_ready/.test(String(i.status || '').toLowerCase())).length / items.length) * 100)
        : 0
  const negativeItems = items.map((i) => ({
    id: i.id,
    title: i.title,
    status: i.status,
    risk_level: i.risk_level,
    automation_level: i.automation_level,
    goclear_review_status: i.goclear_review_status,
    item_type: i.item_type || i.category || 'credit_repair',
    utilization_pct: i.utilization_pct,
  }))
  return {
    progressPercent: progress,
    negativeItemsUnderReview: underReview || (creditRepair?.negativeItemsUnderReview || 0),
    draftLettersReady: creditRepair?.draftLettersReady || items.filter((i) => String(i.status) === 'draft_ready').length,
    goclearReviewsPending: creditRepair?.goclearReviewsPending || items.filter((i) => /pending/.test(String(i.goclear_review_status || ''))).length,
    nextActions: src.tasks.filter((t) => /credit|repair/.test(String(t.task_type || ''))) || [],
    workflowStages: deriveWorkflowStages(src, creditRepair),
    negativeItems,
    goclearReviewStatus: creditRepair?.goclearReviewStatus || (underReview ? `${underReview} items awaiting internal review` : 'No pending internal review'),
    clientGuideRecommendation: creditRepair?.clientGuideRecommendation || 'Complete requested documentation first. GoClear must review any letter or dispute next step before it can be used.',
    monthlyProgress: creditRepair?.monthlyProgress || [],
  }
}

function deriveActivities(src: NormalizedSource, readiness: GuidedFundingReadiness) {
  const history = (readiness.readinessHistory || []).slice(-4).map((h) => ({
    id: `hist-${h.label}`,
    label: h.label,
    status: h.status,
    detail: h.date,
    date: h.date,
  }))
  const tasks = (src.tasks || [])
    .slice(0, 3)
    .map((t, i) => ({ id: `task-${t.id || i}`, label: t.title || 'Task', status: t.status, detail: t.priority === 'high' ? 'High priority' : 'On track', date: t.due_date || '' }))
  return [...history, ...tasks]
}

function deriveHermes(src: NormalizedSource, journey: ClientJourneyState, readiness: GuidedFundingReadiness, route: string): V2HermesView {
  const actionsContext = {
    route,
    track: undefined,
    clientState: {
      documents: src.documents.map((d) => ({ category: d.category, title: d.title, filename: d.filename, goclear_review_status: d.goclear_review_status, status: d.status })),
      missingRequirements: readiness.missingDocuments.slice(0, 4),
      profileComplete: (src.scores.business || 0) >= 80,
      pendingReview: readiness.processingDocuments.length > 0,
      creditReadinessStatus: readiness.stages.credit.status,
      tier1Status: readiness.tier1.status,
      tier2Status: readiness.tier2.status,
      utilizationHigh: src.documents.some((d) => /utilization/i.test(docText(d)) && statusOf(d) === 'missing'),
      evidenceNeeded: readiness.processingDocuments.length > 0,
      reportItemsToReview: src.creditItems.length,
    },
  }
  const messagesContext = {
    route,
    stage: journey.currentStage,
    journey,
    documents: src.documents.map((d) => ({ id: d.id, category: d.category, status: d.status, title: d.title })),
    profileComplete: (src.scores.business || 0) >= 80,
    primaryBlocker: readiness.primaryBlocker,
    nextAction: readiness.nextBestAction,
    readinessState: readiness.state,
    missingFacts: readiness.missingDocuments.slice(0, 4),
    evidenceState: [],
  }
  return {
    recommendations: generateClydeRecommendations(actionsContext),
    quickActions: generateClydeQuickActions(actionsContext),
    messages: generateClydeMessages(messagesContext),
  }
}

export function useV2ClientData(route = '/client-v2/dashboard') {
  const [mode, setMode] = useState<V2DataMode>('loading')
  const [loadError, setLoadError] = useState<string | null>(null)
  const [liveRaw, setLiveRaw] = useState<Record<string, any> | null>(null)
  const [tick, setTick] = useState(0)

  const reload = useCallback(() => setTick((t) => t + 1), [])

  useEffect(() => {
    let cancelled = false
    const shouldLoadLive = clientDataMode.liveSupabaseTestClientEnabled && isSupabaseConfigured
    if (!shouldLoadLive) {
      setMode('demo')
      return () => {
        cancelled = true
      }
    }
    setMode('loading')
    loadClientPortalLiveData()
      .then((data) => {
        if (cancelled) return
        if (data?.profile) {
          setLiveRaw(data as unknown as Record<string, any>)
          setMode('live')
        } else {
          setLiveRaw(null)
          setMode('demo')
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setLoadError(err instanceof Error ? err.message : 'Failed to load portal data')
        setMode('error')
      })
    return () => {
      cancelled = true
    }
  }, [tick])

  const view = useMemo<V2ViewData>(() => {
    const src = mode === 'live' && liveRaw ? normalizeLive(liveRaw as any) : normalizeDemo()
    const journey = deriveJourney(src)
    const readiness = deriveReadiness(src, journey)
    const scores: V2Scores = {
      credit: src.scores.credit || readiness.stages.credit.contribution || 0,
      business: src.scores.business || 0,
      funding: src.scores.funding || readiness.overallScore || 0,
      overall: readiness.overallScore || src.scores.overall || 0,
    }
    const isDemo = mode !== 'live'
    const profileData = src.profile || {}
    const profile: V2ProfileView = {
      name: profileData.name || 'Client',
      membershipTier: profileData.membership_tier || profileData.membershipTier || 'GoClear Membership',
      currentGoal: profileData.currentGoal || profileData.current_goal || 'Improve credit and business readiness ahead of a reviewed funding application.',
      subscriptionStatus: profileData.subscriptionStatus || profileData.subscription_status || 'Active',
      nextReviewDate: profileData.nextReviewDate || profileData.next_review_date || 'TBD',
      advisorName: profileData.advisorName || profileData.advisor_name || 'GoClear Review Team',
      overallStatus: profileData.overallStatus || profileData.overall_status || readiness.state.replace(/_/g, ' '),
      isDemo,
    }
    const flow = calculateCustomerFlowStatus({
      scores: { credit: scores.credit, business: scores.business, funding: scores.funding },
      documents: src.documents,
      profileComplete: { percent: scores.business, complete: scores.business >= 80 },
      lettersReady: (src.creditItems || []).some((i) => String(i.status) === 'draft_ready') || (clientPortalData.creditRepair?.draftLettersReady || 0) > 0,
      reviewPending: (src.creditItems || []).some((i) => /pending/.test(String(i.goclear_review_status || ''))),
    })
    const nextBestActions = generateNextBestActions({
      scores: { credit: scores.credit, business: scores.business, funding: scores.funding },
      documents: src.documents,
      profileComplete: { percent: scores.business, complete: scores.business >= 80 },
      lettersReady: flow.creditProfileStatus.percentComplete > 0,
      reviewPending: flow.reviewStatus.percentComplete > 0,
    })
    const flowView: V2FlowView = {
      ...flow,
      nextBestActions,
      subscriptionSummary: generateSubscriptionValueSummary({
        scores: { credit: scores.credit, business: scores.business, funding: scores.funding },
        documents: src.documents,
        profileComplete: { percent: scores.business, complete: scores.business >= 80 },
        lettersReady: flow.creditProfileStatus.percentComplete > 0,
        reviewPending: flow.reviewStatus.percentComplete > 0,
      }),
    }
    const documents = deriveDocuments(readiness)
    const creditRepair = deriveCreditRepair(src)
    const railStages = deriveRailStages(journey)
    const activities = deriveActivities(src, readiness)
    const hermes = deriveHermes(src, journey, readiness, route)
    return {
      mode,
      isDemo,
      loadError,
      scores,
      profile,
      journey,
      readiness,
      flow: flowView,
      documents,
      creditRepair,
      railStages,
      activities,
      hermes,
      resolvedClientId: liveRaw?.resolvedClientId || null,
    }
  }, [mode, liveRaw, route, loadError])

  return {
    ...view,
    mode,
    isDemo: mode !== 'live',
    reload,
    hermesPageContext: getClydePageContext({ route }),
  }
}