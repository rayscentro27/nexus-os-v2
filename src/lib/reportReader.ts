/**
 * Report Reader — reads ONLY safe (public / internal_summary) Nexus signals and explains them in
 * plain English. It never reads customer/credit/funding/auth/secret/raw-trading data, and never
 * sends report contents to a public provider/search. Pure read of safe aggregates only.
 */

import { listTable, type Row } from '../services/db';

export interface ReportSummary { ok: boolean; text: string; }

export async function readLatestReport(): Promise<ReportSummary> {
  // Safe aggregates only: system health + recent event-ledger titles. No private tables/columns.
  const [events, health] = await Promise.all([
    listTable('nexus_events', { limit: 6, order: 'created_at' }),
    listTable('system_health', { limit: 6, order: 'created_at' }),
  ]);

  if (events.length === 0 && health.length === 0)
    return {
      ok: false,
      text: 'I don’t see a safe Nexus report yet. Once there’s recent activity in the event ledger or system health, I can summarize it here — no private data needed.',
    };

  const lines: string[] = ['Here’s the latest safe Nexus summary (public / internal only — no private data):'];

  if (health.length) {
    const h = health.map((r: Row) => `${r.component ?? r.area ?? 'system'}: ${r.status ?? 'ok'}`).join(' · ');
    lines.push(`• System health — ${h}`);
  }
  if (events.length) {
    lines.push('• Recent ledger events:');
    for (const e of events) {
      const title = String(e.title ?? '').slice(0, 80);
      lines.push(`   – ${e.action ?? 'event'}${title ? `: ${title}` : ''} (${e.status ?? '—'})`);
    }
  }
  lines.push('Want me to explain any of these in more detail, or pull public context on what a healthy benchmark looks like? (I won’t send these private numbers to any public source.)');
  return { ok: true, text: lines.join('\n') };
}
