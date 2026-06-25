/** Review Detail — canonical v1 rating for the selected source + SAFE routing actions.
 *  Actions file approval-gated task_requests (sign-off records); they never execute/publish. */
import { useState } from 'react';
import { createTaskRequest } from '../../lib/taskRequests';
import type { SourceRow } from './RecentSourcesTable';

const ROUTES: { key: string; label: string; task: string }[] = [
  { key: 'opportunity', label: 'Promote to Opportunity Lab', task: 'route_to_opportunity_lab' },
  { key: 'creative', label: 'Send to Creative Studio', task: 'route_to_creative_studio' },
  { key: 'research', label: 'Mark Research Only', task: 'route_research_only' },
  { key: 'park', label: 'Park Source', task: 'route_park_source' },
];

export function ReviewDetailPanel({ source, email, onAskHermes }: { source: SourceRow | null; email: string | null; onAskHermes: (s: SourceRow) => void }) {
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState('');

  if (!source) {
    return <div className="nx-glass"><h3 style={{ margin: 0 }}>Review Detail</h3>
      <div className="nx-muted" style={{ fontSize: 13, marginTop: 8 }}>Select a source from the table to see its v1 rating and routing options.</div></div>;
  }
  const m = source.meta;
  const tags = Array.isArray(m.secondary_tags) ? (m.secondary_tags as string[]) : [];

  async function route(task: string, label: string) {
    if (!source) return;
    setBusy(task); setMsg('');
    const id = await createTaskRequest({
      task_type: task, sensitivity: 'internal_summary', allowed_data_scope: ['public', 'internal_summary'],
      forbidden_data: ['customer_private', 'secrets'], assigned_worker_type: 'research_worker', hermes_visibility: 'summary',
      payload: { research_source_id: source.id, title: source.title, category: source.category, destination: source.destination, action: label },
      summary: `${label} for "${source.title.slice(0, 60)}" — sign-off record only, no execution`,
    }, email);
    setBusy(''); setMsg(id ? `Filed: ${label} (task ${id.slice(0, 8)}…).` : 'Could not file (sign-in / RLS).');
  }

  return (
    <div className="nx-glass">
      <h3 style={{ margin: 0 }}>Review Detail</h3>
      <div style={{ fontWeight: 600, marginTop: 8 }}>{source.title}</div>
      <div className="nx-muted" style={{ fontSize: 12, wordBreak: 'break-all' }}>{source.url}</div>

      <div className="nx-row" style={{ marginTop: 10 }}>
        <span className={`nx-badge ${source.transcript_status === 'captured' ? 'ok' : 'warnb'}`}>transcript: {source.transcript_status}</span>
        <span className="nx-badge infob">review: {source.review_status}</span>
        <span className="nx-tag">{source.category}</span>
        <span className="nx-tag blue">{source.destination}</span>
      </div>

      <div className="nx-soft" style={{ padding: 12, marginTop: 12 }}>
        <div className="nx-between"><b>Opportunity score</b><b>{source.score == null ? '—' : `${source.score}/100`}</b></div>
        {source.score != null && <div className="nx-mini-progress" style={{ marginTop: 6 }}><span style={{ width: `${source.score}%` }} /></div>}
        <div className="nx-muted" style={{ fontSize: 12, marginTop: 8 }}>
          priority: {String(m.priority ?? '—')} · model: {String(m.rating_model_version ?? 'v1')}</div>
        {tags.length > 0 && <div className="nx-chiprow" style={{ marginTop: 8 }}>{tags.map((t) => <span key={t} className="nx-tag">{t}</span>)}</div>}
        {typeof m.compliance_notes === 'string' && <div className="nx-amber" style={{ fontSize: 12, marginTop: 8 }}>⚠ {m.compliance_notes}</div>}
      </div>

      <div className="nx-chiprow" style={{ marginTop: 12 }}>
        <button className="nx-btn" onClick={() => onAskHermes(source)}>Ask Hermes</button>
        {ROUTES.map((r) => (
          <button key={r.key} className="nx-btn ghost" disabled={busy === r.task} onClick={() => route(r.task, r.label)}>{r.label}</button>
        ))}
      </div>
      {msg && <div className="nx-muted" style={{ fontSize: 12, marginTop: 8 }}>{msg}</div>}
      <div className="nx-muted" style={{ fontSize: 11, marginTop: 8 }}>Actions create approval-gated task_requests only — no execution, publish, send, or trade.</div>
    </div>
  );
}
