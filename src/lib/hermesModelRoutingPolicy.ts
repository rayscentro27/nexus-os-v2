/**
 * Hermes Model Routing Policy — decides whether a message needs a model call.
 *
 * The model is ONE tool in Hermes orchestration. Most answers should be NO_MODEL
 * (local context, Supabase data, plain conversation). The model is reserved for
 * higher-value reasoning that genuinely benefits from it.
 */

export type ModelRoute = 'no_model' | 'cheap_model' | 'primary_model' | 'blocked_or_gated';

export interface RoutingDecision {
  route: ModelRoute;
  reason: string;
  maxInputTokens: number;
  maxOutputTokens: number;
  maxTurns: number;
  allowTools: boolean;
  allowedContextSources: string[];
  requiresApproval: boolean;
  fallbackRoute: ModelRoute;
}

const DEFAULTS: Record<ModelRoute, Omit<RoutingDecision, 'route' | 'reason'>> = {
  no_model: {
    maxInputTokens: 0,
    maxOutputTokens: 0,
    maxTurns: 0,
    allowTools: false,
    allowedContextSources: [],
    requiresApproval: false,
    fallbackRoute: 'no_model',
  },
  cheap_model: {
    maxInputTokens: 1500,
    maxOutputTokens: 500,
    maxTurns: 2,
    allowTools: false,
    allowedContextSources: ['page_context', 'supabase_summary', 'operations_summary'],
    requiresApproval: false,
    fallbackRoute: 'no_model',
  },
  primary_model: {
    maxInputTokens: 6000,
    maxOutputTokens: 1200,
    maxTurns: 4,
    allowTools: false,
    allowedContextSources: ['page_context', 'supabase_summary', 'operations_summary', 'research_summary', 'report_excerpt'],
    requiresApproval: false,
    fallbackRoute: 'cheap_model',
  },
  blocked_or_gated: {
    maxInputTokens: 0,
    maxOutputTokens: 0,
    maxTurns: 0,
    allowTools: false,
    allowedContextSources: [],
    requiresApproval: true,
    fallbackRoute: 'no_model',
  },
};

function decide(lower: string): { route: ModelRoute; reason: string } {
  // ── BLOCKED: dangerous actions ──
  if (/\b(send|email|publish|post|tweet|deploy|charge|trade|buy|sell|turn\s+on\s+live|connect\s+funded|dispute|seed|sql|drop|truncate|delete)\b/i.test(lower)) {
    // But allow trading STATUS questions (not execution)
    if (/\b(trading|lab)\b/i.test(lower) && /\b(running|active|status|is\s+trading|trading\s+lab\s+status)\b/i.test(lower)) {
      return { route: 'no_model', reason: 'Trading status question — answerable from section status registry.' };
    }
    return { route: 'blocked_or_gated', reason: 'Execution request — must go through Ray Review approval gate, never direct model.' };
  }

  // ── NO_MODEL: section status questions — always answer from registry ──
  if (/\b(is\s+.+\s+(live|working|running|blocked|static|connected|up|down|active|verified)|what\s+(is|are)\s+(the\s+)?status|show\s+proof|what\s+sections|which\s+sections|what\s+is\s+scheduled|what\s+is\s+blocked|what\s+is\s+live|what\s+is\s+static|is\s+this\s+section|what\s+sections\s+are)\b/i.test(lower)) {
    return { route: 'no_model', reason: 'Section status question — answerable from section status registry.' };
  }

  // ── NO_MODEL: process/tool/report/settings questions — answerable from reports ──
  if (/\b(what\s+processes|what\s+tools|what\s+reports|what\s+settings|what\s+automations|what\s+schedulers|what\s+drafts|what\s+is\s+broken|what\s+needs\s+approval|what\s+should\s+i\s+work\s+on\s+next|when\s+was\s+the\s+last|is\s+youtube\s+research|is\s+trading|is\s+credit|what\s+did\s+we|what\s+wrote|can\s+you\s+run|can\s+you\s+place|can\s+you\s+publish|youtube|transcript|video\s+fetch|channel\s+poll)\b/i.test(lower)) {
    return { route: 'no_model', reason: 'Process/tool/report/status question — answerable from local reports and registry.' };
  }

  // ── NO_MODEL: cost/meta/model/token questions — never spend tokens explaining token cost ──
  if (/\b(cost|token|model\s+call|what\s+did.*cost|how\s+can\s+we\s+reduce|was\s+that\s+necessary|what\s+route|are\s+you\s+using\s+a\s+live\s+model|what\s+model|how\s+are\s+you\s+controlling|can\s+you\s+use\s+ollama|can\s+you\s+use\s+openrouter)\b/i.test(lower)) {
    return { route: 'no_model', reason: 'Cost/meta/model question — must never trigger a model call to explain cost.' };
  }

  // ── NO_MODEL: casual / personality ──
  if (/\b(favorite|joke|funny|how are you|are you real|what are you|who are you|thank|hello|hi |hey)\b/i.test(lower)) {
    return { route: 'no_model', reason: 'Casual/personality question — local conversation brain handles this.' };
  }

  // ── NO_MODEL: simple status already known from local data ──
  if (/\b(how many|how much|count|row count|number of|total|status|is it|are we|do we have)\b/i.test(lower)) {
    if (/\b(model|ollama|oracle|openrouter|edge function|supabase|approval|pending|review)\b/i.test(lower)) {
      return { route: 'no_model', reason: 'Infrastructure status question — answerable from local reports/context.' };
    }
  }

  // ── NO_MODEL: source labels and simple data ──
  if (/\b(source|label|what source|where did|live or static|which data)\b/i.test(lower)) {
    return { route: 'no_model', reason: 'Source label question — answerable from context without model.' };
  }

  // ── NO_MODEL: operations summaries ──
  if (/\b(operations|process|background|scheduler|launchd|report status|audit summary)\b/i.test(lower)) {
    if (!/\b(explain|analyze|compare|strategy|recommend|deep|detailed|plain language)\b/i.test(lower)) {
      return { route: 'no_model', reason: 'Operations summary — local report data is sufficient.' };
    }
  }

  // ── NO_MODEL: memory/recall ──
  if (/\b(what did we|what have we|remember|recall|history|recent|today|yesterday)\b/i.test(lower)) {
    return { route: 'no_model', reason: 'Memory/recall — answerable from local context and chat history.' };
  }

  // ── NO_MODEL: scheduling questions ──
  if (/\b(schedule|next week|next month|tomorrow|when|time|date|deadline)\b/i.test(lower)) {
    if (!/\b(explain|analyze|compare|strategy)\b/i.test(lower)) {
      return { route: 'no_model', reason: 'Scheduling question — time context is available locally.' };
    }
  }

  // ── CHEAP_MODEL: short rewrites and formatting ──
  if (/\b(rewrite|rephrase|simplify|summarize briefly|format|clean up|shorten|plain english|plain language)\b/i.test(lower)) {
    return { route: 'cheap_model', reason: 'Short rewrite/formatting task — cheap model is sufficient.' };
  }

  // ── CHEAP_MODEL: brief report explanation ──
  if (/\b(explain this|what does this mean|translate|in plain english|briefly)\b/i.test(lower)) {
    return { route: 'cheap_model', reason: 'Brief explanation — cheap model can handle this concisely.' };
  }

  // ── PRIMARY_MODEL: strategic reasoning ──
  if (/\b(strategy|strategic|compare|versus|vs|which is better|recommend|advice|plan|roadmap|implementation)\b/i.test(lower)) {
    return { route: 'primary_model', reason: 'Strategic reasoning — benefits from primary model synthesis.' };
  }

  // ── PRIMARY_MODEL: complex multi-source analysis ──
  if (/\b(analyze|analysis|synthesize|deep dive|comprehensive|detailed|full audit|explain.*audit|explain.*report)\b/i.test(lower)) {
    return { route: 'primary_model', reason: 'Complex analysis — benefits from primary model reasoning.' };
  }

  // ── PRIMARY_MODEL: creative/business output ──
  if (/\b(write|draft|create|compose|generate|proposal|pitch|email draft|landing page)\b/i.test(lower)) {
    if (!/\b(send|publish|deploy|post)\b/i.test(lower)) {
      return { route: 'primary_model', reason: 'Creative/business output — benefits from primary model generation.' };
    }
  }

  // Default: no model
  return { route: 'no_model', reason: 'Default path — local context is sufficient for this question.' };
}

/**
 * Decide the model routing for a user message.
 * Returns a RoutingDecision with all budget/cap info.
 */
export function routeModel(message: string, isBackgroundJob = false): RoutingDecision {
  const lower = (message || '').toLowerCase();
  const { route, reason } = decide(lower);

  // Override for background jobs
  if (isBackgroundJob && route === 'primary_model') {
    return {
      ...DEFAULTS.cheap_model,
      route: 'cheap_model',
      reason: 'Background jobs use cheap model only unless Ray approves primary.',
      maxInputTokens: 1000,
      maxOutputTokens: 300,
      maxTurns: 1,
    };
  }
  if (isBackgroundJob && route === 'no_model') {
    return {
      ...DEFAULTS.no_model,
      route: 'no_model',
      reason: 'Background jobs default to no_model unless explicitly allowed.',
    };
  }

  return { ...DEFAULTS[route], route, reason };
}

/**
 * Check if Hermes model is available (for status answers).
 */
export function getModelAvailability(): { configured: boolean; provider: string; model: string } {
  // This reads only env var NAMES, never values
  const chatEnabled = (import.meta.env?.VITE_HERMES_CHAT_ENABLED as string) === 'true';
  return {
    configured: chatEnabled,
    provider: chatEnabled ? 'OpenRouter (via Supabase Edge Function)' : 'not configured',
    model: chatEnabled ? 'openai/gpt-4o-mini (cheapest OpenRouter model)' : 'not configured',
  };
}
