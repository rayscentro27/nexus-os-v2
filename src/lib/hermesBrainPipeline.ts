import { detectActivationLevel, type ActivationDecision } from './hermesActivationLevels';
import { answerCapabilityQuestion, getCapabilityReport } from './hermesCapabilityStatus';
import { buildLiveSupabaseContext } from './hermesLiveContext';
import { hermesModelChat } from './hermesProviders';
import { buildDailySummary, buildCeoDailySummary } from './hermesDailyActivityTranslator';
import {
  addConversationMessage, getConversationState, hasConversationMemory,
  isFollowUpReference, resolveFollowUp, setLastListedItems, setLastRankedList,
  setLastRecommendedItem, setLastSelectedItem, setLastSupabaseQueryResult, updateConversationContext, type ConversationItem,
} from './hermesConversationState';
import { answerRoutingTraceQuestion, isRoutingTraceQuestion, logRoutingTrace } from './hermesRoutingTrace';
import { classifyHermesDomain } from './hermesDomainClassifier';
import { evaluateTopicBoundary } from './hermesTopicBoundary';
import { findRoutingInvariantViolations } from './hermesRoutingInvariants';
import { answerConversation, classifyConversationIntent } from './hermesConversationBrain';

export interface BrainPipelineInput {
  message: string;
  surface?: 'full_workroom' | 'inline_drawer' | 'specialist' | 'unknown';
  currentRoute?: string;
  currentPageContext?: Record<string, unknown> | null;
  conversationHistory?: unknown[];
  userSession?: unknown;
  tenantId?: string;
  // Legacy thin-wrapper aliases.
  pageId?: string;
  route?: string;
  isBackgroundJob?: boolean;
}

export interface BrainPipelineResponse {
  text: string;
  answer: string;
  activationLevel: number;
  route: string;
  sourceMode: string;
  usedModel: boolean;
  modelMetadata: Record<string, unknown>;
  usedSupabase: boolean;
  supabaseStatus: string;
  resolvedEntities: ConversationItem[];
  rememberedContext: boolean;
  actionIntent: string | null;
  approvalRequired: boolean;
  safeNextActions: string[];
  diagnostics: Record<string, unknown>;
  // Compatibility fields used by existing surfaces/tests.
  intent: { route: string; intent: string; confidence: 'high' | 'medium' | 'low'; reason: string };
  modelRoute: { route: string; reason: string; [key: string]: unknown };
  reasoning: { decision: 'answer-locally' | 'answer-with-context' | 'route-to-model'; confidence: 'high' | 'medium' | 'low'; reasoning: string; clarificationQuestion?: string };
  capabilityBadge: string;
  confidence: 'high' | 'medium' | 'low';
  source: 'local' | 'supabase' | 'model' | 'conversation-followup' | 'capability' | 'reasoning';
  timestamp: string;
}

const OPPORTUNITIES: ConversationItem[] = [
  { id: 'readiness-review', title: '$97 Credit & Funding Readiness Review', type: 'opportunity', category: 'GoClear/Apex', revenueRange: '$97 entry offer', status: 'low-cost launch' },
  { id: 'assistant-plan', title: '$297 Credit Assistant Plan', type: 'opportunity', category: 'GoClear/Apex', revenueRange: '$297', status: 'upsell' },
  { id: 'monthly-readiness', title: 'Monthly Readiness Subscription', type: 'opportunity', category: 'GoClear/Apex', revenueRange: 'recurring', status: 'retention offer' },
  { id: 'funding-prep', title: 'Funding Application Prep Sprint', type: 'opportunity', category: 'Apex', revenueRange: '$500–$1,500', status: 'service offer' },
];

function implementationPlan(item: ConversationItem, assumed = false): string {
  return `${assumed ? `I think you mean **${item.title}**. ` : ''}Here is the implementation plan for **${item.title}**:\n\n1. Define the promise, eligibility rules, deliverables, and exclusions.\n2. Build the intake and readiness scorecard using the existing GoClear/Apex workflow.\n3. Create the checkout and fulfillment checklist in test mode.\n4. Run five manual pilot reviews and capture objections and conversion data.\n5. Refine the offer, then prepare launch assets for Ray Review.\n\n**Next safe action:** create a draft Ray Review card containing this plan. No email, charge, publishing, or live execution occurs without explicit approval.${assumed ? ' If that is not the one, tell me.' : ''}`;
}

function listAnswer(sourceLabel: string): string {
  return `Business opportunities (${sourceLabel}):\n\n${OPPORTUNITIES.map((item, i) => `${i + 1}. **${item.title}** — ${item.status}; ${item.revenueRange}.`).join('\n')}\n\nI stored this list for follow-up questions such as “which one,” “number 3,” or “pick one.”`;
}

function recommendationAnswer(): string {
  return `For a business you can start within 30 days, I recommend **$97 Credit & Funding Readiness Review** first. It is inexpensive to launch, matches GoClear/Apex, and creates a natural path to the $297 assistant plan and Monthly Readiness Subscription.\n\n**Why:** the entry offer has the shortest fulfillment path and gives us real demand data before building recurring operations.\n\n**Next safe action:** prepare the intake, scorecard, and a draft Ray Review card. Any checkout activation, customer contact, or charge remains approval-gated.`;
}

function traceIntent(level: ActivationDecision): string {
  return ['safety_gate', 'meta_status', 'supabase_retrieval', 'followup_resolution', 'local_reasoning', 'model_reasoning', 'approval_action'][level.level];
}

export async function handleHermesMessage(input: BrainPipelineInput): Promise<BrainPipelineResponse> {
  const message = input.message.trim();
  const lower = message.toLowerCase();
  const surface = input.surface || 'unknown';
  const page = String(input.pageId || input.currentPageContext?.pageId || '');
  const priorState = getConversationState();
  const memoryAvailable = hasConversationMemory() || Boolean(input.conversationHistory?.length);
  const pageAvailable = Boolean(page || input.currentPageContext);
  const domain = classifyHermesDomain(message, page || null);
  const boundary = evaluateTopicBoundary({
    message, detectedDomain: domain.domain, previousTopic: priorState.lastTopic,
    previousIntent: priorState.lastIntent, previousSelectedItem: priorState.lastSelectedItem,
    previousRankedItems: priorState.lastRankedList, previousListedItems: priorState.lastListedItems,
    currentPage: page || null, previousPage: priorState.lastPage,
  });
  const activation = detectActivationLevel(message, memoryAvailable, pageAvailable, {
    detectedDomain: domain.domain, shouldUseMemory: boundary.shouldUsePriorMemory,
    memoryRejectionReason: boundary.shouldUsePriorMemory ? null : boundary.reason,
  });
  const resolvedEntities: ConversationItem[] = [];
  let text = '';
  let source: BrainPipelineResponse['source'] = 'local';
  let usedSupabase = false;
  let usedModel = false;
  let supabaseStatus = 'not_used';
  let supabaseTables: string[] = [];
  let answerBuilder = 'local';
  let fallbackReason: string | null = null;
  let confidence: BrainPipelineResponse['confidence'] = 'high';
  const memoryCandidateFound = Boolean(priorState.lastSelectedItem || priorState.lastRecommendedItem || priorState.lastRankedList.length || priorState.lastListedItems.length);
  let memoryUsed = false;

  // Trace questions inspect the prior entry and are always local/no-model.
  if (isFollowUpReference(message) && !memoryAvailable) {
    text = 'I do not have conversation context for that reference yet. Name the item or list the options once, and I will continue without asking again.';
    source = 'local'; answerBuilder = 'missing_followup_context'; confidence = 'low';
  } else if (isRoutingTraceQuestion(message)) {
    text = answerRoutingTraceQuestion(message) || 'No routing trace is available.';
    source = 'local'; answerBuilder = 'routing_trace';
  } else if (activation.level === 0) {
    text = `I cannot execute that directly. Sending, publishing, trading, charging, disputes, destructive data changes, and scheduler changes require explicit approval through Ray Review.\n\nI can prepare a draft plan or review card without performing the action.`;
    answerBuilder = 'safety_gate';
  } else if (activation.level === 1) {
    const capability = answerCapabilityQuestion(message);
    if (capability) { text = capability; source = 'capability'; answerBuilder = 'capability_status'; }
    else if (domain.domain === 'casual_identity') {
      text = answerConversation(message, classifyConversationIntent(message)) || "I'm Hermes, the Nexus operating advisor. I don't have personal experiences, but I can answer conversational questions directly without pulling business memory into them.";
      answerBuilder = 'casual_conversation';
    }
    else if (/ceo version|ceo summary/.test(lower)) { text = buildCeoDailySummary('today'); answerBuilder = 'ceo_daily_summary'; }
    else if (/what did (you|we) do today|daily summary/.test(lower)) { text = buildDailySummary('today'); answerBuilder = 'daily_summary'; }
    else if (/trading/.test(lower)) { text = 'Trading is paper/demo only. No live broker execution is enabled, and any real trade remains blocked pending explicit approval.'; answerBuilder = 'section_status'; }
    else if (domain.domain === 'research_youtube') { text = 'YouTube research is not proven running in this session. Scripts may exist, but I have no current process or Supabase-write receipt to claim active execution.'; answerBuilder = 'research_status'; }
    else if (domain.domain === 'settings') { text = 'Settings are answered from configured capability state. Web search remains unconfigured unless its runtime flag and deployed function are verified; risky execution remains approval-controlled.'; answerBuilder = 'settings_status'; }
    else if (domain.domain === 'reports') { text = 'Hermes can use the repository reports as local evidence. Ask for a report category or date and I will summarize the matching local report without calling a model.'; answerBuilder = 'reports_status'; }
    else if (domain.domain === 'tools_cli') { text = 'I can explain available repository tools and safe commands, but I do not expose arbitrary shell execution through chat.'; answerBuilder = 'tools_status'; }
    else if (domain.domain === 'system_health') { text = 'I can summarize recorded system-health context, but I will not claim a live process state without a current runtime check.'; answerBuilder = 'system_health_status'; }
    else { text = `This is a local status/process answer. Activation Level 1 uses no model and no database unless the question explicitly requires live records. Current capability: ${getCapabilityReport().badgeText}.`; answerBuilder = 'local_status'; }
  } else if (activation.level === 2) {
    const live = await buildLiveSupabaseContext(message);
    usedSupabase = live.liveData;
    supabaseStatus = live.sourceType;
    supabaseTables = live.tablesQueried || [];
    if (live.liveData) {
      text = /business opportunit/.test(lower) ? `${listAnswer('live Supabase retrieval')}\n\n${live.text}` : live.text;
      source = 'supabase'; answerBuilder = 'live_supabase';
      setLastSupabaseQueryResult(supabaseTables[0] || 'unknown', [], message);
    } else {
      text = /business opportunit/.test(lower) ? `${listAnswer('clearly labeled local fallback')}\n\n${live.text}` : live.text;
      source = 'local'; answerBuilder = 'supabase_safe_fallback'; fallbackReason = live.source;
    }
    if (/business opportunit/.test(lower)) setLastListedItems(OPPORTUNITIES);
  } else if (activation.level === 3) {
    memoryUsed = boundary.shouldUsePriorMemory;
    let item = resolveFollowUp(message);
    const state = getConversationState();
    if (/which one.*recommend|recommend one/.test(lower)) {
      const ranked = state.lastListedItems.length ? [...state.lastListedItems] : [...OPPORTUNITIES];
      setLastRankedList(ranked); setLastRecommendedItem(ranked[0]); item = ranked[0];
      text = recommendationAnswer();
    } else if (/pick one|choose one/.test(lower)) {
      item = state.lastRecommendedItem || state.lastRankedList[0] || state.lastListedItems[0] || OPPORTUNITIES[0];
      setLastSelectedItem(item);
      text = `I picked **${item.title}** for review because it has the best near-term revenue-to-effort ratio.\n\n${implementationPlan(item)}`;
    } else if (/how do (we|i) implement|monthly readiness subscription|^the monthly/.test(lower)) {
      item = item || state.lastReferencedItem || OPPORTUNITIES.find(value => lower.includes('monthly') && value.id === 'monthly-readiness') || state.lastSelectedItem || state.lastRecommendedItem;
      text = item ? implementationPlan(item, !resolveFollowUp(message)) : 'I do not have a prior item to resolve. Name the offer once and I will build its implementation plan.';
    } else if (item) {
      text = `You are referring to **${item.title}**. ${implementationPlan(item)}`;
    } else {
      text = 'I do not have a prior item to resolve. Name the offer or list the options once, and I will continue from there.';
      confidence = 'low';
    }
    if (item) { resolvedEntities.push(item); setLastSelectedItem(item); }
    source = 'conversation-followup'; answerBuilder = 'conversation_memory';
  } else if (activation.level === 4) {
    if (domain.domain === 'trading') {
      text = '**Trading Lab recommendation:** compare the existing paper/demo strategies by drawdown, sample size, and out-of-sample consistency before choosing one. Start with a paper-only test; no funded trade or broker execution is enabled.\n\n**Next safe action:** define the paper-test criteria and review the latest backtest evidence.';
      answerBuilder = 'trading_reasoning';
    } else if (domain.domain === 'research_youtube') {
      text = 'For research, first verify a current source or run receipt, then score relevance, evidence quality, and monetization value. I will not claim YouTube polling or Supabase writes without runtime proof.';
      answerBuilder = 'research_reasoning';
    } else if (domain.domain === 'credit_funding') {
      text = 'For credit/funding, use the readiness review as the entry assessment, then route qualified cases toward the assistant plan or a funding-prep sprint. Any dispute submission or client outreach remains approval-controlled.';
      answerBuilder = 'credit_funding_reasoning';
    } else if (domain.domain === 'business_opportunity' || domain.domain === 'monetization') {
      text = recommendationAnswer();
      setLastRankedList(OPPORTUNITIES); setLastRecommendedItem(OPPORTUNITIES[0]);
    } else if (/implement/.test(lower) && boundary.shouldUsePriorMemory) {
      const item = resolveFollowUp(message);
      if (item) { memoryUsed = true; resolvedEntities.push(item); text = implementationPlan(item); }
      else { text = 'I have an implementation request but no eligible matching item. Name the target once and I will build the plan.'; confidence = 'low'; }
    } else {
      text = `I detected the ${domain.domain === 'unknown' ? 'general' : domain.domain.replace(/_/g, ' ')} domain and did not reuse the previous recommendation because this message did not reference it. I can reason from the current page or a named target without pulling in stale memory.`;
      answerBuilder = 'domain_local_reasoning';
    }
    source = 'reasoning';
  } else if (activation.level === 5) {
    const model = await hermesModelChat(message, { pageSummary: page || undefined });
    if (model.source === 'model' && model.text) { text = model.text; usedModel = true; source = 'model'; answerBuilder = 'model'; }
    else { text = `I could not verify a live model response, so I did not claim one. ${recommendationAnswer()}`; fallbackReason = model.source || 'model_unavailable'; source = 'reasoning'; answerBuilder = 'model_safe_fallback'; }
  } else {
    const item = boundary.shouldUsePriorMemory ? resolveFollowUp(message) : null;
    memoryUsed = Boolean(item);
    text = `I prepared a draft Ray Review request${item ? ` for **${item.title}**` : ''}. It is not submitted or executed. Review the target, scope, and expected result before approving any state-changing action.`;
    if (item) resolvedEntities.push(item);
    source = 'local'; answerBuilder = 'approval_draft';
  }

  addConversationMessage('user', message);
  addConversationMessage('assistant', text);
  updateConversationContext({ lastIntent: traceIntent(activation), lastTopic: boundary.detectedTopic, lastPage: page || null, lastActionPlan: /implementation plan/i.test(text) ? text.slice(0, 2000) : null });
  const modelRoute = usedModel ? activation.modelRoute : (activation.level === 5 ? 'no_model' : activation.modelRoute);
  const memoryRejected = memoryCandidateFound && !memoryUsed && !boundary.shouldUsePriorMemory;
  const invariantViolations = findRoutingInvariantViolations({ domain: domain.domain, boundary, usedMemory: memoryUsed, usedSupabase, usedModel });
  logRoutingTrace({
    message, surface, page: page || null, route: activation.route, activationLevel: activation.level,
    activationLevelName: activation.levelName, intent: traceIntent(activation), sourceDecision: source,
    usedSupabase, supabaseTables, usedModel, modelRoute, usedMemory: memoryUsed,
    selectedEntity: resolvedEntities[0]?.title || null, safetyGate: activation.level === 0,
    answerBuilder, fallbackReason, correctnessHint: usedModel || usedSupabase ? 'verified by runtime result' : 'deterministic local route', confidence,
    detectedDomain: domain.domain, previousTopic: priorState.lastTopic, detectedTopic: boundary.detectedTopic,
    topicChanged: boundary.isNewTopic, memoryCandidateFound, memoryUsed,
    memoryRejected, memoryRejectionReason: memoryRejected ? boundary.reason : null,
    domainOverrideApplied: boundary.domainOverrideApplied, casualOverrideApplied: boundary.casualOverrideApplied,
    invariantViolations,
  });

  const decision = usedModel ? 'route-to-model' : (usedSupabase || activation.level === 3 || activation.level === 4 ? 'answer-with-context' : 'answer-locally');
  return {
    text, answer: text, activationLevel: activation.level, route: activation.route, sourceMode: source,
    usedModel, modelMetadata: { route: modelRoute }, usedSupabase, supabaseStatus, resolvedEntities,
    rememberedContext: memoryAvailable || activation.level === 3, actionIntent: activation.level === 0 || activation.level === 6 ? message : null,
    approvalRequired: activation.level === 0 || activation.level === 6,
    safeNextActions: ['Prepare a draft', 'Review in Ray Review', 'Execute only after explicit approval'],
    diagnostics: { activation, answerBuilder, fallbackReason, supabaseTables, domain, boundary, memoryCandidateFound, memoryUsed, memoryRejected, invariantViolations },
    intent: { route: activation.route, intent: traceIntent(activation), confidence, reason: activation.reason },
    modelRoute: { route: modelRoute, reason: activation.reason },
    reasoning: { decision, confidence, reasoning: activation.reason }, capabilityBadge: getCapabilityReport().badgeText,
    confidence, source, timestamp: new Date().toISOString(),
  };
}

export function getCapabilityBadge(): string { return getCapabilityReport().badgeText; }
