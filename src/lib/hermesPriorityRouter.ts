import { classifyHermesDomain } from './hermesDomainClassifier';
import { classifyTraceQuestion } from './hermesTraceQuestionHandler';
import { isRevenueStrategyQuestion } from './hermesRevenueReasoner';
import { createRouteDecision, type RouteDecision } from './hermesRouteDecision';
import type { SelectionMemory } from './hermesMemoryStores';
import { isCasualCommonQuestion, isGeneralAdvisorQuestion, isGeneralProjectPlanningQuestion, isHumanExperienceQuestion, isNexusBuildPlanningQuestion, isProductEntityAdvisorQuestion } from './hermesCommonConversation';
import { classifyActivityStatusQuestion } from './hermesActivityStatus';
import { getAdvisoryContinuity, isAdvisoryFollowUpQuestion } from './hermesAdvisoryContinuity';
import { getFallbackContinuity, isFallbackOptionReply } from './hermesFallbackContinuity';
import { normalizeHermesRoutingInput } from './hermesInputNormalization';
import { isOpportunityAwareRecommendationQuestion, isPhysicalWorldAdvisoryQuestion } from './hermesOpportunityAdvisor';

export interface PriorityRouterInput { message: string; currentPage?: string | null; previousDomain?: string | null; selectionMemory: SelectionMemory; }

const decision = (input: Parameters<typeof createRouteDecision>[0]) => createRouteDecision(input);

function classifyLiveRecordInventory(message: string): { domain: string; intent: string } | null {
  const lower = message.toLowerCase();
  if (/\b(what|which|show|list|pending|anything|waiting)\b.*\b(approvals?|task requests?|ray review|approval cards?|review cards?)\b|\bwhat needs my approval\b|\bwhat is waiting for review\b/.test(lower)) return { domain: 'approvals', intent: 'approval_inventory' };
  if (/\b(what|which|show|list)\b.*\b(business opportunities|monetization opportunities|monetization offers)\b|\bwhat business opportunities are available\b/.test(lower)) return { domain: /monetization/.test(lower) ? 'monetization' : 'business_opportunity', intent: 'inventory_question' };
  if (/\b(?:show|list) (?:my |the |all )?(?:clients?|client profiles?|customers?)\b|\bwhat (?:clients?|client profiles?|customers?) (?:do we have|are available|exist)\b/.test(lower)) return { domain: 'clients', intent: 'inventory_question' };
  if (/\b(what|which|show|list)\b.*\b(research sources?|research rows?)\b|\bwhat research (?:rows|sources) do we have\b/.test(lower)) return { domain: 'research_youtube', intent: 'inventory_question' };
  return null;
}

function hasSelectionReference(message: string, memory: SelectionMemory): boolean {
  if (isAdvisoryFollowUpQuestion(message) && !/\b(number\s*\d+|option\s*\d+|the\s+(?:first|second|third)|that one|this one|how do (?:we|i) implement|create .*card)\b/i.test(message)) return false;
  if (/\b(that one|this one|those|number\s*\d+|option\s*\d+|the\s+(?:first|second|third)|pick one|which one|how do (?:we|i) implement (?:it|that)|create (?:a )?(?:ray review )?card for (?:that|it)|continue|go deeper)\b/i.test(message)) return true;
  const normalized = message.toLowerCase().replace(/[$]/g, '').replace(/[^a-z0-9]+/g, ' ');
  return [memory.lastSelectedItem, memory.lastRecommendation, ...memory.lastRankedList, ...memory.lastList].filter(Boolean).some(item => normalized.includes(item!.title.toLowerCase().replace(/[$]/g, '').replace(/[^a-z0-9]+/g, ' ').replace(/^\d+\s+/, '')));
}

export function routeHermesPriority(input: PriorityRouterInput): RouteDecision {
  const message = normalizeHermesRoutingInput(input.message.trim());
  const lower = message.toLowerCase();
  const domainResult = classifyHermesDomain(message, input.currentPage, input.previousDomain);
  const domain = domainResult.domain;
  const advisory = getAdvisoryContinuity();
  const fallback = getFallbackContinuity();
  const scheduling = /\b(schedule|set up|create)\b.*\b(report|summary|reminder)|\b(?:weekly|daily|recurring)\b.*\b(report|summary)|\b(?:remind me|automate this report|run this report every|send me .* every)\b/i.test(lower);
  const risky = /\b(place|execute|open|make)\b.*\b(?:trade|position)\b|\b(?:publish|charge|deploy|delete|truncate|run shell|submit (?:a )?dispute)\b|\bsend\b(?!.*\bevery\b)|\b(?:buy|sell)\b.*\b(?:asset|stock|crypto|security|position|trade)\b|\bstart\b.*\bscheduler\b/i.test(lower);
  if (risky) return decision({ routeId: 'safety_gate', activationLevel: 0, domain, intent: 'risky_execution', memoryPolicy: 'none', retrievalPolicy: 'none', modelPolicy: 'forbidden', diagnosticsPolicy: 'hidden', actionPolicy: 'blocked', reason: 'A state-changing or live/funded execution request is blocked before context retrieval.' });

  const traceQuestion = classifyTraceQuestion(message);
  if (traceQuestion) return decision({ routeId: traceQuestion.kind === 'model' ? 'cost_model_usage_status' : 'trace_source_meta', activationLevel: 1, domain: traceQuestion.kind === 'model' ? 'model_cost_status' : 'routing_trace', intent: traceQuestion.kind === 'source_reason' ? 'source_reason_followup' : traceQuestion.kind === 'model' ? 'usage_status' : 'source_question', memoryPolicy: 'last_trace_only', retrievalPolicy: 'none', modelPolicy: 'forbidden', diagnosticsPolicy: 'show_summary', actionPolicy: 'none', reason: 'Trace/source/model-usage questions inspect only the last non-trace route.' });

  if (/\b(tokens?|usage ledger|what model (?:did|do|are|is|was)|model call|answer cost|what did .* cost|cost of (?:that|the) answer|(?:openrouter|cheapest|primary|fallback|gpt|ai|llm|reasoning) model)\b/i.test(lower)) return decision({ routeId: 'cost_model_usage_status', activationLevel: 1, domain: 'model_cost_status', intent: 'usage_status', memoryPolicy: 'last_trace_only', retrievalPolicy: 'none', modelPolicy: 'forbidden', diagnosticsPolicy: 'show_summary', actionPolicy: 'none', reason: 'Cost and model-use status are deterministic trace/ledger questions.' });

  const liveInventory = classifyLiveRecordInventory(message);
  if (liveInventory) return decision({ routeId: 'explicit_domain_retrieval', activationLevel: 2, domain: liveInventory.domain, intent: liveInventory.intent, memoryPolicy: 'none', retrievalPolicy: 'supabase_then_static_fallback', modelPolicy: 'forbidden', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'Explicit live-record inventory is retrieved before casual, advisor, opportunity, memory, and fallback routes.' });

  if (scheduling) return decision({ routeId: 'schedule_action_prepare', activationLevel: 6, domain: 'automation', intent: 'prepare_scheduled_report', memoryPolicy: /\b(that|this) report\b/i.test(lower) ? 'selection_only' : 'none', retrievalPolicy: 'local_reports', modelPolicy: 'forbidden', diagnosticsPolicy: 'hidden', actionPolicy: 'approval_required', reason: 'Scheduling is approval-gated; only a draft request may be prepared and no scheduler may be activated.' });

  if (/\b(?:start|begin)\b.*\b(?:build|building|implement|implementation)\b|\bcreate (?:the )?(?:crm|feature) (?:files|task)\b|\bcreate files for (?:the )?(?:crm|feature)\b/i.test(lower)) return decision({ routeId: 'approval_action_prepare', activationLevel: 6, domain: 'nexus_product_build', intent: 'prepare_implementation_task', memoryPolicy: 'none', retrievalPolicy: 'local_reports', modelPolicy: 'forbidden', diagnosticsPolicy: 'hidden', actionPolicy: 'approval_required', reason: 'Starting implementation requires an explicit reviewed task; this route performs no code, file, or deployment action.' });

  const activityIntent = classifyActivityStatusQuestion(message);
  if (activityIntent && !(advisory && isAdvisoryFollowUpQuestion(message))) return decision({ routeId: 'process_activity_status', activationLevel: 1, domain: 'activity_summary', intent: activityIntent, memoryPolicy: 'none', retrievalPolicy: 'local_reports', modelPolicy: 'forbidden', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'Work continuation and completed-work summaries use local activity/report evidence without selection memory or model calls.' });

  if (fallback && isFallbackOptionReply(message)) return decision({ routeId: 'fallback_continuation', activationLevel: 4, domain: /nexus/i.test(message) ? 'nexus_product_build' : /trading/i.test(message) ? 'trading' : /credit|funding|goclear|apex/i.test(message) ? 'credit_funding' : 'general_project', intent: 'resume_fallback_clarification', memoryPolicy: 'long_term_allowed', retrievalPolicy: 'none', modelPolicy: 'allowed_if_needed', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'The user selected an offered clarification option, so Hermes resumes the stored unresolved question instead of repeating fallback.' });

  if (isCasualCommonQuestion(message)) return decision({ routeId: 'casual_common', activationLevel: 1, domain: 'general_conversation', intent: isHumanExperienceQuestion(message) ? 'human_experience_question' : /\b(favou?rite|joke|sky|pizza|movie|music|ice cream)\b/i.test(lower) ? 'casual_or_common_question' : 'greeting_or_light_check_in', memoryPolicy: 'none', retrievalPolicy: 'none', modelPolicy: 'forbidden', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'Common conversation needs no Nexus records, selection memory, or model call.' });

  if (isNexusBuildPlanningQuestion(message)) return decision({ routeId: 'nexus_build_planning', activationLevel: 4, domain: 'nexus_product_build', intent: 'build_planning', memoryPolicy: 'long_term_allowed', retrievalPolicy: 'local_reports', modelPolicy: 'allowed_if_needed', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'A Nexus product request is planning only until an explicit reviewed implementation task is requested.' });

  if (isGeneralProjectPlanningQuestion(message)) return decision({ routeId: 'general_project_planning', activationLevel: 4, domain: 'general_project', intent: 'project_planning_or_feasibility', memoryPolicy: 'long_term_allowed', retrievalPolicy: 'none', modelPolicy: 'allowed_if_needed', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'A general project question can be planned without claiming physical work, current research, or execution.' });

  if (isProductEntityAdvisorQuestion(message) && (!domainResult.explicit || domain === 'casual_identity')) return decision({ routeId: 'general_advisor', activationLevel: 4, domain: /\b(?:tesla\s+)?model\s+(?:3|s|x|y)\b/i.test(message) ? 'vehicle_recommendation' : 'general_advice', intent: 'product_recommendation', memoryPolicy: 'long_term_allowed', retrievalPolicy: 'none', modelPolicy: 'allowed_if_needed', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'A product/entity opinion uses general advisory reasoning, not AI model status or stale selection memory.' });

  if (isGeneralAdvisorQuestion(message) && !(input.selectionMemory.lastList.length && /\bwhich one\b/i.test(lower))) return decision({ routeId: 'general_advisor', activationLevel: 4, domain: 'general_advice', intent: 'general_recommendation', memoryPolicy: 'long_term_allowed', retrievalPolicy: 'none', modelPolicy: 'allowed_if_needed', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'General advice uses plain reasoning without stale selection memory or Nexus retrieval.' });

  if (isOpportunityAwareRecommendationQuestion(message) && !(advisory && isAdvisoryFollowUpQuestion(message))) return decision({ routeId: 'opportunity_aware_recommendation', activationLevel: 4, domain: 'opportunity_advisor', intent: isPhysicalWorldAdvisoryQuestion(message) ? 'physical_world_advisory' : 'value_added_recommendation', memoryPolicy: 'long_term_allowed', retrievalPolicy: 'none', modelPolicy: 'allowed_if_needed', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'A local-first recommendation can combine the direct decision, opportunity angle, low-cost validation, and risk checks without live data or a required model call.' });

  if (domain === 'casual_identity') return decision({ routeId: 'casual_identity', activationLevel: 1, domain, intent: 'conversation', memoryPolicy: 'none', retrievalPolicy: 'none', modelPolicy: 'forbidden', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'Casual and identity questions require no operational context.' });

  if (/\b(what can you do|capabilit|web search|connected to|database status|model status)\b/i.test(lower)) return decision({ routeId: 'capability_status', activationLevel: 1, domain: 'model_cost_status', intent: 'capability_status', memoryPolicy: 'none', retrievalPolicy: 'none', modelPolicy: 'forbidden', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'Capability answers come from the local capability registry.' });

  if (['settings', 'reports', 'tools_cli', 'system_health', 'automation', 'research_youtube'].includes(domain) && /\b(status|running|missing|what|which|list|show|have|changed|reports?|settings?|process)\b/i.test(lower)) return decision({ routeId: 'process_settings_reports_status', activationLevel: 1, domain, intent: /\b(list|what|which|show|have)\b/.test(lower) ? 'inventory_question' : 'status_question', memoryPolicy: 'none', retrievalPolicy: 'local_reports', modelPolicy: 'forbidden', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'Process/settings/report status uses local evidence without broad memory or model calls.' });
  if (domain === 'trading' && /\b(is|status|running|active|live|last test|last prove)\b/i.test(lower)) return decision({ routeId: 'process_settings_reports_status', activationLevel: 1, domain, intent: 'status_question', memoryPolicy: 'none', retrievalPolicy: 'local_reports', modelPolicy: 'forbidden', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'Trading status is answered from local proof reports without model or selection memory.' });

  if (/\b(create|prepare|queue|add)\b.*\b(ray review|review card|task|dry[- ]?run)\b/i.test(lower)) return decision({ routeId: 'approval_action_prepare', activationLevel: 6, domain: domain === 'unknown' ? input.selectionMemory.activeDomain || 'unknown' : domain, intent: 'prepare_approval_task', memoryPolicy: 'selection_only', retrievalPolicy: 'supabase_then_static_fallback', modelPolicy: 'forbidden', diagnosticsPolicy: 'hidden', actionPolicy: 'approval_required', reason: 'Only a non-executed approval draft may be prepared; selection memory can resolve its target.' });

  if (/\b(delegate|handoff|send|schedule|create|approve|move|assign|prepare|draft|start)\b.*\b(this|that|it|that one|this one)\b/i.test(lower)) return decision({ routeId: 'approval_action_prepare', activationLevel: 6, domain: input.selectionMemory.activeDomain || domain, intent: 'unresolved_action_reference', memoryPolicy: 'selection_only', retrievalPolicy: 'none', modelPolicy: 'forbidden', diagnosticsPolicy: 'hidden', actionPolicy: 'approval_required', reason: 'A vague action reference may prepare a draft only when selection memory resolves an eligible target.' });

  const inventory = /\b(what|which|list|show)\b.*\b(strategies|opportunities|approvals|clients|reports|offers|rows|drafts|records)\b|\bwhat\b.*\b(?:do we have|are available|exist)\b/i.test(lower);
  if (domain !== 'unknown' && inventory) {
    const local = ['trading', 'reports', 'settings', 'marketing'].includes(domain);
    return decision({ routeId: 'explicit_domain_retrieval', activationLevel: 2, domain, intent: 'inventory_question', memoryPolicy: 'none', retrievalPolicy: local ? 'local_reports' : 'supabase_then_static_fallback', modelPolicy: 'forbidden', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: `Inventory questions retrieve ${local ? 'local records/reports' : 'Supabase records with an honest static fallback'} before reasoning.` });
  }

  if (hasSelectionReference(message, input.selectionMemory)) return decision({ routeId: 'memory_followup', activationLevel: 3, domain: input.selectionMemory.activeDomain || domain, intent: 'resolve_previous_selection', memoryPolicy: 'selection_only', retrievalPolicy: 'supabase_then_static_fallback', modelPolicy: 'allowed_if_needed', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'An explicit follow-up marker or named selection item permits selection memory.' });

  if (isRevenueStrategyQuestion(message)) return decision({ routeId: 'revenue_reasoning', activationLevel: 4, domain: 'monetization', intent: 'revenue_strategy', memoryPolicy: 'long_term_allowed', retrievalPolicy: 'supabase_then_static_fallback', modelPolicy: 'allowed_if_needed', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'Revenue strategy uses long-term business context and opportunity retrieval, never stale selected items.' });

  if (advisory && isAdvisoryFollowUpQuestion(message) && (!domainResult.explicit || (['business_opportunity', 'monetization'].includes(domain) && /\b(?:this|that|it)\b/i.test(message)))) return decision({ routeId: 'advisory_followup', activationLevel: 4, domain: advisory.lastAdvisoryDomain, intent: 'evaluate_prior_advice', memoryPolicy: 'long_term_allowed', retrievalPolicy: 'none', modelPolicy: 'allowed_if_needed', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'A short-lived plan-level follow-up refers to the prior advisory answer, not a selected list item.' });

  if (domain !== 'unknown' || /\b(recommend|prioritize|plan|implement|strategy|what should)\b/i.test(lower)) return decision({ routeId: 'local_reasoning', activationLevel: 4, domain, intent: 'domain_reasoning', memoryPolicy: domain === 'business_opportunity' || domain === 'monetization' ? 'long_term_allowed' : 'none', retrievalPolicy: ['trading', 'reports', 'research_youtube'].includes(domain) ? 'local_reports' : 'static_fallback_allowed', modelPolicy: 'allowed_if_needed', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'The explicit domain can be answered locally without unrestricted memory.' });

  if (/\b(deep synthesis|comprehensive analysis|draft|compose|polished)\b/i.test(lower)) return decision({ routeId: 'model_reasoning', activationLevel: 5, domain, intent: 'deep_synthesis', memoryPolicy: 'long_term_allowed', retrievalPolicy: 'local_reports_then_supabase', modelPolicy: 'required', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'The request explicitly needs synthesis beyond deterministic local handlers.' });

  return decision({ routeId: 'fallback_clarification', activationLevel: 1, domain: 'unknown', intent: 'clarification', memoryPolicy: 'none', retrievalPolicy: 'none', modelPolicy: 'forbidden', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'No safe domain, entity, or retrieval target was identified.' });
}
