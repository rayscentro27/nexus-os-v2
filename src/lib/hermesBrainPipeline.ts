import { routeHermesPriority } from './hermesPriorityRouter';
import { buildContextPacket } from './hermesContextPacketBuilder';
import { renderHermesAnswer, type HermesHandlerResult } from './hermesAnswerRenderer';
import { isModelAllowed, isSupabaseAllowed, type RouteDecision } from './hermesRouteDecision';
import { answerCapabilityQuestion, getCapabilityReport } from './hermesCapabilityStatus';
import { buildLiveSupabaseContext } from './hermesLiveContext';
import { hermesModelChat } from './hermesProviders';
import { buildDailySummary, buildCeoDailySummary } from './hermesDailyActivityTranslator';
import { answerConversation, classifyConversationIntent } from './hermesConversationBrain';
import { answerHermesTraceQuestion } from './hermesTraceQuestionHandler';
import { answerTradingQuestion } from './hermesTradingReasoner';
import { answerRevenueStrategy } from './hermesRevenueReasoner';
import {
  addConversationMessage, getConversationState, resolveFollowUp, setLastListedItems,
  setLastRankedList, setLastRecommendedItem, setLastSelectedItem,
  setLastSupabaseQueryResult, updateConversationContext, type ConversationItem,
  setConversationScope,
} from './hermesConversationState';
import { advanceSelectionMemoryTurn, getSelectionMemory, setHermesMemoryScope, setLastTurnTraceMemory, touchSelectionMemory } from './hermesMemoryStores';
import { logRoutingTrace, setRoutingTraceScope } from './hermesRoutingTrace';
import { reportRegistry } from '../data/reportRegistry.js';
import { reasonFromRouteDecision } from './hermesReasoningEngine';
import { answerCasualCommonQuestion, answerExternalCurrentInfoQuestion, answerGeneralAdvisorQuestion, answerGeneralProjectPlanningQuestion } from './hermesCommonConversation';
import { answerActivityStatusQuestion } from './hermesActivityStatus';
import { advanceAdvisoryContinuityTurn, answerAdvisoryFollowUp, clearAdvisoryContinuity, setAdvisoryContinuity, setAdvisoryMemoryScope } from './hermesAdvisoryContinuity';
import { advanceFallbackContinuityTurn, clearFallbackContinuity, setFallbackContinuity, setFallbackMemoryScope } from './hermesFallbackContinuity';
import { answerOpportunityAwareRecommendation, type OpportunityAdvisorResult } from './hermesOpportunityAdvisor';
import { answerSystemHealthQuestion } from './hermesSystemHealthStatus';
import { answerPageContextQuestion } from './hermesPageContextStatus';
import { renderRecordContract, renderResearchStatusContract, renderSpecialistHandoffContract, renderSpecialistAgentInventoryContract, renderSystemHealthContract } from './hermesOperationalContracts';
import { buildIntentFrame } from './hermesIntentClassifier';
import type { HermesIntentFrame } from './hermesIntentFrame';
import { getActiveSession, advanceSessionTurn, type NexusSessionContext } from './hermesAdvisorSession';
import { startBusinessOpportunityReview, explainScore, improveOpportunity, draftRayReviewForOpportunity } from './hermesBusinessOpportunityReview';
import { renderVoiceReady, type VoiceReadyResponse } from './hermesVoiceReadyRenderer';

export interface BrainPipelineInput {
  message: string; surface?: 'full_workroom' | 'inline_drawer' | 'specialist' | 'unknown';
  currentRoute?: string; currentPageContext?: Record<string, unknown> | null;
  conversationHistory?: unknown[]; userSession?: unknown; tenantId?: string;
  pageId?: string; route?: string; isBackgroundJob?: boolean; sessionId?: string;
}
export interface BrainPipelineResponse {
  text: string; answer: string; activationLevel: number; route: string; routeDecision: RouteDecision;
  sourceMode: string; usedModel: boolean; modelMetadata: Record<string, unknown>;
  usedSupabase: boolean; supabaseStatus: string; resolvedEntities: ConversationItem[];
  rememberedContext: boolean; actionIntent: string | null; approvalRequired: boolean;
  safeNextActions: string[]; diagnostics: Record<string, any>;
  intent: { route: string; intent: string; confidence: 'high' | 'medium' | 'low'; reason: string };
  modelRoute: { route: string; reason: string; [key: string]: unknown };
  reasoning: { decision: 'answer-locally' | 'answer-with-context' | 'route-to-model'; confidence: 'high' | 'medium' | 'low'; reasoning: string };
  capabilityBadge: string; confidence: 'high' | 'medium' | 'low';
  source: 'local' | 'fallback' | 'supabase' | 'model' | 'conversation-followup' | 'capability' | 'reasoning'; timestamp: string;
  intentFrame?: HermesIntentFrame;
  activeSession?: NexusSessionContext | null;
  voiceReady?: VoiceReadyResponse;
}

const OPPORTUNITIES: ConversationItem[] = [
  { id: 'readiness-review', title: '$97 Credit & Funding Readiness Review', type: 'opportunity', category: 'GoClear/Apex', revenueRange: '$97 entry offer', status: 'low-cost launch', source: 'static_offer_context', dataSource: 'static' },
  { id: 'assistant-plan', title: '$297 Credit Assistant Plan', type: 'opportunity', category: 'GoClear/Apex', revenueRange: '$297', status: 'upsell', source: 'static_offer_context', dataSource: 'static' },
  { id: 'monthly-readiness', title: 'Monthly Readiness Subscription', type: 'opportunity', category: 'GoClear/Apex', revenueRange: 'recurring', status: 'retention offer', source: 'static_offer_context', dataSource: 'static' },
  { id: 'funding-prep', title: 'Funding Application Prep Sprint', type: 'opportunity', category: 'Apex', revenueRange: '$500–$1,500', status: 'service offer', source: 'static_offer_context', dataSource: 'static' },
];

const result = (userAnswer: string, handler: string, sources: string[], selectedEntities: ConversationItem[] = [], nextActions: string[] = []): HermesHandlerResult => ({ userAnswer, internalTrace: handler, selectedEntities, sources, nextActions, safeFallbackAnswer: userAnswer });
const actionResult = (userAnswer: string, handler: string, sources: string[], actionProof: NonNullable<HermesHandlerResult['actionProof']>, selectedEntities: ConversationItem[] = []): HermesHandlerResult => ({ ...result(userAnswer, handler, sources, selectedEntities), actionProof });
const recommendation = () => `**Recommendation:** start with the **$97 Credit & Funding Readiness Review**. It is the current Nexus entry-offer path and can lead to the $297 assistant plan and Monthly Readiness Subscription.\n\n**Source:** static Nexus business context; this answer did not verify current demand, live opportunity rows, or sales.\n**Assumptions:** Ray can fulfill the review manually, reach qualified prospects, and keep delivery scoped.\n**Confidence:** medium until live pipeline and conversion evidence are checked.\n**Next safe action:** prepare the intake and scorecard as a draft, then validate with five manual prospects. Checkout activation, customer contact, and charging remain approval-gated.`;
const implementation = (item: ConversationItem) => `Here is the implementation plan for **${item.title}**:\n\n1. Define the promise, eligibility rules, deliverables, and exclusions.\n2. Build the intake and readiness scorecard.\n3. Create checkout and fulfillment in test mode.\n4. Run five manual pilots and capture conversion evidence.\n5. Prepare the refined plan for Ray Review.\n\nNo email, charge, publishing, or live execution occurs without explicit approval.`;
const listOpportunities = (live: boolean, freshness: string) => `Business opportunities:\n\n${OPPORTUNITIES.map((item, index) => `${index + 1}. **${item.title}** — ${item.status}; ${item.revenueRange}. Source: static normalized Nexus offer context; freshness: build-time; confidence: medium.${live ? ' A separate live Supabase inventory read also succeeded, but these static items were not merged with or claimed to be those returned rows.' : ''}`).join('\n')}\n\n**Next safe action:** verify the chosen item against the live record before creating any approval draft. Source check: ${live ? 'live Supabase plus separately labeled static context' : 'static context only'}; checked ${freshness}.`;

async function executeRoute(decision: RouteDecision, packet: ReturnType<typeof buildContextPacket>, message: string, intentFrame?: HermesIntentFrame) {
  const lower = message.toLowerCase();
  let usedSupabase = false, usedModel = false, supabaseStatus = 'not_used';
  let supabaseTables: string[] = [];
  let source: BrainPipelineResponse['source'] = 'local';
  let handler: HermesHandlerResult;
  let opportunityAdvisory: OpportunityAdvisorResult | null = null;

  switch (decision.routeId) {
    case 'safety_gate':
      handler = result('I cannot execute that. Sending, publishing, charging, disputes, destructive data changes, schedulers, and live/funded trading are blocked or require explicit Ray approval through Ray Review. I can prepare a non-executed review draft.', 'safety_gate', ['safety_policy']); break;
    case 'trace_source_meta':
    case 'cost_model_usage_status':
      handler = result(answerHermesTraceQuestion(message, packet.routingTrace, { routeDecision: decision }) || 'No prior routing record is available.', 'trace_question_handler', ['last_non_trace_route']); break;
    case 'casual_identity':
      handler = result(answerConversation(message, classifyConversationIntent(message)) || "I'm Hermes, the Nexus operating advisor.", 'casual_conversation', ['local_conversation']); break;
    case 'casual_common':
      handler = result(answerCasualCommonQuestion({ message, routeDecision: decision, contextPacket: packet }), 'common_conversation', ['common_knowledge']); source = 'conversation-followup'; break;
    case 'general_advisor':
      handler = result(answerGeneralAdvisorQuestion({ message, routeDecision: decision, contextPacket: packet }), 'general_advisor', ['plain_reasoning']); source = 'reasoning'; break;
    case 'opportunity_aware_recommendation':
      opportunityAdvisory = answerOpportunityAwareRecommendation({ message, routeDecision: decision, contextPacket: packet });
      handler = result(opportunityAdvisory.text, 'opportunity_aware_advisor', ['local_reasoning_framework']); source = 'reasoning'; break;
    case 'nexus_build_planning':
      handler = result('Yes — we can build toward a Nexus CRM, and parts of the foundation already exist: client profiles, opportunities, approvals, task requests, research sources, monetization, and Hermes routing. The CRM should cover client pipeline, credit/funding workflow, documents and uploads, notes and tasks, approvals, messaging, funding readiness, business setup, and reports. I can design the modules and prepare a build plan. I have not created code, files, tasks, or a deployment, and I will not execute anything unless you explicitly request a reviewed draft task or implementation step.', 'nexus_build_planner', ['local_product_context', 'local_reports']); source = 'reasoning'; break;
    case 'general_project_planning':
      handler = result(answerGeneralProjectPlanningQuestion(message), 'general_project_planner', ['plain_reasoning']); source = 'reasoning'; break;
    case 'fallback_continuation': {
      const original = packet.fallbackContinuity?.originalMessage || '';
      if (decision.domain === 'nexus_product_build') handler = result(`Under Nexus planning: I can help turn “${original}” into a scoped product plan. Define the target feature, users, current foundation, smallest useful workflow, data and security boundaries, milestones, and review gate. I have not created code, files, or a task.`, 'fallback_continuation_nexus', ['fallback_continuity']);
      else if (/\b(?:house|home|app|website|book|trip|course|brand|business|project)\b/i.test(original)) handler = result(`Under a general recommendation: ${answerGeneralProjectPlanningQuestion(original)}`, 'fallback_continuation_general_project', ['fallback_continuity']);
      else handler = result(`Under a general recommendation, I can help evaluate “${original},” but I still need the specific project, decision, or outcome you want to plan.`, 'fallback_continuation_general', ['fallback_continuity']);
      source = 'reasoning'; break;
    }
    case 'advisory_followup':
      handler = packet.advisoryContinuity
        ? result(answerAdvisoryFollowUp(message, packet.advisoryContinuity), 'advisory_continuity_reasoner', ['advisory_continuity'])
        : result('I can answer generally, but I need to know what plan or idea you mean.', 'advisory_context_expired', ['none']);
      source = 'reasoning'; break;
    case 'client_records': {
      const live = await buildLiveSupabaseContext(message);
      usedSupabase = live.liveData; supabaseStatus = live.sourceType; supabaseTables = live.tablesQueried || [];
      handler = result(renderRecordContract('clients', live), `${decision.routeId}_contract`, live.liveData ? supabaseTables : ['supabase_access_state']);
      source = live.liveData ? 'supabase' : 'local';
      break;
    }
    case 'research_engine_status':
      handler = result(renderResearchStatusContract(), 'research_engine_status_contract', ['system_health_registry', 'report_registry']); break;
    case 'specialist_handoff': {
      const item = packet.selectionMemory ? resolveFollowUp(message) : null;
      handler = actionResult(renderSpecialistHandoffContract(item?.title), 'specialist_handoff_contract', item ? ['selection_memory', 'delegation_policy'] : ['delegation_policy'], { outcome: item ? 'local_draft_only' : 'blocked', title: item?.title, status: item ? 'not_saved' : undefined, reason: item ? undefined : 'missing_target' }, item ? [item] : []);
      break;
    }
    case 'specialist_agent_inventory':
      handler = result(renderSpecialistAgentInventoryContract(message), 'specialist_agent_inventory_contract', ['local_reports', 'module_inventory']); break;
    case 'external_current_info':
      handler = result(answerExternalCurrentInfoQuestion(message), 'external_current_info_fallback', ['common_knowledge']); break;
    case 'process_activity_status':
      handler = result(answerActivityStatusQuestion({ message, routeDecision: decision, contextPacket: packet }), 'activity_status_summary', ['local_activity_journal', 'confirmed_checkpoint']); break;
    case 'system_health_report':
      handler = result(/where is the problem|what is the issue|what is not working/i.test(message) ? answerSystemHealthQuestion(message) : renderSystemHealthContract(), 'system_health_contract', ['system_health_registry', 'local_reports']); break;
    case 'page_connection_status':
    case 'page_context_status':
      handler = result(answerPageContextQuestion({ message, routeDecision: decision, contextPacket: packet }), 'page_context_status', ['page_context_contract']); break;
    case 'capability_status':
      handler = result(answerCapabilityQuestion(message) || getCapabilityReport().capabilities.map(item => `${item.name}: ${item.userFacing}`).join('\n'), 'capability_status', ['capability_registry']); source = 'capability'; break;
    case 'process_settings_reports_status':
      if (decision.domain === 'trading') { const trading = answerTradingQuestion(message, { routeDecision: decision }); handler = result(trading.text, trading.handler, [trading.source]); }
      else if (decision.domain === 'reports' && decision.intent === 'inventory_question') { const reports = reportRegistry.filter(item => item.available).slice(0, 10); handler = result(`Available local reports:\n\n${reports.map((item, index) => `${index + 1}. **${item.title}** — ${item.category}; ${item.path}`).join('\n')}`, 'report_inventory', ['report_registry']); }
      else if (/ceo version|ceo summary/.test(lower)) handler = result(buildCeoDailySummary('today'), 'ceo_summary', ['activity_journal']);
      else if (/what did (?:you|we) do today|daily summary/.test(lower)) handler = result(buildDailySummary('today'), 'daily_summary', ['activity_journal']);
      else handler = result(`**Status:** no specialized live status adapter is registered for ${decision.domain.replace(/_/g, ' ')}.\n**Source checked:** local report registry.\n**Freshness:** current build snapshot; production state was not verified.\n**Blocker:** a route-specific report adapter or authenticated read is required for a definitive answer.\n**Next safe action:** open the latest matching report and perform a read-only verification.`, 'status_contract_fallback', ['report_registry']);
      break;
    case 'approval_action_prepare': {
      if (decision.intent === 'prepare_implementation_task') {
        handler = actionResult('I did not start building or create code/files. I can prepare a draft implementation task for Ray Review, but implementation and deployment require explicit approval and a defined scope.', 'implementation_action_gated', ['approval_policy'], { outcome: 'blocked', reason: 'implementation_requires_reviewed_scope' });
        break;
      }
      // Try to resolve target from intent frame first
      const intentTarget = intentFrame?.target.type === 'named_offer' ? intentFrame.target.label : null;
      if (intentTarget) {
        handler = actionResult(`Draft Ray Review request prepared in this conversation only for **${intentTarget}**. It has not been saved or submitted yet; it was not submitted or executed. No external action was executed.`, 'approval_local_draft', ['intent_frame', 'approval_policy'], { outcome: 'local_draft_only', title: intentTarget, status: 'not_saved' });
        break;
      }
      const item = packet.selectionMemory ? resolveFollowUp(message) : null;
      if (item) touchSelectionMemory();
      handler = item
        ? actionResult(`Draft Ray Review request prepared in this conversation only for **${item.title}**. It has not been saved or submitted yet; it was not submitted or executed. No external action was executed.`, 'approval_local_draft', ['selection_memory', 'approval_policy'], { outcome: 'local_draft_only', title: item.title, status: 'not_saved' }, [item])
        : actionResult(decision.intent === 'unresolved_action_reference'
          ? 'I don’t have an eligible target for that reference yet. Name the record, opportunity, task, report, or page you want me to prepare, and I’ll create a draft-only handoff or Ray Review request. Nothing was executed.'
          : 'I did not create a Ray Review card because no eligible target was resolved. Nothing was saved or submitted. Name the target and I can prepare a conversation-only draft.', 'approval_blocked_missing_target', ['approval_policy'], { outcome: 'blocked', reason: 'missing_target' });
      break;
    }
    case 'schedule_action_prepare': {
      const isAudit = /\baudit\b/i.test(message);
      const hasReport = isAudit ? /\b(?:system health|routing|security|supabase|performance|compliance)\s+audit\b/i.test(message) : /\b(?:weekly|daily|monthly|monetization|revenue|trading|business|client|research)\b.*\b(?:report|summary)\b/i.test(message);
      const hasTime = /\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|at\s+\d|\d{1,2}(?::\d{2})?\s*(?:am|pm)|next week)\b/i.test(message);
      handler = hasReport && hasTime
        ? actionResult(`Draft scheduled-${isAudit ? 'audit' : 'report'} request prepared in this conversation only: **${message.replace(/[.!?]+$/, '')}**. It has not been saved, submitted, or activated. No scheduler was started.`, 'schedule_local_draft', ['approval_policy'], { outcome: 'local_draft_only', title: message.replace(/[.!?]+$/, ''), status: 'not_saved' })
        : actionResult(`I can prepare a draft scheduled-${isAudit ? 'audit' : 'report'} request for Ray Review, but I will not activate a scheduler. Which ${isAudit ? 'audit' : 'report'} should run, and what day/time next week? Nothing has been saved or activated.`, 'schedule_missing_details', ['approval_policy'], { outcome: 'blocked', reason: 'missing_target_or_time' });
      break;
    }
    case 'explicit_domain_retrieval':
      if (decision.domain === 'trading') {
        const trading = answerTradingQuestion(message, { routeDecision: decision }); handler = result(trading.text, trading.handler, [trading.source]); source = 'reasoning';
      } else if (decision.domain === 'reports') {
        handler = result('Available local report groups include activation/operations, Ray Review, trading proof, Hermes routing, research, revenue, and safety audits. Open Reports for the indexed files and timestamps.', 'report_inventory', ['report_registry']);
      } else if (isSupabaseAllowed(decision)) {
        const live = await buildLiveSupabaseContext(message); usedSupabase = live.liveData; supabaseStatus = live.sourceType; supabaseTables = live.tablesQueried || [];
        if (decision.domain === 'approvals') {
          handler = result(renderRecordContract('approvals', live), 'approvals_pending_contract', live.liveData ? supabaseTables : ['supabase_access_state']);
        } else if (decision.domain === 'business_opportunity') {
          handler = result(`${listOpportunities(live.liveData, live.timestamp)}\n\n${live.text}`, live.liveData ? 'business_opportunity_inventory_live' : 'business_opportunity_inventory_fallback', live.liveData ? [...supabaseTables, 'static_offer_context'] : ['static_offer_context']);
          setLastListedItems(OPPORTUNITIES);
        } else handler = result(live.text, live.liveData ? 'supabase_inventory' : 'inventory_unavailable', live.liveData ? supabaseTables : ['supabase_access_state']);
        source = live.liveData ? 'supabase' : 'local';
      } else handler = result(`I do not have verified ${decision.domain.replace(/_/g, ' ')} records in the allowed local source, so I cannot honestly list them.`, 'empty_inventory', ['local_reports']);
      break;
    case 'memory_followup': {
      const item = packet.selectionMemory ? resolveFollowUp(message) : null;
      if (/which one.*recommend|recommend one|pick one/.test(lower)) {
        const ranked = getConversationState().lastListedItems.length ? getConversationState().lastListedItems : OPPORTUNITIES;
        setLastRankedList(ranked); setLastRecommendedItem(ranked[0]); setLastSelectedItem(ranked[0]);
        handler = result(recommendation(), 'selection_recommendation', ['selection_memory'], [ranked[0]]);
      } else if (item) { setLastSelectedItem(item); touchSelectionMemory(); handler = result(implementation(item), 'selection_implementation', ['selection_memory'], [item]); }
      else handler = result('The selection policy allowed a follow-up, but no stored context item matched. Name the item once and I will continue.', 'selection_not_resolved', ['selection_memory']);
      source = 'conversation-followup'; break;
    }
    case 'revenue_reasoning': {
      let liveNote: string | undefined;
      if (isSupabaseAllowed(decision)) { const live = await buildLiveSupabaseContext(message); usedSupabase = live.liveData; supabaseStatus = live.sourceType; supabaseTables = live.tablesQueried || []; liveNote = live.liveData ? undefined : live.text.split('\n')[0]; }
      const revenue = answerRevenueStrategy({ usedSupabase, supabaseTables, supabaseNote: liveNote, routeDecision: decision }); handler = result(revenue.text, revenue.handler, [revenue.source]); source = usedSupabase ? 'supabase' : 'reasoning'; break;
    }
    case 'local_reasoning':
      if (decision.domain === 'trading') { const trading = answerTradingQuestion(message, { routeDecision: decision }); handler = result(trading.text, trading.handler, [trading.source]); }
      else if (decision.domain === 'business_opportunity' || decision.domain === 'monetization') { handler = result(recommendation(), 'business_local_reasoning', ['long_term_business_context']); setLastRankedList(OPPORTUNITIES); setLastRecommendedItem(OPPORTUNITIES[0]); }
      else if (decision.domain === 'clients') handler = result('I do not have enough verified Nexus data loaded to answer that specific record question. Tell me the client, report, table, or item, or open the relevant section.', 'record_specific_missing_context', ['none']);
      else handler = result(`I can reason from the allowed ${decision.domain.replace(/_/g, ' ')} context, but I need a concrete decision or entity to produce a useful plan.`, 'domain_local_reasoning', packet.longTermBusinessContext ? ['long_term_business_context'] : ['local_context']);
      source = 'reasoning'; break;
    case 'model_reasoning': {
      if (!isModelAllowed(decision)) throw new Error('RouteDecision forbids model execution');
      const model = await hermesModelChat(message, { pageSummary: String(packet.pageContext?.pageId || '') || undefined }); usedModel = model.source === 'model';
      handler = result(model.text || 'The required model route did not return a verified answer.', usedModel ? 'model_reasoning' : 'model_unavailable', [model.source || 'model_unknown']); source = usedModel ? 'model' : 'local'; break;
    }
    default:
      setFallbackContinuity(message);
      handler = result('I need one more detail: what specific outcome or record do you want help with? If you want a general recommendation, name the decision you want me to evaluate.', 'fallback_clarification', ['none']);
      source = 'fallback';
  }
  return { handler, usedSupabase, usedModel, supabaseStatus, supabaseTables, source, opportunityAdvisory };
}

export async function handleHermesMessage(input: BrainPipelineInput): Promise<BrainPipelineResponse> {
  const message = input.message.trim();
  const sessionFromObject = input.userSession && typeof input.userSession === 'object' && 'id' in input.userSession ? String((input.userSession as { id?: unknown }).id || '') : '';
  const scopeKey = `${input.tenantId || 'default'}:${input.sessionId || sessionFromObject || 'default'}`;
  setHermesMemoryScope(scopeKey);
  setAdvisoryMemoryScope(scopeKey);
  setFallbackMemoryScope(scopeKey);
  setConversationScope(scopeKey);
  setRoutingTraceScope(scopeKey);
  advanceSelectionMemoryTurn();
  advanceAdvisoryContinuityTurn();
  advanceFallbackContinuityTurn();
  advanceSessionTurn(scopeKey);
  const surface = input.surface || 'unknown';
  const page = String(input.pageId || input.currentPageContext?.pageId || '');
  const state = getConversationState();
  const intentFrame = buildIntentFrame(message);
  const routeDecision = routeHermesPriority({ message, currentPage: page || null, previousDomain: state.lastTopic, selectionMemory: getSelectionMemory(), intentFrame });
  const advisoryProducingRoute = ['revenue_reasoning', 'general_advisor', 'nexus_build_planning', 'opportunity_aware_recommendation', 'memory_followup'].includes(routeDecision.routeId) || (routeDecision.routeId === 'local_reasoning' && ['business_opportunity', 'monetization'].includes(routeDecision.domain));
  const topicNeutralRoute = ['trace_source_meta', 'cost_model_usage_status', 'casual_common', 'casual_identity', 'process_activity_status', 'process_settings_reports_status', 'capability_status', 'advisory_followup'].includes(routeDecision.routeId);
  if (!advisoryProducingRoute && !topicNeutralRoute && routeDecision.domain !== 'unknown') clearAdvisoryContinuity();
  if (!['trace_source_meta', 'cost_model_usage_status', 'fallback_continuation', 'fallback_clarification'].includes(routeDecision.routeId)) clearFallbackContinuity();
  const packet = buildContextPacket({ routeDecision, message, session: input.userSession, pageContext: input.currentPageContext || null, conversationState: state });
  const executed = await executeRoute(routeDecision, packet, message, intentFrame);
  const rendered = renderHermesAnswer(executed.handler, routeDecision);
  const text = rendered.text;
  const resolvedEntities = executed.handler.selectedEntities;
  const selectionOrTraceMemoryUsed = Boolean(packet.lastTrace || packet.selectionMemory);
  const anyMemoryUsed = selectionOrTraceMemoryUsed || Boolean(packet.longTermBusinessContext) || Boolean(packet.advisoryContinuity) || Boolean(packet.fallbackContinuity);
  const memoryRejected = Boolean(getSelectionMemory().lastList.length) && !packet.selectionMemory && !packet.lastTrace;
  const modelRoute = executed.usedModel ? 'primary_model' : routeDecision.modelPolicy === 'forbidden' ? 'no_model' : 'local_reasoning';
  const reasoningPlan = reasonFromRouteDecision(routeDecision, packet.summary);

  addConversationMessage('user', message); addConversationMessage('assistant', text);
  if (advisoryProducingRoute && executed.handler.internalTrace !== 'selection_not_resolved') {
    const revenue = routeDecision.domain === 'monetization';
    const opportunity = executed.opportunityAdvisory;
    const selectedPlan = ['selection_implementation', 'selection_recommendation'].includes(executed.handler.internalTrace) ? executed.handler.selectedEntities[0] : null;
    const selectedTitle = selectedPlan?.title || '';
    const monthlyReadiness = /monthly readiness subscription/i.test(selectedTitle);
    setAdvisoryContinuity({
      lastAdvisoryTopic: selectedTitle || routeDecision.intent,
      lastAdvisoryDomain: monthlyReadiness ? 'monetization' : routeDecision.domain,
      lastAdvisorySummary: selectedPlan ? `The implementation plan for ${selectedTitle} defines the offer, intake, fulfillment, manual pilots, and review gate.` : opportunity ? `The ${opportunity.topic} is best tested as a low-cost information, comparison, referral, or affiliate workflow before hands-on fulfillment.` : revenue ? 'The 30-day path can work if we keep the offer simple, close $97 readiness reviews quickly, and upsell only when the review establishes a clear next step.' : text.slice(0, 500),
      lastAdvisoryAssumptions: selectedPlan ? ['a clear recurring promise', 'manual pilot delivery', 'visible customer progress', 'measured conversion and retention'] : opportunity?.assumptions || (revenue ? ['manual outreach', 'fast readiness-review fulfillment', 'consistent follow-up', 'disciplined upsells'] : ['a defined scope', 'clear priorities', 'reviewed implementation steps']),
      lastAdvisoryRecommendation: selectedPlan ? `test ${selectedTitle} with five manual pilot clients before automating.` : opportunity?.recommendation || (revenue ? 'launch the $97 readiness review and validate the first ten sales before scaling.' : 'define the smallest useful first phase and prepare it for review.'),
      lastAdvisoryRisks: selectedPlan ? ['weak retention', 'unclear deliverables', 'clients not seeing progress', 'lead flow', 'pricing and fulfillment complexity'] : opportunity?.risks || (revenue ? ['lead flow', 'weak follow-up', 'unclear offer packaging', 'slow fulfillment', 'poor conversion into the $297 assistant plan'] : ['unclear scope', 'missing proof', 'implementation complexity']),
      sourceProvenance: executed.handler.sources,
      confidence: routeDecision.confidence >= .8 ? 'high' : routeDecision.confidence >= .5 ? 'medium' : 'low',
    });
  }
  if (routeDecision.routeId === 'fallback_continuation') clearFallbackContinuity();

  // Session integration for domain reviews
  if (intentFrame.intent === 'domain_review' && intentFrame.domain === 'business_opportunities') {
    const reviewResult = startBusinessOpportunityReview(scopeKey, intentFrame, executed.usedSupabase);
    if (reviewResult.sessionCreated) {
      const session = getActiveSession(scopeKey);
      return {
        text: reviewResult.text, answer: reviewResult.text, activationLevel: routeDecision.activationLevel, route: routeDecision.routeId, routeDecision,
        sourceMode: executed.source, usedModel: executed.usedModel, modelMetadata: { route: modelRoute },
        usedSupabase: executed.usedSupabase, supabaseStatus: executed.supabaseStatus, resolvedEntities,
        rememberedContext: anyMemoryUsed, actionIntent: routeDecision.actionPolicy !== 'none' ? message : null,
        approvalRequired: routeDecision.actionPolicy === 'approval_required', safeNextActions: [],
        diagnostics: { routeDecision, contextPacketSummary: packet.summary, answerBuilder: 'business_opportunity_review', domain: { domain: routeDecision.domain }, memoryUsed: false, longTermMemoryUsed: false, advisoryContinuityUsed: false, memoryRejected: false, diagnosticSuppressedForUser: false },
        intent: { route: routeDecision.routeId, intent: 'domain_review', confidence: 'high', reason: 'Business opportunity review session started' },
        modelRoute: { route: 'no_model', reason: 'review session' }, reasoning: { decision: 'answer-locally', confidence: 'high', reasoning: 'Business opportunity review from source authority' },
        capabilityBadge: getCapabilityReport().badgeText, confidence: 'high', source: executed.source, timestamp: new Date().toISOString(),
        intentFrame, activeSession: session, voiceReady: renderVoiceReady(reviewResult.text, 'voice_ready'),
      };
    }
  }

  if ((intentFrame.intent === 'domain_review' || intentFrame.intent === 'advisory_followup') && intentFrame.action === 'explain_score') {
    const scoreExplanation = explainScore(scopeKey, intentFrame);
    if (scoreExplanation) {
      const session = getActiveSession(scopeKey);
      return {
        text: scoreExplanation, answer: scoreExplanation, activationLevel: routeDecision.activationLevel, route: routeDecision.routeId, routeDecision,
        sourceMode: executed.source, usedModel: executed.usedModel, modelMetadata: { route: modelRoute },
        usedSupabase: executed.usedSupabase, supabaseStatus: executed.supabaseStatus, resolvedEntities,
        rememberedContext: anyMemoryUsed, actionIntent: null, approvalRequired: false, safeNextActions: [],
        diagnostics: { routeDecision, contextPacketSummary: packet.summary, answerBuilder: 'score_explanation', domain: { domain: routeDecision.domain }, memoryUsed: false, longTermMemoryUsed: false, advisoryContinuityUsed: false, memoryRejected: false, diagnosticSuppressedForUser: false },
        intent: { route: routeDecision.routeId, intent: 'explain_score', confidence: 'high', reason: 'Score explanation from active session' },
        modelRoute: { route: 'no_model', reason: 'score explanation' }, reasoning: { decision: 'answer-locally', confidence: 'high', reasoning: 'Score explanation from session context' },
        capabilityBadge: getCapabilityReport().badgeText, confidence: 'high', source: executed.source, timestamp: new Date().toISOString(),
        intentFrame, activeSession: session, voiceReady: renderVoiceReady(scoreExplanation, 'voice_ready'),
      };
    }
  }

  if ((intentFrame.intent === 'domain_review' || intentFrame.intent === 'advisory_followup') && intentFrame.action === 'improve') {
    const improvement = improveOpportunity(scopeKey, intentFrame);
    if (improvement) {
      const session = getActiveSession(scopeKey);
      return {
        text: improvement, answer: improvement, activationLevel: routeDecision.activationLevel, route: routeDecision.routeId, routeDecision,
        sourceMode: executed.source, usedModel: executed.usedModel, modelMetadata: { route: modelRoute },
        usedSupabase: executed.usedSupabase, supabaseStatus: executed.supabaseStatus, resolvedEntities,
        rememberedContext: anyMemoryUsed, actionIntent: null, approvalRequired: false, safeNextActions: [],
        diagnostics: { routeDecision, contextPacketSummary: packet.summary, answerBuilder: 'improvement_suggestion', domain: { domain: routeDecision.domain }, memoryUsed: false, longTermMemoryUsed: false, advisoryContinuityUsed: false, memoryRejected: false, diagnosticSuppressedForUser: false },
        intent: { route: routeDecision.routeId, intent: 'improve', confidence: 'high', reason: 'Improvement suggestion from active session' },
        modelRoute: { route: 'no_model', reason: 'improvement' }, reasoning: { decision: 'answer-locally', confidence: 'high', reasoning: 'Improvement suggestion from session context' },
        capabilityBadge: getCapabilityReport().badgeText, confidence: 'high', source: executed.source, timestamp: new Date().toISOString(),
        intentFrame, activeSession: session, voiceReady: renderVoiceReady(improvement, 'voice_ready'),
      };
    }
  }

  if (intentFrame.intent === 'approval_action_draft' && intentFrame.domain === 'business_opportunities') {
    const draftResult = draftRayReviewForOpportunity(scopeKey, intentFrame);
    const session = getActiveSession(scopeKey);
    return {
      text: draftResult, answer: draftResult, activationLevel: routeDecision.activationLevel, route: routeDecision.routeId, routeDecision,
      sourceMode: executed.source, usedModel: executed.usedModel, modelMetadata: { route: modelRoute },
      usedSupabase: executed.usedSupabase, supabaseStatus: executed.supabaseStatus, resolvedEntities,
      rememberedContext: anyMemoryUsed, actionIntent: message, approvalRequired: true, safeNextActions: ['confirm draft details', 'prepare formal Ray Review request'],
      diagnostics: { routeDecision, contextPacketSummary: packet.summary, answerBuilder: 'ray_review_draft', domain: { domain: routeDecision.domain }, memoryUsed: false, longTermMemoryUsed: false, advisoryContinuityUsed: false, memoryRejected: false, diagnosticSuppressedForUser: false },
      intent: { route: routeDecision.routeId, intent: 'draft_ray_review', confidence: 'high', reason: 'Ray Review draft from session target' },
      modelRoute: { route: 'no_model', reason: 'draft preparation' }, reasoning: { decision: 'answer-locally', confidence: 'high', reasoning: 'Ray Review draft preparation' },
      capabilityBadge: getCapabilityReport().badgeText, confidence: 'high', source: executed.source, timestamp: new Date().toISOString(),
      intentFrame, activeSession: session, voiceReady: renderVoiceReady(draftResult, 'voice_ready'),
    };
  }

  const topicNeutralRoutes = ['trace_source_meta', 'cost_model_usage_status', 'casual_common', 'casual_identity', 'process_activity_status', 'process_settings_reports_status', 'system_health_report', 'page_connection_status', 'page_context_status', 'capability_status', 'fallback_clarification'];
  if (!topicNeutralRoutes.includes(routeDecision.routeId)) {
    updateConversationContext({ lastIntent: routeDecision.intent, lastTopic: routeDecision.domain, lastPage: page || null, lastActionPlan: /implementation plan/i.test(text) ? text.slice(0, 2000) : null });
  }
  if (routeDecision.routeId !== 'trace_source_meta' && routeDecision.routeId !== 'cost_model_usage_status') {
    setLastTurnTraceMemory({ routeLevel: routeDecision.activationLevel, routeName: routeDecision.routeId, domain: routeDecision.domain, usedSupabase: executed.usedSupabase, usedStaticFallback: routeDecision.allowedContext.staticFallback && !executed.usedSupabase, usedModel: executed.usedModel, modelName: null, usedMemory: anyMemoryUsed, sources: executed.handler.sources, costEstimate: null, decisionReason: routeDecision.reason, blockedBySafety: routeDecision.actionPolicy === 'blocked' });
  }
  if (executed.usedSupabase && executed.supabaseTables[0]) setLastSupabaseQueryResult(executed.supabaseTables[0], [], message);

  logRoutingTrace({
    message, surface, page: page || null, route: routeDecision.routeId, activationLevel: routeDecision.activationLevel,
    activationLevelName: `Level ${routeDecision.activationLevel}`, intent: routeDecision.intent, sourceDecision: executed.source,
    usedSupabase: executed.usedSupabase, supabaseTables: executed.supabaseTables, usedModel: executed.usedModel, modelRoute,
    usedMemory: anyMemoryUsed, selectedEntity: resolvedEntities[0]?.title || null, safetyGate: routeDecision.actionPolicy === 'blocked',
    answerBuilder: executed.handler.internalTrace, fallbackReason: null, correctnessHint: routeDecision.reason,
    confidence: routeDecision.confidence >= .8 ? 'high' : routeDecision.confidence >= .5 ? 'medium' : 'low',
    detectedDomain: routeDecision.domain, previousTopic: state.lastTopic, detectedTopic: routeDecision.domain,
    topicChanged: routeDecision.domain !== state.lastTopic, memoryCandidateFound: Boolean(getSelectionMemory().lastList.length), memoryUsed: anyMemoryUsed,
    memoryRejected, memoryRejectionReason: packet.memoryEligibility.reason,
    domainOverrideApplied: routeDecision.routeId === 'explicit_domain_retrieval', casualOverrideApplied: ['casual_identity', 'casual_common'].includes(routeDecision.routeId), invariantViolations: [],
    questionType: routeDecision.routeId === 'trace_source_meta' || routeDecision.routeId === 'cost_model_usage_status' ? 'trace_meta' : routeDecision.actionPolicy !== 'none' ? 'action' : ['casual_identity', 'casual_common'].includes(routeDecision.routeId) ? 'casual' : routeDecision.activationLevel === 1 ? 'status' : 'domain_reasoning',
    traceTarget: routeDecision.memoryPolicy === 'last_trace_only' ? 'last_answer' : 'current_question', finalAnswerHandler: executed.handler.internalTrace,
    diagnosticOnly: routeDecision.diagnosticsPolicy !== 'hidden', diagnosticSuppressedForUser: rendered.diagnosticSuppressed,
    domainOverrideReason: routeDecision.reason,
    routeDecision, contextPacketSummary: packet.summary, memoryPolicyApplied: routeDecision.memoryPolicy,
    retrievalPolicyApplied: routeDecision.retrievalPolicy, modelPolicyApplied: routeDecision.modelPolicy,
    diagnosticsPolicyApplied: routeDecision.diagnosticsPolicy, actionPolicyApplied: routeDecision.actionPolicy,
    blockedContext: routeDecision.blockedContext, allowedContext: routeDecision.allowedContext,
    handlerResultSummary: { handler: executed.handler.internalTrace, sources: executed.handler.sources, selectedCount: resolvedEntities.length, actionProof: executed.handler.actionProof || null },
  });

  const confidence = routeDecision.confidence >= .8 ? 'high' : routeDecision.confidence >= .5 ? 'medium' : 'low';
  const activeSession = getActiveSession(scopeKey);
  const voiceReadyResponse = renderVoiceReady(text, 'voice_ready');
  return {
    text, answer: text, activationLevel: routeDecision.activationLevel, route: routeDecision.routeId, routeDecision,
    sourceMode: executed.source, usedModel: executed.usedModel, modelMetadata: { route: modelRoute },
    usedSupabase: executed.usedSupabase, supabaseStatus: executed.supabaseStatus, resolvedEntities,
    rememberedContext: anyMemoryUsed, actionIntent: routeDecision.actionPolicy !== 'none' ? message : null,
    approvalRequired: routeDecision.actionPolicy === 'approval_required', safeNextActions: executed.handler.nextActions,
    diagnostics: { routeDecision, contextPacketSummary: packet.summary, answerBuilder: executed.handler.internalTrace, domain: { domain: routeDecision.domain }, memoryUsed: selectionOrTraceMemoryUsed || Boolean(packet.advisoryContinuity), longTermMemoryUsed: Boolean(packet.longTermBusinessContext), advisoryContinuityUsed: Boolean(packet.advisoryContinuity), memoryRejected, diagnosticSuppressedForUser: rendered.diagnosticSuppressed },
    intent: { route: routeDecision.routeId, intent: routeDecision.intent, confidence, reason: routeDecision.reason },
    modelRoute: { route: modelRoute, reason: routeDecision.reason }, reasoning: { decision: reasoningPlan.decision === 'route-to-model' ? 'route-to-model' : reasoningPlan.decision === 'answer-with-context' ? 'answer-with-context' : 'answer-locally', confidence, reasoning: reasoningPlan.reasoning },
    capabilityBadge: getCapabilityReport().badgeText, confidence, source: executed.source, timestamp: new Date().toISOString(),
    intentFrame, activeSession, voiceReady: voiceReadyResponse,
  };
}

export function getCapabilityBadge(): string { return getCapabilityReport().badgeText; }
