import { hermesChat, type HermesContext, type HermesHistoryTurn, type ProviderResult } from '../hermesProviders';
import type { HermesWorkroomResponse } from '../hermes/hermesWorkroomResponse';

export type HermesModelFirstMode = 'OFF' | 'SHADOW' | 'RAY_ONLY_PILOT' | 'ACTIVE';

export interface HermesModelFirstInput {
  message: string;
  actorRole?: 'ray' | 'admin' | 'operator' | 'client' | 'alpha' | 'unknown';
  sessionId?: string;
  recentHistory?: HermesHistoryTurn[];
  pageContext?: Record<string, unknown> | null;
}

export interface HermesModelFirstResult {
  usedModelFirst: boolean;
  response?: Partial<HermesWorkroomResponse>;
  provider?: ProviderResult;
  reason: string;
}

function modelFirstMode(): HermesModelFirstMode {
  const env = import.meta.env as Record<string, string | undefined>;
  const mode = env.VITE_HERMES_MODEL_FIRST_MODE || env.HERMES_MODEL_FIRST_MODE || 'OFF';
  return ['SHADOW', 'RAY_ONLY_PILOT', 'ACTIVE'].includes(mode) ? mode as HermesModelFirstMode : 'OFF';
}

export function getHermesModelFirstMode(): HermesModelFirstMode {
  return modelFirstMode();
}

export function isHermesModelFirstPrimary(actorRole: HermesModelFirstInput['actorRole'] = 'unknown'): boolean {
  const mode = modelFirstMode();
  if (mode === 'ACTIVE') return actorRole !== 'client' && actorRole !== 'alpha';
  if (mode === 'RAY_ONLY_PILOT') return actorRole === 'ray' || actorRole === 'admin';
  return false;
}

function safeText(value: unknown, max = 700): string {
  return typeof value === 'string' ? value.slice(0, max) : '';
}

function buildContext(input: HermesModelFirstInput): HermesContext {
  const pageContext = input.pageContext || {};
  const facts = [
    safeText(pageContext.route, 120) && `Route: ${safeText(pageContext.route, 120)}`,
    safeText(pageContext.pageId, 120) && `Page: ${safeText(pageContext.pageId, 120)}`,
    'Hermes model-first pilot: answer ordinary conversation directly; use Nexus evidence only for current private facts or governed actions.',
  ].filter(Boolean).join('\n');
  return {
    facts,
    history: (input.recentHistory || []).slice(-10),
  };
}

function responseFromProvider(provider: ProviderResult, text: string): Partial<HermesWorkroomResponse> {
  const metadata = provider.metadata || {};
  const providerName = String(metadata.provider || provider.modelProvider || 'openrouter');
  const modelName = String(metadata.model || provider.modelName || 'unknown_model');
  const decisionType = String(metadata.decisionType || 'DIRECT_RESPONSE');
  const toolRequested = metadata.toolRequested ? String(metadata.toolRequested) : '';
  const evidenceState = metadata.source === 'NEXUS_TOOL' ? 'TOOL_EVIDENCE' : 'MODEL_REASONING';
  return {
    role: 'hermes',
    text,
    mode: 'MODEL_FIRST',
    intent: 'model_first_conversation',
    responseStrategy: decisionType === 'TOOL_REQUEST' ? 'APPROVED_MODEL_TOOL_BRIDGE' : decisionType === 'CLARIFICATION' ? 'APPROVED_MODEL_CLARIFICATION' : 'APPROVED_MODEL_DIRECT',
    evidenceState,
    confidence: 0.86,
    actions: [],
    memoryUsed: ['visible_recent_history'],
    contextUsed: ['supabase_edge_function:hermes-chat', `provider:${providerName}`, `model:${modelName}`, 'recent_visible_history', toolRequested && `tool:${toolRequested}`].filter(Boolean) as string[],
    warnings: [
      metadata.fallbackUsed ? 'provider_fallback_used' : '',
      metadata.toolAllowed === false ? `tool_denied:${String(metadata.toolErrorCode || 'policy')}` : '',
    ].filter(Boolean),
    traceId: typeof metadata.traceId === 'string' ? metadata.traceId : `hermes-model-first-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
  };
}

function degradedResponse(reason: string, provider?: ProviderResult): Partial<HermesWorkroomResponse> {
  return {
    role: 'hermes',
    text: 'My conversational model is temporarily unavailable. I can still provide certain verified local Nexus status responses, but general conversation is degraded.',
    mode: 'MODEL_FIRST_DEGRADED',
    intent: 'provider_unavailable',
    responseStrategy: 'MODEL_FIRST_DEGRADED',
    evidenceState: 'NOT_CONFIGURED',
    confidence: 0.6,
    actions: [],
    memoryUsed: [],
    contextUsed: ['model_first_provider_status'],
    warnings: [reason, provider?.metadata?.errorCode ? String(provider.metadata.errorCode) : 'provider_unavailable'].filter(Boolean),
    traceId: `hermes-model-first-degraded-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
  };
}

export async function runHermesModelFirstConversation(input: HermesModelFirstInput): Promise<HermesModelFirstResult> {
  if (!isHermesModelFirstPrimary(input.actorRole)) {
    return { usedModelFirst: false, reason: `model_first_${modelFirstMode().toLowerCase()}` };
  }

  const provider = await hermesChat(input.message, 'model_first_conversation', buildContext(input));
  if (provider.configured && provider.text.trim()) {
    return {
      usedModelFirst: true,
      provider,
      response: responseFromProvider(provider, provider.text),
      reason: 'model_first_response',
    };
  }
  if (provider.blocked) {
    return {
      usedModelFirst: true,
      provider,
      response: responseFromProvider(provider, provider.text),
      reason: 'model_first_firewall_block',
    };
  }
  return {
    usedModelFirst: true,
    provider,
    response: degradedResponse(provider.metadata?.errorCode ? String(provider.metadata.errorCode) : 'provider_not_configured', provider),
    reason: 'model_first_degraded',
  };
}
