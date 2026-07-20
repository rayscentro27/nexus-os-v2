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
    .replace(/\breadines\b/g, 'readiness')
    .replace(/\bre viw\b/g, 'review')
    .replace(/\breviw\b/g, 'review')
    .replace(/\bdeparment\b/g, 'department')
    .replace(/\bdepartmant\b/g, 'department')
    .replace(/\bsystm\b/g, 'system')
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

  if (/\b(dont|don't|do not)\b.*\b(create|make|turn|draft|task|work|review)\b|\bmake a plan but don'?t create a task\b/i.test(text)) {
    return { mode: 'DECISION_SUPPORT', intent: 'active_topic_planning', confidence: hasAdvisoryContext ? 0.88 : 0.78, reason: 'Message asks for planning while explicitly negating work creation.' };
  }

  if (/\b(prepare|make|draft)\b.*\b(plan)\b.*\b(blocked|department|engineering|operations|credit|funding|queue|first step)\b/.test(text)) {
    return { mode: 'DECISION_SUPPORT', intent: 'department_plan', confidence: 0.9, reason: 'Message asks for a department plan without explicit work creation.' };
  }

  if (/\b(prepare|create|draft|send)\b.*\b(ray review|approval|review)\b|\bprepare (?:that|this) for (?:ray )?review\b/i.test(text)) {
    return { mode: 'APPROVAL_REQUEST', intent: 'prepare_approval_request', confidence: 0.92, reason: 'Message explicitly asks for Ray Review or approval preparation.' };
  }

  if (/\b(create|turn|make|prepare|assign|draft)\b.*\b(task|work request|governed work|work order)\b|\bassign this to\b/i.test(text)) {
    return { mode: 'TASK_REQUEST', intent: 'create_governed_work_request', confidence: 0.92, reason: 'Message explicitly asks to create or assign governed work.' };
  }

  if (/^(good morning|morning|good afternoon|afternoon|good evening|evening|good night|night|hi|hello|hey|yo|sup|gm)(?: hermes| ray)?[.!? ]*$/.test(text)) {
    return { mode: 'SOCIAL_GREETING', intent: /night/.test(text) ? 'farewell_or_light_check_in' : 'greeting_or_light_check_in', confidence: 0.98, reason: 'Obvious social greeting with no operational request.' };
  }

  if (/^(thank you|thanks|appreciate it|that makes sense|that tracks|i agree|makes sense|got it|ok|okay|ok that tracks|cool)[.!? ]*$/.test(text)) {
    return { mode: 'CASUAL_CONVERSATION', intent: 'acknowledgement', confidence: 0.94, reason: 'Short acknowledgement or casual turn.' };
  }

  if (/\b(how are you|how did you sleep|did you sleep|are you tired|are you awake|what's up|whats up)\b/.test(text)) {
    return { mode: 'CASUAL_CONVERSATION', intent: 'casual_check_in', confidence: 0.95, reason: 'Casual question without operational request.' };
  }

  if (/\b(what can hermes actually do now|what can hermes do|what can you do now|what cant you do yet|what can't you do yet|hermes actually do)\b/.test(text)) {
    return { mode: 'FACTUAL_QUESTION', intent: 'hermes_capability_status', confidence: 0.91, reason: 'Question asks what Hermes can and cannot do now.' };
  }

  if (/\b(who has final authority|final authority|who approves|who decides)\b/.test(text)) {
    return { mode: 'FACTUAL_QUESTION', intent: 'authority_model', confidence: 0.94, reason: 'Question asks for Nexus authority model.' };
  }

  if (/\b(what are you unsure about|what is unknown|show uncertainty|uncertainty|not hype|limitations?|what do you not know)\b/.test(text)) {
    return { mode: 'FACTUAL_QUESTION', intent: 'uncertainty_status', confidence: 0.88, reason: 'Question asks Hermes to state unknowns or limitations.' };
  }

  if (/\b(report|reports)\b/.test(text)) {
    return { mode: 'FACTUAL_QUESTION', intent: /latest|recent|most recent|show|summarize|where|find|newest|talks about|mention/.test(text) ? 'report_lookup' : 'report_catalog', confidence: 0.9, reason: 'Question asks about approved Nexus reports.' };
  }

  if (/\b(do you use a real model|which provider|provider.*right now|provider tools active|real model when you answer)\b/.test(text)) {
    return { mode: 'FACTUAL_QUESTION', intent: 'provider_status', confidence: 0.94, reason: 'Question asks for Hermes model-provider status.' };
  }

  if (/\b(stripe live|live stripe|stripe production|trading active|live trades?|live trading|alpha.*supabase|alpha.*customer data|github mcp|github writer|web search|system health|how is the system|currently blocked|what is currently blocked|blocked by policy|what is blocked by policy|blocking deployment|deployment blocked|can alpha see client data|dont activate stripe|don't activate stripe|do not activate stripe)\b/.test(text)) {
    return { mode: 'SYSTEM_STATUS', intent: 'system_status_honesty', confidence: 0.93, reason: 'Question asks for known system or capability status.' };
  }

  if (/\b(what time is it|whats the time|what's the time|time in arizona|clock time|current time|time now|what day is it|what is today'?s date|current date|what date is it|what date are we on|what day is today|is today|what date are we working from|date are we working from)\b/.test(text)) {
    return { mode: 'FACTUAL_QUESTION', intent: 'current_time_or_date', confidence: 0.96, reason: 'Question asks for current time or date.' };
  }

  if (/\b(where did (?:that|this|the answer) (?:come from|get|come)|where did you get that|what evidence supports|what backs up|show me what evidence you used|evidence you used|how did you know|what source|source for that|is that your opinion|is that a fact|evidence or judgment|how current is that)\b/.test(text)) {
    return { mode: 'FACTUAL_QUESTION', intent: 'explain_previous_source', confidence: 0.94, reason: 'Question asks for prior answer provenance.' };
  }

  if (/\b(what departments are active|department list|which departments|department registry)\b/.test(text)) {
    return { mode: 'FACTUAL_QUESTION', intent: 'department_list', confidence: 0.94, reason: 'Question asks for active governed departments.' };
  }

  if (/\b(operations|engineering|research|knowledge|credit|funding|department)\b.*\b(working on|doing|need|needs|queue|inbox|status|active|risk|overdue|approval|approvals|blocked|blockers|completed|finished|incident|incidents|dependency|dependencies)\b|\b(which department has the biggest risk|what is overdue|what completed recently|what finished today|what needs my approval|what is blocked)\b/.test(text)) {
    const intent = /approval|needs my approval/.test(text) ? 'department_approvals'
      : /blocked|blockers/.test(text) ? 'department_blockers'
        : /completed|finished/.test(text) ? 'department_completed_work'
          : /incident/.test(text) ? 'department_incidents'
            : /dependency|dependencies/.test(text) ? 'department_dependencies'
              : /working on|queue|inbox|need|needs/.test(text) ? 'department_queue'
                : 'department_status';
    return { mode: 'FACTUAL_QUESTION', intent, confidence: 0.92, reason: 'Question asks for Department Operations evidence.' };
  }

  if (/\b(what have we completed on hermes|what is still missing|where are we really at with hermes|departments?|department operations|governed automation|what wave|in the wave|hermes wave|automation departments|what did we finish|what did we build|are we done with hermes|what are we working on|what is next|next major phase|what is the next major phase|what did we complete|what is currently stuck|currently stuck)\b/.test(text)) {
    return { mode: 'FACTUAL_QUESTION', intent: 'project_status', confidence: 0.9, reason: 'Question asks for project or roadmap status.' };
  }

  if (/\b(redesign|design|layout|give me three options|give me another option|another option|which option would you choose|dashboard|command center|workroom|client portal|workflow make sense|workflow|what would you change|why would that be better|what could go wrong|phase one|phases|what do you think of this layout|improve the .*page|page change|cleaner|reorganized|think it through|help me think)\b/.test(text)) {
    return { mode: 'PROJECT_DISCUSSION', intent: 'project_discussion_design', confidence: 0.86, reason: 'Question asks for project/design discussion, not execution.' };
  }

  if (/\b(let'?s|lets|okay|ok|continue|start|work on|break it|break|plan it|plan|what comes first|what do we need to do|what do we need to decide|decide first|first step|pick back up|pick up|resume)\b.*\b(readiness|review|journey|thing|that|it|plan|\$97|offer)\b/.test(text) || /\bhelp me plan it|break it down|break it into steps|what comes first|what do we need to do first|continue what we were discussing|do not create anything|what should that offer include|pick up where we left off on the offer|resume the readiness thing|readiness review plan|readiness review plan pls|what do we need to decide first|what do we need to decide|decide first|how long should it take|what do we need from them|what happens after they pay|make a plan but don\'?t create a task\b/.test(text)) {
    return { mode: 'DECISION_SUPPORT', intent: 'active_topic_planning', confidence: hasAdvisoryContext ? 0.88 : 0.8, reason: 'Question asks to continue or plan the active/named topic without execution.' };
  }

  if (/\b(going back to|go back to|return to|earlier|previous)\b.*\b(client live data|client live-data|live data flag|live-data flag)\b/.test(text)) {
    return { mode: hasAdvisoryContext ? 'FOLLOW_UP_ADVICE' : 'CLARIFICATION_REQUIRED', intent: hasAdvisoryContext ? 'followup_blockers' : 'missing_advisory_context', confidence: hasAdvisoryContext ? 0.9 : 0.55, reason: 'Explicit older-topic recall should resolve against advisory history.' };
  }

  if (hasAdvisoryContext && /\b(first step|what would the first step be|what should the first step be|what comes first|what do we do first|what should we do first)\b/.test(text)) {
    return { mode: 'FOLLOW_UP_ADVICE', intent: 'followup_deep_dive', confidence: 0.9, reason: 'Question asks for the first step on the active advisory topic.' };
  }

  if (/\b(clients?|customers?|paying customers|client rows|client count)\b/.test(text)) {
    return { mode: 'FACTUAL_QUESTION', intent: 'customer_aggregate_status', confidence: 0.9, reason: 'Question asks for aggregate customer/client status.' };
  }

  if (/\b(why that one|why this one|why did you choose that|why is that first|why you pick that|what makes that the priority)\b/.test(text)) {
    return { mode: hasAdvisoryContext ? 'FOLLOW_UP_ADVICE' : 'CLARIFICATION_REQUIRED', intent: hasAdvisoryContext ? 'followup_rationale' : 'missing_advisory_context', confidence: hasAdvisoryContext ? 0.9 : 0.55, reason: 'Question asks for the rationale behind prior advice.' };
  }

  if (/\b(is that realistic|is this realistic|is it realistic|can we actually do that|is that possible|can we pull that off|can we really pull that off)\b/.test(text)) {
    return { mode: hasAdvisoryContext ? 'FOLLOW_UP_ADVICE' : 'CLARIFICATION_REQUIRED', intent: hasAdvisoryContext ? 'followup_feasibility' : 'missing_advisory_context', confidence: hasAdvisoryContext ? 0.9 : 0.55, reason: 'Question asks whether the prior recommendation is feasible.' };
  }

  if (/\b(what would stop us|what are the blockers|what could prevent this|what could derail it|what might mess it up|what is the downside|what is the risk)\b/.test(text)) {
    return { mode: hasAdvisoryContext ? 'FOLLOW_UP_ADVICE' : 'CLARIFICATION_REQUIRED', intent: hasAdvisoryContext ? 'followup_blockers' : 'missing_advisory_context', confidence: hasAdvisoryContext ? 0.9 : 0.55, reason: 'Question asks for blockers or constraints on prior advice.' };
  }

  if (/\b(go deeper|explain that in more detail|break that down|tell me more about)\b.*\b(number\s*\d+|option\s*\d+|the first option|the second option|the third option)\b/.test(text)) {
    return { mode: hasAdvisoryContext ? 'FOLLOW_UP_ADVICE' : 'SELECTION_REFERENCE', intent: hasAdvisoryContext ? 'followup_deep_dive' : 'resolve_selection_reference', confidence: hasAdvisoryContext ? 0.9 : 0.72, reason: 'Message asks for deeper analysis of a numbered option.' };
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

  if (/\b(why is that priority over revenue|priority over revenue)\b/.test(text)) {
    return { mode: 'EXECUTIVE_ADVICE', intent: 'priority_vs_revenue', confidence: 0.9, reason: 'Question asks to compare operating priority against revenue action.' };
  }

  if (/\b(biggest risk|biggest danger|biggest problem|most exposed|hurt us the most|could go wrong first|what could go wrong|where are we exposed)\b/.test(text)) {
    return { mode: 'EXECUTIVE_ADVICE', intent: 'executive_risk', confidence: 0.92, reason: 'Question asks for the highest current operating risk.' };
  }

  if (/\b(make money today|generate revenue today|sell first|fastest revenue action|money action|money move|revenue action|how can we make money|what can generate revenue)\b/.test(text)) {
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
