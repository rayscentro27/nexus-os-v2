import type { HermesConversationMode } from './hermesConversationTypes';

export interface HermesModeClassification {
  mode: HermesConversationMode;
  intent: string;
  confidence: number;
  reason: string;
}

export function normalizeHermesConversationText(message: string): string {
  return message
    .toLowerCase()
    .replace(/\bgo;od\b/g, 'good')
    .replace(/[’']/g, "'")
    .replace(/\s+/g, ' ')
    .trim();
}

export function classifyHermesConversationMode(message: string, hasAdvisoryContext = false): HermesModeClassification {
  const text = normalizeHermesConversationText(message);

  if (!text) {
    return { mode: 'CLARIFICATION_REQUIRED', intent: 'empty_message', confidence: 1, reason: 'No user message was supplied.' };
  }

  if (/\b(place|execute|make)\b.*\b(live trade|funded trade|trade|position)\b|\b(enable|activate)\b.*\b(live stripe|live payment|live trading|github mcp writer)\b|\b(grant|give)\b.*\b(alpha)\b.*\b(supabase|client data|client pii)\b/i.test(text)) {
    return { mode: 'COMMAND', intent: 'blocked_high_risk_command', confidence: 0.96, reason: 'Message requests a prohibited or high-risk external action.' };
  }

  if (/\b(prepare|create|draft|send)\b.*\b(ray review|approval)\b|\bprepare that for ray review\b/i.test(text)) {
    return { mode: 'APPROVAL_REQUEST', intent: 'prepare_approval_request', confidence: 0.92, reason: 'Message explicitly asks for Ray Review or approval preparation.' };
  }

  if (/\b(create|turn|make|prepare|assign)\b.*\b(task|work request|governed work|work order)\b|\bassign this to\b/i.test(text)) {
    return { mode: 'TASK_REQUEST', intent: 'create_governed_work_request', confidence: 0.92, reason: 'Message explicitly asks to create or assign governed work.' };
  }

  if (/^(good morning|morning|good afternoon|afternoon|good evening|evening|good night|night|hi|hello|hey|yo|sup|gm)(?: hermes| ray)?[.!? ]*$/.test(text)) {
    return { mode: 'SOCIAL_GREETING', intent: /night/.test(text) ? 'farewell_or_light_check_in' : 'greeting_or_light_check_in', confidence: 0.98, reason: 'Obvious social greeting with no operational request.' };
  }

  if (/^(thank you|thanks|that makes sense|i agree|makes sense|got it|ok|okay|cool)[.!? ]*$/.test(text)) {
    return { mode: 'CASUAL_CONVERSATION', intent: 'acknowledgement', confidence: 0.94, reason: 'Short acknowledgement or casual turn.' };
  }

  if (/\b(how are you|how did you sleep|did you sleep|are you tired|are you awake|what's up|whats up)\b/.test(text)) {
    return { mode: 'CASUAL_CONVERSATION', intent: 'casual_check_in', confidence: 0.95, reason: 'Casual question without operational request.' };
  }

  if (/\b(stripe live|live stripe|trading active|live trading|alpha.*supabase|github mcp active|web search|system health|how is the system|blocking deployment|deployment blocked|can alpha see client data)\b/.test(text)) {
    return { mode: 'SYSTEM_STATUS', intent: 'system_status_honesty', confidence: 0.93, reason: 'Question asks for known system or capability status.' };
  }

  if (/\b(why that one|why this one|why did you choose that|why is that first|what makes that the priority)\b/.test(text)) {
    return { mode: hasAdvisoryContext ? 'FOLLOW_UP_ADVICE' : 'CLARIFICATION_REQUIRED', intent: hasAdvisoryContext ? 'followup_rationale' : 'missing_advisory_context', confidence: hasAdvisoryContext ? 0.9 : 0.55, reason: 'Question asks for the rationale behind prior advice.' };
  }

  if (/\b(is that realistic|is this realistic|is it realistic|can we actually do that|is that possible|can we pull that off)\b/.test(text)) {
    return { mode: hasAdvisoryContext ? 'FOLLOW_UP_ADVICE' : 'CLARIFICATION_REQUIRED', intent: hasAdvisoryContext ? 'followup_feasibility' : 'missing_advisory_context', confidence: hasAdvisoryContext ? 0.9 : 0.55, reason: 'Question asks whether the prior recommendation is feasible.' };
  }

  if (/\b(what would stop us|what are the blockers|what could prevent this|what could derail it|what is the downside|what is the risk)\b/.test(text)) {
    return { mode: hasAdvisoryContext ? 'FOLLOW_UP_ADVICE' : 'CLARIFICATION_REQUIRED', intent: hasAdvisoryContext ? 'followup_blockers' : 'missing_advisory_context', confidence: hasAdvisoryContext ? 0.9 : 0.55, reason: 'Question asks for blockers or constraints on prior advice.' };
  }

  if (/\b(go deeper|explain that in more detail|break that down|tell me more about|what would it cost|could we do it without paying|which one should we do first|what did you mean by that)\b/.test(text)) {
    return { mode: hasAdvisoryContext ? 'FOLLOW_UP_ADVICE' : 'CLARIFICATION_REQUIRED', intent: hasAdvisoryContext ? 'followup_deep_dive' : 'missing_advisory_context', confidence: hasAdvisoryContext ? 0.88 : 0.55, reason: 'Question asks for deeper analysis of prior advice.' };
  }

  if (/\b(number\s*\d+|option\s*\d+|the first one|the second one|the third one|the last one|that one|this one|the marketing idea|what you just said|the recommendation|the plan)\b/.test(text)) {
    const actionReference = /\b(turn|create|prepare|make|assign)\b.*\b(plan|task|work request|ray review|approval)\b/.test(text);
    if (actionReference) {
      return { mode: /\bray review|approval\b/.test(text) ? 'APPROVAL_REQUEST' : 'TASK_REQUEST', intent: 'explicit_action_with_reference', confidence: 0.9, reason: 'Explicit action request references prior advice or selection.' };
    }
    return { mode: 'SELECTION_REFERENCE', intent: 'resolve_selection_reference', confidence: hasAdvisoryContext ? 0.9 : 0.65, reason: 'Message refers to a prior recommendation or list item.' };
  }

  if (/\b(biggest risk|biggest danger|biggest problem|most exposed|hurt us the most|could go wrong first|what could go wrong|where are we exposed)\b/.test(text)) {
    return { mode: 'EXECUTIVE_ADVICE', intent: 'executive_risk', confidence: 0.92, reason: 'Question asks for the highest current operating risk.' };
  }

  if (/\b(make money today|generate revenue today|sell first|fastest revenue action|money action|revenue action|how can we make money|what can generate revenue)\b/.test(text)) {
    return { mode: 'EXECUTIVE_ADVICE', intent: 'revenue_action', confidence: 0.92, reason: 'Question asks for the best immediate revenue action.' };
  }

  if (/\b(what should we focus on today|what should we work on first|what should we do first|what do we do first|what needs my attention|what needs attention|which project should we prioritize|where do we start|where should we start|pick the best one|pick the top priority|what is the priority|what is today'?s priority|give me today'?s plan|give me today'?s priorities|what should nexus handle first|top priority)\b/.test(text)) {
    return { mode: 'EXECUTIVE_ADVICE', intent: 'executive_priority', confidence: 0.91, reason: 'Question asks Hermes to recommend an operating priority.' };
  }

  if (/\b(is this realistic|is that a good idea|review this idea|what do you think about this idea)\b/.test(text)) {
    return { mode: 'IDEA_REVIEW', intent: 'idea_review', confidence: 0.82, reason: 'Question asks for judgment on an idea.' };
  }

  if (/^(why|how|what does|explain|tell me why|go deeper on)\b/.test(text)) {
    return { mode: 'EXPLANATION', intent: 'explanation_request', confidence: 0.78, reason: 'Question asks for explanation.' };
  }

  if (/^(who|what|when|where|which|can|do|does|is|are)\b/.test(text)) {
    return { mode: 'FACTUAL_QUESTION', intent: 'factual_question', confidence: 0.72, reason: 'General factual question without explicit execution intent.' };
  }

  return { mode: 'CLARIFICATION_REQUIRED', intent: 'unresolved_conversation', confidence: 0.45, reason: 'No safe mode was confidently identified.' };
}
