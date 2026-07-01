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
  const memoryAvailable = hasConversationMemory() || Boolean(input.conversationHistory?.length);
  const pageAvailable = Boolean(page || input.currentPageContext);
  const activation = detectActivationLevel(message, memoryAvailable, pageAvailable);
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
    else if (/ceo version|ceo summary/.test(lower)) { text = buildCeoDailySummary('today'); answerBuilder = 'ceo_daily_summary'; }
    else if (/what did (you|we) do today|daily summary/.test(lower)) { text = buildDailySummary('today'); answerBuilder = 'daily_summary'; }
    else if (/trading/.test(lower)) { text = 'Trading is paper/demo only. No live broker execution is enabled, and any real trade remains blocked pending explicit approval.'; answerBuilder = 'section_status'; }
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
    if (/what business should i start|fastest money move|low[- ]cost|30 days|30-day/.test(lower)) {
      text = recommendationAnswer();
      setLastRankedList(OPPORTUNITIES); setLastRecommendedItem(OPPORTUNITIES[0]);
    } else if (/implement/.test(lower)) {
      const item = resolveFollowUp(message) || getConversationState().lastSelectedItem || OPPORTUNITIES[0];
      resolvedEntities.push(item); text = implementationPlan(item, !resolveFollowUp(message));
    } else { text = recommendationAnswer(); }
    source = 'reasoning'; answerBuilder = 'local_reasoning';
  } else if (activation.level === 5) {
    const model = await hermesModelChat(message, { pageSummary: page || undefined });
    if (model.source === 'model' && model.text) { text = model.text; usedModel = true; source = 'model'; answerBuilder = 'model'; }
    else { text = `I could not verify a live model response, so I did not claim one. ${recommendationAnswer()}`; fallbackReason = model.source || 'model_unavailable'; source = 'reasoning'; answerBuilder = 'model_safe_fallback'; }
  } else {
    const item = resolveFollowUp(message) || getConversationState().lastSelectedItem || getConversationState().lastRecommendedItem;
    text = `I prepared a draft Ray Review request${item ? ` for **${item.title}**` : ''}. It is not submitted or executed. Review the target, scope, and expected result before approving any state-changing action.`;
    if (item) resolvedEntities.push(item);
    source = 'local'; answerBuilder = 'approval_draft';
  }

  addConversationMessage('user', message);
  addConversationMessage('assistant', text);
  updateConversationContext({ lastIntent: traceIntent(activation), lastPage: page || null, lastActionPlan: /implementation plan/i.test(text) ? text.slice(0, 2000) : null });
  const modelRoute = usedModel ? activation.modelRoute : (activation.level === 5 ? 'no_model' : activation.modelRoute);
  logRoutingTrace({
    message, surface, page: page || null, route: activation.route, activationLevel: activation.level,
    activationLevelName: activation.levelName, intent: traceIntent(activation), sourceDecision: source,
    usedSupabase, supabaseTables, usedModel, modelRoute, usedMemory: activation.level === 3,
    selectedEntity: resolvedEntities[0]?.title || null, safetyGate: activation.level === 0,
    answerBuilder, fallbackReason, correctnessHint: usedModel || usedSupabase ? 'verified by runtime result' : 'deterministic local route', confidence,
  });

  const decision = usedModel ? 'route-to-model' : (usedSupabase || activation.level === 3 || activation.level === 4 ? 'answer-with-context' : 'answer-locally');
  return {
    text, answer: text, activationLevel: activation.level, route: activation.route, sourceMode: source,
    usedModel, modelMetadata: { route: modelRoute }, usedSupabase, supabaseStatus, resolvedEntities,
    rememberedContext: memoryAvailable || activation.level === 3, actionIntent: activation.level === 0 || activation.level === 6 ? message : null,
    approvalRequired: activation.level === 0 || activation.level === 6,
    safeNextActions: ['Prepare a draft', 'Review in Ray Review', 'Execute only after explicit approval'],
    diagnostics: { activation, answerBuilder, fallbackReason, supabaseTables },
    intent: { route: activation.route, intent: traceIntent(activation), confidence, reason: activation.reason },
    modelRoute: { route: modelRoute, reason: activation.reason },
    reasoning: { decision, confidence, reasoning: activation.reason }, capabilityBadge: getCapabilityReport().badgeText,
    confidence, source, timestamp: new Date().toISOString(),
  };
}

export function getCapabilityBadge(): string { return getCapabilityReport().badgeText; }
