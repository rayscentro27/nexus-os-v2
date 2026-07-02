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
} from './hermesConversationState';
import { getSelectionMemory, setLastTurnTraceMemory, touchSelectionMemory } from './hermesMemoryStores';
import { logRoutingTrace } from './hermesRoutingTrace';
import { reportRegistry } from '../data/reportRegistry.js';
import { reasonFromRouteDecision } from './hermesReasoningEngine';

export interface BrainPipelineInput {
  message: string; surface?: 'full_workroom' | 'inline_drawer' | 'specialist' | 'unknown';
  currentRoute?: string; currentPageContext?: Record<string, unknown> | null;
  conversationHistory?: unknown[]; userSession?: unknown; tenantId?: string;
  pageId?: string; route?: string; isBackgroundJob?: boolean;
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
  source: 'local' | 'supabase' | 'model' | 'conversation-followup' | 'capability' | 'reasoning'; timestamp: string;
}

const OPPORTUNITIES: ConversationItem[] = [
  { id: 'readiness-review', title: '$97 Credit & Funding Readiness Review', type: 'opportunity', category: 'GoClear/Apex', revenueRange: '$97 entry offer', status: 'low-cost launch' },
  { id: 'assistant-plan', title: '$297 Credit Assistant Plan', type: 'opportunity', category: 'GoClear/Apex', revenueRange: '$297', status: 'upsell' },
  { id: 'monthly-readiness', title: 'Monthly Readiness Subscription', type: 'opportunity', category: 'GoClear/Apex', revenueRange: 'recurring', status: 'retention offer' },
  { id: 'funding-prep', title: 'Funding Application Prep Sprint', type: 'opportunity', category: 'Apex', revenueRange: '$500–$1,500', status: 'service offer' },
];

const result = (userAnswer: string, handler: string, sources: string[], selectedEntities: ConversationItem[] = [], nextActions: string[] = []): HermesHandlerResult => ({ userAnswer, internalTrace: handler, selectedEntities, sources, nextActions, safeFallbackAnswer: userAnswer });
const recommendation = () => `For a business you can start within 30 days, I recommend **$97 Credit & Funding Readiness Review** first. It is inexpensive to launch, matches GoClear/Apex, and creates a path to the $297 assistant plan and Monthly Readiness Subscription.\n\n**Next safe action:** prepare the intake, scorecard, and a draft Ray Review card. Any checkout activation, customer contact, or charge remains approval-gated.`;
const implementation = (item: ConversationItem) => `Here is the implementation plan for **${item.title}**:\n\n1. Define the promise, eligibility rules, deliverables, and exclusions.\n2. Build the intake and readiness scorecard.\n3. Create checkout and fulfillment in test mode.\n4. Run five manual pilots and capture conversion evidence.\n5. Prepare the refined plan for Ray Review.\n\nNo email, charge, publishing, or live execution occurs without explicit approval.`;
const listOpportunities = (label: string) => `Business opportunities (${label}):\n\n${OPPORTUNITIES.map((item, index) => `${index + 1}. **${item.title}** — ${item.status}; ${item.revenueRange}.`).join('\n')}`;

async function executeRoute(decision: RouteDecision, packet: ReturnType<typeof buildContextPacket>, message: string) {
  const lower = message.toLowerCase();
  let usedSupabase = false, usedModel = false, supabaseStatus = 'not_used';
  let supabaseTables: string[] = [];
  let source: BrainPipelineResponse['source'] = 'local';
  let handler: HermesHandlerResult;

  switch (decision.routeId) {
    case 'safety_gate':
      handler = result('I cannot execute that. Sending, publishing, charging, disputes, destructive data changes, schedulers, and live/funded trading are blocked or require explicit Ray approval through Ray Review. I can prepare a non-executed review draft.', 'safety_gate', ['safety_policy']); break;
    case 'trace_source_meta':
    case 'cost_model_usage_status':
      handler = result(answerHermesTraceQuestion(message, packet.routingTrace, { routeDecision: decision }) || 'No prior routing record is available.', 'trace_question_handler', ['last_non_trace_route']); break;
    case 'casual_identity':
      handler = result(answerConversation(message, classifyConversationIntent(message)) || "I'm Hermes, the Nexus operating advisor.", 'casual_conversation', ['local_conversation']); break;
    case 'capability_status':
      handler = result(answerCapabilityQuestion(message) || getCapabilityReport().capabilities.map(item => `${item.name}: ${item.userFacing}`).join('\n'), 'capability_status', ['capability_registry']); source = 'capability'; break;
    case 'process_settings_reports_status':
      if (decision.domain === 'trading') { const trading = answerTradingQuestion(message, { routeDecision: decision }); handler = result(trading.text, trading.handler, [trading.source]); }
      else if (decision.domain === 'reports' && decision.intent === 'inventory_question') { const reports = reportRegistry.filter(item => item.available).slice(0, 10); handler = result(`Available local reports:\n\n${reports.map((item, index) => `${index + 1}. **${item.title}** — ${item.category}; ${item.path}`).join('\n')}`, 'report_inventory', ['report_registry']); }
      else if (/ceo version|ceo summary/.test(lower)) handler = result(buildCeoDailySummary('today'), 'ceo_summary', ['activity_journal']);
      else if (/what did (?:you|we) do today|daily summary/.test(lower)) handler = result(buildDailySummary('today'), 'daily_summary', ['activity_journal']);
      else handler = result(`Local ${decision.domain.replace(/_/g, ' ')} evidence is allowed for this status question. No model or selection memory was used.`, 'local_status', ['local_reports']);
      break;
    case 'approval_action_prepare': {
      const item = packet.selectionMemory ? resolveFollowUp(message) : null;
      if (item) touchSelectionMemory();
      handler = result(`I prepared a draft Ray Review request${item ? ` for **${item.title}**` : ''}. It is not submitted or executed. Review the target, scope, and expected result before approving any state-changing action.`, 'approval_draft', ['selection_memory', 'approval_policy'], item ? [item] : []); break;
    }
    case 'explicit_domain_retrieval':
      if (decision.domain === 'trading') {
        const trading = answerTradingQuestion(message, { routeDecision: decision }); handler = result(trading.text, trading.handler, [trading.source]); source = 'reasoning';
      } else if (decision.domain === 'reports') {
        handler = result('Available local report groups include activation/operations, Ray Review, trading proof, Hermes routing, research, revenue, and safety audits. Open Reports for the indexed files and timestamps.', 'report_inventory', ['report_registry']);
      } else if (isSupabaseAllowed(decision)) {
        const live = await buildLiveSupabaseContext(message); usedSupabase = live.liveData; supabaseStatus = live.sourceType; supabaseTables = live.tablesQueried || [];
        if (decision.domain === 'business_opportunity') {
          handler = result(`${listOpportunities(live.liveData ? 'live query plus normalized offer context' : 'clearly labeled static fallback')}\n\n${live.text}`, live.liveData ? 'business_opportunity_inventory_live' : 'business_opportunity_inventory_fallback', live.liveData ? supabaseTables : ['static_offer_context']);
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
      else handler = result(`I can reason from the allowed ${decision.domain.replace(/_/g, ' ')} context, but I need a concrete decision or entity to produce a useful plan.`, 'domain_local_reasoning', packet.longTermBusinessContext ? ['long_term_business_context'] : ['local_context']);
      source = 'reasoning'; break;
    case 'model_reasoning': {
      if (!isModelAllowed(decision)) throw new Error('RouteDecision forbids model execution');
      const model = await hermesModelChat(message, { pageSummary: String(packet.pageContext?.pageId || '') || undefined }); usedModel = model.source === 'model';
      handler = result(model.text || 'The required model route did not return a verified answer.', usedModel ? 'model_reasoning' : 'model_unavailable', [model.source || 'model_unknown']); source = usedModel ? 'model' : 'local'; break;
    }
    default:
      handler = result('I do not have enough current page, domain, record, or eligible selection context to answer that safely. Name the target once and I will continue.', 'fallback_clarification', ['none']);
  }
  return { handler, usedSupabase, usedModel, supabaseStatus, supabaseTables, source };
}

export async function handleHermesMessage(input: BrainPipelineInput): Promise<BrainPipelineResponse> {
  const message = input.message.trim();
  const surface = input.surface || 'unknown';
  const page = String(input.pageId || input.currentPageContext?.pageId || '');
  const state = getConversationState();
  const routeDecision = routeHermesPriority({ message, currentPage: page || null, previousDomain: state.lastTopic, selectionMemory: getSelectionMemory() });
  const packet = buildContextPacket({ routeDecision, message, session: input.userSession, pageContext: input.currentPageContext || null, conversationState: state });
  const executed = await executeRoute(routeDecision, packet, message);
  const rendered = renderHermesAnswer(executed.handler, routeDecision);
  const text = rendered.text;
  const resolvedEntities = executed.handler.selectedEntities;
  const selectionOrTraceMemoryUsed = Boolean(packet.lastTrace || packet.selectionMemory);
  const anyMemoryUsed = selectionOrTraceMemoryUsed || Boolean(packet.longTermBusinessContext);
  const memoryRejected = Boolean(getSelectionMemory().lastList.length) && !packet.selectionMemory && !packet.lastTrace;
  const modelRoute = executed.usedModel ? 'primary_model' : routeDecision.modelPolicy === 'forbidden' ? 'no_model' : 'local_reasoning';
  const reasoningPlan = reasonFromRouteDecision(routeDecision, packet.summary);

  addConversationMessage('user', message); addConversationMessage('assistant', text);
  if (routeDecision.routeId !== 'trace_source_meta' && routeDecision.routeId !== 'cost_model_usage_status') {
    updateConversationContext({ lastIntent: routeDecision.intent, lastTopic: routeDecision.domain, lastPage: page || null, lastActionPlan: /implementation plan/i.test(text) ? text.slice(0, 2000) : null });
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
    domainOverrideApplied: routeDecision.routeId === 'explicit_domain_retrieval', casualOverrideApplied: routeDecision.routeId === 'casual_identity', invariantViolations: [],
    questionType: routeDecision.routeId === 'trace_source_meta' || routeDecision.routeId === 'cost_model_usage_status' ? 'trace_meta' : routeDecision.actionPolicy !== 'none' ? 'action' : routeDecision.routeId === 'casual_identity' ? 'casual' : routeDecision.activationLevel === 1 ? 'status' : 'domain_reasoning',
    traceTarget: routeDecision.memoryPolicy === 'last_trace_only' ? 'last_answer' : 'current_question', finalAnswerHandler: executed.handler.internalTrace,
    diagnosticOnly: routeDecision.diagnosticsPolicy !== 'hidden', diagnosticSuppressedForUser: rendered.diagnosticSuppressed,
    domainOverrideReason: routeDecision.reason,
    routeDecision, contextPacketSummary: packet.summary, memoryPolicyApplied: routeDecision.memoryPolicy,
    retrievalPolicyApplied: routeDecision.retrievalPolicy, modelPolicyApplied: routeDecision.modelPolicy,
    diagnosticsPolicyApplied: routeDecision.diagnosticsPolicy, actionPolicyApplied: routeDecision.actionPolicy,
    blockedContext: routeDecision.blockedContext, allowedContext: routeDecision.allowedContext,
    handlerResultSummary: { handler: executed.handler.internalTrace, sources: executed.handler.sources, selectedCount: resolvedEntities.length },
  });

  const confidence = routeDecision.confidence >= .8 ? 'high' : routeDecision.confidence >= .5 ? 'medium' : 'low';
  return {
    text, answer: text, activationLevel: routeDecision.activationLevel, route: routeDecision.routeId, routeDecision,
    sourceMode: executed.source, usedModel: executed.usedModel, modelMetadata: { route: modelRoute },
    usedSupabase: executed.usedSupabase, supabaseStatus: executed.supabaseStatus, resolvedEntities,
    rememberedContext: anyMemoryUsed, actionIntent: routeDecision.actionPolicy !== 'none' ? message : null,
    approvalRequired: routeDecision.actionPolicy === 'approval_required', safeNextActions: executed.handler.nextActions,
    diagnostics: { routeDecision, contextPacketSummary: packet.summary, answerBuilder: executed.handler.internalTrace, domain: { domain: routeDecision.domain }, memoryUsed: selectionOrTraceMemoryUsed, longTermMemoryUsed: Boolean(packet.longTermBusinessContext), memoryRejected, diagnosticSuppressedForUser: rendered.diagnosticSuppressed },
    intent: { route: routeDecision.routeId, intent: routeDecision.intent, confidence, reason: routeDecision.reason },
    modelRoute: { route: modelRoute, reason: routeDecision.reason }, reasoning: { decision: reasoningPlan.decision === 'route-to-model' ? 'route-to-model' : reasoningPlan.decision === 'answer-with-context' ? 'answer-with-context' : 'answer-locally', confidence, reasoning: reasoningPlan.reasoning },
    capabilityBadge: getCapabilityReport().badgeText, confidence, source: executed.source, timestamp: new Date().toISOString(),
  };
}

export function getCapabilityBadge(): string { return getCapabilityReport().badgeText; }
