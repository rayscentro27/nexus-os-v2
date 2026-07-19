import type { HermesAdvisoryContext, HermesConversationResult } from './hermesConversationTypes';

export type HermesWorkroomActionType =
  | 'DRAFT_RAY_REVIEW'
  | 'PREPARE_SPECIALIST_HANDOFF'
  | 'CREATE_TASK_REQUEST'
  | 'NONE';

export interface HermesWorkroomAction {
  id: string;
  type: HermesWorkroomActionType;
  label: string;
  enabled: boolean;
  requiresApproval: boolean;
  payload?: Record<string, unknown>;
}

export interface HermesWorkroomResponse {
  messageId: string;
  role: 'hermes';
  text: string;
  mode: string;
  intent: string;
  responseStrategy: string;
  evidenceState: string;
  confidence: number;
  createdAt: string;
  actions: HermesWorkroomAction[];
  memoryUsed: string[];
  contextUsed: string[];
  warnings: string[];
  traceId?: string;
  advisoryContext?: HermesAdvisoryContext;
  recommendationMetadata?: {
    createsAdvisoryContext: boolean;
    advisoryId: string;
    topicId?: string;
    topicLabel?: string;
    sourceIntent?: string;
    responseStrategy?: string;
    recommendationIds: string[];
  };
}

export type HermesWorkroomChatMessage = Omit<Partial<HermesWorkroomResponse>, 'role'> & {
  id: string;
  role: 'ray' | 'hermes';
  text: string;
  source?: string;
};

function stableId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
}

function text(value: unknown, fallback = ''): string {
  return typeof value === 'string' && value.trim() ? value : fallback;
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item)).filter(Boolean).slice(0, 12) : [];
}

function confidence(value: unknown): number {
  if (typeof value === 'number' && Number.isFinite(value)) return Math.max(0, Math.min(1, value));
  if (value === 'high') return 0.9;
  if (value === 'medium') return 0.7;
  if (value === 'low') return 0.45;
  return 0.75;
}

function isKnownWorkroomActionType(value: unknown): value is HermesWorkroomActionType {
  return ['DRAFT_RAY_REVIEW', 'PREPARE_SPECIALIST_HANDOFF', 'CREATE_TASK_REQUEST', 'NONE'].includes(String(value));
}

function safeAdvisoryContext(value: unknown): HermesAdvisoryContext | undefined {
  if (!value || typeof value !== 'object') return undefined;
  const candidate = value as Partial<HermesAdvisoryContext>;
  if (typeof candidate.advisoryId !== 'string' || typeof candidate.topic !== 'string' || !Array.isArray(candidate.recommendations)) return undefined;
  return JSON.parse(JSON.stringify({
    ...candidate,
    recommendations: candidate.recommendations.filter((item) => item && typeof item === 'object' && typeof item.id === 'string' && typeof item.label === 'string'),
    status: candidate.status || 'ACTIVE',
  })) as HermesAdvisoryContext;
}

function canonicalCreatedAdvisory(result: HermesConversationResult): HermesAdvisoryContext | undefined {
  const advisory = result.session.advisoryContext;
  if (!advisory) return undefined;
  if (advisory.sourceIntent && advisory.sourceIntent !== result.intent) return undefined;
  if (!['EXECUTIVE_ADVICE', 'FOLLOW_UP_ADVICE', 'SELECTION_REFERENCE', 'TASK_REQUEST', 'APPROVAL_REQUEST'].includes(result.mode)) return undefined;
  return safeAdvisoryContext(advisory);
}

function actionFromCanonical(result: HermesConversationResult): HermesWorkroomAction[] {
  if (!result.action) {
    return [
      {
        id: stableId('ray-review'),
        type: 'DRAFT_RAY_REVIEW',
        label: 'Draft Ray Review request',
        enabled: true,
        requiresApproval: true,
        payload: { source: 'workroom_followup', mode: result.mode, intent: result.intent },
      },
      {
        id: stableId('handoff'),
        type: 'PREPARE_SPECIALIST_HANDOFF',
        label: 'Prepare specialist handoff',
        enabled: true,
        requiresApproval: true,
        payload: { source: 'workroom_followup', mode: result.mode, intent: result.intent },
      },
    ];
  }
  if (result.action.type === 'CREATE_GOVERNED_TASK') {
    return [{
      id: stableId('task-request'),
      type: 'CREATE_TASK_REQUEST',
      label: 'Prepare governed task',
      enabled: true,
      requiresApproval: true,
      payload: result.action.payload,
    }];
  }
  if (result.action.type === 'PREPARE_RAY_REVIEW') {
    return [{
      id: stableId('ray-review'),
      type: 'DRAFT_RAY_REVIEW',
      label: 'Draft Ray Review request',
      enabled: true,
      requiresApproval: true,
      payload: result.action.payload,
    }];
  }
  return [{
    id: stableId('blocked'),
    type: 'NONE',
    label: 'Action blocked by policy',
    enabled: false,
    requiresApproval: true,
    payload: result.action.payload,
  }];
}

export function normalizeHermesWorkroomResponse(
  raw: HermesConversationResult | Partial<HermesWorkroomResponse> | null | undefined,
  options: { messageId?: string; createdAt?: string } = {},
): HermesWorkroomResponse {
  const createdAt = options.createdAt || text((raw as Partial<HermesWorkroomResponse> | undefined)?.createdAt, new Date().toISOString());
  const messageId = options.messageId || text((raw as Partial<HermesWorkroomResponse> | undefined)?.messageId, stableId('hermes'));
  const canonical = raw && 'response' in raw ? raw as HermesConversationResult : null;
  const persisted = raw && !canonical ? raw as Partial<HermesWorkroomResponse> : null;
  const responseText = canonical ? canonical.response : persisted?.text;
  const advisoryContext = canonical ? canonicalCreatedAdvisory(canonical) : safeAdvisoryContext(persisted?.advisoryContext);
  const normalized: HermesWorkroomResponse = {
    messageId,
    role: 'hermes',
    text: text(responseText, 'I hit a local response-normalization error. Nothing was executed. Try again from the Workroom.'),
    mode: canonical ? canonical.mode : text(persisted?.mode, 'UNKNOWN'),
    intent: canonical ? canonical.intent : text(persisted?.intent, 'unknown'),
    responseStrategy: canonical ? canonical.responseStrategy : text(persisted?.responseStrategy, 'UNKNOWN'),
    evidenceState: canonical ? canonical.evidenceState : text(persisted?.evidenceState, 'UNKNOWN'),
    confidence: canonical ? confidence(canonical.confidence) : confidence(persisted?.confidence),
    createdAt,
    actions: canonical
      ? actionFromCanonical(canonical)
      : Array.isArray(persisted?.actions)
        ? persisted.actions
            .filter((action): action is HermesWorkroomAction => Boolean(action && typeof action === 'object' && isKnownWorkroomActionType((action as Partial<HermesWorkroomAction>).type)))
            .map((action) => ({
              id: text(action.id, stableId('action')),
              type: action.type,
              label: text(action.label, action.type),
              enabled: Boolean(action.enabled),
              requiresApproval: Boolean(action.requiresApproval),
              payload: action.payload && typeof action.payload === 'object' ? action.payload : undefined,
            }))
        : [],
    memoryUsed: canonical ? stringArray(canonical.memoryUsed) : stringArray(persisted?.memoryUsed),
    contextUsed: canonical ? stringArray(canonical.contextUsed) : stringArray(persisted?.contextUsed),
    warnings: canonical ? stringArray(canonical.warnings) : stringArray(persisted?.warnings),
    traceId: canonical ? canonical.traceId : text(persisted?.traceId, ''),
    advisoryContext,
    recommendationMetadata: advisoryContext ? {
      createsAdvisoryContext: true,
      advisoryId: advisoryContext.advisoryId,
      topicId: advisoryContext.topicId,
      topicLabel: advisoryContext.topicLabel,
      sourceIntent: advisoryContext.sourceIntent,
      responseStrategy: advisoryContext.sourceResponseStrategy,
      recommendationIds: advisoryContext.recommendations.map((item) => item.id),
    } : undefined,
  };
  return JSON.parse(JSON.stringify(normalized)) as HermesWorkroomResponse;
}

export function toHermesChatMessage(response: HermesWorkroomResponse): HermesWorkroomChatMessage {
  return {
    id: response.messageId,
    ...response,
    source: response.evidenceState,
  };
}

export function isSafeWorkroomAction(action: unknown): action is HermesWorkroomAction {
  if (!action || typeof action !== 'object') return false;
  const candidate = action as Partial<HermesWorkroomAction>;
  return isKnownWorkroomActionType(candidate.type)
    && typeof candidate.label === 'string'
    && typeof candidate.enabled === 'boolean'
    && typeof candidate.requiresApproval === 'boolean'
    && typeof (candidate as { onClick?: unknown }).onClick === 'undefined';
}
