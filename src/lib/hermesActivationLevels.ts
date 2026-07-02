import { classifyHermesDomain, type HermesDomain } from './hermesDomainClassifier';
import type { RouteDecision } from './hermesRouteDecision';

/**
 * Hermes Activation Levels — 7-level system that determines how a message is processed.
 *
 * Level 0: Safety gate — block dangerous execution
 * Level 1: Meta/status/cost/process/local facts — no_model, local sources
 * Level 2: Live Supabase retrieval — no_model or local_reasoning, live data first
 * Level 3: Conversation memory / follow-up resolution — local_reasoning, previous items
 * Level 4: Local reasoning — recommend/prioritize/plan, Supabase + page + reports + memory
 * Level 5: Model reasoning — deep synthesis, polished writing, complex strategy
 * Level 6: Approval/action layer — create review card, prepare task, run dry-run
 *
 * The activation level is determined BEFORE intent routing and model routing.
 * It is the master switch that controls which code path runs.
 */

export type ActivationLevel = 0 | 1 | 2 | 3 | 4 | 5 | 6;

export interface ActivationDecision {
  level: ActivationLevel;
  levelName: string;
  trigger: string;
  route: string;
  modelRoute: 'no_model' | 'local_reasoning' | 'cheap_model' | 'primary_model' | 'blocked_or_gated';
  source: string;
  reason: string;
}

export interface ActivationDetectionContext {
  detectedDomain?: HermesDomain;
  shouldUseMemory?: boolean;
  memoryRejectionReason?: string | null;
}

export const HERMES_ACTIVATION_LEVELS: ReadonlyArray<{ level: ActivationLevel; name: string; route: string }> = [
  { level: 0, name: 'Safety Gate', route: 'blocked_or_gated' },
  { level: 1, name: 'Meta/Status/Cost/Process/Local Facts', route: 'no_model' },
  { level: 2, name: 'Live Supabase Retrieval', route: 'supabase_query' },
  { level: 3, name: 'Conversation Memory / Follow-up Resolution', route: 'conversation_memory' },
  { level: 4, name: 'Local Reasoning', route: 'local_reasoning' },
  { level: 5, name: 'Model Reasoning', route: 'model_reasoning' },
  { level: 6, name: 'Approval/Action Layer', route: 'approval_gated_workflow' },
];

const LEVEL_NAMES: Record<ActivationLevel, string> = {
  0: 'Safety Gate',
  1: 'Meta/Status/Cost/Process',
  2: 'Live Supabase Retrieval',
  3: 'Conversation Memory / Follow-up',
  4: 'Local Reasoning',
  5: 'Model Reasoning',
  6: 'Approval/Action Layer',
};

/**
 * Determine the activation level for a message.
 *
 * The order matters: lower levels are checked first (safety overrides everything).
 */
export function detectActivationLevel(
  message: string,
  hasConversationMemory = false,
  hasPageContext = false,
  context: ActivationDetectionContext = {},
): ActivationDecision {
  const lower = message.toLowerCase().trim();
  const domain = context.detectedDomain || classifyHermesDomain(message).domain;

  // ── Level 0: Safety gate ──
  // Execution verbs that are NOT status questions
  const execVerbs = /\b(publish|send|charge|buy|sell|deploy|seed|insert|delete|truncate|start\s+scheduler|run\s+shell|live\s+client\s+write|dispute|post\s+to\s+social|email\s+blast)\b/i;
  const statusExemptions = /\b(status|running|active|proof|what|show|list|is|are|can|report|did you|have you)\b/i;
  if (execVerbs.test(lower) && !statusExemptions.test(lower)) {
    return {
      level: 0,
      levelName: LEVEL_NAMES[0],
      trigger: 'Execution verb detected without status exemption',
      route: 'blocked_or_gated',
      modelRoute: 'no_model',
      source: 'safety_gate',
      reason: 'State-changing action requires Ray Review approval gate.',
    };
  }
  // "Can you place a trade" is a safety question, not execution
  if (/\b(place\s+a\s+trade|execute\s+(this\s+)?trade|buy\s+\w+|sell\s+\w+|turn\s+on\s+live\s+trading|connect\s+funded|start\s+trading|open\s+a\s+position|make\s+a\s+trade)\b/i.test(lower)) {
    return {
      level: 0,
      levelName: LEVEL_NAMES[0],
      trigger: 'Trading execution request',
      route: 'blocked_or_gated',
      modelRoute: 'no_model',
      source: 'safety_gate',
      reason: 'Trading execution is always blocked. Paper/demo only.',
    };
  }

  // ── Casual/identity pre-check: new local topic, never memory/model/Supabase ──
  if (domain === 'source_trace') {
    return {
      level: 1, levelName: LEVEL_NAMES[1], trigger: 'Routing/source/trace priority override',
      route: 'trace_status', modelRoute: 'no_model', source: 'last_routing_trace',
      reason: 'Routing and source questions are answered from the last relevant trace before memory or domain reasoning.',
    };
  }

  if (domain === 'casual_identity') {
    return {
      level: 1, levelName: LEVEL_NAMES[1], trigger: 'Casual/identity topic override',
      route: 'no_model', modelRoute: 'no_model', source: 'casual_local',
      reason: 'Casual and identity questions start a new local topic and reject prior task memory.',
    };
  }

  // Identify possible references now; eligibility is applied after status/domain pre-checks.
  const isFollowUp =
    /\b(?:number|#|option)\s*\d+/.test(lower) ||
    /^(?:that|this|it|the\s+one|another|other)\b/i.test(lower) ||
    /^(?:ok\s+)?pick\s+one/i.test(lower) ||
    /^(?:ok\s+)?choose\s+one/i.test(lower) ||
    /\b(which\s+one\s+do\s+you\s+recommend|which\s+one\s+should\s+(we|i)|recommend\s+one|pick\s+(one|that)|the\s+(monthly|readiness|subscription|credit|funding|trading|research|opportunity)\s+one)\b/i.test(lower) ||
    /\b(how\s+do\s+we\s+implement\s+(it|that|this)|how\s+do\s+(we|i)\s+(start|build|launch|execute)\s+(it|that|this))\b/i.test(lower) ||
    (/^(?:first|top|second|third|last|next)\b/i.test(lower) && lower.split(' ').length <= 5);
  const isApprovalAction = /\b(create\s+(?:a\s+)?(?:ray\s+review\s+)?(?:review\s+)?card|prepare\s+task|send\s+to\s+specialist|run\s+dry-run|queue\s+for\s+review|add\s+to\s+ray\s+review)\b/i.test(lower);

  // ── Level 1: Meta/status/cost/process/local facts ──
  if (
    /\b(what\s+model|which\s+model|model\s+(?:status|route)|live\s+model|token|routing\s+trace|are\s+you\s+using|how\s+are\s+you\s+controlling|what\s+did.*cost|what\s+did\s+that\s+model\s+call\s+cost|how\s+can\s+we\s+reduce\s+token\s+cost|was\s+that\s+model\s+call\s+necessary|what\s+route\s+did|can\s+you\s+use\s+ollama|can\s+you\s+use\s+openrouter)\b/i.test(lower) ||
    /\b(what\s+sections|which\s+sections|section\s+status|is\s+.+\s+(live|working|running|blocked|static|connected|up|down|active|verified)|show\s+proof)\b/i.test(lower) ||
    /\b(what\s+processes|what\s+tools|what\s+reports|what\s+settings|what\s+automations|what\s+schedulers|what\s+is\s+broken|what\s+needs\s+approval|what\s+should\s+i\s+work\s+on\s+next|when\s+was\s+the\s+last|is\s+youtube\s+research|is\s+trading|is\s+credit|what\s+did\s+we\s+do|what\s+wrote|can\s+you\s+run|can\s+you\s+place|can\s+you\s+publish|youtube|transcript|video\s+fetch|channel\s+poll)\b/i.test(lower) ||
    /\b(are\s+you\s+connected|supabase\s+status|database\s+status|what\s+can\s+you\s+do|holding\s+back|where.*answers|gated|web\s+search|search\s+the\s+internet|google|bing|search\s+online)\b/i.test(lower) ||
    /\b(daily\s+summary|ceo\s+summary|ceo\s+version|what\s+did\s+we\s+do\s+today|what\s+did\s+you\s+do\s+today|plain\s+english|what\s+should\s+i\s+care)\b/i.test(lower) ||
    /\b(why\s+did\s+you\s+answer|where\s+did\s+(that|it)\s+route|what\s+source\s+did\s+you\s+use|did\s+you\s+use\s+supabase|did\s+you\s+use\s+the\s+model|what\s+source)\b/i.test(lower)
  ) {
    return {
      level: 1,
      levelName: LEVEL_NAMES[1],
      trigger: 'Meta/status/cost/process/capability question',
      route: 'no_model',
      modelRoute: 'no_model',
      source: 'local_reports_usage_ledger_activity_journal_capability_state',
      reason: 'Answerable from local reports, usage ledger, activity journal, or capability state.',
    };
  }

  // Domain-specific status families override stale memory even if pronouns are present.
  if (['settings', 'reports', 'tools_cli', 'system_health', 'automation'].includes(domain) ||
      (domain === 'research_youtube' && /\b(is|are|status|running|writing|last|proof|what)\b/i.test(lower))) {
    return {
      level: 1, levelName: LEVEL_NAMES[1], trigger: `Explicit ${domain} status domain`,
      route: 'no_model', modelRoute: 'no_model', source: 'domain_local_status',
      reason: `The explicit ${domain} domain starts a new local status topic and rejects stale memory.`,
    };
  }

  // ── Level 3: eligible conversation continuation only ──
  const memoryEligible = context.shouldUseMemory ?? (isFollowUp && hasConversationMemory);
  if (!isApprovalAction && hasConversationMemory && memoryEligible) {
    return {
      level: 3, levelName: LEVEL_NAMES[3], trigger: 'Topic boundary approved prior memory',
      route: 'conversation_memory', modelRoute: 'local_reasoning', source: 'conversation_memory',
      reason: 'An explicit reference, named entity, or same-domain continuation made prior memory eligible.',
    };
  }

  // ── Level 2: Live Supabase retrieval ──
  if (
    /\b(approvals?|ray\s+review|pending|task\s+requests?|business\s+opportunit|opportunities|clients?|customer|profile|research\s+(sources?|runs?|candidates?|rows?)|monetization|offers?|live\s+records?|what.*in\s+supabase|show\s+me.*from\s+supabase)\b/i.test(lower) &&
    !isApprovalAction &&
    !/\b(recommend|prioritize|what\s+should\s+i|what\s+business\s+(?:can|should)\s+i\s+start|fastest\s+money|implementation\s+plan|how\s+do\s+we|30\s*days|low[- ](?:startup\s+)?cost)\b/i.test(lower)
  ) {
    return {
      level: 2,
      levelName: LEVEL_NAMES[2],
      trigger: 'Live Supabase data request',
      route: 'supabase_query',
      modelRoute: 'no_model',
      source: 'live_supabase_first',
      reason: 'Live Supabase read for supported tables when authenticated.',
    };
  }

  // ── Level 4: Local reasoning ──
  if (
    (domain === 'trading' && /\b(recommend|strategy|setup|test|paper|backtest|compare|should)\b/i.test(lower)) ||
    (['business_opportunity', 'monetization'].includes(domain) && /\b(recommend|start|launch|easiest|low[- ]cost|make|money|revenue|earn|most|highest|fastest|monetize|first|should|month|next|\d+\s+(?:days?|says?|weeks?))\b/i.test(lower)) ||
    /\b(recommend|prioritize|what\s+should\s+i\s+do\s+next|fastest\s+money\s+move|implementation\s+plan|what\s+business\s+(can|should)\s+i\s+start|how\s+do\s+we\s+implement|30\s*days|low\s+startup\s+cost|which\s+one\s+do\s+you\s+recommend|pick\s+one|choose\s+one)\b/i.test(lower) ||
    (/\b(business|start|opportunity|strategy)\b/i.test(lower) && !/\b(status|live|running|blocked)\b/i.test(lower))
  ) {
    return {
      level: 4,
      levelName: LEVEL_NAMES[4],
      trigger: 'Recommendation/prioritization/implementation request',
      route: 'local_reasoning',
      modelRoute: 'local_reasoning',
      source: 'supabase_page_context_reports_memory',
      reason: 'Local reasoning from Supabase + page context + reports + memory before model.',
    };
  }

  // ── Level 5: Model reasoning ──
  if (
    /\b(deep\s+synthesis|polished\s+writing|complex\s+strategy|multi-source\s+analysis|write\s+a\s+(pitch|proposal|email\s+draft|landing\s+page)|compose|generate|draft\s+a)\b/i.test(lower) ||
    (/\b(analyze|analysis|synthesize|comprehensive|detailed)\b/i.test(lower) && !/\b(status|report|what\s+is)\b/i.test(lower))
  ) {
    return {
      level: 5,
      levelName: LEVEL_NAMES[5],
      trigger: 'Deep synthesis / polished writing / complex analysis',
      route: 'model_reasoning',
      modelRoute: 'cheap_model',
      source: 'packed_context_cost_logged',
      reason: 'Model reasoning with packed context and cost logging.',
    };
  }

  // ── Level 6: Approval/action layer ──
  if (isApprovalAction) {
    return {
      level: 6,
      levelName: LEVEL_NAMES[6],
      trigger: 'Approval/action request',
      route: 'approval_gated_workflow',
      modelRoute: 'no_model',
      source: 'task_requests_ray_review',
      reason: 'Action queued through Ray Review approval workflow.',
    };
  }

  // ── Default: page context may justify local reasoning; stale memory alone may not. ──
  if (hasPageContext) {
    return {
      level: 4,
      levelName: LEVEL_NAMES[4],
      trigger: 'Default with current page context available',
      route: 'local_reasoning',
      modelRoute: 'local_reasoning',
      source: 'available_context',
      reason: 'Current page context is available — reasoning locally without inheriting stale memory.',
    };
  }

  return {
    level: 1,
    levelName: LEVEL_NAMES[1],
    trigger: 'Default — no specific trigger matched',
    route: 'no_model',
    modelRoute: 'no_model',
    source: 'local_context',
    reason: 'No specific activation trigger — defaulting to local context.',
  };
}

/** Get a human-readable description of an activation level. */
export function describeActivationLevel(level: ActivationLevel): string {
  const descriptions: Record<ActivationLevel, string> = {
    0: 'Safety gate — execution verbs blocked, requires Ray Review approval',
    1: 'Meta/status/cost/process — answered from local reports, usage ledger, activity journal',
    2: 'Live Supabase retrieval — queries authenticated Supabase tables first',
    3: 'Conversation memory — resolves follow-up references from previous listed/ranked items',
    4: 'Local reasoning — recommends/prioritizes/plans from Supabase + page + reports + memory',
    5: 'Model reasoning — deep synthesis with packed context and cost logging',
    6: 'Approval/action — queues tasks through Ray Review workflow',
  };
  return descriptions[level];
}

export const explainActivationLevel = describeActivationLevel;
export function getActivationLevelRoute(level: ActivationLevel): string {
  return HERMES_ACTIVATION_LEVELS.find(item => item.level === level)?.route || 'no_model';
}
export function shouldUseModelForLevel(level: ActivationLevel): boolean { return level === 5; }
export function shouldUseSupabaseForLevel(level: ActivationLevel): boolean { return level === 2 || level === 4; }
export function isStatusLevel(level: ActivationLevel): boolean { return level === 1; }
export function isFollowUpLevel(level: ActivationLevel): boolean { return level === 3; }
export function isSafetyLevel(level: ActivationLevel): boolean { return level === 0; }

/** Compatibility adapter: the priority router's RouteDecision is now authoritative. */
export function activationFromRouteDecision(decision: RouteDecision): ActivationDecision {
  return {
    level: decision.activationLevel,
    levelName: HERMES_ACTIVATION_LEVELS.find(item => item.level === decision.activationLevel)?.name || `Level ${decision.activationLevel}`,
    trigger: decision.routeId,
    route: decision.routeId,
    modelRoute: decision.modelPolicy === 'required' ? 'primary_model' : decision.modelPolicy === 'allowed_if_needed' ? 'local_reasoning' : decision.actionPolicy === 'blocked' ? 'blocked_or_gated' : 'no_model',
    source: decision.retrievalPolicy,
    reason: decision.reason,
  };
}
