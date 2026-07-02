import type { HermesIntentFrame } from './hermesIntentFrame';
import type { NexusSessionContext } from './hermesAdvisorSession';
import type { HermesDecisionState, HermesResponseMode } from './hermesDecisionState';

export type ConversationMove =
  | 'new_domain_question' | 'source_provenance_question' | 'safety_explanation_followup'
  | 'previous_answer_followup' | 'last_recommendation_followup' | 'active_session_navigation'
  | 'active_session_continuation' | 'active_target_action' | 'timeline_recap'
  | 'response_depth_change' | 'general_advisor' | 'casual_common' | 'fallback';

export interface ConversationMoveResult {
  conversationMove: ConversationMove;
  responseMode?: HermesResponseMode;
  reason: string;
}

const sessionNavigation = /^(?:next|previous|continue|number\s*\d+|open\s+(?:number\s*)?\d+|start there|walk through them|review them)[.!]?$/i;
const responseMode = (message: string): HermesResponseMode | null => {
  if (/\b(?:audit version|source details|technical details|show the path)\b/i.test(message)) return 'audit';
  if (/\b(?:show (?:me )?(?:the )?trace|where did that come from|where did you get that|what source did you use)\b/i.test(message)) return 'trace';
  if (/\b(?:ceo version|jarvis version|make it simple|short version|keep it brief)\b/i.test(message)) return 'ceo';
  return null;
};

export function classifyConversationMove(input: {
  message: string; intentFrame: HermesIntentFrame; activeSession: NexusSessionContext | null; decisionState: HermesDecisionState;
}): ConversationMoveResult {
  const { message, intentFrame, activeSession, decisionState } = input;
  const lower = message.toLowerCase();
  if (/\bwhy did you (?:block|stop|refuse|deny) (?:that|it|this)|why was that blocked\b/i.test(lower) && decisionState.lastSafetyDecision) return { conversationMove: 'safety_explanation_followup', reason: 'Question refers to the last stored safety decision.' };
  if (/\bwhy (?:do|did) you recommend (?:that|it|this|that one)|why (?:is|was) that (?:your )?(?:top|best)\b/i.test(lower)) return decisionState.lastRecommendation ? { conversationMove: 'last_recommendation_followup', reason: 'Question targets the last stored recommendation.' } : { conversationMove: 'previous_answer_followup', reason: 'Recommendation wording was used, but no stored recommendation is eligible.' };
  const mode = responseMode(message);
  if (mode) return { conversationMove: mode === 'trace' ? 'source_provenance_question' : 'response_depth_change', responseMode: mode, reason: `Global ${mode} response mode requested for the last answer.` };
  if (/\bwhat did we (?:work on|do|finish|push)|what changed yesterday|what did we finish yesterday|yesterday(?:'s)? recap\b/i.test(lower)) return { conversationMove: 'timeline_recap', reason: 'Requested a dated activity recap.' };
  if (/\bwhere did we (?:leave off|stop)|where were we|catch me up\b/i.test(lower)) return { conversationMove: 'timeline_recap', reason: 'Requested work continuation/activity context.' };
  if (intentFrame.intent === 'trace_question') return { conversationMove: 'source_provenance_question', responseMode: 'trace', reason: 'Source/provenance question targets the last successful answer.' };
  if (/\b(?:create|prepare|draft|send)\b.*\b(?:ray review|specialist handoff)\b/i.test(lower)) return { conversationMove: 'active_target_action', reason: 'Action request requires target resolution before session continuation.' };
  if (activeSession && sessionNavigation.test(message.trim())) return { conversationMove: 'active_session_navigation', reason: 'Explicit navigation command is valid for the active session.' };
  if (activeSession?.activeMode === 'business_opportunity_review' && /\b(?:start with the highest(?: scored)? one|start with (?:the )?(?:top|first) one|why did it get that score|how can we improve it|what would stop us|what are the risks|what are the blockers|next opportunity|continue opportunities)\b/i.test(lower)) return { conversationMove: 'active_session_continuation', reason: 'Message is a valid business opportunity continuation.' };
  if (activeSession?.activeMode === 'report_inventory_review' && /\b(?:continue reports|review the reports|can we review them)\b/i.test(lower)) return { conversationMove: 'active_session_continuation', reason: 'Message is a valid report continuation.' };
  if (intentFrame.intent === 'casual_common' || intentFrame.intent === 'greeting') return { conversationMove: 'casual_common', responseMode: 'casual', reason: 'Casual/common conversation.' };
  if (intentFrame.domain !== 'unknown' && !intentFrame.isFollowup) return { conversationMove: 'new_domain_question', reason: `Explicit ${intentFrame.domain} domain question.` };
  if (intentFrame.intent === 'advisory_followup') return { conversationMove: 'general_advisor', reason: 'Plan-level advisory follow-up uses advisory continuity, not the prior answer or a stale session.' };
  if (/\bhow can i test (?:this|that|it)(?: for free)?\b/i.test(lower)) return { conversationMove: 'general_advisor', reason: 'Validation question continues prior advisory context.' };
  if (decisionState.lastAnswer && /\b(?:why|how|what about)\b.*\b(?:that|it|this)\b/i.test(lower)) return { conversationMove: 'previous_answer_followup', reason: 'Pronoun follow-up targets the immediately previous answer.' };
  if (intentFrame.intent === 'general_advisor' || intentFrame.intent === 'business_advice') return { conversationMove: 'general_advisor', reason: 'General advisory request.' };
  return { conversationMove: 'fallback', reason: 'No eligible recent context or explicit intent resolved.' };
}
