import type { ClientJourneyState } from '../../lib/clientJourneyModel'
import type { ClientStageId } from '../../lib/clientStageModel'
import type { GuidedFundingReadiness } from '../../lib/clientFundingReadiness'
import type { CustomerTrackStatus } from '../../lib/customerFlowEngine'

export type V2DataMode = 'loading' | 'live' | 'demo' | 'error'

export interface V2Scores {
  credit: number
  business: number
  funding: number
  overall: number
}

export interface V2ProfileView {
  name: string
  membershipTier: string
  currentGoal: string
  subscriptionStatus: string
  nextReviewDate: string
  advisorName: string
  overallStatus: string
  isDemo: boolean
}

export interface V2DocumentView {
  required: string[]
  uploaded: string[]
  missing: string[]
  underReview: string[]
  processingCount: number
  requiredCount: number
  uploadedCount: number
}

export interface V2CreditRepairView {
  progressPercent: number
  negativeItemsUnderReview: number
  draftLettersReady: number
  goclearReviewsPending: number
  nextActions: Array<Record<string, any>>
}

export interface V2RailStage {
  id: ClientStageId
  label: string
  shortLabel: string
  path: string
  description: string
  nextStep: string
  state: 'completed' | 'current' | 'blocked' | 'locked'
  score: number
}

export interface V2ActivityItem {
  id: string
  label: string
  status: string
  detail: string
  date: string
}

export interface V2HermesView {
  recommendations: Array<Record<string, any>>
  quickActions: Array<Record<string, any>>
  messages: Array<Record<string, any>>
}

export interface V2FlowView {
  creditProfileStatus: CustomerTrackStatus
  businessProfileStatus: CustomerTrackStatus
  businessFundingStatus: CustomerTrackStatus
  documentsStatus: CustomerTrackStatus
  reviewStatus: CustomerTrackStatus
  monthlyProgressStatus: CustomerTrackStatus
  nextBestActions: Array<Record<string, any>>
  subscriptionSummary: Record<string, any>
}

export interface V2ViewData {
  mode: V2DataMode
  isDemo: boolean
  loadError: string | null
  scores: V2Scores
  profile: V2ProfileView | null
  journey: ClientJourneyState
  readiness: GuidedFundingReadiness
  flow: V2FlowView
  documents: V2DocumentView
  creditRepair: V2CreditRepairView
  railStages: V2RailStage[]
  activities: V2ActivityItem[]
  hermes: V2HermesView
  resolvedClientId: string | null
}