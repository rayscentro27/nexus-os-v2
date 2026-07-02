import type { HermesIntentFrame } from './hermesIntentFrame';
import type { SelectionMemory } from './hermesMemoryStores';
import type { NexusSessionContext, SuccessfulTraceEntry } from './hermesAdvisorSession';
import type { HermesDecisionState, HermesResponseMode } from './hermesDecisionState';
import { classifyConversationMove, type ConversationMove } from './hermesConversationMoveClassifier';

export interface ResolvedConversationState {
  conversationMove: ConversationMove;
  winningContext: 'last_trace' | 'last_safety_decision' | 'last_answer' | 'last_recommendation' | 'active_session' | 'active_target' | 'new_domain' | 'page_context' | 'timeline' | 'none';
  domain?: string;
  target?: { id?: string; label?: string; type?: 'record' | 'recommendation' | 'report' | 'session_item' | 'page' | 'unknown' };
  action?: string;
  responseMode: HermesResponseMode;
  sourcePreference?: 'supabase' | 'report' | 'static' | 'timeline' | 'none';
  shouldPauseStaleSession: boolean;
  needsClarification: boolean;
  clarificationQuestion?: string;
  reasonForDecision: string;
}

export interface ArbiterInput {
  message: string; lower: string; intentFrame: HermesIntentFrame; activeSession: NexusSessionContext | null;
  lastRecommendation: { title: string; domain: string } | null; lastSuccessfulTrace: SuccessfulTraceEntry | null;
  selectionMemory: SelectionMemory; previousDomain: string | null; pageContext: string | null; decisionState: HermesDecisionState;
}

export function resolveHermesConversationState(input: ArbiterInput): ResolvedConversationState {
  const move = classifyConversationMove({ message: input.message, intentFrame: input.intentFrame, activeSession: input.activeSession, decisionState: input.decisionState });
  const responseMode = move.responseMode || (move.conversationMove === 'casual_common' ? 'casual' : input.decisionState.responseMode || 'ceo');
  const base = { conversationMove: move.conversationMove, responseMode, shouldPauseStaleSession: false, needsClarification: false, reasonForDecision: move.reason } as ResolvedConversationState;
  switch (move.conversationMove) {
    case 'safety_explanation_followup': return { ...base, winningContext: 'last_safety_decision', shouldPauseStaleSession: true, domain: 'safety' };
    case 'source_provenance_question': return { ...base, winningContext: 'last_trace', responseMode: move.responseMode || 'trace', shouldPauseStaleSession: true, domain: 'routing_trace' };
    case 'response_depth_change': return { ...base, winningContext: 'last_answer', shouldPauseStaleSession: true, domain: input.decisionState.lastAnswer?.domain };
    case 'last_recommendation_followup': return { ...base, winningContext: 'last_recommendation', shouldPauseStaleSession: true, domain: input.decisionState.lastRecommendation?.domain, target: input.decisionState.lastRecommendation ? { label: input.decisionState.lastRecommendation.label, type: 'recommendation' } : undefined };
    case 'previous_answer_followup': return { ...base, winningContext: 'last_answer', shouldPauseStaleSession: true, domain: input.decisionState.lastAnswer?.domain, target: input.decisionState.lastAnswer?.target };
    case 'active_target_action': return { ...base, winningContext: 'active_target', action: input.intentFrame.action, domain: input.activeSession?.activeDomain || input.intentFrame.domain };
    case 'active_session_navigation':
    case 'active_session_continuation': return { ...base, winningContext: 'active_session', domain: input.activeSession?.activeDomain || input.intentFrame.domain };
    case 'new_domain_question': return { ...base, winningContext: input.intentFrame.domain === 'current_page' ? 'page_context' : 'new_domain', shouldPauseStaleSession: true, domain: input.intentFrame.domain, sourcePreference: input.intentFrame.sourceNeed === 'live_records_required' ? 'supabase' : input.intentFrame.sourceNeed === 'report_preferred' ? 'report' : 'none' };
    case 'timeline_recap': return { ...base, winningContext: 'timeline', shouldPauseStaleSession: true, domain: 'activity_summary', sourcePreference: 'timeline' };
    case 'general_advisor': return { ...base, winningContext: 'last_answer', shouldPauseStaleSession: true, domain: input.previousDomain || input.intentFrame.domain };
    case 'casual_common': return { ...base, winningContext: 'none', shouldPauseStaleSession: true, domain: 'general_conversation' };
    default: return { ...base, winningContext: 'none', needsClarification: true, clarificationQuestion: 'What specific result do you want from this?', domain: 'unknown' };
  }
}

/** Compatibility alias for current callers. */
export const arbitrateConversationState = resolveHermesConversationState;
