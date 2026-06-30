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

  // Entity references (this, that, first one, etc.)
  if (/\b(this|that|first|second|third|another|other|next|those|these)\b/.test(lower) &&
    /\b(strategy|item|opportunity|offer|candidate|draft|report|client|rule|action|row|card|thing|one)\b/.test(lower)) {
    return 'entity_question';
  }

  // Comparison
  if (/\b(compare|versus|vs\.?|difference between|how does .+ compare|which is better)\b/.test(lower)) {
    return 'comparison';
  }

  // Memory/history
  if (/\b(what did we|what have we|what changed|what happened|show me|recall|remember|history|recent|today|yesterday|last week)\b/.test(lower)) {
    return 'memory_history';
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
  if (/\b(strategy|strategies|analyze|analysis|backtest|optimize|performance|return|risk)\b/.test(lower)) {
    return 'strategy_analysis';
  }

  // Execution
  if (/\b(execute|run|deploy|publish|send|submit|trade|charge|process)\b/.test(lower)) {
    return 'execution';
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
