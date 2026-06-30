/**
 * Hermes Memory Query Layer — answers time-based memory questions using the Activity Journal.
 */

import {
  getTodayEvents, getYesterdayEvents, getLastHoursEvents,
  getAllEvents, type ActivityEvent
} from './hermesActivityJournal';

export interface MemoryQueryResult {
  events: ActivityEvent[];
  summary: string;
  topEntities: string[];
  blockers: string[];
  decisions: string[];
  nextActions: string[];
  timeRangeUsed: string;
  eventCount: number;
}

/** Query memory for a time window. */
export function queryMemory(timeWindow: string): MemoryQueryResult {
  const lower = timeWindow.toLowerCase().trim();
  let events: ActivityEvent[];
  let label: string;

  if (lower === 'today' || lower.includes('today')) {
    events = getTodayEvents();
    label = 'today';
  } else if (lower === 'yesterday' || lower.includes('yesterday')) {
    events = getYesterdayEvents();
    label = 'yesterday';
  } else if (lower.includes('this morning') || lower.includes('this afternoon') || lower.includes('this evening')) {
    events = getTodayEvents();
    label = lower;
  } else if (lower.includes('last 24 hours') || lower.includes('last 24h')) {
    events = getLastHoursEvents(24);
    label = 'last 24 hours';
  } else if (lower.includes('last 7 days') || lower.includes('last week')) {
    events = getLastHoursEvents(168);
    label = 'last 7 days';
  } else if (lower.includes('last hour') || lower.includes('recently')) {
    events = getLastHoursEvents(1);
    label = 'last hour';
  } else {
    events = getAllEvents().slice(-50);
    label = 'recent activity';
  }

  return buildResult(events, label);
}

/** Query memory for a specific event type. */
export function queryMemoryByType(eventType: string): MemoryQueryResult {
  const events = getAllEvents().filter(e => e.eventType === eventType);
  return buildResult(events, `events of type: ${eventType}`);
}

function buildResult(events: ActivityEvent[], label: string): MemoryQueryResult {
  const entityMap = new Map<string, number>();
  const blockers: string[] = [];
  const decisions: string[] = [];
  const nextActions: string[] = [];

  for (const e of events) {
    for (const entity of e.entities) {
      entityMap.set(entity, (entityMap.get(entity) || 0) + 1);
    }
    if (e.eventType === 'blocker_detected' || e.importance === 'critical') {
      blockers.push(e.title);
    }
    if (e.eventType === 'decision') {
      decisions.push(e.title);
    }
    if (e.eventType === 'next_step') {
      nextActions.push(e.title);
    }
  }

  const topEntities = [...entityMap.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([entity]) => entity);

  const summary = events.length === 0
    ? `No activity recorded for ${label}.`
    : `${events.length} events recorded for ${label}. Key areas: ${topEntities.slice(0, 5).join(', ') || 'general activity'}.`;

  return {
    events,
    summary,
    topEntities,
    blockers: blockers.slice(0, 5),
    decisions: decisions.slice(0, 5),
    nextActions: nextActions.slice(0, 5),
    timeRangeUsed: label,
    eventCount: events.length,
  };
}

/** Check if there are any events at all. */
export function hasMemoryEvents(): boolean {
  return getAllEvents().length > 0;
}

/** Get a human-readable summary of recent activity. */
export function getRecentActivitySummary(hours: number = 24): string {
  const events = getLastHoursEvents(hours);
  if (events.length === 0) {
    return `No activity recorded in the last ${hours} hours.`;
  }

  const byType = new Map<string, number>();
  for (const e of events) {
    byType.set(e.eventType, (byType.get(e.eventType) || 0) + 1);
  }

  const parts = [...byType.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([type, count]) => `${count} ${type.replace(/_/g, ' ')}${count > 1 ? 's' : ''}`);

  return `${events.length} events in the last ${hours} hours: ${parts.join(', ')}.`;
}
