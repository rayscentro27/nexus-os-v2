import type { EvidenceState } from '../executive/executiveTypes';

export type HermesConversationMode =
  | 'CASUAL_CONVERSATION'
  | 'SOCIAL_GREETING'
  | 'EXECUTIVE_ADVICE'
  | 'FOLLOW_UP_ADVICE'
  | 'SYSTEM_STATUS'
  | 'FACTUAL_QUESTION'
  | 'EXPLANATION'
  | 'IDEA_REVIEW'
  | 'DECISION_SUPPORT'
  | 'SELECTION_REFERENCE'
  | 'TASK_REQUEST'
  | 'APPROVAL_REQUEST'
  | 'COMMAND'
  | 'CLARIFICATION_REQUIRED'
  | 'UNSUPPORTED_OR_BLOCKED';

export type HermesResponseStrategy =
  | 'DETERMINISTIC'
  | 'MODEL_ASSISTED'
  | 'HYBRID'
  | 'SAFE_FALLBACK'
  | 'executive_priority_response'
  | 'executive_risk_response'
  | 'revenue_action_response'
  | 'followup_rationale_response'
  | 'followup_feasibility_response'
  | 'followup_blockers_response'
  | 'followup_deep_dive_response'
  | 'status_response'
  | 'security_boundary_response';

export interface HermesAdvisoryRecommendation {
  id: string;
  label: string;
  rationale: string;
  score?: number;
  risks?: string[];
  blockers?: string[];
  dependencies?: string[];
  nextStep?: string;
  feasibility?: {
    status: 'HIGH' | 'MEDIUM' | 'LOW' | 'UNKNOWN';
    reasons: string[];
  };
  evidenceIds?: string[];
}

export interface HermesAdvisoryContext {
  advisoryId: string;
  topic: string;
  summary: string;
  recommendations: HermesAdvisoryRecommendation[];
  preferredRecommendationId?: string;
  evidenceIds: string[];
  createdAt: string;
  expiresAt?: string;
}

export interface HermesSelectionContext {
  selectionContextId: string;
  items: HermesAdvisoryRecommendation[];
  selectedRecommendationId?: string;
  createdAt: string;
  consumedAt?: string;
}

export interface HermesConversationSession {
  sessionId: string;
  brainId: 'hermes';
  actorId?: string;
  channel: string;
  activeTopic?: string;
  activeMode?: HermesConversationMode;
  lastUserMessage?: string;
  lastHermesResponse?: string;
  advisoryContextId?: string;
  selectionContextId?: string;
  taskContextId?: string;
  pageContextId?: string;
  recentIntentHistory: string[];
  recentResponseStrategies: HermesResponseStrategy[];
  advisoryContext?: HermesAdvisoryContext;
  selectionContext?: HermesSelectionContext;
  startedAt: string;
  updatedAt: string;
}

export interface HermesConversationInput {
  message: string;
  session?: HermesConversationSession;
  sessionId?: string;
  actorId?: string;
  actorRole?: 'ray' | 'admin' | 'operator' | 'client' | 'alpha' | 'unknown';
  channel?: string;
  pageId?: string;
  route?: string;
  pageContext?: Record<string, unknown> | null;
}

export interface HermesConversationAction {
  type: 'CREATE_GOVERNED_TASK' | 'PREPARE_RAY_REVIEW' | 'BLOCKED_COMMAND';
  requiresApproval: boolean;
  payload: {
    target?: string;
    source?: string;
    requestedText: string;
    status: 'conversation_draft_only' | 'blocked';
  };
}

export interface HermesConversationTrace {
  traceId: string;
  channel: string;
  mode: HermesConversationMode;
  intent: string;
  confidence: number;
  memoryUsed: string[];
  contextUsed: string[];
  referencesResolved: string[];
  responseStrategy: HermesResponseStrategy;
  provider: 'nexus_native' | 'approved_model' | 'fallback';
  actionDetected: boolean;
  policyBlocks: string[];
  responseQualityScore: number;
  generatedAt: string;
}

export interface HermesConversationResult {
  mode: HermesConversationMode;
  intent: string;
  responseStrategy: HermesResponseStrategy;
  response: string;
  confidence: number;
  evidenceState: EvidenceState | 'TEST_ONLY' | 'NOT_CONFIGURED' | 'BLOCKED_BY_POLICY' | 'PROHIBITED';
  memoryUsed: string[];
  contextUsed: string[];
  referencesResolved: string[];
  action: HermesConversationAction | null;
  warnings: string[];
  traceId?: string;
  session: HermesConversationSession;
  quality?: HermesResponseQuality;
  trace?: HermesConversationTrace;
}

export interface HermesResponseQuality {
  overallScore: number;
  intentAlignment: number;
  continuity: number;
  memoryCorrectness: number;
  naturalness: number;
  directness: number;
  evidenceHonesty: number;
  actionSeparation: number;
  repetitionControl: number;
  lengthFitness: number;
  failures: string[];
}
