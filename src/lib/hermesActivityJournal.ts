/**
 * Hermes Activity Journal — localStorage-backed activity memory so Hermes can
 * answer "what did we work on yesterday?", "what changed today?", etc.
 *
 * Future: Supabase adapter interface stubbed but not wired yet.
 */

export interface ActivityEvent {
  id: string;
  timestamp: string;
  timezone: string;
  source: string;
  pageId: string;
  route: string;
  eventType: string;
  title: string;
  summary: string;
  entities: string[];
  status: string;
  importance: 'low' | 'medium' | 'high' | 'critical';
  dataSource: string;
  relatedReport?: string;
  relatedCommit?: string;
  relatedTask?: string;
  safetyLevel: 'safe' | 'gated' | 'blocked';
}

export type EventType =
  | 'page_view' | 'hermes_message' | 'opencode_result' | 'build_result'
  | 'route_error' | 'runtime_error' | 'button_action' | 'approval_action'
  | 'task_created' | 'report_generated' | 'blocker_detected' | 'ray_feedback'
  | 'decision' | 'next_step' | 'memory_saved' | 'source_hint_saved';

const JOURNAL_KEY = 'nexus_hermes_activity_journal';
const MAX_EVENTS = 500;

function safe(): Storage | null {
  try { return typeof window !== 'undefined' ? window.localStorage : null; } catch { return null; }
}

function loadEvents(): ActivityEvent[] {
  const ls = safe();
  if (!ls) return [];
  try {
    const raw = ls.getItem(JOURNAL_KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw);
    return Array.isArray(arr) ? arr : [];
  } catch { return []; }
}

function saveEvents(events: ActivityEvent[]): void {
  const ls = safe();
  if (!ls) return;
  try {
    ls.setItem(JOURNAL_KEY, JSON.stringify(events.slice(-MAX_EVENTS)));
  } catch { /* quota exceeded — ignore */ }
}

/** Record an activity event. */
export function recordActivity(event: Omit<ActivityEvent, 'id' | 'timestamp' | 'timezone'>): ActivityEvent {
  const now = new Date();
  const full: ActivityEvent = {
    ...event,
    id: `act-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    timestamp: now.toISOString(),
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  };
  const events = loadEvents();
  events.push(full);
  saveEvents(events);
  return full;
}

/** Get all events (most recent last). */
export function getAllEvents(): ActivityEvent[] {
  return loadEvents();
}

/** Get events within a time window. */
export function getEventsInRange(start: Date, end: Date): ActivityEvent[] {
  return loadEvents().filter(e => {
    const t = new Date(e.timestamp);
    return t >= start && t <= end;
  });
}

/** Get events from today. */
export function getTodayEvents(): ActivityEvent[] {
  const now = new Date();
  const start = new Date(now);
  start.setHours(0, 0, 0, 0);
  return getEventsInRange(start, now);
}

/** Get events from yesterday. */
export function getYesterdayEvents(): ActivityEvent[] {
  const now = new Date();
  const start = new Date(now);
  start.setDate(start.getDate() - 1);
  start.setHours(0, 0, 0, 0);
  const end = new Date(start);
  end.setHours(23, 59, 59, 999);
  return getEventsInRange(start, end);
}

/** Get events from the last N hours. */
export function getLastHoursEvents(hours: number): ActivityEvent[] {
  const now = new Date();
  const start = new Date(now);
  start.setHours(start.getHours() - hours);
  return getEventsInRange(start, now);
}

/** Get events matching a time window. */
export function getEventsForWindow(window: { start: Date; end: Date }): ActivityEvent[] {
  return getEventsInRange(window.start, window.end);
}

/** Clear all events. */
export function clearJournal(): void {
  const ls = safe();
  if (ls) try { ls.removeItem(JOURNAL_KEY); } catch { /* ignore */ }
}
