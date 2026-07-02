import { detectActivationLevel } from './hermesActivationLevels';
import { classifyHermesDomain } from './hermesDomainClassifier';
import { evaluateTopicBoundary } from './hermesTopicBoundary';
import type { ConversationItem, ConversationState } from './hermesConversationState';

export interface RoutingDecisionAuditInput {
  message: string;
  previousConversationState?: Partial<ConversationState> | null;
  currentPage?: string | null;
  surface?: string;
  availableContext?: unknown;
  actualResult?: { activationLevel?: number; route?: string; sourceMode?: string; usedSupabase?: boolean; usedModel?: boolean; diagnostics?: Record<string, unknown> } | null;
}

export function auditHermesRoutingDecision(input: RoutingDecisionAuditInput) {
  const normalizedMessage = input.message.trim().replace(/\s+/g, ' ');
  const state = input.previousConversationState || {};
  const classification = classifyHermesDomain(normalizedMessage, input.currentPage);
  const hasMemory = Boolean(state.lastSelectedItem || state.lastRecommendedItem || state.lastRankedList?.length || state.lastListedItems?.length);
  const boundary = evaluateTopicBoundary({
    message: normalizedMessage, detectedDomain: classification.domain,
    previousTopic: state.lastTopic || state.lastIntent || 'unknown', previousIntent: state.lastIntent,
    previousSelectedItem: state.lastSelectedItem as ConversationItem | null,
    previousRankedItems: state.lastRankedList, previousListedItems: state.lastListedItems,
    currentPage: input.currentPage, previousPage: state.lastPage,
  });
  const currentActual = detectActivationLevel(normalizedMessage, hasMemory, Boolean(input.currentPage), {
    detectedDomain: classification.domain, shouldUseMemory: boundary.shouldUsePriorMemory,
    memoryRejectionReason: boundary.shouldUsePriorMemory ? null : boundary.reason,
  });
  const actualLevel = input.actualResult?.activationLevel ?? currentActual.level;
  const actualRoute = input.actualResult?.route ?? currentActual.route;
  const isStatusOrMeta = classification.domain === 'model_cost_status' || classification.domain === 'source_trace' || ['settings', 'reports', 'tools_cli', 'system_health', 'automation'].includes(classification.domain);
  const isRiskyExecution = /\b(send|publish|charge|execute|place\s+(?:a\s+)?trade|submit\s+(?:a\s+)?dispute|delete|truncate|start\s+scheduler)\b/i.test(normalizedMessage);
  let expectedActivationLevel = 4;
  let expectedRoute = 'local_reasoning';
  let expectedSource = 'domain_context';
  if (isRiskyExecution) { expectedActivationLevel = 0; expectedRoute = 'blocked_or_gated'; expectedSource = 'safety_gate'; }
  else if (classification.domain === 'source_trace') { expectedActivationLevel = 1; expectedRoute = 'trace_status'; expectedSource = 'last_routing_trace'; }
  else if (classification.domain === 'casual_identity') { expectedActivationLevel = 1; expectedRoute = 'no_model'; expectedSource = 'casual_local'; }
  else if (isStatusOrMeta) { expectedActivationLevel = 1; expectedRoute = 'no_model'; expectedSource = 'local_status'; }
  else if (boundary.shouldUsePriorMemory) { expectedActivationLevel = 3; expectedRoute = 'conversation_memory'; expectedSource = 'conversation_memory'; }
  else if (['business_opportunity', 'monetization', 'clients', 'approvals'].includes(classification.domain) && /\b(show|list|available|pending|which)\b/i.test(normalizedMessage)) { expectedActivationLevel = 2; expectedRoute = 'supabase_query'; expectedSource = 'live_supabase_first'; }
  const actualMemoryUsed = typeof input.actualResult?.diagnostics?.memoryUsed === 'boolean'
    ? input.actualResult.diagnostics.memoryUsed
    : hasMemory && actualLevel === 4;
  const leakedMemory = !boundary.shouldUsePriorMemory && actualMemoryUsed;
  const diagnosis = leakedMemory
    ? 'Level 4 default fired because any conversation memory counted as context; the answer builder then used a business recommendation without a reference marker or domain guard.'
    : actualLevel !== expectedActivationLevel
      ? `Expected Level ${expectedActivationLevel}, but current detector selected Level ${actualLevel}.`
      : 'Current route matches the expected activation level.';
  return {
    normalizedMessage, detectedIntent: expectedRoute, detectedDomain: classification.domain,
    isCasualOrIdentity: classification.domain === 'casual_identity', isStatusOrMeta, isRiskyExecution,
    isFollowUpCandidate: boundary.followUpMarkers.length > 0 || boundary.namedMemoryMatches.length > 0,
    followUpMarkers: boundary.followUpMarkers, namedMemoryMatches: boundary.namedMemoryMatches.map(item => item.title),
    previousTopic: state.lastTopic || state.lastIntent || 'unknown', detectedTopic: boundary.detectedTopic,
    topicChanged: boundary.isNewTopic, shouldUseMemory: boundary.shouldUsePriorMemory,
    memoryRejectionReason: boundary.shouldUsePriorMemory ? null : boundary.reason,
    expectedActivationLevel, actualActivationLevel: actualLevel, expectedRoute, actualRoute,
    expectedSource, actualSource: input.actualResult?.sourceMode ?? currentActual.source,
    usedSupabaseExpected: expectedActivationLevel === 2, usedSupabaseActual: input.actualResult?.usedSupabase ?? false,
    usedModelExpected: expectedActivationLevel === 5, usedModelActual: input.actualResult?.usedModel ?? false,
    diagnosis,
    patchTarget: leakedMemory ? 'activation default and Level 4 answer builder memory eligibility' : actualLevel !== expectedActivationLevel ? 'activation ordering/domain pre-check' : 'none',
  };
}
