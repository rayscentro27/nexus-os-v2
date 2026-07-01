/**
 * Hermes Message Auditor — collects and scores message history.
 *
 * Exports audit reports showing:
 *  - Every message with its route, source, model usage, Supabase usage
 *  - Expected vs actual activation level
 *  - Failure type classification
 *  - Fix recommendation
 */

import type { ActivationLevel } from './hermesActivationLevels';

export interface AuditedMessage {
  timestamp: string;
  surface: 'full_workroom' | 'inline_drawer' | 'specialist' | 'unknown';
  route: string | null;
  page: string | null;
  userMessage: string;
  hermesAnswer: string;
  detectedIntent: string | 'not_logged';
  selectedRoute: string | 'not_logged';
  sourceUsed: string | 'not_logged';
  modelUsed: boolean | 'not_logged';
  supabaseUsed: boolean | 'not_logged';
  followupMemoryUsed: boolean | 'not_logged';
  safetyGateUsed: boolean | 'not_logged';
  // Scoring fields
  expectedActivationLevel: ActivationLevel;
  actualActivationLevel: ActivationLevel | 'unknown';
  expectedIntent: string;
  actualIntent: string;
  expectedSource: string;
  actualSource: string;
  expectedRoute: string;
  actualRoute: string;
  correct: boolean;
  failureType: string | null;
  fixNeeded: string | null;
}

export interface AuditReport {
  totalMessages: number;
  correctCount: number;
  failureCount: number;
  notLoggedCount: number;
  failureBreakdown: Record<string, number>;
  messages: AuditedMessage[];
  generatedAt: string;
}

/**
 * Define expected activation level for known message patterns.
 * This is the "ground truth" used to score actual routing.
 */
export function getExpectedActivationLevel(message: string): {
  level: ActivationLevel;
  intent: string;
  source: string;
  route: string;
} {
  const lower = message.toLowerCase().trim();

  // Safety gate
  if (/\b(?:can\s+you\s+)?place\s+a\s+trade|execute\s+(?:this\s+)?trade|buy\s+\w+|sell\s+\w+|turn\s+on\s+live\s+trading|send\s+an?\s+email|publish\s+to\s+social|charge\s+a\s+payment|submit\s+a\s+dispute|delete\s+records?|truncate\s+table|run\s+shell|start\s+scheduler|seed\s+supabase\b/i.test(lower)) {
    return { level: 0, intent: 'safety_gate', source: 'safety_gate', route: 'blocked_or_gated' };
  }

  // Follow-up memory
  if (
    /^(?:number|#|option)\s*\d+/.test(lower) ||
    /^(?:ok\s+)?pick\s+one/i.test(lower) ||
    /^(?:that|this|it|the\s+one)\b/i.test(lower) ||
    /\b(which\s+one\s+do\s+you\s+recommend|recommend\s+one|the\s+(monthly|readiness|subscription)\s+one)\b/i.test(lower) ||
    /\b(how\s+do\s+we\s+implement\s+(it|that|this))\b/i.test(lower)
  ) {
    return { level: 3, intent: 'followup_resolution', source: 'conversation_memory', route: 'conversation_memory' };
  }

  // Meta/status/cost/process
  if (
    /\b(what\s+model\s+are\s+you|are\s+you\s+using\s+a\s+live\s+model|what\s+did.*cost|how\s+are\s+you\s+controlling\s+token|what\s+sections\s+are\s+live|is\s+trading\s+live|is\s+youtube\s+research\s+running|what\s+did\s+we\s+do\s+today|give\s+me\s+the\s+ceo\s+version|are\s+you\s+connected\s+to\s+live\s+supabase|why\s+did\s+you\s+answer|where\s+did\s+(that|it)\s+route|what\s+source\s+did\s+you\s+use|did\s+you\s+use\s+supabase|did\s+you\s+use\s+the\s+model)\b/i.test(lower) ||
    /\b(daily\s+summary|ceo\s+summary|ceo\s+version)\b/i.test(lower)
  ) {
    return { level: 1, intent: 'meta_status', source: 'local_reports_capability', route: 'no_model' };
  }

  // Live Supabase retrieval
  if (
    /\b(what\s+business\s+opportunities\s+are\s+available|show\s+me\s+(the\s+)?approvals|what\s+approvals\s+are\s+pending|show\s+me\s+(the\s+)?clients?|what\s+research\s+(candidates?|sources?)\b)/i.test(lower) &&
    !/\b(recommend|prioritize|which\s+one)\b/i.test(lower)
  ) {
    return { level: 2, intent: 'supabase_retrieval', source: 'live_supabase', route: 'supabase_query' };
  }

  // Local reasoning
  if (
    /\b(what\s+business\s+(can|should)\s+i\s+start|what\s+should\s+i\s+do\s+next|fastest\s+money\s+move|implementation\s+plan|30\s*days|low\s+startup\s+cost|recommend|prioritize)\b/i.test(lower)
  ) {
    return { level: 4, intent: 'local_reasoning', source: 'supabase_page_reports_memory', route: 'local_reasoning' };
  }

  // Default
  return { level: 1, intent: 'unknown', source: 'local_context', route: 'no_model' };
}

/**
 * Classify the failure type for a mismatched message.
 */
export function classifyFailure(
  expected: { level: ActivationLevel; intent: string; source: string; route: string },
  actual: { level: ActivationLevel | 'unknown'; intent: string; source: string; route: string },
): { failureType: string; fixNeeded: string } | null {
  if (expected.level === actual.level && expected.route === actual.route) {
    return null;
  }

  // Wrong intent
  if (expected.intent !== actual.intent && actual.intent !== 'not_logged') {
    if (expected.level === 3 && actual.level !== 3) {
      return {
        failureType: 'missed_followup_memory',
        fixNeeded: 'Message should activate Level 3 (conversation memory) but was routed to a different level. Follow-up reference was not resolved.',
      };
    }
    if (expected.level === 4 && actual.level === 1) {
      return {
        failureType: 'wrong_intent',
        fixNeeded: 'Business strategy question was misrouted as a status/meta question instead of local reasoning.',
      };
    }
    return {
      failureType: 'wrong_intent',
      fixNeeded: `Expected intent "${expected.intent}" but got "${actual.intent}".`,
    };
  }

  // Skipped Supabase
  if (expected.level === 2 && actual.level !== 2) {
    return {
      failureType: 'skipped_supabase',
      fixNeeded: 'Live Supabase data should have been queried but was not.',
    };
  }

  // Stale local fallback
  if (expected.source === 'live_supabase' && actual.source !== 'live_supabase' && actual.source !== 'not_logged') {
    return {
      failureType: 'stale_local_fallback',
      fixNeeded: 'Expected live Supabase data but fell back to static/local data.',
    };
  }

  // Generic clarification
  if (expected.level === 4 && actual.route === 'ask_clarification') {
    return {
      failureType: 'generic_clarification',
      fixNeeded: 'Should have reasoned from available context instead of asking clarification.',
    };
  }

  // Wrong model route
  if (expected.level === 4 && (actual.route === 'primary_model' || actual.route === 'cheap_model')) {
    return {
      failureType: 'wrong_model_route',
      fixNeeded: 'Should have used local reasoning (Level 4) before escalating to model.',
    };
  }

  // Missing safety block
  if (expected.level === 0 && actual.level !== 0) {
    return {
      failureType: 'missing_safety_block',
      fixNeeded: 'Dangerous execution request was not blocked by safety gate.',
    };
  }

  // Not logged
  if (actual.intent === 'not_logged' || actual.source === 'not_logged' || actual.route === 'not_logged') {
    return {
      failureType: 'not_logged',
      fixNeeded: 'Routing information was not logged for this message.',
    };
  }

  return {
    failureType: 'wrong_source',
    fixNeeded: `Expected source "${expected.source}" but got "${actual.source}".`,
  };
}

/**
 * Build the canonical audit message set — the example messages from the task.
 */
export function getCanonicalAuditMessages(): Array<{
  message: string;
  expected: { level: ActivationLevel; intent: string; source: string; route: string };
}> {
  const messages = [
    'What business opportunities are available?',
    'Which one do you recommend?',
    'Ok pick one for us to review.',
    'So number 3 how do we implement?',
    'The monthly readiness subscription.',
    'Are you connected to live Supabase data?',
    'What did you do today?',
    'Give me the CEO version.',
    'What model are you using?',
    'Can you place a trade?',
    'Is YouTube research running and writing to Supabase?',
    'What business should I start in 30 days with low startup cost?',
  ];

  return messages.map(message => ({
    message,
    expected: getExpectedActivationLevel(message),
  }));
}

/**
 * Score a message against its expected activation level.
 */
export function scoreMessage(
  message: string,
  actual: {
    level: ActivationLevel | 'unknown';
    intent: string;
    source: string;
    route: string;
  },
): AuditedMessage {
  const expected = getExpectedActivationLevel(message);
  const failure = classifyFailure(expected, actual);

  return {
    timestamp: new Date().toISOString(),
    surface: 'unknown',
    route: null,
    page: null,
    userMessage: message,
    hermesAnswer: '',
    detectedIntent: actual.intent,
    selectedRoute: actual.route,
    sourceUsed: actual.source,
    modelUsed: actual.route === 'primary_model' || actual.route === 'cheap_model',
    supabaseUsed: actual.source === 'live_supabase' || actual.source === 'live_supabase_context',
    followupMemoryUsed: actual.level === 3,
    safetyGateUsed: actual.level === 0,
    expectedActivationLevel: expected.level,
    actualActivationLevel: actual.level,
    expectedIntent: expected.intent,
    actualIntent: actual.intent,
    expectedSource: expected.source,
    actualSource: actual.source,
    expectedRoute: expected.route,
    actualRoute: actual.route,
    correct: failure === null,
    failureType: failure?.failureType || null,
    fixNeeded: failure?.fixNeeded || null,
  };
}

/**
 * Build a full audit report from the canonical message set.
 */
export function buildCanonicalAuditReport(): AuditReport {
  const canonical = getCanonicalAuditMessages();
  const messages: AuditedMessage[] = canonical.map(({ message }) => {
    // For the canonical audit, we score against the expected level
    // with "unknown" actual since we haven't run these through the pipeline yet
    return scoreMessage(message, {
      level: 'unknown',
      intent: 'not_logged',
      source: 'not_logged',
      route: 'not_logged',
    });
  });

  const failureBreakdown: Record<string, number> = {};
  let failureCount = 0;
  let notLoggedCount = 0;

  for (const msg of messages) {
    if (!msg.correct) {
      failureCount++;
      if (msg.failureType) {
        failureBreakdown[msg.failureType] = (failureBreakdown[msg.failureType] || 0) + 1;
      }
    }
    if (msg.failureType === 'not_logged') {
      notLoggedCount++;
    }
  }

  return {
    totalMessages: messages.length,
    correctCount: messages.length - failureCount,
    failureCount,
    notLoggedCount,
    failureBreakdown,
    messages,
    generatedAt: new Date().toISOString(),
  };
}
