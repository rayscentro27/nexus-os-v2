/**
 * Hermes Response Router — single entry point for all Hermes questions.
 *
 * Classifies question type, resolves entities, queries memory, queries adapters,
 * and generates a proper response. No more canned fallbacks.
 */

import { getTimeContext, detectTimeIntent } from './hermesTimeContext';
import { buildPageContext, type PageContext } from './hermesContextBridge';
import { resolveEntity, setLastReferencedEntity } from './hermesEntityResolver';
import { queryMemory } from './hermesMemoryQuery';
import { detectLearningInstruction, storeHint, findMatchingHints } from './hermesSourceHints';
import { querySupabaseContext } from './hermesSupabaseContextAdapter';
import { getBackendStatusMessage } from './hermesBackendContextAdapter';

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
  | 'unclear';

export interface ResponseContext {
  message: string;
  pageId?: string;
  route?: string;
  activeTab?: string;
  selectedItem?: PageContext['selectedItem'];
  visibleItems?: PageContext['visibleItems'];
  availableActions?: string[];
}

export interface HermesResponse {
  text: string;
  confidence: 'high' | 'medium' | 'low' | 'none';
  source: 'time_context' | 'page_context' | 'entity_resolution' | 'memory' | 'supabase_stub' | 'backend_stub' | 'canned' | 'honest_fallback' | 'learning';
  questionType: QuestionType;
  needsClarification: boolean;
  clarificationQuestion?: string;
  sourceHint?: string;
}

/** Main entry point — classify, resolve, respond. */
export function hermesResponseRouter(ctx: ResponseContext): HermesResponse {
  const { message, pageId, route, activeTab, selectedItem, visibleItems, availableActions } = ctx;

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
  const pageContext: PageContext | null = pageId
    ? { ...buildPageContext(pageId, route), activeTab: activeTab || null, selectedItem: selectedItem || null, visibleItems: visibleItems || [], availableActions: availableActions || [] }
    : null;

  // 3. Classify question type
  const questionType = classifyQuestion(message);

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

    case 'trading':
      return handleTrading(message, pageContext);

    default:
      return handleUnclear(message, pageContext);
  }
}

function classifyQuestion(text: string): QuestionType {
  const lower = text.toLowerCase().trim();

  // Greetings
  if (/^(hi|hello|hey|yo|sup|good morning|good afternoon|good evening|good night|howdy|hola|hey there|what's up|whats up)\b/.test(lower)) {
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

  // Learning/memory instructions
  if (detectLearningInstruction(text).isLearning) {
    return 'learning_instruction';
  }

  // Entity references (this, that, first one, etc.) — check BEFORE nexus topics
  if (/\b(this|that|first|second|third|another|other|next|those|these)\b/.test(lower) &&
    /\b(strategy|item|opportunity|offer|candidate|draft|report|client|rule|action|row|card|thing|one)\b/.test(lower)) {
    return 'entity_question';
  }

  // Nexus-specific topic matching (check before generic patterns)
  for (const pattern of Object.keys(nexusTopics)) {
    if (lower.includes(pattern)) {
      return 'nexus_topic';
    }
  }

  // Comparison
  if (/\b(compare|versus|vs\.?|difference between|how does .+ compare|which is better)\b/.test(lower)) {
    return 'comparison';
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
  if (/\b(trad|oanda|vibe|forex|market|position)\b/.test(lower)) {
    return 'trading';
  }

  // Supabase queries
  if (/\b(supabase|database|query|row|table|live data)\b/.test(lower)) {
    return 'supabase_query';
  }

  // Backend queries
  if (/\b(model|ai|llm|gpt|claude|backend|endpoint)\b/.test(lower)) {
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

  // Casual / personal
  if (/\b(coffee|sleep|tired|bored|hungry|weekend|vacation|chill|relax|did you sleep|how are you|how'?s it going|what'?s your day like)\b/.test(lower)) {
    return 'casual';
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

  let responseText = `I understand you want to schedule something for ${timeIntent.timeOfDayMention || 'later'}. `;

  if (timeIntent.timeWindow) {
    const startStr = timeIntent.timeWindow.start.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
    const endStr = timeIntent.timeWindow.end.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
    responseText += `That would be between ${startStr} and ${endStr} today. `;

    if (pageContext?.availableActions) {
      const schedulableActions = pageContext.availableActions.filter(a => !pageContext.blockedActions?.includes(a));
      if (schedulableActions.length > 0) {
        responseText += `Available actions on this page: ${schedulableActions.join(', ')}. Which would you like me to schedule?`;
      } else {
        responseText += `I can help you plan this, but I don't have specific scheduling actions on this page. What would you like to do?`;
      }
    } else {
      responseText += `I can help you plan this. What would you like to schedule?`;
    }
  } else {
    responseText += `Could you be more specific about the time? For example: "this evening", "tomorrow morning", "in 2 hours", or "next Friday".`;
  }

  return {
    text: responseText,
    confidence: 'medium',
    source: 'time_context',
    questionType: 'scheduling',
    needsClarification: !timeIntent.timeWindow,
    clarificationQuestion: !timeIntent.timeWindow ? 'Could you specify when you want to schedule this?' : undefined,
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

  responseText += `What would you like to know about these?`;

  return {
    text: responseText,
    confidence: 'high',
    source: 'page_context',
    questionType: 'page_question',
    needsClarification: false,
  };
}

function handleEntityQuestion(message: string, pageContext: PageContext | null): HermesResponse {
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

  let responseText = `You're referring to ${item.title}. `;
  responseText += `Status: ${item.status}. `;
  if (item.score !== undefined) responseText += `Score: ${item.score}. `;
  if (item.confidence) responseText += `Confidence: ${item.confidence}. `;
  if (item.revenueRange) responseText += `Revenue potential: ${item.revenueRange}. `;

  responseText += `\n\nData source: ${item.dataSource}. ${item.dataSource === 'local_static' ? 'This is bundled local context — not live data.' : ''}`;

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
  if (!pageContext || pageContext.visibleItems.length < 2) {
    return {
      text: `I need at least two items to compare. Could you tell me which items you'd like me to compare?`,
      confidence: 'low',
      source: 'page_context',
      questionType: 'comparison',
      needsClarification: true,
      clarificationQuestion: 'Which two items would you like me to compare?',
    };
  }

  const items = pageContext.visibleItems.slice(0, 2);
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

function handleSupabaseQuery(_message: string): HermesResponse {
  const result = querySupabaseContext('unknown');

  return {
    text: `I don't have live Supabase access from this chat layer. ${result.reason}\n\nI can see loaded page context and local bundled data, but I cannot query Supabase directly. If you need live data, I can create a task to query it through a safe internal process.`,
    confidence: 'medium',
    source: 'supabase_stub',
    questionType: 'supabase_query',
    needsClarification: false,
    sourceHint: 'Supabase adapter stub — not wired yet',
  };
}

function handleBackendQuery(_message: string): HermesResponse {
  return {
    text: getBackendStatusMessage(),
    confidence: 'medium',
    source: 'backend_stub',
    questionType: 'backend_query',
    needsClarification: false,
    sourceHint: 'Backend adapter stub — not wired yet',
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
  const isPublish = /\b(publish|send email|submit|charge|payment)\b/.test(lower);

  if (isLiveTrade || isPublish) {
    let responseText = `⚠️ I can't execute that directly from this chat. `;
    if (isLiveTrade) {
      responseText += `Live trading requires going through the Trading workflow with proper risk checks. I can help you set up the trade parameters and guide you through the approval process.`;
    }
    if (isPublish) {
      responseText += `External actions like publishing, sending emails, or processing payments require explicit approval and are routed through safe internal processes.`;
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

function handleUnclear(message: string, _pageContext: PageContext | null): HermesResponse {
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

  // Provide honest context about what we can do
  let responseText = `I'm not sure what you're asking for. Here's what I can help with right now:\n\n`;
  responseText += `• **Page context**: I can review what's on your current page\n`;
  responseText += `• **Entity references**: I can resolve "this", "that", "first one", etc.\n`;
  responseText += `• **Time/date**: I can tell you the current time and help with scheduling\n`;
  responseText += `• **Memory**: I can recall what we've worked on (local activity journal)\n`;
  responseText += `• **Strategy analysis**: I can help review strategies on the current page\n`;
  responseText += `• **Learning**: You can say "remember that..." to teach me preferences\n\n`;
  responseText += `I don't have live Supabase, web search, or real AI model access from this chat layer. I use local bundled context, browser time, and localStorage memory.\n\n`;
  responseText += `What would you like to focus on?`;

  return {
    text: responseText,
    confidence: 'none',
    source: 'honest_fallback',
    questionType: 'unclear',
    needsClarification: true,
    clarificationQuestion: 'What would you like help with?',
  };
}

function handleNexusTopic(message: string, pageContext: PageContext | null): HermesResponse {
  const lower = message.toLowerCase();
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
  const responseText = `Here's what's waiting for your decision, ranked by impact:\n\n1. **Synthetic customer insert** — unlocks the live dashboard test. This is the highest-impact decision.\n2. **Stripe test completion** — proves the payment journey works. Needs the customer insert first.\n3. **Resend configuration fix** — unblocks email sending. Requires a new API key and domain verification.\n4. **Content and communication drafts** — lower priority but ready to go.\n\nI'd handle them in that order. The first two are about proving the money path. The third is about communication. The fourth is about content.\n\nData source: local bundled context (static). Not live approval queue data.`;

  return {
    text: responseText,
    confidence: 'medium',
    source: 'page_context',
    questionType: 'approval',
    needsClarification: false,
  };
}

function handleMoney(_message: string, _pageContext: PageContext | null): HermesResponse {
  const responseText = `The closest money path is the $97 readiness review. We have the offer priced, the Stripe test session created, and the synthetic customer package staged. What's missing is your approval to insert the customer and complete the test charge. Once that's done, we can flip the dashboard flag and prove the journey end-to-end.\n\nAfter $97, the $297 and $497 tiers are natural extensions. The affiliate pathways and subscriptions come after we have proof that the core offer works.\n\nData source: local bundled context (static). Not live revenue data.`;

  return {
    text: responseText,
    confidence: 'medium',
    source: 'page_context',
    questionType: 'money',
    needsClarification: false,
  };
}

function handleBlockers(_message: string, _pageContext: PageContext | null): HermesResponse {
  const responseText = `The real blockers, in order of impact:\n\n1. **Synthetic customer not inserted** — this blocks the entire dashboard verification and money path proof\n2. **Resend domain/key mismatch** — blocks all email sending, including onboarding\n3. **Client live-data flag off** — the dashboard shows static fallback instead of real data\n4. **YouTube transcript missing** — blocks content pipeline for an approved video\n5. **NotebookLM export missing** — blocks knowledge sync\n\nThe first two are the ones that matter most. The customer insert unlocks revenue proof. Resend unlocks communication. Everything else is parallel work.\n\nData source: local bundled context (static). Not live system status.`;

  return {
    text: responseText,
    confidence: 'medium',
    source: 'page_context',
    questionType: 'blockers',
    needsClarification: false,
  };
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

function handleCasual(_message: string, _pageContext: PageContext | null): HermesResponse {
  const time = getTimeContext();
  const responseText = `I'm here and running on the same operating context as always. The system is healthy, the reports are current, and I've got the context loaded. It's ${time.formattedTime} on ${time.dayOfWeek}.\n\nWhat's on your mind?`;

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
  const responseText = `Here's the local status summary:\n\n- **Engines:** 9 of 9 passed\n- **Schedules:** 2 safe cycles loaded (08:00 and 18:00)\n- **Ray Review:** 0 decisions waiting\n- **Offers:** 9 registered\n- **Research:** 50 candidates scored, 26 immediately actionable\n- **Revenue:** $0 confirmed, $97 test path pending\n- **Blockers:** 5 active (customer insert, Resend, live-data flag, YouTube transcript, NotebookLM export)\n\nThe system is operational. The next value comes from clearing approvals, not generating more status files.\n\nData source: local bundled context (static). Not live system status.`;

  return {
    text: responseText,
    confidence: 'medium',
    source: 'page_context',
    questionType: 'summary',
    needsClarification: false,
  };
}

function handleTrading(_message: string, _pageContext: PageContext | null): HermesResponse {
  const responseText = `Trading status: Oanda demo endpoint is verified, one unit was placed and closed as a smoke test, zero open positions. Vibe paper backtest passed with 50 synthetic trades. Live trading is completely blocked—no real money, no funded accounts, no recurring orders.\n\nMy recommendation: keep daily market reads and paper analysis running behind the scheduler. Keep demo execution behind a decision card. Live trading stays off until you explicitly decide otherwise.\n\nData source: local bundled context (static). Not live trading data.`;

  return {
    text: responseText,
    confidence: 'medium',
    source: 'page_context',
    questionType: 'trading',
    needsClarification: false,
  };
}
