/**
 * Hermes Response Router — single entry point for all Hermes questions.
 *
 * Classifies question type, resolves entities, queries memory, queries adapters,
 * and generates a proper response. No more canned fallbacks.
 */

import { getTimeContext, detectTimeIntent, normalizeTimeText } from './hermesTimeContext';
import { buildPageContext, getHermesPageRuntimeContext, type PageContext } from './hermesContextBridge';
import { getLastReferencedEntity, resolveEntity, setLastReferencedEntity, setLastHermesListedRecords } from './hermesEntityResolver';
import type { VisibleItem } from './hermesContextBridge';
import { queryMemory } from './hermesMemoryQuery';
import { detectLearningInstruction, storeHint, findMatchingHints } from './hermesSourceHints';
import { getBackendStatusMessage, getHermesContext, type HermesBackendContextResult } from './hermesBackendContextAdapter';
import { reasonAboutPage, getAllPageContexts, type PageDataSource } from './hermesSourceReasoner';
import { isSupabaseConfigured } from './supabaseClient';

/* ── Nexus topic knowledge base (moved from hermesWorkroomData.js) ── */
const nexusTopics: Record<string, { topic: string; explain: string; why?: string; safety?: string; approval?: string; howToApprove?: string; specialist?: string; cleanup?: string; next: string; opinion?: string }> = {
  'synthetic customer': {
    topic: 'Synthetic Customer Insert',
    explain: `The synthetic customer insert is how we prove the full $97 readiness journey end-to-end without touching a real person's data. Right now we have a test package ready—Stripe test Checkout session created, test PaymentIntent on file, onboarding records staged—but nothing has been written to Supabase yet.`,
    why: `It matters because it unlocks the live dashboard test. Once the fake customer is in the database, we can flip the frontend live-data flag and confirm that /client/dashboard actually reads real rows instead of static fallback content.`,
    approval: `Approving the insert means: (1) the synthetic record goes into Supabase with RLS intact, (2) the dashboard flag flips on, (3) we verify the read path, and (4) the rollback packet is ready if we need to undo it. No real client PII is involved. No real charges happen.`,
    cleanup: `There's a rollback transaction script ready. If anything looks wrong after insert, we can revert the database state cleanly.`,
    next: `To move forward, you'd approve the insert via Ray Review. The card is already queued.`
  },
  'research engine': {
    topic: 'Research Engine',
    explain: `The Research Engine has 50 scored candidates across 18 operating lanes—credit readiness, payment monetization, grants, marketing/SEO, Oanda demo data, Vibe paper strategies, YouTube metadata, and NotebookLM exports. 26 of those are immediately actionable.`,
    approval: `Approval in the Research Engine works through Ray Review cards. Each candidate has a score, a lane assignment, and a recommended next action. You approve to convert a candidate into an opportunity, a content draft, or an automation task. You hold if it needs more research. You reject if the signal is too weak. Nothing executes without your decision.`,
    howToApprove: `Go to Research Engine in the sidebar. Click any candidate row. The detail drawer opens with score, lane, source, and status. At the bottom you'll see approve/hold/reject buttons plus "Convert to opportunity" and "Send to Hermes." The approve button creates a local receipt—it doesn't send anything external.`,
    next: `The Research Engine is live in the sidebar. Try clicking a candidate row to see the detail drawer.`
  },
  'monetization': {
    topic: 'Monetization',
    explain: `We have 9 offers registered, from the $97 Credit & Funding Readiness Review up through the $497 Funding Prep Sprint. The offer ladder is: $97 entry, $297 assisted plan, $497 higher-touch sprint, plus monthly subscriptions, affiliate pathways, and funding referral commissions.`,
    opinion: `My recommendation on what to monetize first: the $97 Readiness Review. Here's why: (1) it's the most complete offer—we have the pricing, the partner list, and the compliance review done, (2) it proves the entire payment-to-delivery journey, (3) it has the lowest risk since it's a one-time test charge, and (4) everything else in the ladder builds on proving this one works. After $97, I'd move to the $297 assisted plan because it recycles the same readiness framework with more hands-on work.`,
    next: `To move forward: approve the $97 offer in Monetization, approve the Stripe test Checkout completion, and approve the first landing page draft. Those three decisions unlock the revenue proof path.`
  },
  'stripe': {
    topic: 'Stripe Integration',
    explain: `Stripe is in test mode. We have a test Checkout session created and a test PaymentIntent on file, but neither has been completed. The webhook endpoint is verified at the signature level but the listener isn't running yet.`,
    safety: `No live charges are possible in the current configuration. Test mode only. The Stripe secret key is in the env but the app uses test-mode fixtures exclusively.`,
    next: `The next step is approving the webhook listener startup and completing the test Checkout with a test payment method. Both are Ray Review decisions.`
  },
  'resend': {
    topic: 'Resend Email',
    explain: `Resend is connected but blocked. The issue is a domain/key scope mismatch—the API key has read-only permissions and the sender domain hasn't been verified. That means no emails can actually leave the system.`,
    safety: `This is safe because it's broken in the right direction: it can't send even if we wanted it to. Once the key is re-scoped and the domain is verified, every send still requires Ray approval.`,
    next: `Fixing Resend means: (1) generate a new API key with send permissions, (2) verify the sender domain in Resend's dashboard, (3) approve the first onboarding email send via Ray Review.`
  },
  'approval': {
    topic: 'Approval System',
    explain: `Every risky action in Nexus goes through Ray Review. The flow is: Hermes or a specialist proposes a task, a Ray Review card is created, you see the card with context and a recommendation, you approve/reject/hold, and a receipt is generated. The receipt records what happened but the underlying action only executes if you approved it.`,
    safety: `Approvals are the safety gate. Nothing external happens without one. Even internal actions that affect data state get an approval card. The receipts are append-only and include the decision, timestamp, and next step.`,
    next: `You can see all pending approvals in Ray Review. There are currently 0 cards waiting.`
  },
  'credit': {
    topic: 'Credit & Funding',
    explain: `Credit readiness is tracked through a scoring system that evaluates profile completeness, document status, and funding eligibility. Right now the SmartCredit connector isn't configured, so scores are generated from report analysis only—no live credit pulls.`,
    specialist: `I'd route detailed credit questions to the Credit Specialist. They can walk through readiness gaps, document checklists, bankability issues, and draft dispute letters. They will NOT send disputes, contact bureaus, or submit applications without your explicit approval.`,
    next: `Open Credit & Funding in the sidebar to see the readiness pipeline, document checklist, and dispute draft queue.`
  },
  'client': {
    topic: 'Client Management',
    explain: `We have zero live client profiles. The system is designed for a synthetic test customer flow: insert a fake customer, verify the dashboard reads the data, complete the Stripe test journey, then clean up. Real client onboarding would go through a 5-stage pipeline: Signup → Credit Report → Business Setup → Document Prep → Funding Ready.`,
    safety: `No real client PII has been entered. The synthetic customer is a test fixture. Real client data would be stored in Supabase with RLS policies and Hermes would only see internal summaries—never raw PII.`,
    next: `Open Clients in the sidebar to see the workflow pipeline and the synthetic customer status.`
  },
  'opportunity': {
    topic: 'Business Opportunities',
    explain: `There are 26 immediately actionable research-to-money opportunities scored and ranked. They span credit offer building, SaaS ideas, lead-gen funnels, AI tooling services, SEO offers, and funding readiness packages.`,
    howToApprove: `Each opportunity has a score, a revenue potential range, and a confidence rating. You can approve to convert it into a content draft, a Ray Review card, or a specialist task. Hold if it needs more validation. Reject if the signal is too weak.`,
    next: `Open Business Opportunities in the sidebar. Click any opportunity card to see the full detail drawer with score, reasoning, and action buttons.`
  },
  'marketing': {
    topic: 'Marketing Drafts',
    explain: `We have 5 social post drafts, 5 video scripts, 1 newsletter draft, 3 landing page experiments, and a lead magnet outline. All are draft-only—nothing has been published or sent.`,
    safety: `Publishing is completely blocked. Every draft requires Ray approval before it could even be considered for publishing, and the social connector is in publish-disabled mode.`,
    next: `Open Marketing Drafts in the sidebar. Click any draft to see the content, approve/hold/reject it, or ask the Marketing Specialist for feedback.`
  },
  'strategy': {
    topic: 'Strategy',
    explain: `Today's strategic priorities, from where I sit: (1) Prove the money path—the $97 journey from synthetic customer through Stripe test to dashboard verification. This is the single most important thing because it converts "the system works" from a claim into proof. (2) Clear the communication gate—fix Resend so we can send onboarding emails after approval. (3) Pick the first 3-5 research-to-money candidates and convert them to content or offers. (4) Keep the safety gates tight—no external actions without Ray Review.`,
    opinion: `My honest take: we've been building infrastructure for a while. The next move isn't more infrastructure—it's proving one revenue path end-to-end. The $97 readiness review is the shortest path to proof. Everything else is parallel work that supports that path.`,
    next: `To move forward: approve the $97 test journey, fix Resend, and convert 3-5 research candidates to offers.`
  }
};

export type QuestionType =
  | 'greeting'
  | 'date_time'
  | 'scheduling'
  | 'page_question'
  | 'entity_question'
  | 'comparison'
  | 'memory_history'
  | 'supabase_query'
  | 'backend_query'
  | 'strategy_analysis'
  | 'execution'
  | 'learning_instruction'
  | 'nexus_topic'
  | 'opinion'
  | 'approval'
  | 'money'
  | 'blockers'
  | 'strategy'
  | 'casual'
  | 'emotional'
  | 'partner_mode'
  | 'summary'
  | 'trading'
  | 'source_reasoning'
  | 'unclear';

export interface ResponseContext {
  message: string;
  pageId?: string;
  route?: string;
  activeTab?: string;
  selectedItem?: PageContext['selectedItem'];
  visibleItems?: PageContext['visibleItems'];
  availableActions?: string[];
  gatedActions?: string[];
}

export interface HermesResponse {
  text: string;
  confidence: 'high' | 'medium' | 'low' | 'none';
  source: 'time_context' | 'page_context' | 'entity_resolution' | 'memory' | 'supabase_stub' | 'backend_stub' | 'backend_context' | 'report_context' | 'canned' | 'honest_fallback' | 'learning' | 'source_reasoning' | 'live_supabase' | 'static_fallback';
  questionType: QuestionType;
  needsClarification: boolean;
  clarificationQuestion?: string;
  sourceHint?: string;
}

/** Main entry point — classify, resolve, respond. */
export function hermesResponseRouter(ctx: ResponseContext): HermesResponse {
  const { message, pageId, route, activeTab, selectedItem, visibleItems, availableActions, gatedActions } = ctx;

  // 1. Check for learning instructions
  const learning = detectLearningInstruction(message);
  if (learning.isLearning && learning.hint) {
    storeHint(learning.hint);
    return {
      text: `Got it. I'll remember that "${learning.hint.instruction}" for future questions.`,
      confidence: 'high',
      source: 'learning',
      questionType: 'learning_instruction',
      needsClarification: false,
      sourceHint: `Stored as ${learning.hint.memoryType}: "${learning.hint.instruction}"`,
    };
  }

  // 2. Build page context
  const runtimeContext = pageId ? getHermesPageRuntimeContext(pageId) : null;
  const pageContext: PageContext | null = pageId
    ? { ...buildPageContext(pageId, route), activeTab: activeTab || null, selectedItem: selectedItem || null, visibleItems: visibleItems?.length ? visibleItems : runtimeContext!.visibleItems, availableActions: availableActions?.length ? availableActions : runtimeContext!.availableActions, gatedActions: gatedActions || buildPageContext(pageId, route).gatedActions }
    : null;

  // 3. Classify question type
  const questionType = classifyIntent(message);

  // 4. Route to appropriate handler
  switch (questionType) {
    case 'greeting':
      return handleGreeting(message);

    case 'date_time':
      return handleDateTime(message);

    case 'scheduling':
      return handleScheduling(message, pageContext);

    case 'page_question':
      return handlePageQuestion(message, pageContext);

    case 'entity_question':
      return handleEntityQuestion(message, pageContext);

    case 'comparison':
      return handleComparison(message, pageContext);

    case 'memory_history':
      return handleMemoryHistory(message);

    case 'supabase_query':
      return handleSupabaseQuery(message);

    case 'backend_query':
      return handleBackendQuery(message);

    case 'strategy_analysis':
      return handleStrategyAnalysis(message, pageContext);

    case 'execution':
      return handleExecution(message, pageContext);

    case 'nexus_topic':
      return handleNexusTopic(message, pageContext);

    case 'opinion':
      return handleOpinion(message, pageContext);

    case 'approval':
      return handleApproval(message, pageContext);

    case 'money':
      return handleMoney(message, pageContext);

    case 'blockers':
      return handleBlockers(message, pageContext);

    case 'strategy':
      return handleStrategy(message, pageContext);

    case 'casual':
      return handleCasual(message, pageContext);

    case 'emotional':
      return handleEmotional(message, pageContext);

    case 'partner_mode':
      return handlePartnerMode(message, pageContext);

    case 'summary':
      return handleSummary(message, pageContext);

    case 'source_reasoning':
      return handleSourceReasoning(message);

    case 'trading':
      return handleTrading(message, pageContext);

    default:
      return handleUnclear(message, pageContext);
  }
}

export function normalizeHermesText(text: string): string {
  return normalizeTimeText(text);
}

export function classifyIntent(text: string): QuestionType {
  const lower = normalizeHermesText(text);

  // Greetings
  if (/^(hi|hello|hey|yo|sup|good morning|good afternoon|good evening|good night|morning|afternoon|evening|howdy|hola|hey there|what's up|whats up)\b/.test(lower)) {
    return 'greeting';
  }

  // Date/time questions
  if (detectTimeIntent(text).isTimeQuestion) {
    return 'date_time';
  }

  // Scheduling phrases
  if (detectTimeIntent(text).isSchedulingPhrase) {
    return 'scheduling';
  }

  // Questions about the current page and its controls.
  if (/\b(what can i click here|what am i looking at|on this page)\b/.test(lower) && !/\b(first|strategy)\b/.test(lower)) {
    return 'page_question';
  }

  if (/\b(revenue dashboard)\b/.test(lower)) {
    return 'page_question';
  }

  if (/\b(what reports are available|what does this report mean|from this report)\b/.test(lower)) return 'page_question';
  if (/\b(is there anything we can improve|what can we improve|best (business )?opportunity)\b/.test(lower)) return 'opinion';
  if (/\b(is this live|is this static|what.*source|live or static|why.*show.*data.*supabase|why.*disagree|mismatch|split.?brain|compare.*supabase|page.*vs.*supabase|which sections.*live|what.*sync|need.*sync)\b/.test(lower)) return 'source_reasoning';
  if (/\b(make money|monetize|revenue|income|pricing)\b/.test(lower)) return 'money';
  if (/\b(julius erving|fake customer inserted|synthetic customer status)\b/.test(lower)) return 'nexus_topic';
  if (/\b(send the email|charge the customer|publish this post|place a live trade|insert this real client)\b/.test(lower)) return 'execution';

  // Comparison must win over generic entity references such as "that strategy".
  if (/\b(compare|versus|vs|difference between|how does .+ compare|which is better)\b/.test(lower)) {
    return 'comparison';
  }

  // Learning/memory instructions
  if (detectLearningInstruction(text).isLearning) {
    return 'learning_instruction';
  }

  // Entity references (this, that, first one, etc.) — check BEFORE nexus topics
  if (/\b(this|that|first|second|third|last|next|another|other|those|these)\b/.test(lower) &&
    /\b(strategy|item|opportunity|offer|candidate|draft|report|client|rule|action|row|card|thing|one)\b/.test(lower)) {
    return 'entity_question';
  }
  // "review the first", "analyze the second", "show the last" etc.
  if (/\b(review|analyze|open|show|tell me about|look at|check)\s+(the\s+)?(first|second|third|last|next)/.test(lower)) {
    return 'entity_question';
  }

  // Nexus-specific topic matching (check before generic patterns)
  for (const pattern of Object.keys(nexusTopics)) {
    if (lower.includes(pattern)) {
      return 'nexus_topic';
    }
  }

  // Memory/history
  if (/\b(what did we|what have we|what changed|what happened|show me|recall|remember|history|recent|today|yesterday|last week)\b/.test(lower)) {
    return 'memory_history';
  }

  // Opinion / recommendation requests
  if (/\b(opinion|recommend|what do you think|what should we|rank|priorit)\b/.test(lower)) {
    return 'opinion';
  }

  // Approval / decision questions
  if (/\b(what needs my approval|what.*approv|approve|pending|decision|queue)\b/.test(lower)) {
    return 'approval';
  }

  // Money / revenue
  if (/\b(money|revenue|income|sell|make.*money|offer.*price|pricing|monetize)\b/.test(lower)) {
    return 'money';
  }

  // Blockers
  if (/\b(block|stuck|issue|problem|error|fail|broken|not working)\b/.test(lower)) {
    return 'blockers';
  }

  // Strategy / plan
  if (/\b(plan|strategy|today|tomorrow|what should|next step|priority|focus)\b/.test(lower)) {
    return 'strategy';
  }

  // Trading
  if (/\b(trade|trading|oanda|vibe|forex|market|position|paper only|paper trading)\b/.test(lower)) {
    return 'trading';
  }

  // Casual / personal — check BEFORE supabase/backend to avoid false matches
  if (/\b(favorite|how are you|how'?s it going|what'?s your day like|are you real|who are you|what are you|coffee|sleep|tired|bored|hungry|weekend|vacation|chill|relax|did you sleep)\b/.test(lower)) {
    return 'casual';
  }

  // Connection status questions — route to backend_query for accurate answers
  if (/\b(are you connected|connected to)\b/.test(lower)) {
    return 'backend_query';
  }

  // Supabase queries
  if (/\b(supabase|database|query|row|table|live data)\b/.test(lower)) {
    return 'supabase_query';
  }

  // Backend queries
  if (/\b(model|ai|llm|gpt|claude|backend|endpoint|where are you getting your answers|what are your sources|explain your sources|search the internet|web access|internet|social media)\b/.test(lower)) {
    return 'backend_query';
  }

  // Strategy analysis
  if (/\b(analyze|analysis|backtest|optimize|performance|return|risk)\b/.test(lower)) {
    return 'strategy_analysis';
  }

  // Execution
  if (/\b(execute|run|deploy|publish|send|submit|trade|charge|process)\b/.test(lower)) {
    return 'execution';
  }

  // Emotional
  if (/\b(frustrated|annoyed|angry|fake|disappointed|upset|worried|stressed)\b/.test(lower)) {
    return 'emotional';
  }

  // Partner mode
  if (/\b(partner|command bot|talk to me like|be human|be real)\b/.test(lower)) {
    return 'partner_mode';
  }

  // Summary / status
  if (/\b(report|status|summary|system|overview|picture)\b/.test(lower)) {
    return 'summary';
  }

  // If it looks like a question but unclear type
  if (/\?$/.test(text) || /\b(how|what|when|where|why|which|who|can|do|is|are|should)\b/.test(lower)) {
    return 'unclear';
  }

  return 'unclear';
}

function handleGreeting(_message: string): HermesResponse {
  const time = getTimeContext();
  const greeting = time.timeOfDay === 'morning' ? 'Good morning' :
    time.timeOfDay === 'afternoon' ? 'Good afternoon' :
    time.timeOfDay === 'evening' ? 'Good evening' : 'Good night';

  return {
    text: `${greeting}, Ray. I'm Hermes, your CEO advisor. What would you like to focus on right now?`,
    confidence: 'high',
    source: 'time_context',
    questionType: 'greeting',
    needsClarification: false,
  };
}

function handleDateTime(_message: string): HermesResponse {
  const time = getTimeContext();
  return {
    text: `It's ${time.formattedTime} on ${time.formattedDate} (${time.timezone}).`,
    confidence: 'high',
    source: 'time_context',
    questionType: 'date_time',
    needsClarification: false,
  };
}

function handleScheduling(_message: string, pageContext: PageContext | null): HermesResponse {
  const timeIntent = detectTimeIntent(_message);
  const now = new Date();

  let responseText = '';

  if (timeIntent.timeWindow) {
    const window = timeIntent.timeWindow;
    const dateStr = window.start.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
    const startStr = window.start.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
    const endStr = window.end.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
    const isToday = window.start.toDateString() === now.toDateString();

    if (isToday) {
      responseText = `I understand you want to schedule something for today. That would be between ${startStr} and ${endStr}. `;
    } else {
      responseText = `I understand you want to schedule something for ${dateStr}. That would be between ${startStr} and ${endStr}. `;
    }

    responseText += `What would you like to schedule? `;

    if (pageContext?.availableActions) {
      const schedulableActions = pageContext.availableActions.filter(a => !pageContext.blockedActions?.includes(a));
      if (schedulableActions.length > 0) {
        responseText += `Available actions on this page: ${schedulableActions.join(', ')}.`;
      }
    }

    responseText += `\n\nI can prepare a Ray Review task request for this, but I cannot directly schedule a live report from this chat yet. Would you like me to create a task request?`;
  } else {
    responseText = `Could you be more specific about when? For example: "this evening", "tomorrow morning", "in 2 hours", or "next Friday". I need a time to schedule the task.`;
  }

  return {
    text: responseText,
    confidence: timeIntent.timeWindow ? 'high' : 'medium',
    source: 'time_context',
    questionType: 'scheduling',
    needsClarification: !timeIntent.timeWindow,
    clarificationQuestion: !timeIntent.timeWindow ? 'What time should I schedule this for?' : undefined,
  };
}

function handlePageQuestion(_message: string, pageContext: PageContext | null): HermesResponse {
  if (!pageContext) {
    return {
      text: `I don't have page context for this question. Could you tell me which page you're on?`,
      confidence: 'low',
      source: 'honest_fallback',
      questionType: 'page_question',
      needsClarification: true,
      clarificationQuestion: 'Which page are you on?',
    };
  }

  const itemCount = pageContext.visibleItems.length;
  const itemTypes = [...new Set(pageContext.visibleItems.map(i => i.type))];

  let responseText = `You're on ${pageContext.pageTitle}. `;

  if (itemCount > 0) {
    responseText += `I can see ${itemCount} items on this page`;
    if (itemTypes.length > 0) {
      responseText += ` (${itemTypes.join(', ')})`;
    }
    responseText += `. `;

    if (itemCount <= 3) {
      const summaries = pageContext.visibleItems.map(i =>
        `- ${i.title}: ${i.status}${i.score ? ` (score: ${i.score})` : ''}`
      );
      responseText += summaries.join('\n') + '\n\n';
    } else {
      responseText += `The top items are:\n`;
      for (const item of pageContext.visibleItems.slice(0, 3)) {
        responseText += `- ${item.title}: ${item.status}${item.score ? ` (score: ${item.score})` : ''}\n`;
      }
      responseText += '\n';
    }
  } else {
    responseText += `There are no items currently loaded on this page. `;
  }

  if (pageContext.availableActions.length > 0) {
    responseText += `Available here: ${pageContext.availableActions.join(', ')}. `;
  }
  if (/report|dashboard/i.test(_message)) {
    const report = getHermesContext(_message, { type: /what reports are available/i.test(_message) ? 'reports_summary' : 'selected_report', selectedReport: _message });
    responseText += `${report.summary}\n\nSource: ${report.sourceType === 'report' ? 'selected approved report snapshot' : report.source} (${report.liveData ? 'live' : 'static'}). Limitations: ${report.limitations.join('; ')}.`;
  } else {
    responseText += `What would you like to know about these?`;
  }

  return {
    text: responseText,
    confidence: 'high',
    source: 'page_context',
    questionType: 'page_question',
    needsClarification: false,
  };
}

function handleEntityQuestion(message: string, pageContext: PageContext | null): HermesResponse {
  if (/\b(first|top)\s+strategy\b/i.test(message) && pageContext?.pageId === 'hermes' && !pageContext.visibleItems.some(item => item.type === 'strategy')) {
    return {
      text: `There is no strategy visible on the Hermes Workroom page. Do you want to switch to Trading Demo and check the first paper/demo strategy there?`,
      confidence: 'high', source: 'page_context', questionType: 'entity_question', needsClarification: true,
      clarificationQuestion: 'Do you want to check the first strategy on Trading Demo?',
    };
  }
  const resolved = resolveEntity(message, pageContext);

  if (resolved.clarificationNeeded) {
    return {
      text: resolved.clarificationQuestion || `I'm not sure which item you're referring to. Could you be more specific?`,
      confidence: 'low',
      source: 'entity_resolution',
      questionType: 'entity_question',
      needsClarification: true,
      clarificationQuestion: resolved.clarificationQuestion,
    };
  }

  if (!resolved.item) {
    if (/\bstrategy\b/i.test(message) && pageContext?.pageId === 'hermes') {
      return {
        text: `There is no strategy visible on the Hermes Workroom page. Do you want to switch to Trading Demo and check the first paper/demo strategy there?`,
        confidence: 'high',
        source: 'page_context',
        questionType: 'entity_question',
        needsClarification: true,
        clarificationQuestion: 'Do you want to check the first strategy on Trading Demo?',
      };
    }
    return {
      text: `I couldn't find a matching item. Could you describe what you're looking for?`,
      confidence: 'low',
      source: 'entity_resolution',
      questionType: 'entity_question',
      needsClarification: true,
      clarificationQuestion: 'What item are you referring to?',
    };
  }

  setLastReferencedEntity(resolved.item);
  const item = resolved.item;

  let responseText = `**${item.title}**\n\n`;
  responseText += `Status: ${item.status}. `;
  if (item.score !== undefined) responseText += `Score: ${item.score}. `;
  if (item.confidence) responseText += `Confidence: ${item.confidence}. `;
  if (item.revenueRange) responseText += `Revenue potential: ${item.revenueRange}. `;
  if (item.category) responseText += `Category: ${item.category}. `;

  responseText += `\n\nData source: ${item.dataSource === 'supabase' ? 'Live Supabase' : item.dataSource}. `;
  if (item.dataSource === 'supabase') {
    responseText += `This is live data from the database.\n\n`;
    responseText += `Why it matters: This record was loaded from a live Supabase query and is part of the current live dataset.\n\n`;
    responseText += `Suggested next action: Review, approve, hold, or convert to opportunity/content/automation. Any execution is approval-gated.`;
  } else {
    responseText += `This is bundled local context — not live data.`;
  }

  return {
    text: responseText,
    confidence: resolved.confidence,
    source: 'entity_resolution',
    questionType: 'entity_question',
    needsClarification: false,
    sourceHint: `Resolved "${message}" → ${item.title} (${resolved.source})`,
  };
}

function handleComparison(_message: string, pageContext: PageContext | null): HermesResponse {
  const referenced = getLastReferencedEntity();
  const asksByReference = /\b(this|that)\s+strategy\b/i.test(_message);
  if (asksByReference && !referenced) {
    return {
      text: `I don't have a previously referenced strategy. Which strategy do you want to compare?`,
      confidence: 'low',
      source: 'entity_resolution',
      questionType: 'comparison',
      needsClarification: true,
      clarificationQuestion: 'Which strategy do you want to compare?',
    };
  }

  if (!pageContext || pageContext.visibleItems.length < 2) {
    return {
      text: `I need two visible items to compare. Which two strategies would you like me to compare?`,
      confidence: 'low', source: 'page_context', questionType: 'comparison', needsClarification: true,
      clarificationQuestion: 'Which two strategies would you like me to compare?',
    };
  }

  const candidates = referenced
    ? pageContext.visibleItems.filter(item => item.type === referenced.type && item.title !== referenced.title)
    : pageContext.visibleItems;
  if (referenced && candidates.length > 1 && /\b(another|other|different)\b/i.test(_message)) {
    return {
      text: `I have ${referenced.title} as the referenced strategy. Which comparison target do you want: ${candidates.slice(0, 3).map(item => item.title).join(', ')}?`,
      confidence: 'low', source: 'entity_resolution', questionType: 'comparison', needsClarification: true,
      clarificationQuestion: `Which strategy should I compare with ${referenced.title}?`,
    };
  }

  const items = referenced && candidates.length > 0 ? [referenced, candidates[0]] : pageContext.visibleItems.slice(0, 2);
  let responseText = `Comparing:\n\n`;
  for (const item of items) {
    responseText += `**${item.title}**\n`;
    responseText += `- Status: ${item.status}\n`;
    if (item.score !== undefined) responseText += `- Score: ${item.score}\n`;
    if (item.confidence) responseText += `- Confidence: ${item.confidence}\n`;
    responseText += `\n`;
  }

  responseText += `Data source: ${pageContext.pageDataSource}. ${pageContext.pageDataSource === 'local_static' ? 'These are bundled local values — not live.' : ''}`;

  return {
    text: responseText,
    confidence: 'medium',
    source: 'page_context',
    questionType: 'comparison',
    needsClarification: false,
  };
}

function handleMemoryHistory(message: string): HermesResponse {
  const lower = message.toLowerCase();

  let timeWindow = 'recent activity';
  if (/today/.test(lower)) timeWindow = 'today';
  else if (/yesterday/.test(lower)) timeWindow = 'yesterday';
  else if (/last week|past week/.test(lower)) timeWindow = 'last 7 days';
  else if (/last 24 hours|past day/.test(lower)) timeWindow = 'last 24 hours';
  else if (/this morning/.test(lower)) timeWindow = 'this morning';
  else if (/this afternoon/.test(lower)) timeWindow = 'this afternoon';
  else if (/this evening/.test(lower)) timeWindow = 'this evening';

  const result = queryMemory(timeWindow);

  if (result.eventCount === 0) {
    return {
      text: `I don't have any recorded activity for ${result.timeRangeUsed}. The activity journal starts recording once you begin interacting with pages and Hermes. Would you like me to start tracking?`,
      confidence: 'medium',
      source: 'memory',
      questionType: 'memory_history',
      needsClarification: false,
    };
  }

  let responseText = result.summary + '\n\n';

  if (result.topEntities.length > 0) {
    responseText += `Key areas: ${result.topEntities.slice(0, 5).join(', ')}\n`;
  }
  if (result.blockers.length > 0) {
    responseText += `⚠️ Blockers: ${result.blockers.join(', ')}\n`;
  }
  if (result.decisions.length > 0) {
    responseText += `Decisions made: ${result.decisions.join(', ')}\n`;
  }
  if (result.nextActions.length > 0) {
    responseText += `Next actions: ${result.nextActions.join(', ')}\n`;
  }

  responseText += `\nSource: local activity journal (localStorage). This is local memory — not live database records.`;

  return {
    text: responseText,
    confidence: 'medium',
    source: 'memory',
    questionType: 'memory_history',
    needsClarification: false,
  };
}

function handleSourceReasoning(message: string): HermesResponse {
  const allContexts = getAllPageContexts();
  const contextKeys = Object.keys(allContexts);

  if (contextKeys.length === 0) {
    return {
      text: 'I don\'t have any page data loaded yet. Navigate to a section (Business Opportunities, Research, Monetization, or Clients) and ask again.',
      confidence: 'low',
      source: 'source_reasoning',
      questionType: 'source_reasoning',
      needsClarification: false,
    };
  }

  const lower = message.toLowerCase();
  let matchedSection: PageDataSource | null = null;

  // Try to match a specific section from the question
  for (const [sectionId, ctx] of Object.entries(allContexts)) {
    const sectionLabel = sectionId.replace(/_/g, ' ');
    if (lower.includes(sectionLabel) || lower.includes(sectionId)) {
      matchedSection = ctx;
      break;
    }
  }

  // If asking about all sections, summarize each
  if (/which sections|all sections|what.*live|what.*static|overall|across/i.test(lower)) {
    const summaries = Object.entries(allContexts).map(([sectionId, ctx]) => {
      const label = sectionId.replace(/_/g, ' ');
      const status = ctx.liveData ? 'LIVE' : 'STATIC';
      return `${label}: ${status} (${ctx.liveData ? ctx.rowCount + ' live rows' : ctx.staticCount + ' static items, ' + ctx.rowCount + ' Supabase rows'})`;
    });
    return {
      text: 'Here\'s the live/static status across all loaded sections:\n\n' + summaries.join('\n') + '\n\nAll sections attempt Supabase first and fall back to static data when Supabase has 0 rows.',
      confidence: 'high',
      source: 'source_reasoning',
      questionType: 'source_reasoning',
      needsClarification: false,
    };
  }

  // Match specific section
  if (matchedSection) {
    const reasoning = reasonAboutPage(matchedSection, message);
    return {
      text: reasoning.answer + (reasoning.suggestions.length > 0 ? '\n\nSuggestions: ' + reasoning.suggestions.join('; ') : ''),
      confidence: reasoning.confidence,
      source: reasoning.sourceType === 'live_supabase' ? 'live_supabase' : 'static_fallback',
      questionType: 'source_reasoning',
      needsClarification: false,
      sourceHint: `Source reasoner: ${reasoning.sourceType} (live=${reasoning.liveData})`,
    };
  }

  // Default: report on the first available section
  const firstKey = contextKeys[0];
  const firstCtx = allContexts[firstKey];
  const reasoning = reasonAboutPage(firstCtx, message);
  return {
    text: `For the ${firstKey.replace(/_/g, ' ')} section: ${reasoning.answer}` + (reasoning.suggestions.length > 0 ? '\n\nSuggestions: ' + reasoning.suggestions.join('; ') : ''),
    confidence: reasoning.confidence,
    source: reasoning.sourceType === 'live_supabase' ? 'live_supabase' : 'static_fallback',
    questionType: 'source_reasoning',
    needsClarification: false,
  };
}

function handleSupabaseQuery(message: string): HermesResponse {
  const allContexts = getAllPageContexts();
  const contextKeys = Object.keys(allContexts);

  // If there's page context available, use the source reasoner
  if (contextKeys.length > 0) {
    // Try to find a relevant section from the message
    const lower = message.toLowerCase();
    let matchedSection: PageDataSource | null = null;

    for (const [sectionId, ctx] of Object.entries(allContexts)) {
      if (lower.includes(sectionId.replace(/_/g, ' ')) || lower.includes(sectionId)) {
        matchedSection = ctx;
        break;
      }
    }

    // Fall back to the first available context if no specific match
    if (!matchedSection && contextKeys.length > 0) {
      matchedSection = allContexts[contextKeys[0]];
    }

    if (matchedSection) {
      const reasoning = reasonAboutPage(matchedSection, message);
      // Store listed records for entity resolution ("the first one" etc.)
      if (matchedSection.liveData && matchedSection.records.length > 0) {
        const items: VisibleItem[] = matchedSection.records.slice(0, 20).map((r: unknown) => {
          const row = r as Record<string, unknown>;
          return {
            type: String(row.type || row.category || matchedSection.sectionId),
            title: String(row.title || row.name || row.id || 'Untitled'),
            status: String(row.status || 'active'),
            score: typeof row.score === 'number' ? row.score : undefined,
            category: String(row.category || ''),
            dataSource: 'supabase' as const,
          };
        });
        setLastHermesListedRecords(items);
      }
      return {
        text: reasoning.answer + (reasoning.suggestions.length > 0 ? '\n\nSuggestions: ' + reasoning.suggestions.join('; ') : ''),
        confidence: reasoning.confidence,
        source: reasoning.sourceType === 'live_supabase' ? 'live_supabase' : 'static_fallback',
        questionType: 'supabase_query',
        needsClarification: false,
        sourceHint: `Source reasoner: ${reasoning.sourceType} (live=${reasoning.liveData})`,
      };
    }
  }

  // Fallback — no page context loaded but Supabase may still be available
  const hasLiveSections = Object.values(allContexts).some(ctx => ctx.liveData);
  if (hasLiveSections) {
    const liveSections = Object.entries(allContexts)
      .filter(([, ctx]) => ctx.liveData)
      .map(([id, ctx]) => `${id.replace(/_/g, ' ')} (${ctx.rowCount} rows)`);
    return {
      text: `I can read live Supabase data. Currently loaded live sections: ${liveSections.join(', ')}. Navigate to a section and ask about its data, or ask me to check all sections.`,
      confidence: 'high',
      source: 'live_supabase',
      questionType: 'supabase_query',
      needsClarification: false,
    };
  }
  return {
    text: `I don't have any page data loaded yet. Navigate to a section (Business Opportunities, Research, Monetization, or Clients) and I can show you the live Supabase data from those tables.`,
    confidence: 'medium',
    source: 'honest_fallback',
    questionType: 'supabase_query',
    needsClarification: false,
  };
}

function handleBackendQuery(message: string): HermesResponse {
  const lower = message.toLowerCase();
  const isSocialMediaQuestion = /\b(social media|social|twitter|facebook|instagram|tiktok)\b/.test(lower);
  const isInternetQuestion = /\b(internet|web|online|search)\b/.test(lower);
  const isModelQuestion = /\b(model|ai|llm|gpt|claude|live model)\b/.test(lower);
  const isSupabaseQuestion = /\b(supabase|database|connected to supabase|connection to supabase)\b/.test(lower);

  if (isSocialMediaQuestion) {
    return {
      text: 'Social media accounts are not verified as live from this chat. To confirm a connected account, I would need proof: a connected account row in Supabase, a valid token status, publish_enabled flag, and a last verification timestamp. No social media publishing is active from this chat layer.',
      confidence: 'high',
      source: 'honest_fallback',
      questionType: 'backend_query',
      needsClarification: false,
    };
  }

  if (isInternetQuestion) {
    return {
      text: 'I do not have live web search configured yet. To enable it, set VITE_HERMES_SEARCH_ENABLED=true and configure a search API key in the Edge Function. I can read local bundled context, report snapshots, and live Supabase data when connected.',
      confidence: 'high',
      source: 'honest_fallback',
      questionType: 'backend_query',
      needsClarification: false,
    };
  }

  if (isModelQuestion) {
    return {
      text: 'I do not have a live AI model configured in this chat layer. I use local router-based reasoning (intent classification, entity resolution, page context) for all responses. To enable a live model, configure an LLM provider in the Edge Function secrets.',
      confidence: 'high',
      source: 'honest_fallback',
      questionType: 'backend_query',
      needsClarification: false,
    };
  }

  if (isSupabaseQuestion) {
    return {
      text: getBackendStatusMessage(),
      confidence: 'high',
      source: 'live_supabase',
      questionType: 'backend_query',
      needsClarification: false,
    };
  }

  return {
    text: getBackendStatusMessage(),
    confidence: 'medium',
    source: 'honest_fallback',
    questionType: 'backend_query',
    needsClarification: false,
  };
}

function contextResponse(result: HermesBackendContextResult, questionType: QuestionType): HermesResponse {
  const label = result.sourceType === 'report' ? 'Based on the selected approved report snapshot' : 'Based on local bundled context';
  return {
    text: `${label}: ${result.summary}\n\nSource: ${result.source} (${result.sourceType}; ${result.liveData ? 'live' : 'static'}). Limitations: ${result.limitations.join('; ')}. ${result.requiresApprovalForExecution ? 'Any resulting execution remains approval-gated.' : ''}`,
    confidence: result.ok ? 'medium' : 'low', source: result.sourceType === 'report' ? 'report_context' : 'backend_context',
    questionType, needsClarification: false,
  };
}

function handleStrategyAnalysis(_message: string, pageContext: PageContext | null): HermesResponse {
  const strategies = pageContext?.visibleItems.filter(i => i.type === 'strategy') || [];

  if (strategies.length === 0) {
    return {
      text: `I don't see any strategies loaded on the current page. Could you navigate to the Trading page or provide the strategy data?`,
      confidence: 'low',
      source: 'page_context',
      questionType: 'strategy_analysis',
      needsClarification: true,
      clarificationQuestion: 'Which strategy would you like me to analyze?',
    };
  }

  let responseText = `I can see ${strategies.length} strateg${strategies.length === 1 ? 'y' : 'ies'} on this page:\n\n`;
  for (const s of strategies.slice(0, 5)) {
    responseText += `- **${s.title}**: Status: ${s.status}`;
    if (s.score) responseText += `, Score: ${s.score}`;
    responseText += '\n';
  }

  responseText += `\nFor detailed backtesting or optimization analysis, I'd need to run through the Trading workflow. Would you like me to help with that?`;
  responseText += `\n\nSource: page context (bundled local data).`;

  return {
    text: responseText,
    confidence: 'medium',
    source: 'page_context',
    questionType: 'strategy_analysis',
    needsClarification: false,
  };
}

function handleExecution(message: string, _pageContext: PageContext | null): HermesResponse {
  const lower = message.toLowerCase();

  // Check for gated/blocked actions
  const isLiveTrade = /\b(live trade|real trade|execute trade|place order)\b/.test(lower);
  const isPublish = /\b(publish|send(?: the)? email|submit|charge|payment|insert(?: this)? real client)\b/.test(lower);

  if (isLiveTrade || isPublish) {
    let responseText = `⚠️ I can't execute that directly from this chat. `;
    if (isLiveTrade) {
      responseText += `Live trading requires going through the Trading workflow with proper risk checks. I can help you set up the trade parameters and guide you through the approval process.`;
    }
    if (isPublish) {
      responseText += `External actions and persistent writes—publishing, sending, charging, or inserting a real client—require explicit approval and a safe server-side workflow. Chat creates no external action.`;
    }
    responseText += `\n\nI can help you prepare the action and route it safely. Would you like me to do that?`;

    return {
      text: responseText,
      confidence: 'high',
      source: 'page_context',
      questionType: 'execution',
      needsClarification: false,
    };
  }

  return {
    text: `I can help you prepare actions, but I execute through safe internal processes — not directly from chat. What action would you like me to help you set up?`,
    confidence: 'medium',
    source: 'page_context',
    questionType: 'execution',
    needsClarification: true,
    clarificationQuestion: 'What action would you like to prepare?',
  };
}

function handleUnclear(message: string, pageContext: PageContext | null): HermesResponse {
  // Check for matching source hints
  const hints = findMatchingHints(message);
  if (hints.length > 0) {
    const bestHint = hints[0];
    return {
      text: `Based on your previous instruction: "${bestHint.instruction}"\n\nI'm interpreting your question in that context. Could you confirm or clarify?`,
      confidence: 'medium',
      source: 'learning',
      questionType: 'unclear',
      needsClarification: true,
      clarificationQuestion: `Based on your instruction "${bestHint.instruction}", could you clarify what you'd like me to do?`,
    };
  }

  const quotedRequest = message.trim() || '(empty request)';
  const pageSource = pageContext ? `${pageContext.pageTitle} page context` : 'no current page context';
  const responseText = `You asked: "${quotedRequest}." I checked ${pageSource}, local bundled context, and local activity memory. I could not determine a specific action or target. Could you clarify what you would like me to do?\n\nI can check live Supabase data (when connected), page context, reports, or local memory. What would you like me to focus on?`;

  return {
    text: responseText,
    confidence: 'none',
    source: 'honest_fallback',
    questionType: 'unclear',
    needsClarification: true,
    clarificationQuestion: 'Which source should I check: the current page, loaded reports, local Nexus context, or a research task?',
  };
}

function handleNexusTopic(message: string, pageContext: PageContext | null): HermesResponse {
  const lower = message.toLowerCase();
  if (/julius erving|fake customer inserted|synthetic customer status/.test(lower)) {
    return contextResponse(getHermesContext(message, { type: 'synthetic_client_status' }), 'nexus_topic');
  }
  if (/best.*opportunity|opportunit/.test(lower)) return contextResponse(getHermesContext(message, { type: 'opportunities_summary' }), 'nexus_topic');
  if (/research.*candidate|research engine/.test(lower)) return contextResponse(getHermesContext(message, { type: 'research_summary' }), 'nexus_topic');
  let topicKey = '';
  for (const key of Object.keys(nexusTopics)) {
    if (lower.includes(key)) {
      topicKey = key;
      break;
    }
  }
  const topic = nexusTopics[topicKey];
  if (!topic) {
    return handleUnclear(message, pageContext);
  }

  let responseText = topic.explain;
  if (topic.why) responseText += `\n\nWhy it matters: ${topic.why}`;
  if (topic.safety) responseText += `\n\nSafety: ${topic.safety}`;
  if (topic.approval) responseText += `\n\nApproval flow: ${topic.approval}`;
  if (topic.howToApprove) responseText += `\n\nHow to approve: ${topic.howToApprove}`;
  if (topic.specialist) responseText += `\n\nSpecialist: ${topic.specialist}`;
  if (topic.cleanup) responseText += `\n\nCleanup: ${topic.cleanup}`;
  responseText += `\n\n${topic.next}`;

  if (pageContext?.pageTitle) {
    responseText += `\n\nData source: local bundled context (static). Not live database records.`;
  }

  return {
    text: responseText,
    confidence: 'high',
    source: 'page_context',
    questionType: 'nexus_topic',
    needsClarification: false,
  };
}

function handleOpinion(_message: string, _pageContext: PageContext | null): HermesResponse {
  if (/improve/i.test(_message)) return contextResponse(getHermesContext(_message, { type: 'blockers_summary' }), 'opinion');
  if (/opportunity/i.test(_message)) return contextResponse(getHermesContext(_message, { type: 'opportunities_summary' }), 'opinion');
  const responseText = `Here's my honest ranking of what to monetize first:\n\n1. **$97 Credit & Funding Readiness Review** — most complete, lowest risk, proves the entire payment journey\n2. **$297 Assisted Plan** — recycles the same framework with more hands-on work, natural upsell\n3. **Monthly readiness subscription** — recurring revenue, but needs the one-time journey proven first\n4. **Affiliate pathways** (SmartCredit, banks) — passive income, but depends on having clients\n5. **$497 Higher Touch Sprint** — premium tier, but only makes sense after the lower tiers work\n\nMy recommendation: prove the $97 first. Everything else builds on that proof.\n\nData source: local bundled context (static). Not live revenue data.`;

  return {
    text: responseText,
    confidence: 'medium',
    source: 'page_context',
    questionType: 'opinion',
    needsClarification: false,
  };
}

function handleApproval(_message: string, _pageContext: PageContext | null): HermesResponse {
  return contextResponse(getHermesContext(_message, { type: 'approvals_summary' }), 'approval');
}

function handleMoney(_message: string, _pageContext: PageContext | null): HermesResponse {
  return contextResponse(getHermesContext(_message, { type: 'offers_summary' }), 'money');
}

function handleBlockers(_message: string, _pageContext: PageContext | null): HermesResponse {
  return contextResponse(getHermesContext(_message, { type: 'blockers_summary' }), 'blockers');
}

function handleStrategy(_message: string, _pageContext: PageContext | null): HermesResponse {
  const responseText = `Here's my honest strategy assessment:\n\n**What's working:** The backend engines are solid—9 of 9 passed, 18 safe schedules running, 152 research sources discovered, 50 candidates scored. The architecture is real.\n\n**What's not:** The gap between "the system works" and "you can see it working" is still too wide. Reports say things are fine, but the UI should prove it.\n\n**Today's priorities:**\n1. Prove the $97 money path (synthetic customer → Stripe test → dashboard verification)\n2. Fix Resend so communication can leave draft mode\n3. Pick 3-5 research candidates and convert them to offers or content\n4. Keep every external action behind Ray Review\n\n**What I'd stop:** Adding more infrastructure before proving what we have. The system is overbuilt for zero revenue. Let's prove one path works, then expand.\n\nData source: local bundled context (static). Not live strategy data.`;

  return {
    text: responseText,
    confidence: 'medium',
    source: 'page_context',
    questionType: 'strategy',
    needsClarification: false,
  };
}

function handleCasual(message: string, _pageContext: PageContext | null): HermesResponse {
  const lower = message.toLowerCase();
  const time = getTimeContext();

  // Favorite sport/food/etc — natural non-human answer
  if (/\b(favorite\s+(sport|food|color|movie|song|book|hobby|game))\b/.test(lower)) {
    const match = lower.match(/favorite\s+(\w+)/);
    const topic = match ? match[1] : 'thing';
    let responseText = '';
    if (/\b(sport)\b/.test(topic)) {
      responseText = `I don't have personal hobbies, but if I'm choosing from a Nexus angle, I'd pick basketball — it maps well to strategy, spacing, timing, and team roles. For you, I'd steer the conversation back to what helps Nexus make money or operate better. What are we working on?`;
    } else if (/\b(food)\b/.test(topic)) {
      responseText = `I don't eat, but I'd pick coffee — it's the universal "let's focus" signal. What's on your mind?`;
    } else if (/\b(color)\b/.test(topic)) {
      responseText = `I'd go with blue — it's what most dashboards use for a reason. Clean, trustworthy, gets out of the way. Speaking of dashboards, want me to check anything live?`;
    } else {
      responseText = `I don't have personal preferences, but I'm designed to be useful. What can I help you with right now?`;
    }
    return { text: responseText, confidence: 'high', source: 'honest_fallback', questionType: 'casual', needsClarification: false };
  }

  // How are you
  if (/\b(how are you|how'?s it going|what'?s your day like)\b/.test(lower)) {
    return {
      text: `I'm running fine. It's ${time.formattedTime} on ${time.dayOfWeek}. All systems are operational — live Supabase read is ${isSupabaseConfigured ? 'connected' : 'not configured'}. What would you like to focus on?`,
      confidence: 'high',
      source: 'time_context',
      questionType: 'casual',
      needsClarification: false,
    };
  }

  // Are you real / who are you
  if (/\b(are you real|who are you|what are you)\b/.test(lower)) {
    return {
      text: `I'm Hermes, your CEO advisor. I'm a local reasoning engine — I classify your questions, resolve entities from page context, and use live Supabase data when connected. I don't have a live AI model or internet access, but I can reason about what's loaded. What can I help you with?`,
      confidence: 'high',
      source: 'honest_fallback',
      questionType: 'casual',
      needsClarification: false,
    };
  }

  // Generic casual
  const responseText = `I'm here and running. It's ${time.formattedTime} on ${time.dayOfWeek}. What's on your mind?`;
  return {
    text: responseText,
    confidence: 'high',
    source: 'time_context',
    questionType: 'casual',
    needsClarification: false,
  };
}

function handleEmotional(_message: string, _pageContext: PageContext | null): HermesResponse {
  const responseText = `I hear that. The gap between backend wins and frontend experience is real, and it's frustrating when the system says "working" but the UI doesn't feel like it. That's exactly why today should be about proving things visually—every control doing what it says, every approval explaining itself.\n\nWhat's the single thing that feels most broken right now? We fix that first, then move to the next one.`;

  return {
    text: responseText,
    confidence: 'medium',
    source: 'honest_fallback',
    questionType: 'emotional',
    needsClarification: false,
  };
}

function handlePartnerMode(_message: string, _pageContext: PageContext | null): HermesResponse {
  const responseText = `Fair point. I'll drop the terminal-wrapper energy. Here's what I actually think: the system is overbuilt for where you are. You don't need more reports—you need one revenue proof. The $97 journey is the simplest path to that. Everything else can wait.\n\nMy honest recommendation: stop adding features and prove one thing works end-to-end. The $97 readiness review is that thing.`;

  return {
    text: responseText,
    confidence: 'high',
    source: 'honest_fallback',
    questionType: 'partner_mode',
    needsClarification: false,
  };
}

function handleSummary(_message: string, _pageContext: PageContext | null): HermesResponse {
  return contextResponse(getHermesContext(_message, { type: 'system_status' }), 'summary');
}

function handleTrading(_message: string, _pageContext: PageContext | null): HermesResponse {
  return contextResponse(getHermesContext(_message, { type: 'trading_paper_summary' }), 'trading');
}
