/**
 * Hermes Time Context Provider — gives Hermes real browser time/date/daypart
 * so it can answer "what day is it?", "good evening", "schedule for tonight", etc.
 *
 * Future: server-time adapter stubbed but not faked.
 */

export interface TimeContext {
  browserTime: Date;
  isoTimestamp: string;
  localDate: string;
  formattedDate: string;
  formattedTime: string;
  dayOfWeek: string;
  timezone: string;
  timeOfDay: 'morning' | 'afternoon' | 'evening' | 'night';
  source: 'browser';
  serverTimeAvailable: false;
}

export interface TimeWindow {
  start: Date;
  end: Date;
  label: string;
}

/** Matching-only normalization. Callers retain the original input for display. */
export function normalizeTimeText(text: string): string {
  return text
    .toLowerCase()
    .replace(/[\u2018\u2019]/g, "'")
    .replace(/\btodays\b/g, "today's")
    .replace(/[^a-z0-9'\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/** Get the current time context from the browser. */
export function getTimeContext(): TimeContext {
  const now = new Date();
  const hour = now.getHours();
  const timeOfDay: TimeContext['timeOfDay'] =
    hour >= 5 && hour < 12 ? 'morning' :
    hour >= 12 && hour < 17 ? 'afternoon' :
    hour >= 17 && hour < 21 ? 'evening' : 'night';

  return {
    browserTime: now,
    isoTimestamp: now.toISOString(),
    localDate: now.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }),
    formattedDate: now.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }),
    formattedTime: now.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true }),
    dayOfWeek: now.toLocaleDateString('en-US', { weekday: 'long' }),
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    timeOfDay,
    source: 'browser',
    serverTimeAvailable: false,
  };
}

/** Resolve a relative time phrase to a concrete time window. */
export function resolveRelativeTime(phrase: string, now?: Date): TimeWindow | null {
  const base = now || new Date();
  const lower = normalizeTimeText(phrase);

  // Today/tonight/evening/this evening
  if (/^(today|tonight|this evening|this afternoon|this morning)$/.test(lower)) {
    const start = new Date(base);
    start.setHours(lower.includes('morning') ? 6 : lower.includes('afternoon') ? 12 : 17, 0, 0, 0);
    const end = new Date(base);
    end.setHours(lower.includes('morning') ? 12 : lower.includes('afternoon') ? 17 : 23, 59, 59, 999);
    return { start, end, label: lower };
  }

  // Tomorrow
  if (/^tomorrow(\s+(morning|afternoon|evening|night))?$/.test(lower)) {
    const tomorrow = new Date(base);
    tomorrow.setDate(tomorrow.getDate() + 1);
    const part = lower.includes('morning') ? 6 : lower.includes('afternoon') ? 12 : lower.includes('evening') ? 17 : 0;
    tomorrow.setHours(part, 0, 0, 0);
    const end = new Date(tomorrow);
    end.setHours(part < 12 ? 12 : part < 17 ? 17 : 23, 59, 59, 999);
    return { start: tomorrow, end, label: lower };
  }

  // Later today / in X hours
  const inHoursMatch = lower.match(/in\s+(\d+)\s+hours?/);
  if (inHoursMatch || lower === 'later today') {
    const hours = inHoursMatch ? parseInt(inHoursMatch[1]) : 2;
    const start = new Date(base);
    start.setHours(start.getHours() + hours, 0, 0, 0);
    const end = new Date(start);
    end.setHours(end.getHours() + 2);
    return { start, end, label: `in ${hours} hours` };
  }

  // Next Friday / next Monday / etc.
  const dayNames = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
  const nextDayMatch = lower.match(/next\s+(sunday|monday|tuesday|wednesday|thursday|friday|saturday)/);
  if (nextDayMatch) {
    const targetDay = dayNames.indexOf(nextDayMatch[1]);
    const start = new Date(base);
    const currentDay = start.getDay();
    const daysAhead = ((targetDay - currentDay + 7) % 7) || 7;
    start.setDate(start.getDate() + daysAhead);
    start.setHours(9, 0, 0, 0);
    const end = new Date(start);
    end.setHours(17, 0, 0, 0);
    return { start, end, label: `next ${nextDayMatch[1]}` };
  }

  // Yesterday
  if (lower === 'yesterday') {
    const yesterday = new Date(base);
    yesterday.setDate(yesterday.getDate() - 1);
    yesterday.setHours(0, 0, 0, 0);
    const end = new Date(yesterday);
    end.setHours(23, 59, 59, 999);
    return { start: yesterday, end, label: 'yesterday' };
  }

  return null;
}

/** Detect if a message contains time-related questions or scheduling phrases. */
export function detectTimeIntent(text: string): {
  isTimeQuestion: boolean;
  isSchedulingPhrase: boolean;
  timeWindow: TimeWindow | null;
  timeOfDayMention: string | null;
} {
  const lower = normalizeTimeText(text);

  const isTimeQuestion = /\b(what is today's date|what date is it|what day is it|what day are we on|what is the date|today's date|today date|what time is it|current time|time now|current date)\b/.test(lower);
  const relativeTimePattern = /\b(this evening|tonight|tomorrow(?: morning| afternoon| evening| night)?|later today|in \d+ hours?|next (?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b/;
  const isSchedulingPhrase = relativeTimePattern.test(lower);

  let timeWindow: TimeWindow | null = null;
  let timeOfDayMention: string | null = null;

  // Extract time window from scheduling phrases
  const timePhrases = [
    /this evening/, /tonight/, /this afternoon/, /this morning/,
    /tomorrow(\s+(morning|afternoon|evening|night))?/,
    /later today/, /in \d+ hours?/,
    /next (monday|tuesday|wednesday|thursday|friday|saturday|sunday)/,
    /yesterday/
  ];
  for (const phrase of timePhrases) {
    const match = lower.match(phrase);
    if (match) {
      timeWindow = resolveRelativeTime(match[0]);
      timeOfDayMention = match[0];
      break;
    }
  }

  return { isTimeQuestion, isSchedulingPhrase, timeWindow, timeOfDayMention };
}
