/**
 * Hermes Daily Activity Translator — turns raw activity journal events
 * into plain-English CEO-ready summaries.
 *
 * No I/O. No model calls. All deterministic.
 */

import { getTodayEvents, getYesterdayEvents, getAllEvents, type ActivityEvent } from './hermesActivityJournal';
import { translateCategory, isLowValueCategory } from './hermesPlainEnglishTranslator';
import { getSectionSummary, getResearchEngineStatus } from './nexusSectionStatusRegistry';

/**
 * Group events by translated category.
 */
function groupByCategory(events: ActivityEvent[]): Map<string, ActivityEvent[]> {
  const groups = new Map<string, ActivityEvent[]>();
  for (const e of events) {
    const cat = translateCategory(e.source || e.eventType || 'uncategorized');
    if (!groups.has(cat)) groups.set(cat, []);
    groups.get(cat)!.push(e);
  }
  return groups;
}

/**
 * Identify completed work from events.
 */
function identifyCompleted(events: ActivityEvent[]): string[] {
  const completed: string[] = [];
  const groups = groupByCategory(events);

  for (const [cat, items] of groups) {
    if (isLowValueCategory(cat)) continue;

    if (cat === 'Hermes conversation' && items.length >= 2) {
      completed.push(`Hermes conversation (${items.length} exchanges)`);
    } else if (cat === 'Nexus section status review') {
      completed.push('Nexus section status review');
    } else if (cat === 'Supabase/live data check') {
      completed.push('Supabase data check');
    } else if (cat === 'code/build result' || cat === 'build result') {
      completed.push('Code/build work');
    } else if (cat === 'Report review' || cat === 'report generation') {
      completed.push('Report review');
    } else if (cat === 'Process/activity verification') {
      completed.push('Process verification');
    } else if (cat === 'Settings/config review') {
      completed.push('Settings/config review');
    } else if (cat === 'Ray Review action' || cat === 'Ray Review / approval workflow') {
      completed.push('Ray Review / approval workflow');
    } else if (cat === 'error encountered') {
      completed.push('Error encountered and noted');
    } else if (cat === 'Trading Lab / paper-demo review') {
      completed.push('Trading Lab / paper-demo review');
    } else if (cat === 'Hermes model/status check' || cat === 'Model cost/token review') {
      completed.push('Hermes model/status review');
    } else if (cat === 'decision made' || cat === 'next step identified') {
      completed.push('Decision or next step identified');
    } else if (cat !== 'conversation' && cat !== 'page navigation' && cat !== 'UI action') {
      completed.push(cat);
    }
  }

  return completed.length > 0 ? completed : ['No major work completed yet today.'];
}

/**
 * Identify blockers from events.
 */
function identifyBlockers(): string[] {
  const blockers: string[] = [];
  const summary = getSectionSummary();
  const yt = getResearchEngineStatus();

  if (summary.static > 0) blockers.push(`${summary.static} sections still using static/bundled data`);
  if (summary.report_snapshot > 0) blockers.push(`${summary.report_snapshot} sections using report snapshots, not live workflows`);
  if (yt.youtubeProofStatus === 'not_proven_live') blockers.push('YouTube research not proven live');
  if (summary.blocked > 0) blockers.push(`${summary.blocked} sections have blockers`);

  return blockers.length > 0 ? blockers : ['No critical blockers identified.'];
}

/**
 * Build a plain-English daily summary.
 */
export function buildDailySummary(date?: 'today' | 'yesterday'): string {
  const events = date === 'yesterday' ? getYesterdayEvents() : getTodayEvents();
  const allEvents = getAllEvents();
  const dateLabel = date === 'yesterday' ? 'yesterday' : 'today';

  // Determine memory source
  const memorySource = allEvents.length > 0
    ? 'local browser activity journal'
    : 'section status registry (no journal events recorded)';

  const durableNote = allEvents.length > 0
    ? `I'm using the local browser activity journal, so this is useful but not durable cross-device memory yet.`
    : '';

  if (events.length === 0) {
    const sectionSummary = getSectionSummary();
    return [
      `Plain-English summary:`,
      `No activity events recorded for ${dateLabel}. The Nexus system is running with ${sectionSummary.live} live sections, ${sectionSummary.static} static sections, and ${sectionSummary.report_snapshot} report-backed sections.`,
      ``,
      `Completed today:`,
      `  - No logged activity events`,
      ``,
      `Still blocked:`,
      ...identifyBlockers().map((b) => `  - ${b}`),
      ``,
      `Next best move:`,
      `  - Check section status or run a Supabase data check`,
      ``,
      `Proof/source:`,
      `  ${memorySource}`,
      durableNote ? `\n  ${durableNote}` : '',
    ].join('\n');
  }

  const completed = identifyCompleted(events);
  const blockers = identifyBlockers();

  const summaryLines = [
    `Hermes was active ${dateLabel} with ${events.length} logged events.`,
  ];
  if (completed.length > 0 && completed[0] !== 'No major work completed yet today.') {
    summaryLines.push(`Key work included: ${completed.slice(0, 3).join(', ')}.`);
  }

  return [
    `Plain-English summary:`,
    summaryLines.join(' '),
    ``,
    `Completed today:`,
    ...completed.map((c) => `  - ${c}`),
    ``,
    `Still blocked:`,
    ...blockers.map((b) => `  - ${b}`),
    ``,
    `Next best move:`,
    `  - Review section status, check YouTube research proof, or activate Credit & Funding`,
    ``,
    `Proof/source:`,
    `  ${memorySource}`,
    durableNote ? `\n  ${durableNote}` : '',
  ].join('\n');
}

/**
 * Build a CEO summary for the day.
 */
export function buildCeoDailySummary(date?: 'today' | 'yesterday'): string {
  const events = date === 'yesterday' ? getYesterdayEvents() : getTodayEvents();
  const allEvents = getAllEvents();
  const dateLabel = date === 'yesterday' ? 'yesterday' : 'today';
  const sectionSummary = getSectionSummary();

  const memorySource = allEvents.length > 0
    ? 'local browser activity journal'
    : 'section status registry';

  const blockers = identifyBlockers();

  const summaryParts = [];
  if (events.length > 0) {
    summaryParts.push(`${events.length} events logged`);
  }
  summaryParts.push(`${sectionSummary.live} live sections, ${sectionSummary.static} static sections`);

  return [
    `CEO Summary:`,
    `Nexus is ${sectionSummary.live > 0 ? 'operational in core areas' : 'still setting up'}. ${events.length > 0 ? `${events.length} activity events were recorded ${dateLabel}.` : `No activity events were logged ${dateLabel}.`} ${summaryParts.join(', ')}.`,
    ``,
    `Business impact:`,
    blockers.length > 0
      ? `The unfinished parts (YouTube research, Credit & Funding, Marketing Drafts) are the workflows that connect directly to revenue. Until those are live, Nexus is strong on infrastructure but light on money-making workflows.`
      : `Core workflows are active and connected. Revenue-generating workflows are the next priority.`,
    ``,
    `What is working:`,
    ...[
      'Hermes advisor with live Supabase + model routing',
      'Ray Review approval workflow',
      'Section status registry with proof layers',
      'Process inventory with PID proof',
    ].map((w) => `  - ${w}`),
    ``,
    `What is not working yet:`,
    ...blockers.map((b) => `  - ${b}`),
    ``,
    `Next move:`,
    `  - ${blockers.length > 0 ? 'Activate Credit & Funding and Marketing Drafts to connect revenue workflows' : 'Review section status and plan next activation'}`,
    ``,
    `Proof/source:`,
    `  ${memorySource}${events.length > 0 ? ` (${events.length} events)` : ''}`,
  ].join('\n');
}
