/**
 * Hermes Reasoning Engine — local reasoning before model call.
 *
 * Decides:
 *  1. Can I answer this from context alone? → Build answer locally
 *  2. Do I have enough context to answer confidently? → Answer with what I know
 *  3. Should I ask for clarification? → Only when NO context exists at all
 *  4. Does this genuinely need a model? → Route to model with reasoning plan
 *
 * The model is a TOOL, not a crutch. Most answers should come from local reasoning.
 */

import { getLastListedItems, getLastRankedList, getLastReferencedItem, getLastSupabaseQueryResult } from './hermesConversationState';
import type { RouteDecision } from './hermesRouteDecision';

export type ReasoningDecision = 'answer-locally' | 'answer-with-context' | 'ask-clarification' | 'route-to-model';

export interface ReasoningPlan {
  decision: ReasoningDecision;
  confidence: 'high' | 'medium' | 'low';
  reasoning: string;
  localAnswer?: string;
  contextUsed?: string[];
  modelTask?: string;
  clarificationQuestion?: string;
  memoryCandidateFound?: boolean;
  memoryUsed?: boolean;
  memoryRejected?: boolean;
  memoryRejectionReason?: string | null;
  selectedMemoryItem?: string | null;
}

/** Get what context is available. */
function getAvailableContext(shouldUsePriorMemory = true): string[] {
  const ctx: string[] = [];
  if (!shouldUsePriorMemory) return ctx;
  if (getLastListedItems().length > 0) ctx.push(`lastListedItems(${getLastListedItems().length})`);
  if (getLastRankedList().length > 0) ctx.push(`lastRankedList(${getLastRankedList().length})`);
  if (getLastReferencedItem()) ctx.push(`lastReferencedItem(${getLastReferencedItem()!.title})`);
  if (getLastSupabaseQueryResult()) ctx.push(`lastSupabaseQuery(${getLastSupabaseQueryResult()!.table})`);
  return ctx;
}

/**
 * Core reasoning function — decides HOW to answer before deciding WHAT to answer.
 */
export function reasonAboutMessage(
  message: string,
  pageContext: { route: string; pageId: string; visibleItems: unknown[] } | null,
  intentRoute: string,
  modelRoute: string,
  memoryBoundary: { shouldUsePriorMemory: boolean; reason: string } = { shouldUsePriorMemory: true, reason: 'legacy caller did not provide a boundary' },
): ReasoningPlan {
  const lower = message.toLowerCase();
  if (/\b(where\s+did.*(?:answer|response)|what\s+source|did.*(?:supabase|database|model|ai)|what\s+domain\s+did|what\s+route\s+did|strategic reasoning)\b/i.test(lower)) {
    return { decision: 'answer-locally', confidence: 'high', reasoning: 'Trace/source priority overrides memory and domain reasoning.', contextUsed: [] };
  }
  const memoryCandidateFound = getAvailableContext(true).length > 0;
  const context = getAvailableContext(memoryBoundary.shouldUsePriorMemory);
  const hasCtx = context.length > 0;
  const memoryDiagnostics = {
    memoryCandidateFound,
    memoryUsed: memoryBoundary.shouldUsePriorMemory && memoryCandidateFound,
    memoryRejected: !memoryBoundary.shouldUsePriorMemory && memoryCandidateFound,
    memoryRejectionReason: !memoryBoundary.shouldUsePriorMemory ? memoryBoundary.reason : null,
    selectedMemoryItem: memoryBoundary.shouldUsePriorMemory ? getLastReferencedItem()?.title || null : null,
  };
  const hasPage = Boolean(pageContext?.visibleItems?.length);

  // ── Follow-up references: always answer locally if we have context ──
  if (/^(?:number|#|option)\s*\d+$|^(?:that|this|it|the\s+one)$/i.test(lower.trim())) {
    if (hasCtx || intentRoute === 'page_context') {
      return {
        decision: 'answer-locally',
        confidence: 'high',
        reasoning: 'Follow-up reference with conversation context available.',
        contextUsed: context, ...memoryDiagnostics,
      };
    }
    return {
      decision: 'ask-clarification',
      confidence: 'low',
      reasoning: 'Follow-up reference but no conversation context exists.',
      clarificationQuestion: 'I don\'t have context from a previous listing. What item are you referring to?', ...memoryDiagnostics,
    };
  }

  // Explicit page context takes precedence over the generic no-model rule.
  if (pageContext && intentRoute === 'page_context') {
    return {
      decision: 'answer-with-context', confidence: 'high',
      reasoning: 'Page context is available. Can answer from visible items and page state.',
      contextUsed: [...context, 'pageContext'], ...memoryDiagnostics,
    };
  }

  // ── Section status / process / cost / activity / CEO summary → always local ──
  if (modelRoute === 'no_model') {
    return {
      decision: 'answer-locally',
      confidence: 'high',
      reasoning: 'This question is answerable from local context, reports, or registry without model reasoning.',
      contextUsed: context,
    };
  }

  // ── Capability questions → always local ──
  if (intentRoute === 'capability_status') {
    return {
      decision: 'answer-locally',
      confidence: 'high',
      reasoning: 'Capability questions are answered from the capability status module, not the model.',
      contextUsed: context,
    };
  }

  // ── Casual / personality → always local ──
  if (intentRoute === 'casual') {
    return {
      decision: 'answer-locally',
      confidence: 'high',
      reasoning: 'Casual conversation handled by conversation brain.',
      contextUsed: context,
    };
  }

  // ── Operations / reports / memory → local first ──
  if (['operations', 'reports_memory'].includes(intentRoute)) {
    return {
      decision: 'answer-locally',
      confidence: 'high',
      reasoning: 'Operations and memory questions are answerable from local reports and activity journal.',
      contextUsed: context,
    };
  }

  // ── Page context questions ──
  if (intentRoute === 'page_context') {
    if (hasPage) {
      return {
        decision: 'answer-with-context',
        confidence: 'high',
        reasoning: 'Page context is available. Can answer from visible items and page state.',
        contextUsed: [...context, 'pageContext'],
      };
    }
    // Even without explicit page context, if we have conversation context, don't ask clarification
    if (hasCtx) {
      return {
        decision: 'answer-with-context',
        confidence: 'medium',
        reasoning: 'No explicit page context, but conversation context may cover this.',
        contextUsed: context,
      };
    }
  }

  // A model-routed ambiguous strategy request with no context is the narrow case
  // where clarification is appropriate.
  if (/\b(strategy|plan|roadmap)\b/i.test(lower) && !hasCtx && !hasPage && modelRoute !== 'no_model') {
    return {
      decision: 'ask-clarification', confidence: 'low',
      reasoning: 'Strategic request has no target, page context, or conversation entity.',
      clarificationQuestion: buildClarificationQuestion(message),
    };
  }

  // ── Business strategy / opportunity questions ──
  if (/\b(business|start|opportunity|monetization|revenue|strategy|30\s*days|what can i do|how to make money)\b/i.test(lower)) {
    if (hasCtx) {
      return {
        decision: 'answer-with-context',
        confidence: 'medium',
        reasoning: 'Business strategy question with conversation context. Can reason from available data.',
        contextUsed: context,
      };
    }
    // Don't ask clarification — reason from available page/report context
    return {
      decision: 'answer-with-context',
      confidence: 'medium',
      reasoning: 'Business strategy question. Reasoning from page context and available reports, not asking clarification.',
      contextUsed: context,
    };
  }

  // ── Supabase queries → check state first ──
  if (intentRoute === 'nexus_supabase') {
    if (hasCtx) {
      return {
        decision: 'answer-with-context',
        confidence: 'high',
        reasoning: 'Supabase query with conversation context. Can build on previous results.',
        contextUsed: context,
      };
    }
  }

  // ── Questions with page context → answer with context ──
  if (hasPage || hasCtx) {
    return {
      decision: 'answer-with-context',
      confidence: 'medium',
      reasoning: 'Context available from page or conversation. Building answer from what is known.',
      contextUsed: context,
    };
  }

  // ── Model-worthy questions with no context ──
  if (modelRoute === 'primary_model' || modelRoute === 'cheap_model') {
    // Only ask clarification when we truly have NO context at all
    if (!hasCtx && !hasPage) {
      return {
        decision: 'ask-clarification',
        confidence: 'low',
        reasoning: 'Strategic question with no conversation or page context. Need a specific target to reason about.',
        clarificationQuestion: buildClarificationQuestion(message),
      };
    }
    return {
      decision: 'answer-with-context',
      confidence: 'medium',
      reasoning: 'Strategic question with some context. Building best answer from available information.',
      contextUsed: context,
    };
  }

  // ── Default: try to answer with what we have ──
  if (hasCtx || hasPage) {
    return {
      decision: 'answer-with-context',
      confidence: 'low',
      reasoning: 'Limited context but attempting to answer rather than asking clarification.',
      contextUsed: context,
    };
  }

  return {
    decision: 'ask-clarification',
    confidence: 'low',
    reasoning: 'No context available. Need clarification to provide a useful answer.',
    clarificationQuestion: buildClarificationQuestion(message),
  };
}

/** Build a context-aware clarification question instead of a generic one. */
function buildClarificationQuestion(message: string): string {
  const lower = message.toLowerCase();

  if (/business|start|opportunity|money|revenue/.test(lower)) {
    return 'I can analyze business opportunities, but I need to know — are you asking about the opportunities already listed in your Nexus data, or are you looking for new ideas outside what is currently tracked?';
  }

  if (/strategy|plan|roadmap/.test(lower)) {
    return 'I can reason about strategy, but need a specific target — which section, offer, or goal should I focus the strategy on?';
  }

  if (/recommend|advice|which/.test(lower)) {
    return 'I can give a recommendation, but need to know — which items are you comparing? Are these items from the current page, or from Supabase data?';
  }

  return 'I want to give you a useful answer, not a generic one. Can you tell me which specific page, section, or data set you are asking about?';
}

/** RouteDecision policy adapter used by the shared brain pipeline. */
export function reasonFromRouteDecision(decision: RouteDecision, contextSummary: Record<string, unknown>): ReasoningPlan {
  if (decision.modelPolicy === 'required') return { decision: 'route-to-model', confidence: 'high', reasoning: decision.reason, contextUsed: Object.keys(contextSummary).filter(key => Boolean(contextSummary[key])) };
  if (decision.activationLevel >= 2) return {
    decision: 'answer-with-context', confidence: decision.confidence >= .8 ? 'high' : 'medium', reasoning: decision.reason,
    contextUsed: Object.keys(contextSummary).filter(key => Boolean(contextSummary[key])),
    memoryUsed: Boolean(contextSummary.selectionMemoryAttached || contextSummary.longTermMemoryAttached || contextSummary.lastTraceAttached),
    memoryRejected: !contextSummary.selectionMemoryAttached && decision.memoryPolicy === 'none',
    memoryRejectionReason: decision.memoryPolicy === 'none' ? 'RouteDecision forbids selection memory.' : null,
  };
  return { decision: 'answer-locally', confidence: decision.confidence >= .8 ? 'high' : 'medium', reasoning: decision.reason, contextUsed: Object.keys(contextSummary).filter(key => Boolean(contextSummary[key])) };
}
