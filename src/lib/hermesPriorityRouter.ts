import { classifyHermesDomain } from './hermesDomainClassifier';
import { classifyTraceQuestion } from './hermesTraceQuestionHandler';
import { isRevenueStrategyQuestion } from './hermesRevenueReasoner';
import { createRouteDecision, type RouteDecision } from './hermesRouteDecision';
import type { SelectionMemory } from './hermesMemoryStores';

export interface PriorityRouterInput { message: string; currentPage?: string | null; previousDomain?: string | null; selectionMemory: SelectionMemory; }

const decision = (input: Parameters<typeof createRouteDecision>[0]) => createRouteDecision(input);

function hasSelectionReference(message: string, memory: SelectionMemory): boolean {
  if (/\b(that(?: one)?|this(?: one)?|it|those|number\s*\d+|option\s*\d+|the\s+(?:first|second|third)|pick one|which one|how do (?:we|i) implement it|continue|go deeper)\b/i.test(message)) return true;
  const normalized = message.toLowerCase().replace(/[$]/g, '').replace(/[^a-z0-9]+/g, ' ');
  return [memory.lastSelectedItem, memory.lastRecommendation, ...memory.lastRankedList, ...memory.lastList].filter(Boolean).some(item => normalized.includes(item!.title.toLowerCase().replace(/[$]/g, '').replace(/[^a-z0-9]+/g, ' ').replace(/^\d+\s+/, '')));
}

export function routeHermesPriority(input: PriorityRouterInput): RouteDecision {
  const message = input.message.trim();
  const lower = message.toLowerCase();
  const domain = classifyHermesDomain(message, input.currentPage, input.previousDomain).domain;
  const risky = /\b(place|execute|open|make)\b.*\b(?:trade|position)\b|\b(?:publish|send|charge|buy|sell|deploy|delete|truncate|run shell|start scheduler|submit (?:a )?dispute)\b/i.test(lower);
  if (risky) return decision({ routeId: 'safety_gate', activationLevel: 0, domain, intent: 'risky_execution', memoryPolicy: 'none', retrievalPolicy: 'none', modelPolicy: 'forbidden', diagnosticsPolicy: 'hidden', actionPolicy: 'blocked', reason: 'A state-changing or live/funded execution request is blocked before context retrieval.' });

  if (classifyTraceQuestion(message)) return decision({ routeId: 'trace_source_meta', activationLevel: 1, domain: 'routing_trace', intent: 'source_question', memoryPolicy: 'last_trace_only', retrievalPolicy: 'none', modelPolicy: 'forbidden', diagnosticsPolicy: 'show_summary', actionPolicy: 'none', reason: 'Trace/source questions inspect only the last non-trace route.' });

  if (/\b(tokens?|usage ledger|what model did|model call|answer cost|what did .* cost|cost of (?:that|the) answer)\b/i.test(lower)) return decision({ routeId: 'cost_model_usage_status', activationLevel: 1, domain: 'model_cost_status', intent: 'usage_status', memoryPolicy: 'last_trace_only', retrievalPolicy: 'none', modelPolicy: 'forbidden', diagnosticsPolicy: 'show_summary', actionPolicy: 'none', reason: 'Cost and model-use status are deterministic trace/ledger questions.' });

  if (domain === 'casual_identity') return decision({ routeId: 'casual_identity', activationLevel: 1, domain, intent: 'conversation', memoryPolicy: 'none', retrievalPolicy: 'none', modelPolicy: 'forbidden', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'Casual and identity questions require no operational context.' });

  if (/\b(what can you do|capabilit|web search|connected to|database status|model status)\b/i.test(lower)) return decision({ routeId: 'capability_status', activationLevel: 1, domain: 'model_cost_status', intent: 'capability_status', memoryPolicy: 'none', retrievalPolicy: 'none', modelPolicy: 'forbidden', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'Capability answers come from the local capability registry.' });

  if (['settings', 'reports', 'tools_cli', 'system_health', 'automation', 'research_youtube'].includes(domain) && /\b(status|running|missing|what|which|list|show|have|changed|reports?|settings?|process)\b/i.test(lower)) return decision({ routeId: 'process_settings_reports_status', activationLevel: 1, domain, intent: /\b(list|what|which|show|have)\b/.test(lower) ? 'inventory_question' : 'status_question', memoryPolicy: 'none', retrievalPolicy: 'local_reports', modelPolicy: 'forbidden', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'Process/settings/report status uses local evidence without broad memory or model calls.' });
  if (domain === 'trading' && /\b(is|status|running|active|live|last test|last prove)\b/i.test(lower)) return decision({ routeId: 'process_settings_reports_status', activationLevel: 1, domain, intent: 'status_question', memoryPolicy: 'none', retrievalPolicy: 'local_reports', modelPolicy: 'forbidden', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'Trading status is answered from local proof reports without model or selection memory.' });

  if (/\b(create|prepare|queue|add)\b.*\b(ray review|review card|task|dry[- ]?run)\b/i.test(lower)) return decision({ routeId: 'approval_action_prepare', activationLevel: 6, domain: domain === 'unknown' ? input.selectionMemory.activeDomain || 'unknown' : domain, intent: 'prepare_approval_task', memoryPolicy: 'selection_only', retrievalPolicy: 'supabase_then_static_fallback', modelPolicy: 'forbidden', diagnosticsPolicy: 'hidden', actionPolicy: 'approval_required', reason: 'Only a non-executed approval draft may be prepared; selection memory can resolve its target.' });

  const inventory = /\b(what|which|list|show)\b.*\b(strategies|opportunities|approvals|clients|reports|offers|rows|drafts|records)\b|\bwhat\b.*\b(?:do we have|are available|exist)\b/i.test(lower);
  if (domain !== 'unknown' && inventory) {
    const local = ['trading', 'reports', 'settings', 'marketing'].includes(domain);
    return decision({ routeId: 'explicit_domain_retrieval', activationLevel: 2, domain, intent: 'inventory_question', memoryPolicy: 'none', retrievalPolicy: local ? 'local_reports' : 'supabase_then_static_fallback', modelPolicy: 'forbidden', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: `Inventory questions retrieve ${local ? 'local records/reports' : 'Supabase records with an honest static fallback'} before reasoning.` });
  }

  if (hasSelectionReference(message, input.selectionMemory)) return decision({ routeId: 'memory_followup', activationLevel: 3, domain: input.selectionMemory.activeDomain || domain, intent: 'resolve_previous_selection', memoryPolicy: 'selection_only', retrievalPolicy: 'supabase_then_static_fallback', modelPolicy: 'allowed_if_needed', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'An explicit follow-up marker or named selection item permits selection memory.' });

  if (isRevenueStrategyQuestion(message)) return decision({ routeId: 'revenue_reasoning', activationLevel: 4, domain: 'monetization', intent: 'revenue_strategy', memoryPolicy: 'long_term_allowed', retrievalPolicy: 'supabase_then_static_fallback', modelPolicy: 'allowed_if_needed', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'Revenue strategy uses long-term business context and opportunity retrieval, never stale selected items.' });

  if (domain !== 'unknown' || /\b(recommend|prioritize|plan|implement|strategy|what should)\b/i.test(lower)) return decision({ routeId: 'local_reasoning', activationLevel: 4, domain, intent: 'domain_reasoning', memoryPolicy: domain === 'business_opportunity' || domain === 'monetization' ? 'long_term_allowed' : 'none', retrievalPolicy: ['trading', 'reports', 'research_youtube'].includes(domain) ? 'local_reports' : 'static_fallback_allowed', modelPolicy: 'allowed_if_needed', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'The explicit domain can be answered locally without unrestricted memory.' });

  if (/\b(deep synthesis|comprehensive analysis|draft|compose|polished)\b/i.test(lower)) return decision({ routeId: 'model_reasoning', activationLevel: 5, domain, intent: 'deep_synthesis', memoryPolicy: 'long_term_allowed', retrievalPolicy: 'local_reports_then_supabase', modelPolicy: 'required', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'The request explicitly needs synthesis beyond deterministic local handlers.' });

  return decision({ routeId: 'fallback_clarification', activationLevel: 1, domain: 'unknown', intent: 'clarification', memoryPolicy: 'none', retrievalPolicy: 'none', modelPolicy: 'forbidden', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'No safe domain, entity, or retrieval target was identified.' });
}
