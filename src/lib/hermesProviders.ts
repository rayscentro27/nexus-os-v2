/**
 * Hermes provider abstraction (browser side).
 *
 * The real chat/search providers run SERVER-SIDE only (Supabase Edge Functions hold the keys);
 * the browser never contains a chat/search API key. The frontend only knows a boolean flag
 * (VITE_HERMES_CHAT_ENABLED / VITE_HERMES_SEARCH_ENABLED) saying whether the server endpoint is
 * available, and which provider to use is selected server-side by env (env-based, not hardcoded).
 *
 * If no provider is configured, the caller renders a clear "not configured" message — Hermes must
 * never fake current facts. Private data is never sent to a public provider/search.
 *
 * Model routing: the `hermesModelChat` function integrates routing policy, context packing,
 * usage logging, and fallback. The model is ONE tool — most answers use no_model.
 */

import { supabase } from './supabaseClient';
import { containsSensitive } from './dataScopes';
import { routeModel } from './hermesModelRoutingPolicy';
import { packContext } from './hermesContextPacker';
import { logModelAttempt, logModelSkipped } from './hermesModelUsageLedger';
import type { VisibleItem } from './hermesContextBridge';

const CHAT_ENABLED = (import.meta.env.VITE_HERMES_CHAT_ENABLED as string | undefined) === 'true';
const SEARCH_ENABLED = (import.meta.env.VITE_HERMES_SEARCH_ENABLED as string | undefined) === 'true';

export interface ProviderResult {
  configured: boolean;   // false → caller shows the canonical "not configured" line
  blocked?: boolean;     // true → request was refused by the firewall (do not show not-configured)
  text: string;
  source?: string;       // "local", "model", "model_fallback_local", "not_configured", "no_model_route"
  route?: string;        // routing decision route
  modelProvider?: string;
  modelName?: string;
  usageId?: string;
}

const NOT_CONFIGURED: ProviderResult = { configured: false, text: '' };

export interface HermesHistoryTurn {
  role: 'user' | 'assistant';
  content: string;
}

export interface HermesPendingActionContext {
  action_type: string;
  title: string;
  safe_summary: string;
  sensitivity: string;
  proposed_worker_type: string;
  allowed_data_scope: string[];
  forbidden_data: string[];
  hermes_visibility: string;
  requires_approval: true;
  source_assistant_message_id?: string;
  source_timestamp?: string;
}

/** Safe, internal_summary-only context the model may see (no private data). */
export interface HermesContext {
  pending?: string;     // task_type awaiting approval, or undefined
  facts?: string;       // safe counts snapshot
  report?: string;      // compact safe report summary
  taskStatus?: string;  // redacted latest task status
  pendingAction?: HermesPendingActionContext;
  history?: HermesHistoryTurn[];
}

/** Drop any context field that trips the firewall — belt-and-suspenders before it leaves the browser. */
function sanitizeContext(ctx?: HermesContext): HermesContext | undefined {
  if (!ctx) return undefined;
  const out: HermesContext = {};
  for (const k of ['pending', 'facts', 'report', 'taskStatus'] as const) {
    const v = ctx[k];
    if (v && !containsSensitive(v)) out[k] = v;
  }
  if (ctx.pendingAction) {
    const summary = String(ctx.pendingAction.safe_summary || '').slice(0, 600);
    const title = String(ctx.pendingAction.title || '').slice(0, 120);
    if (!containsSensitive(summary) && !containsSensitive(title)) {
      out.pendingAction = {
        ...ctx.pendingAction,
        title,
        safe_summary: summary,
        forbidden_data: (ctx.pendingAction.forbidden_data || []).slice(0, 12),
        allowed_data_scope: (ctx.pendingAction.allowed_data_scope || []).slice(0, 8),
      };
    }
  }
  if (Array.isArray(ctx.history)) {
    const safeTurns = ctx.history
      .slice(-10)
      .map((turn) => ({ role: turn.role, content: String(turn.content || '').slice(0, 700) }))
      .filter((turn) => turn.content.trim() && !containsSensitive(turn.content));
    let total = 0;
    out.history = [];
    for (const turn of safeTurns) {
      if (total + turn.content.length > 3500) break;
      out.history.push(turn);
      total += turn.content.length;
    }
    if (out.history.length === 0) delete out.history;
  }
  return Object.keys(out).length ? out : undefined;
}

/** Conversational reply from the real chat provider (server-side), or not-configured. */
export async function hermesChat(message: string, mode: string, context?: HermesContext): Promise<ProviderResult> {
  if (!CHAT_ENABLED || !supabase) return NOT_CONFIGURED;
  if (containsSensitive(message))
    return { configured: true, blocked: true, text: "I won't send that to an external model — it looks like private data." };
  try {
    const { data, error } = await supabase.functions.invoke('hermes-chat', {
      body: { message, mode, context: sanitizeContext(context) },
    });
    if (error || !data || data.configured === false) return NOT_CONFIGURED;
    return { configured: true, text: String(data.reply ?? '') };
  } catch {
    return NOT_CONFIGURED;
  }
}

/**
 * Routed model chat — the main entry point for Hermes model calls.
 * Goes through: routing policy → context packing → model call → usage logging → fallback.
 */
export async function hermesModelChat(
  message: string,
  options: {
    mode?: string;
    context?: HermesContext;
    visibleItems?: VisibleItem[];
    selectedItem?: VisibleItem | null;
    pageSummary?: string;
    isBackgroundJob?: boolean;
  } = {}
): Promise<ProviderResult> {
  // Step 1: Route through policy
  const decision = routeModel(message, options.isBackgroundJob);

  // NO_MODEL: answer locally, no model call
  if (decision.route === 'no_model') {
    logModelSkipped(decision.reason, 'local_answer');
    return {
      configured: false,
      text: '',
      source: 'no_model_route',
      route: 'no_model',
    };
  }

  // BLOCKED_OR_GATED: never call model
  if (decision.route === 'blocked_or_gated') {
    logModelSkipped(decision.reason, 'blocked_execution');
    return {
      configured: true,
      blocked: true,
      text: `This action is approval-gated and will not be sent to a model. ${decision.reason}`,
      source: 'blocked_or_gated',
      route: 'blocked_or_gated',
    };
  }

  // Step 2: Pack context within budget
  const packet = packContext(message, decision.route, {
    visibleItems: options.visibleItems as any,
    selectedItem: options.selectedItem as any,
    pageSummary: options.pageSummary,
    isBackgroundJob: options.isBackgroundJob,
  });

  // Step 3: Check if provider is available
  if (!CHAT_ENABLED || !supabase) {
    logModelAttempt({
      route: decision.route,
      modelProvider: 'none',
      modelName: 'none',
      promptType: decision.route,
      estimatedInputTokens: packet.estimatedInputTokens,
      estimatedOutputTokens: 0,
      contextSources: packet.sourcesIncluded,
      wasModelCalled: false,
      skippedReason: 'Provider not configured',
      fallbackUsed: '',
      costEstimateAvailable: false,
      error: '',
      durationMs: 0,
    });
    return {
      configured: false,
      text: '',
      source: 'not_configured',
      route: decision.route,
    };
  }

  // Step 4: Call model via server-side Edge Function
  const startTime = Date.now();
  const contextPayload: HermesContext = {
    ...options.context,
    facts: packet.compactContext || options.context?.facts,
  };

  try {
    const result = await hermesChat(message, options.mode || 'conversation', contextPayload);
    const durationMs = Date.now() - startTime;

    if (result.blocked) {
      logModelAttempt({
        route: decision.route,
        modelProvider: 'firewall',
        modelName: 'blocked',
        promptType: decision.route,
        estimatedInputTokens: packet.estimatedInputTokens,
        estimatedOutputTokens: 0,
        contextSources: packet.sourcesIncluded,
        wasModelCalled: false,
        skippedReason: 'Blocked by firewall',
        fallbackUsed: '',
        costEstimateAvailable: false,
        error: '',
        durationMs,
      });
      return result;
    }

    if (!result.configured || !result.text) {
      // Model unavailable — fallback to local
      logModelAttempt({
        route: decision.route,
        modelProvider: 'unknown',
        modelName: 'unavailable',
        promptType: decision.route,
        estimatedInputTokens: packet.estimatedInputTokens,
        estimatedOutputTokens: 0,
        contextSources: packet.sourcesIncluded,
        wasModelCalled: false,
        skippedReason: 'Model unavailable',
        fallbackUsed: 'local',
        costEstimateAvailable: false,
        error: 'Model returned empty or not configured',
        durationMs,
      });
      return {
        configured: true,
        text: 'Model unavailable, used local reasoning.',
        source: 'model_fallback_local',
        route: decision.route,
      };
    }

    // Success
    logModelAttempt({
      route: decision.route,
      modelProvider: 'supabase_edge_function',
      modelName: 'hermes-chat',
      promptType: decision.route,
      estimatedInputTokens: packet.estimatedInputTokens,
      estimatedOutputTokens: Math.ceil(result.text.length / 4),
      contextSources: packet.sourcesIncluded,
      wasModelCalled: true,
      skippedReason: '',
      fallbackUsed: '',
      costEstimateAvailable: false,
      error: '',
      durationMs,
    });

    return {
      configured: true,
      text: result.text,
      source: 'model',
      route: decision.route,
      modelProvider: 'supabase_edge_function',
      modelName: 'hermes-chat',
    };
  } catch (e) {
    const durationMs = Date.now() - startTime;
    logModelAttempt({
      route: decision.route,
      modelProvider: 'error',
      modelName: 'error',
      promptType: decision.route,
      estimatedInputTokens: packet.estimatedInputTokens,
      estimatedOutputTokens: 0,
      contextSources: packet.sourcesIncluded,
      wasModelCalled: false,
      skippedReason: 'Error',
      fallbackUsed: 'local',
      costEstimateAvailable: false,
      error: String(e).slice(0, 200),
      durationMs,
    });
    return {
      configured: true,
      text: 'Model call failed, used local reasoning.',
      source: 'model_fallback_local',
      route: decision.route,
    };
  }
}

/** Public web search (server-side) for public questions only, or not-configured. */
export async function publicSearch(query: string): Promise<ProviderResult> {
  if (!SEARCH_ENABLED || !supabase) return NOT_CONFIGURED;
  if (containsSensitive(query))
    return { configured: true, blocked: true, text: "That looks like private data — I won't search public sources for it." };
  try {
    const { data, error } = await supabase.functions.invoke('hermes-search', { body: { query } });
    if (error || !data || data.configured === false) return NOT_CONFIGURED;
    return { configured: true, text: String(data.summary ?? '') };
  } catch {
    return NOT_CONFIGURED;
  }
}

export const CHAT_NOT_CONFIGURED_MSG = 'Hermes chat provider is not configured yet.';
export const SEARCH_NOT_CONFIGURED_MSG = 'Public search is not configured yet, so I cannot verify current information.';
