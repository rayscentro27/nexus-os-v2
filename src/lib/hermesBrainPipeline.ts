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
import { rayReviewCards } from '../data/rayReviewData.js';
import { reasonFromRouteDecision } from './hermesReasoningEngine';
import { answerCasualCommonQuestion, answerExternalCurrentInfoQuestion, answerGeneralAdvisorQuestion, answerGeneralProjectPlanningQuestion } from './hermesCommonConversation';
import { classifyOperatingQuestion, answerOperatingQuestion } from './hermesLocalOperatingCommands';
import { getReadinessActionMetadata } from './nexusReadinessRegistry';
import { answerActivityStatusQuestion } from './hermesActivityStatus';
import { advanceAdvisoryContinuityTurn, answerAdvisoryFollowUp, clearAdvisoryContinuity, setAdvisoryContinuity, setAdvisoryMemoryScope } from './hermesAdvisoryContinuity';
import { advanceFallbackContinuityTurn, clearFallbackContinuity, setFallbackContinuity, setFallbackMemoryScope } from './hermesFallbackContinuity';
import { answerOpportunityAwareRecommendation, type OpportunityAdvisorResult } from './hermesOpportunityAdvisor';
import { answerSystemHealthQuestion } from './hermesSystemHealthStatus';
import { answerPageContextQuestion } from './hermesPageContextStatus';
import { cleanRecordSourceSummary, renderRecordContract, renderResearchStatusContract, renderSpecialistHandoffContract, renderSpecialistAgentInventoryContract, renderSystemHealthContract, type CleanSourceSummary } from './hermesOperationalContracts';
import { buildIntentFrame } from './hermesIntentClassifier';
import type { HermesIntentFrame } from './hermesIntentFrame';
import { getActiveSession, advanceSessionTurn, startReviewSession, updateSessionSource, updateSessionList, setSessionFocus, type NexusSessionContext, setLastSuccessfulTrace, getLastSuccessfulTrace, getSessionFocusForContinuation, getSessionListForContinuation } from './hermesAdvisorSession';
import { startBusinessOpportunityReview, explainScore, improveOpportunity, draftRayReviewForOpportunity } from './hermesBusinessOpportunityReview';
import { renderVoiceReady, type VoiceReadyResponse } from './hermesVoiceReadyRenderer';
import { resolveHermesConversationState } from './hermesConversationArbiter';
import { getHermesDecisionState, updateHermesDecisionState } from './hermesDecisionState';
import { resolveHermesActionTarget } from './hermesActionResolver';
import { renderLastAnswerProvenance, renderResponseMode } from './hermesResponseModeRenderer';
import { hermesCapabilityRegistry, renderHermesAccessMapCeo } from './hermesCapabilityRegistry';
import type { HermesUiAction } from './hermesUiActions';

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
  uiActions?: HermesUiAction[];
  accessMatrix?: typeof hermesCapabilityRegistry;
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

async function executeRoute(decision: RouteDecision, packet: ReturnType<typeof buildContextPacket>, message: string, scopeKey: string, intentFrame?: HermesIntentFrame) {
  const lower = message.toLowerCase();
  let usedSupabase = false, usedModel = false, supabaseStatus = 'not_used';
  let supabaseTables: string[] = [];
  let source: BrainPipelineResponse['source'] = 'local';
  let handler: HermesHandlerResult;
  let opportunityAdvisory: OpportunityAdvisorResult | null = null;
  let sourceSummary: CleanSourceSummary | null = null;
  let uiActions: HermesUiAction[] = [];
  let accessMatrix: typeof hermesCapabilityRegistry | undefined;

  switch (decision.routeId) {
    case 'safety_gate':
      handler = result('I cannot execute that. Sending, publishing, charging, disputes, destructive data changes, schedulers, and live/funded trading are blocked or require explicit Ray approval through Ray Review. I can prepare a non-executed review draft.', 'safety_gate', ['safety_policy']); break;
    case 'safety_explanation': {
      const safety = getHermesDecisionState(scopeKey).lastSafetyDecision;
      handler = result(safety ? `I blocked it because ${safety.reason} I can ${safety.safeAlternatives.join(' or ')}, but I cannot perform the external action directly without approval.` : 'I do not have a prior safety decision in this session to explain.', 'safety_explanation', ['last_safety_decision', 'approval_policy']);
      break;
    }
    case 'response_mode_change': {
      const state = getHermesDecisionState(scopeKey);
      handler = result(renderResponseMode({ text: state.lastAnswer?.text || '', mode: state.responseMode, lastAnswer: state.lastAnswer }), 'response_mode_renderer', state.lastAnswer?.sources || ['last_answer']);
      break;
    }
    case 'recommendation_explanation': {
      const recommendation = getHermesDecisionState(scopeKey).lastRecommendation;
      handler = result(recommendation ? `I recommended **${recommendation.label}** because ${recommendation.reason} Source: ${recommendation.source}. The recommendation is still an advisory judgment, not proof of demand or execution readiness.` : 'I do not have a prior recommendation in this session to explain.', 'recommendation_explanation', recommendation ? [recommendation.source] : ['none']);
      break;
    }
    case 'previous_answer_followup': {
      const previous = getHermesDecisionState(scopeKey).lastAnswer;
      handler = result(previous ? `The previous answer was about ${previous.domain.replace(/_/g, ' ')}. I do not have a stored recommendation attached to it, so I should not invent a recommendation rationale. Ask me to recommend one item and I can explain the choice.` : 'I do not have a previous answer in this session to explain.', 'previous_answer_followup', previous?.sources || ['none']);
      break;
    }
    case 'trace_source_meta':
    case 'cost_model_usage_status': {
      const lastAnswer = getHermesDecisionState(scopeKey).lastAnswer;
      if (decision.routeId === 'trace_source_meta' && lastAnswer?.domain === 'clients' && lastAnswer.sources.includes('client_profiles')) {
        handler = result(renderLastAnswerProvenance(lastAnswer), 'trace_question_handler', ['last_answer_provenance']);
        break;
      }
      const lastSuccess = getLastSuccessfulTrace(scopeKey);
      const traceAnswer = answerHermesTraceQuestion(message, packet.routingTrace, { routeDecision: decision });
      let finalTraceAnswer = traceAnswer || 'No prior routing record is available.';
      if (lastSuccess && !traceAnswer) {
        const sessionNote = lastSuccess.sessionState ? ` I had an active ${lastSuccess.sessionState.activeMode || 'review'} session with ${lastSuccess.sessionState.itemCount || 0} items. The focus was ${lastSuccess.sessionState.focusLabel || 'not set'}.` : '';
        finalTraceAnswer = `The last successful answer used the **${lastSuccess.route}** route for the **${lastSuccess.domain}** domain. Source: ${lastSuccess.source}. Supabase: ${lastSuccess.usedSupabase ? 'yes' : 'no'}. Model: ${lastSuccess.usedModel ? 'yes' : 'no'}. Sources: ${lastSuccess.sources.join(', ') || 'local context'}.${sessionNote} I did not execute any action.`;
      }
      handler = result(finalTraceAnswer, 'trace_question_handler', ['last_non_trace_route']);
      break;
    }
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
      sourceSummary = cleanRecordSourceSummary('clients', live);
      handler = result(renderRecordContract('clients', live), `${decision.routeId}_contract`, ['client_profiles']);
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
    case 'readiness_operating_status': {
      const opQuestion = classifyOperatingQuestion(message);
      const areaMap: Record<string, string> = { credit_repair_ready: 'credit_repair', business_funding_ready: 'business_funding', ready_to_onboard_client: 'client_onboarding', missing_credit_repair: 'credit_repair', missing_business_funding: 'business_funding', can_sell_97_review: 'readiness_review_offer', what_should_ray_do_first: 'readiness_review_offer', draft_ray_review_readiness: 'readiness_review_offer', specialist_handoff_credit: 'credit_repair', specialist_handoff_funding: 'business_funding', what_parts_manual: 'credit_repair', what_parts_automated: 'credit_repair', what_parts_approval_gated: 'credit_repair', what_can_client_see: 'client_portal', what_can_admin_see: 'admin_review', how_to_deliver_97: 'readiness_review_offer', start_readiness_review: 'readiness_review_intake', what_questions_to_ask: 'readiness_review_intake', create_client_intake: 'readiness_review_intake', score_client_manually: 'readiness_review_scorecard', create_client_report: 'readiness_review_client_report', what_to_tell_client: 'readiness_review_client_report', upgrade_recommendation: 'readiness_review_upgrade_path', prepare_297_upsell: 'readiness_review_upgrade_path', prepare_monthly_subscription: 'readiness_review_upgrade_path', specialist_handoff_from_review: 'readiness_review_specialist_handoff', start_client_intake: 'readiness_review_intake', open_readiness_intake: 'readiness_review_intake', open_admin_review: 'readiness_review_admin_fulfillment', score_this_review: 'readiness_review_scorecard', draft_client_report_flow: 'readiness_review_client_report', what_missing_from_review: 'readiness_review_client_report', what_tell_this_client: 'readiness_review_client_report', best_upgrade_path: 'readiness_review_upgrade_path', prepare_specialist_handoff_flow: 'readiness_review_specialist_handoff' };
      const actionMeta = opQuestion ? getReadinessActionMetadata(areaMap[opQuestion] || 'credit_repair') : null;
      if (actionMeta) uiActions = [actionMeta];
      handler = result(opQuestion ? answerOperatingQuestion(opQuestion) : 'I need more detail. Ask about credit repair readiness, business funding readiness, whether you can sell the $97 review, or what is missing.', 'readiness_operating_status', ['readiness_registry']); break;
    }
    case 'system_health_report':
      handler = result(/where is the problem|what is the issue|what is not working/i.test(message) ? answerSystemHealthQuestion(message) : renderSystemHealthContract(), 'system_health_contract', ['system_health_registry', 'local_reports']); break;
    case 'page_connection_status':
    case 'page_context_status':
      handler = result(answerPageContextQuestion({ message, routeDecision: decision, contextPacket: packet }), 'page_context_status', ['page_context_contract']); break;
    case 'capability_status':
      handler = result(answerCapabilityQuestion(message) || getCapabilityReport().capabilities.map(item => `${item.name}: ${item.userFacing}`).join('\n'), 'capability_status', ['capability_registry']); source = 'capability'; break;
    case 'access_map':
      accessMatrix = hermesCapabilityRegistry;
      uiActions = [{ title: 'Hermes access map', summary: 'Read-only capability and connection matrix.', actionLabel: 'Open access map', actionType: 'open_access_map', href: '#hermes', source: 'hermes_capability_registry' }];
      handler = result(renderHermesAccessMapCeo(), 'access_map_contract', ['hermes_capability_registry']); source = 'capability'; break;
    case 'process_settings_reports_status':
      if (decision.domain === 'trading') { const trading = answerTradingQuestion(message, { routeDecision: decision }); handler = result(trading.text, trading.handler, [trading.source]); }
      else if (decision.domain === 'reports' && decision.intent === 'inventory_question') {
        const reports = reportRegistry.filter(item => item.available).slice(0, 10);
        const highlights = reports.slice(0, 3).map((item) => item.title).join(', ');
        handler = result(`I found ${reports.length} reports. I’d start with ${highlights}. Which one do you want to open?`, 'report_inventory', ['report_registry']);
        uiActions = reports.map((item) => ({ title: item.title, category: item.category, summary: `${item.category} report available in the Nexus report library.`, actionLabel: 'Open report', actionType: 'open_report', href: '#reports', reportPath: item.path, source: 'local_report_registry', freshness: item.modified }));
        const reportSessionItems = reports.map((item, index) => ({ rank: index + 1, id: item.path, label: item.title, domain: item.category, source: 'report_registry', summary: item.category }));
        startReviewSession(scopeKey, 'reports', 'report_inventory_review'); updateSessionSource(scopeKey, { type: 'report', name: 'local report registry', timestamp: new Date().toISOString(), verification: 'verified' }); updateSessionList(scopeKey, reportSessionItems); if (reportSessionItems.length > 0) setSessionFocus(scopeKey, { id: reportSessionItems[0].id, label: reportSessionItems[0].label, domain: reportSessionItems[0].domain, summary: reportSessionItems[0].summary, source: reportSessionItems[0].source });
      }
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
      const resolvedTarget = resolveHermesActionTarget({ message, intentFrame: intentFrame!, activeSession: getActiveSession(scopeKey), decisionState: getHermesDecisionState(scopeKey) });
      const item = packet.selectionMemory ? resolveFollowUp(message) : null;
      if (item) touchSelectionMemory();
      const targetLabel = resolvedTarget?.label || item?.title;
      handler = targetLabel
        ? actionResult(`**Ray Review Draft** — ${targetLabel}\n\n**Target:** ${targetLabel}\n**Why review is needed:** confirm evidence, scope, risk, and approval boundaries before any persistent or external action.\n**Source used:** ${resolvedTarget?.source || 'selection memory'}\n**Proposed decision:** approve, revise, or hold after reviewing the evidence.\n**Next safe action:** review this conversation-only draft and confirm the decision criteria.\n\nThis conversation only draft has not been saved or submitted; it was not submitted or executed. Status: not saved, not submitted, not executed.`, 'approval_local_draft', [resolvedTarget?.source || 'selection_memory', 'approval_policy'], { outcome: 'local_draft_only', title: targetLabel, status: 'not_saved' }, item ? [item] : [])
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
          uiActions = rayReviewCards.filter((card) => card.status === 'pending').slice(0, 5).map((card) => ({ title: card.title, status: card.status, category: card.category, priority: card.riskLevel, actionLabel: 'Open approval', actionType: 'open_approval', approvalId: card.id, href: '#rayreview', source: 'local_ray_review_registry', approvalRequired: true }));
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
    case 'active_session_continue': {
      const focus = getSessionFocusForContinuation(scopeKey);
      const list = getSessionListForContinuation(scopeKey);
      const activeSession = getActiveSession(scopeKey);
      const mode = activeSession?.activeMode || 'business_opportunity_review';
      if (mode === 'report_inventory_review') {
        if (/\b(?:review them|can we review|walkthrough|one by one|walk through)\b/i.test(lower)) {
          const reportList = list.length > 0 ? list.map((r, i) => `${i + 1}. ${r.label} — ${r.summary || r.domain}`).join('\n') : 'the available reports';
          handler = result(`I have the report list open. We can go through them one by one. I would start with ${list[0]?.label || 'the first report'}, depending on whether you want ${list[0]?.domain || 'operational status'} first.\n\n${reportList}\n\nWhich one would you like to start with? You can say "number 1," "next," or name the report.`, 'report_inventory_review_continue', ['active_session', 'report_registry']);
        } else if (/\b(?:start there|we can start there|let'?s start there|open number|number\s*\d+|next|previous)\b/i.test(lower)) {
          let targetIndex = 0;
          const numMatch = lower.match(/number\s*(\d+)/);
          if (numMatch) {
            targetIndex = parseInt(numMatch[1], 10) - 1;
          } else if (/\bprevious\b/i.test(lower) && focus) {
            const currentIdx = list.findIndex(r => r.label === focus.label);
            targetIndex = currentIdx > 0 ? currentIdx - 1 : 0;
          } else if (/\bnext\b/i.test(lower) && focus) {
            const currentIdx = list.findIndex(r => r.label === focus.label);
            targetIndex = currentIdx >= 0 ? currentIdx + 1 : 0;
          }
          const target = list[targetIndex];
          if (target) {
            setSessionFocus(scopeKey, { id: target.id, label: target.label, domain: target.domain, summary: target.summary, source: target.source });
            handler = result(`Let us look at **${target.label}**. This is a ${target.domain || 'operational'} report. ${target.summary || 'It covers current operational status.'}\n\nSay "next" to continue to the next report, or name a specific report number.`, 'report_inventory_item_review', ['active_session', 'report_registry']);
          } else {
            handler = result(`That is beyond the list. We have ${list.length} reports available. Say "next" to continue, or name a number between 1 and ${list.length}.`, 'report_inventory_out_of_range', ['active_session']);
          }
        } else if (focus) {
          handler = result(`Let us look at **${focus.label}**. This is a ${focus.domain || 'operational'} report. ${focus.summary || 'It covers current operational status.'}\n\nSay "next" to continue to the next report, or name a specific report number.`, 'report_inventory_item_review', ['active_session', 'report_registry']);
        } else {
          handler = result('I have the report list open. Say "review them one by one" to walk through, or name a specific report.', 'report_inventory_no_focus', ['active_session']);
        }
      } else {
        if (/\b(?:start there|we can start there|let'?s start there|start with the highest(?: scored)? one|start with (?:the )?(?:top|first) one)\b/i.test(lower)) {
          const target = focus || (list.length > 0 ? list[0] : null);
          if (target) {
            handler = result(`Let us start with **${target.label}**. ${target.summary || 'This is our entry-level offer.'} The score explanation is based on barrier to entry, value proposition clarity, and upsell potential. We can review the scoring factors, look at improvement steps, or prepare a Ray Review draft.\n\nSay "why did it get that score" for scoring details, "how can we improve it" for improvement suggestions, or "create a Ray Review draft for that" to prepare a review card.`, 'session_continue_start', ['active_session', 'business_opportunity_context']);
          } else {
            handler = result('I have an active session but no specific item is loaded. Say "pull up the business opportunity report" to refresh the list.', 'session_continue_no_focus', ['active_session']);
          }
        } else if (/\b(?:walk(?:\s+me)?(?:\s+through)?(?:\s+the)?(?:\s+full)?(?:\s+list)?|let'?s walkthrough|one by one|review them)\b/i.test(lower)) {
          if (list.length > 0) {
            const first = list[0];
            handler = result(`Let us walk through the full list one by one. Starting with item 1:\n\n**${first.label}** — ${first.summary || 'Entry-level offer.'}\n\n${first.evidence ? `Supporting evidence: ${first.evidence.join('; ')}.` : ''}\n\nThis is ranked #${first.rank || 1} based on barrier to entry, value proposition clarity, and upsell potential. Say "next" to continue to item 2, or ask "why did it get that score" for details on this item.`, 'session_walkthrough_start', ['active_session', 'business_opportunity_context']);
          } else {
            handler = result('I have an active session but the list is empty. Say "pull up the business opportunity report" to refresh.', 'session_walkthrough_empty', ['active_session']);
          }
        } else if (/\bnext\b/i.test(lower) && focus) {
          const currentIndex = list.findIndex(i => i.label === focus.label);
          const nextItem = list[currentIndex + 1];
          if (nextItem) {
            setSessionFocus(scopeKey, { id: nextItem.id, label: nextItem.label, domain: nextItem.domain, score: nextItem.score, summary: nextItem.summary, source: nextItem.source, evidence: nextItem.evidence });
            handler = result(`Item ${nextItem.rank || currentIndex + 2}: **${nextItem.label}** — ${nextItem.summary || 'Opportunity.'}\n\n${nextItem.evidence ? `Supporting evidence: ${nextItem.evidence.join('; ')}.` : ''}\n\nSay "next" to continue, or ask about scoring/improvement for this item.`, 'session_walkthrough_next', ['active_session', 'business_opportunity_context']);
          } else {
            handler = result('That is the end of the list. We have reviewed all items. You can say "create a Ray Review draft" for any item, or ask "how can we improve it" for next steps.', 'session_walkthrough_complete', ['active_session']);
          }
        } else if (/\b(?:what would stop us|what could stop us|what are the blockers|what are the risks|what could go wrong|what is the downside|why might this fail|blockers?|risks?)\b/i.test(lower) && focus) {
          const blockerThemes: Record<string, string[]> = {
            '$97 Credit & Funding Readiness Review': ['lead flow and prospect outreach', 'unclear offer scope or deliverables', 'fulfillment speed and response time', 'weak proof or missing case studies', 'checkout or follow-up automation not ready', 'upsell conversion to $297 plan not validated', 'compliance and expectation management'],
            '$297 Credit Assistant Plan': ['client retention and engagement', 'deliverable complexity', 'support load scaling', 'pricing perception vs. value delivered', 'fulfillment consistency across clients'],
            'Monthly Readiness Subscription': ['churn risk without visible progress', 'content freshness and relevance', 'engagement drop-off after initial signup', 'competitive alternatives at similar price'],
            'Funding Application Prep Sprint': ['client readiness and documentation', 'application turnaround time', 'approval rate variability', 'scope creep on complex cases', 'seasonal demand fluctuations'],
          };
          const itemBlockers = blockerThemes[focus.label] || ['lead flow and market validation', 'offer scope clarity', 'fulfillment capacity', 'proof and case studies', 'checkout readiness', 'upsell path validation', 'compliance management'];
          const blockerList = itemBlockers.map((b, i) => `${i + 1}. ${b.charAt(0).toUpperCase() + b.slice(1)}`).join('\n');
          handler = result(`The main blockers for **${focus.label}** are:\n\n${blockerList}\n\nThese are the typical friction points for this type of offer. Want me to prioritize them by impact, or focus on the one you think is the biggest risk right now?`, 'session_blocker_analysis', ['active_session', 'business_opportunity_context']);
        } else if (/\b(?:create.*(?:ray review|review card).*for (?:that|it|this)|draft.*(?:ray review|review).*for (?:that|it|this)|send.*(?:this|that).*to.*(?:ray review|review)|prepare.*(?:ray review|review).*for (?:this|that))\b/i.test(lower) && focus) {
          const draftText = `**Ray Review Draft** — ${focus.label}\n\n**Target:** ${focus.label}\n**Reason for review:** Evaluate go/no-go for this opportunity based on barrier to entry, value proposition, and upsell potential.\n**Source:** ${focus.source || 'active session context'}\n**Proposed decision:** Approve for development if lead flow, fulfillment, and proof requirements are met.\n**Next safe action:** Confirm this draft and I will prepare the formal Ray Review request.\n\nThis is a conversation-only draft: not saved, not submitted, and not executed.`;
          handler = result(draftText, 'session_ray_review_draft', ['active_session', 'business_opportunity_context']);
        } else if (focus) {
          handler = result(`We are looking at **${focus.label}**. ${focus.summary || ''}\n\nYou can say "why did it get that score" for scoring details, "how can we improve it" for improvement suggestions, "what would stop us" for blockers, or "create a Ray Review draft for that" to prepare a review card.`, 'session_continue_focus', ['active_session', 'business_opportunity_context']);
        } else {
          handler = result('I have an active business opportunity review session. Say "start with the highest scored one" to begin, "walk through the full list one by one" to review all, or name a specific opportunity.', 'session_continue_no_focus', ['active_session']);
        }
      }
      source = 'local'; break;
    }
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
  return { handler, usedSupabase, usedModel, supabaseStatus, supabaseTables, source, opportunityAdvisory, sourceSummary, uiActions, accessMatrix };
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
  const lower = message.toLowerCase();
  const intentFrame = buildIntentFrame(message);
  const routeDecision = routeHermesPriority({ message, currentPage: page || null, previousDomain: state.lastTopic, selectionMemory: getSelectionMemory(), intentFrame, scopeKey });

  // Conversation State Arbiter — resolves competing context signals
  const selectionMem = getSelectionMemory();
  const lastRec = selectionMem.lastRecommendation ? { title: selectionMem.lastRecommendation.title, domain: selectionMem.lastRecommendation.type === 'opportunity' ? 'business_opportunity' : state.lastTopic || 'general' } : null;
  const decisionState = getHermesDecisionState(scopeKey);
  const arbiterResult = resolveHermesConversationState({
    message, lower, intentFrame,
    activeSession: getActiveSession(scopeKey),
    lastRecommendation: lastRec,
    lastSuccessfulTrace: getLastSuccessfulTrace(scopeKey),
    selectionMemory: selectionMem,
    previousDomain: state.lastTopic,
    pageContext: page || null,
    decisionState,
  });

  // Override route when arbiter has higher-confidence resolution
  if (arbiterResult.conversationMove === 'safety_explanation_followup') {
    routeDecision.routeId = 'safety_explanation'; routeDecision.domain = 'safety'; routeDecision.intent = 'explain_safety_decision'; routeDecision.reason = arbiterResult.reasonForDecision;
  } else if (arbiterResult.conversationMove === 'response_depth_change') {
    updateHermesDecisionState(scopeKey, { responseMode: arbiterResult.responseMode });
    routeDecision.routeId = 'response_mode_change'; routeDecision.domain = arbiterResult.domain || 'last_answer'; routeDecision.intent = 'rerender_last_answer'; routeDecision.reason = arbiterResult.reasonForDecision;
  } else if (arbiterResult.conversationMove === 'source_provenance_question' && routeDecision.routeId !== 'trace_source_meta' && routeDecision.routeId !== 'cost_model_usage_status') {
    routeDecision.routeId = 'trace_source_meta';
    routeDecision.domain = 'routing_trace';
    routeDecision.intent = 'source_question';
    routeDecision.reason = arbiterResult.reasonForDecision;
  } else if (arbiterResult.conversationMove === 'last_recommendation_followup') {
    routeDecision.routeId = 'recommendation_explanation'; routeDecision.domain = arbiterResult.domain || 'general_advice'; routeDecision.intent = 'explain_recommendation'; routeDecision.reason = arbiterResult.reasonForDecision;
  } else if (arbiterResult.conversationMove === 'previous_answer_followup') {
    routeDecision.routeId = 'previous_answer_followup'; routeDecision.domain = arbiterResult.domain || 'last_answer'; routeDecision.intent = 'explain_previous_answer'; routeDecision.reason = arbiterResult.reasonForDecision;
  } else if (arbiterResult.conversationMove === 'timeline_recap' && routeDecision.routeId !== 'process_activity_status') {
    routeDecision.routeId = 'process_activity_status';
    routeDecision.domain = 'activity_summary';
    routeDecision.intent = /yesterday/i.test(message) ? 'yesterday_completed_summary' : 'today_completed_summary';
    routeDecision.reason = arbiterResult.reasonForDecision;
  } else if (['active_session_navigation', 'active_session_continuation'].includes(arbiterResult.conversationMove) && routeDecision.routeId !== 'active_session_continue') {
    routeDecision.routeId = 'active_session_continue';
    routeDecision.domain = arbiterResult.domain || 'unknown';
    routeDecision.intent = 'session_continuation';
    routeDecision.reason = arbiterResult.reasonForDecision;
  } else if (arbiterResult.conversationMove === 'general_advisor' && ['trace_source_meta', 'cost_model_usage_status'].includes(routeDecision.routeId)) {
    routeDecision.routeId = 'advisory_followup';
    routeDecision.domain = arbiterResult.domain || 'general_advice';
    routeDecision.intent = 'evaluate_prior_advice';
    routeDecision.reason = arbiterResult.reasonForDecision;
  }
  const advisoryProducingRoute = ['revenue_reasoning', 'general_advisor', 'nexus_build_planning', 'opportunity_aware_recommendation', 'memory_followup'].includes(routeDecision.routeId) || (routeDecision.routeId === 'local_reasoning' && ['business_opportunity', 'monetization'].includes(routeDecision.domain));
  const topicNeutralRoute = ['trace_source_meta', 'cost_model_usage_status', 'casual_common', 'casual_identity', 'process_activity_status', 'readiness_operating_status', 'process_settings_reports_status', 'capability_status', 'advisory_followup'].includes(routeDecision.routeId);
  if (!advisoryProducingRoute && !topicNeutralRoute && routeDecision.domain !== 'unknown') clearAdvisoryContinuity();
  if (!['trace_source_meta', 'cost_model_usage_status', 'fallback_continuation', 'fallback_clarification'].includes(routeDecision.routeId)) clearFallbackContinuity();
  const packet = buildContextPacket({ routeDecision, message, session: input.userSession, pageContext: input.currentPageContext || null, conversationState: state });
  const executed = await executeRoute(routeDecision, packet, message, scopeKey, intentFrame);
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
      if (reviewResult.topItem) updateHermesDecisionState(scopeKey, { lastRecommendation: { label: reviewResult.topItem.label, domain: 'business_opportunities', reason: 'it has the lowest barrier to entry, the clearest value proposition, and the strongest natural upsell path.', source: reviewResult.topItem.source, timestamp: new Date().toISOString() }, lastAnswer: { text: reviewResult.text, route: routeDecision.routeId, intent: 'domain_review', domain: 'business_opportunities', sources: [reviewResult.sourceUsed], usedSupabase: executed.usedSupabase, assumptions: ['ranking uses the current opportunity scoring framework'], blockers: [], confidence: 'medium', target: { id: reviewResult.topItem.id, label: reviewResult.topItem.label, type: 'recommendation' }, timestamp: new Date().toISOString() } });
      setLastSuccessfulTrace(scopeKey, { route: routeDecision.routeId, domain: routeDecision.domain, source: executed.source, usedSupabase: executed.usedSupabase, usedModel: executed.usedModel, sources: executed.handler.sources, intentFrame: { intent: intentFrame.intent, domain: intentFrame.domain, action: intentFrame.action }, sessionState: { activeMode: session?.activeMode, activeDomain: session?.activeDomain, itemCount: reviewResult.itemCount, focusLabel: reviewResult.topItem?.label }, timestamp: new Date().toISOString() });
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
      setLastSuccessfulTrace(scopeKey, { route: routeDecision.routeId, domain: routeDecision.domain, source: executed.source, usedSupabase: executed.usedSupabase, usedModel: executed.usedModel, sources: executed.handler.sources, sessionState: { activeMode: session?.activeMode, activeDomain: session?.activeDomain, focusLabel: session?.currentFocus?.label }, timestamp: new Date().toISOString() });
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
      setLastSuccessfulTrace(scopeKey, { route: routeDecision.routeId, domain: routeDecision.domain, source: executed.source, usedSupabase: executed.usedSupabase, usedModel: executed.usedModel, sources: executed.handler.sources, sessionState: { activeMode: session?.activeMode, activeDomain: session?.activeDomain, focusLabel: session?.currentFocus?.label }, timestamp: new Date().toISOString() });
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
    setLastSuccessfulTrace(scopeKey, { route: routeDecision.routeId, domain: routeDecision.domain, source: executed.source, usedSupabase: executed.usedSupabase, usedModel: executed.usedModel, sources: executed.handler.sources, sessionState: { activeMode: session?.activeMode, activeDomain: session?.activeDomain, focusLabel: session?.currentFocus?.label }, timestamp: new Date().toISOString() });
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

  const topicNeutralRoutes = ['trace_source_meta', 'cost_model_usage_status', 'casual_common', 'casual_identity', 'process_activity_status', 'readiness_operating_status', 'process_settings_reports_status', 'system_health_report', 'page_connection_status', 'page_context_status', 'capability_status', 'fallback_clarification'];
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
  const responseMode = routeDecision.routeId === 'response_mode_change' ? getHermesDecisionState(scopeKey).responseMode : arbiterResult.responseMode;
  const finalText = routeDecision.routeId === 'response_mode_change' || routeDecision.routeId === 'trace_source_meta' ? text : renderResponseMode({ text, mode: responseMode, domain: routeDecision.domain });
  const voiceReadyResponse = renderVoiceReady(finalText, responseMode === 'audit' ? 'screen' : 'voice_ready');

  if (routeDecision.routeId === 'safety_gate') {
    const isEmail = /\b(?:send|email)\b/i.test(message);
    updateHermesDecisionState(scopeKey, { lastSafetyDecision: { request: message, blockedAction: isEmail ? 'external email send' : 'prohibited or approval-gated execution', reason: isEmail ? 'sending email to clients is a real external action that requires approval.' : 'the request would perform a real external or protected action.', safeAlternatives: isEmail ? ['draft the email', 'prepare an approval-gated Ray Review item'] : ['prepare a conversation-only draft', 'prepare a Ray Review item'], timestamp: new Date().toISOString() } });
  }

  const recommendationTarget = resolvedEntities[0]?.title || (['business_local_reasoning', 'selection_recommendation'].includes(executed.handler.internalTrace) ? '$97 Credit & Funding Readiness Review' : null);
  if (recommendationTarget) updateHermesDecisionState(scopeKey, { lastRecommendation: { label: recommendationTarget, domain: routeDecision.domain, reason: 'it has the lowest launch barrier, a clear entry offer, and a defined upsell path.', source: executed.handler.sources[0] || 'local reasoning', timestamp: new Date().toISOString() } });

  if (!['trace_source_meta', 'cost_model_usage_status', 'response_mode_change'].includes(routeDecision.routeId)) {
    updateHermesDecisionState(scopeKey, { responseMode: responseMode === 'casual' ? 'ceo' : responseMode, lastAnswer: { text, route: routeDecision.routeId, intent: routeDecision.intent, domain: routeDecision.domain, sources: executed.handler.sources, usedSupabase: executed.usedSupabase, assumptions: executed.source === 'reasoning' ? ['local reasoning was used'] : [], blockers: executed.sourceSummary?.blocker ? [executed.sourceSummary.blocker] : executed.handler.actionProof?.outcome === 'blocked' ? [executed.handler.actionProof.reason || 'action blocked'] : [], confidence, sourceStatus: executed.sourceSummary?.status, sourceRowCount: executed.sourceSummary?.rowCount, target: recommendationTarget ? { label: recommendationTarget, type: 'recommendation' } : activeSession?.currentFocus ? { id: activeSession.currentFocus.id, label: activeSession.currentFocus.label, type: activeSession.activeMode === 'report_inventory_review' ? 'report' : 'session_item' } : undefined, timestamp: new Date().toISOString() } });
  }

  // Persist lastSuccessfulTrace for non-fallback, non-trace answers
  if (routeDecision.routeId !== 'fallback_clarification' && routeDecision.routeId !== 'trace_source_meta' && routeDecision.routeId !== 'cost_model_usage_status' && routeDecision.routeId !== 'safety_gate') {
    setLastSuccessfulTrace(scopeKey, { route: routeDecision.routeId, domain: routeDecision.domain, source: executed.source, usedSupabase: executed.usedSupabase, usedModel: executed.usedModel, sources: executed.handler.sources, sessionState: activeSession ? { activeMode: activeSession.activeMode, activeDomain: activeSession.activeDomain, itemCount: activeSession.activeList?.length, focusLabel: activeSession.currentFocus?.label } : undefined, timestamp: new Date().toISOString() });
  }

  return {
    text: finalText, answer: finalText, activationLevel: routeDecision.activationLevel, route: routeDecision.routeId, routeDecision,
    sourceMode: executed.source, usedModel: executed.usedModel, modelMetadata: { route: modelRoute },
    usedSupabase: executed.usedSupabase, supabaseStatus: executed.supabaseStatus, resolvedEntities,
    rememberedContext: anyMemoryUsed, actionIntent: routeDecision.actionPolicy !== 'none' ? message : null,
    approvalRequired: routeDecision.actionPolicy === 'approval_required', safeNextActions: executed.handler.nextActions,
    diagnostics: { routeDecision, contextPacketSummary: packet.summary, answerBuilder: executed.handler.internalTrace, domain: { domain: routeDecision.domain }, memoryUsed: selectionOrTraceMemoryUsed || Boolean(packet.advisoryContinuity), longTermMemoryUsed: Boolean(packet.longTermBusinessContext), advisoryContinuityUsed: Boolean(packet.advisoryContinuity), memoryRejected, diagnosticSuppressedForUser: rendered.diagnosticSuppressed },
    intent: { route: routeDecision.routeId, intent: routeDecision.intent, confidence, reason: routeDecision.reason },
    modelRoute: { route: modelRoute, reason: routeDecision.reason }, reasoning: { decision: reasoningPlan.decision === 'route-to-model' ? 'route-to-model' : reasoningPlan.decision === 'answer-with-context' ? 'answer-with-context' : 'answer-locally', confidence, reasoning: reasoningPlan.reasoning },
    capabilityBadge: getCapabilityReport().badgeText, confidence, source: executed.source, timestamp: new Date().toISOString(),
    intentFrame, activeSession, voiceReady: voiceReadyResponse, uiActions: executed.uiActions, accessMatrix: executed.accessMatrix,
  };
}

export function getCapabilityBadge(): string { return getCapabilityReport().badgeText; }
