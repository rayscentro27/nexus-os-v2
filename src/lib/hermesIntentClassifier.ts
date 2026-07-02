import type { HermesIntentFrame, IntentType, IntentDomain, IntentTarget, IntentAction, SourceNeed, SafetyDisposition, FollowupType } from './hermesIntentFrame';

function normalizeMessage(raw: string): string {
  return raw.normalize('NFKC').replace(/['']/g, "'").replace(/\s+/g, ' ').trim().toLowerCase();
}

function detectSafety(raw: string): SafetyDisposition {
  if (/\b(publish|charge|deploy|delete|truncate|execute|place|send|submit)\b.*\b(?:now|live|customer|trade|database|production)?\b|\bstart\b.*\bscheduler\b|\b(buy|sell)\b.*\b(?:asset|stock|crypto)\b/i.test(raw)) return 'blocked';
  if (/\b(create|prepare|draft|queue|add)\b.*\b(?:ray review|review card|task|handoff|schedule)\b/i.test(raw)) return 'approval_required';
  if (/\b(delegate|handoff|send|schedule|create|approve|move|assign|prepare|draft|start)\b.*\b(this|that|it|that one|this one)\b/i.test(raw)) return 'approval_required';
  return 'safe';
}

function detectIntentType(raw: string, lower: string): IntentType {
  if (/\b(?:where did|what source|what part of|how did you decide|why did you answer|show (?:the )?(?:full )?(?:route|trace)|was that (?:live|local))\b/i.test(lower)) return 'trace_question';
  if (/\b(?:how|what) (?:is|does) (?:the |our )?(?:system health|nexus health)\b|\bsystem health\b|\b(?:is|how) (?:nexus|system) (?:healthy|working)\b|\b(?:what is broken|what is not working|what is working)\b/i.test(lower)) return 'status_question';
  if (/\b(?:do i have|are there|show|list|what|which|any|how many)\b.*\b(?:approval|approvals|ray review|review cards?)\b/i.test(lower)) return 'record_lookup';
  if (/\b(?:do we have|are there|show|list|how many|any)\b.*\b(?:clients?|customers?|client records?)\b/i.test(lower)) return 'record_lookup';
  if (/\b(?:is|does|how is|check|show|what is)\b.*\b(?:research engine|youtube research|research pipeline)\b/i.test(lower)) return 'record_lookup';
  if (/\b(?:pull up|review|walk me through|let'?s review|show me|what are|what is|let me see|open)\b.*\b(?:business opportunit|opportunities|report|pipeline|list)\b/i.test(lower)) return 'domain_review';
  if (/\b(?:why did it|why was|explain the score|what is the score based on|why is number)\b/i.test(lower)) return 'domain_review';
  if (/\b(?:how can we|how do we|what should we|what would stop|is that realistic|what should we do first)\b/i.test(lower)) return 'advisory_followup';
  if (/\b(?:next one|start with|compare number|number \d+|that one|this one|the (?:first|second|third))\b/i.test(lower)) return 'selection_followup';
  if (/\b(?:create|prepare|draft)\b.*\b(?:ray review|review card|handoff)\b/i.test(lower)) return 'approval_action_draft';
  if (/\b(?:prepare|create|draft)\b.*\bspecialist handoff\b/i.test(lower)) return 'specialist_handoff';
  if (/\b(?:can (?:you|we)|could (?:you|we)|what would it take to)\b.*\b(?:build|make|design|add)\b.*\b(?:crm|client portal|dashboard|workflow|feature|nexus)\b/i.test(lower)) return 'build_planning';
  if (/\b(?:are you connected to|can you see|what page|what section|what color|what colour)\b.*\b(?:this|the|page|app|dashboard)\b/i.test(lower)) return 'page_context';
  if (/\b(?:what can you do|capabilit|web search|connected to|database status|model status)\b/i.test(lower)) return 'brain_capability_status';
  if (/^(?:good\s+)?(?:morning|afternoon|evening|night)\b|^(?:hi|hello|hey|yo|sup)\b/i.test(lower)) return 'greeting';
  if (/\b(?:favou?rite|do you like|what do you like|tell me a joke|what color|what colour|movie|music|pizza|ice cream)\b/i.test(lower)) return 'casual_common';
  if (/\b(?:score|scores?|results?|winner|champion|standings?|news|weather|forecast|stock|price)\b.*\b(?:last night|tonight|today|yesterday|recently|latest)\b/i.test(lower)) return 'external_current_info';
  return 'unknown';
}

function detectDomain(raw: string, lower: string, intent: IntentType): IntentDomain {
  if (intent === 'trace_question') return 'trace';
  if (intent === 'status_question') {
    if (/\bsystem health\b|\bnexus health\b|\b(?:is|how) (?:nexus|system) (?:healthy|working)\b/i.test(lower)) return 'system_health';
    return 'system_health';
  }
  if (intent === 'page_context') return 'current_page';
  if (intent === 'brain_capability_status') return 'general_conversation';
  if (intent === 'external_current_info') return 'external_info';
  if (intent === 'casual_common') return 'general_conversation';
  if (intent === 'greeting') return 'general_conversation';

  if (/\b(?:business opportunity|opportunities|readiness review|credit.*funding|monetiz|revenue|offer|pipeline)\b/i.test(lower)) {
    if (/\bmonetiz|revenue|income|profit|earn\b/i.test(lower)) return 'monetization';
    if (/\bcredit|funding|readiness|dispute|tradeline\b/i.test(lower)) return 'credit_funding';
    return 'business_opportunities';
  }
  if (/\b(?:approval|approvals|ray review|review cards?|task requests?)\b/i.test(lower)) return 'approvals';
  if (/\b(?:clients?|customers?|profiles?|onboarding)\b/i.test(lower)) return 'clients';
  if (/\b(?:youtube|video|transcript|channel|research|sources?)\b/i.test(lower)) return 'research';
  if (/\b(?:trad(?:e|ing)|forex|stock|crypto|broker|strategy)\b/i.test(lower)) return 'trading';
  if (/\b(?:credit|funding|readiness|dispute|tradeline|fundability)\b/i.test(lower)) return 'credit_funding';
  if (/\b(?:crm|client portal|dashboard|workflow|feature|nexus)\b/i.test(lower)) return 'nexus_product_build';
  if (/\b(?:reports?|briefs?|audit files?)\b/i.test(lower)) return 'reports';
  if (/\b(?:specialist|agent)\b/i.test(lower)) return 'specialist_agents';
  if (/\b(?:settings?|configuration|configured)\b/i.test(lower)) return 'reports';

  return 'unknown';
}

function detectTarget(raw: string, lower: string, domain: IntentDomain): IntentTarget {
  // Check for named offers with dollar amounts - capture from original message for proper casing
  const dollarMatch = raw.match(/\$\d+\s+Credit\s+&\s+Funding\s+Readiness\s+Review/i) ||
                      raw.match(/\$\d+\s+\w+(?:\s+\w+)*?(?:\s+Review|Plan|Subscription|Sprint)/i) ||
                      lower.match(/\$\d+\s+credit\s+&?\s*funding\s+readiness\s+review/i) ||
                      lower.match(/\$\d+\s+\w+(?:\s+\w+)*?(?:\s+review|plan|subscription|sprint)/i);
  if (dollarMatch) return { type: 'named_offer', label: dollarMatch[0].trim(), confidence: 0.9 };

  // Check for other named offers
  const namedMatch = raw.match(/(?:the\s+)?(?:Credit|Funding|Readiness|Assistant|Monthly)\s+(?:Review|Plan|Subscription|Sprint|Preparation)\b/i) ||
                     lower.match(/(?:the\s+)?(?:credit|funding|readiness|assistant|monthly)\s+(?:review|plan|subscription|sprint|preparation)\b/i);
  if (namedMatch) return { type: 'named_offer', label: namedMatch[0].trim(), confidence: 0.85 };

  const rankMatch = lower.match(/\b(?:number|#)\s*(\d+)\b|\b(?:top|first|second|third|highest|best)\b/i);
  if (rankMatch) {
    const rank = rankMatch[1] ? parseInt(rankMatch[1]) : /top|first|highest|best/i.test(rankMatch[0]) ? 1 : /second/i.test(rankMatch[0]) ? 2 : 3;
    return { type: 'ranked_item', rank, confidence: 0.8 };
  }

  if (/\b(?:that one|this one|it|that|this)\b/i.test(lower)) return { type: 'active_session_item', confidence: 0.7 };

  if (domain === 'current_page') return { type: 'page', confidence: 0.6 };
  if (domain === 'reports') return { type: 'report', confidence: 0.6 };

  return { type: 'none', confidence: 0.3 };
}

function detectAction(raw: string, lower: string, intent: IntentType): IntentAction {
  if (intent === 'approval_action_draft') return 'draft_ray_review';
  if (intent === 'specialist_handoff') return 'prepare_handoff';
  if (intent === 'trace_question') return 'explain_source';
  if (/\b(?:why did it|why was|explain the score|what is the score based on)\b/i.test(lower)) return 'explain_score';
  if (/\b(?:how can we|how do we|what should we change|improve|make it stronger)\b/i.test(lower)) return 'improve';
  if (/\b(?:compare|difference|versus|vs)\b/i.test(lower)) return 'compare';
  if (/\b(?:recommend|what should|best|top|highest)\b/i.test(lower)) return 'recommend';
  if (/\b(?:review|walk me through|let's review|pull up)\b/i.test(lower)) return 'review';
  if (/\b(?:list|show|what|which|how many|are there)\b/i.test(lower)) return 'list_inventory';
  if (intent === 'status_question' || intent === 'record_lookup') return 'answer';
  return 'answer';
}

function detectSourceNeed(domain: IntentDomain, action: IntentAction, intent: IntentType): SourceNeed {
  if (intent === 'trace_question') return 'local_trace';
  if (intent === 'page_context') return 'page_context';
  if (intent === 'casual_common' || intent === 'greeting') return 'general_reasoning';
  if (domain === 'business_opportunities' || domain === 'monetization' || domain === 'credit_funding') return 'live_records_required';
  if (domain === 'approvals' || domain === 'clients') return 'live_records_required';
  if (domain === 'research') return 'report_preferred';
  if (domain === 'trading') return 'report_preferred';
  if (domain === 'system_health') return 'report_preferred';
  if (domain === 'reports') return 'report_preferred';
  if (action === 'review' || action === 'list_inventory') return 'live_records_required';
  return 'general_reasoning';
}

function detectFollowup(raw: string, lower: string, intent: IntentType, domain: IntentDomain): { isFollowup: boolean; followupType?: FollowupType } {
  if (/\b(?:next one|start with|compare number|number \d+|that one|this one|the (?:first|second|third))\b/i.test(lower)) {
    return { isFollowup: true, followupType: 'selection' };
  }

  if (/\b(?:is that realistic|what would stop us|how do we start|what should we do first|how can we|how do we|what should we change|improve|make it stronger)\b/i.test(lower)) {
    return { isFollowup: true, followupType: 'advisory' };
  }

  if (/\b(?:why did you|where did you|how did you|what source|what part of)\b/i.test(lower)) {
    return { isFollowup: true, followupType: 'trace' };
  }

  if (/\b(?:why did it|how can we|improve|what would stop)\b/i.test(lower) && domain !== 'unknown') {
    return { isFollowup: true, followupType: 'domain_review' };
  }

  return { isFollowup: false };
}

function computeConfidence(frame: Omit<HermesIntentFrame, 'confidence'>): number {
  let score = 0.5;

  if (frame.intent !== 'unknown') score += 0.15;
  if (frame.domain !== 'unknown') score += 0.1;
  if (frame.target.type !== 'none' && frame.target.confidence > 0.5) score += 0.1;
  if (frame.action !== 'none' && frame.action !== 'answer') score += 0.05;
  if (frame.isFollowup) score += 0.05;
  if (frame.safetyDisposition === 'blocked') score += 0.05;

  return Math.min(1, Math.max(0, score));
}

export function buildIntentFrame(raw: string): HermesIntentFrame {
  const normalizedMessage = normalizeMessage(raw);
  const safetyDisposition = detectSafety(raw);
  const intent = detectIntentType(raw, normalizedMessage);
  const domain = detectDomain(raw, normalizedMessage, intent);
  const target = detectTarget(raw, normalizedMessage, domain);
  const action = detectAction(raw, normalizedMessage, intent);
  const sourceNeed = detectSourceNeed(domain, action, intent);
  const { isFollowup, followupType } = detectFollowup(raw, normalizedMessage, intent, domain);

  const signals: string[] = [];
  if (safetyDisposition !== 'safe') signals.push(`safety:${safetyDisposition}`);
  if (intent !== 'unknown') signals.push(`intent:${intent}`);
  if (domain !== 'unknown') signals.push(`domain:${domain}`);
  if (target.type !== 'none') signals.push(`target:${target.type}`);
  if (action !== 'answer' && action !== 'none') signals.push(`action:${action}`);
  if (isFollowup) signals.push(`followup:${followupType}`);

  const frame: Omit<HermesIntentFrame, 'confidence'> = {
    rawMessage: raw,
    normalizedMessage,
    intent,
    domain,
    target,
    action,
    sourceNeed,
    isFollowup,
    followupType,
    safetyDisposition,
    signals,
  };

  return { ...frame, confidence: computeConfidence(frame) };
}
