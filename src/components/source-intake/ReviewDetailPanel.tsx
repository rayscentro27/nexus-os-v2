/** Review Detail + Hermes Review — canonical v1 rating for the selected source + SAFE actions.
 *  Buttons file approval-gated task_requests (sign-off only) or navigate; they never execute,
 *  publish, capture, or send transcript text to external AI. */
import { useState } from 'react';
import { createTaskRequest } from '../../lib/taskRequests';
import { SAFE_DESTINATIONS, getApprovalRequirement, type NexusAction, type RiskTrigger } from '../../config/nexusActionPolicy';
import { ApprovalVisibilityNote } from '../common/ActionStatusBadge';
import type { SourceRow } from './RecentSourcesTable';

const ROUTES: { key: string; label: string; task: string }[] = [
  { key: 'opportunity', label: 'Promote to Opportunity Lab', task: 'route_to_opportunity_lab' },
  { key: 'creative', label: 'Send to Creative Studio', task: 'route_to_creative_studio' },
  { key: 'research', label: 'Mark Research Only', task: 'route_research_only' },
  { key: 'park', label: 'Park Source', task: 'route_park_source' },
];

function strArr(v: unknown): string[] { return Array.isArray(v) ? (v as string[]) : []; }

export function ReviewDetailPanel({ source, email, onAskHermes }: { source: SourceRow | null; email: string | null; onAskHermes: (s: SourceRow) => void }) {
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState('');
  const [showWhy, setShowWhy] = useState(false);

  if (!source) {
    return <div className="nx-glass"><h3 style={{ margin: 0 }}>Hermes Review</h3>
      <div className="nx-muted" style={{ fontSize: 13, marginTop: 8 }}>Select a source in the table to see its plain-English review, v1 score, and routing options.</div></div>;
  }
  const m = source.meta;
  const tags = strArr(m.secondary_tags);
  const reasonsFor = strArr(m.reasons_for_score);
  const reasonsAgainst = strArr(m.reasons_against);
  const scoreSense = (source.score ?? 0) >= 60 ? 'high' : (source.score ?? 0) >= 35 ? 'moderate' : 'low';

  async function fileTask(task: string, label: string) {
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

  const field = (k: string, v: React.ReactNode) => (
    <div style={{ marginTop: 8 }}><span className="nx-muted" style={{ fontSize: 11 }}>{k}</span><div style={{ fontSize: 13 }}>{v}</div></div>
  );

  return (
    <div className="nx-glass">
      <div className="nx-row" style={{ marginBottom: 4 }}>
        <div className="nx-orb" style={{ width: 26, height: 26 }} />
        <h3 style={{ margin: 0 }}>Hermes Review</h3>
      </div>
      <div style={{ fontWeight: 600, marginTop: 6 }}>{source.title}</div>
      <div className="nx-muted" style={{ fontSize: 11, wordBreak: 'break-all' }}>{source.url}</div>

      <div className="nx-row" style={{ marginTop: 10 }}>
        <span className={`nx-badge ${source.transcript_status === 'captured' ? 'ok' : 'warnb'}`}>transcript: {source.transcript_status}</span>
        <span className="nx-badge infob">review: {source.review_status}</span>
        <span className="nx-tag">{source.category}</span>
        <span className="nx-tag blue">{source.destination}</span>
      </div>

      <div className="nx-soft" style={{ padding: 12, marginTop: 12 }}>
        <div className="nx-between"><b>Opportunity score</b><b>{source.score == null ? '—' : `${source.score}/100`} <span className="nx-muted" style={{ fontSize: 11 }}>({scoreSense})</span></b></div>
        {source.score != null && <div className="nx-mini-progress" style={{ marginTop: 6 }}><span style={{ width: `${source.score}%` }} /></div>}
        <div className="nx-muted" style={{ fontSize: 12, marginTop: 8 }}>priority: {String(m.priority ?? '—')} · model: {String(m.rating_model_version ?? 'v1')} · captured: {source.created_at ? new Date(source.created_at).toLocaleString() : '—'}</div>
      </div>

      {source.summary && field('Plain-English summary', source.summary)}
      {source.why_it_matters && field('Why it matters', source.why_it_matters)}
      {field('Recommended next action', `Review, then route to ${source.destination}.`)}
      {typeof m.compliance_notes === 'string' && <div className="nx-amber" style={{ fontSize: 12, marginTop: 8 }}>⚠ {m.compliance_notes}</div>}

      {(() => {
        const triggers: RiskTrigger[] = [];
        if (typeof m.compliance_notes === 'string' && /guarantee|high|risk/i.test(m.compliance_notes)) triggers.push('high_compliance_risk');
        if (!SAFE_DESTINATIONS.has(source.destination)) triggers.push('risky_destination');
        const action: NexusAction = { category: triggers.length ? 'needs_review' : 'safe_internal_route', triggers };
        const needs = getApprovalRequirement(action);
        return (
          <div className="nx-soft" style={{ padding: 10, marginTop: 8 }}>
            <ApprovalVisibilityNote action={action} />
            <div className="nx-muted" style={{ fontSize: 11, marginTop: 4 }}>
              Approval {needs ? 'required' : 'not required'} — {needs ? `reason: ${triggers.join(', ')}` : `destination "${source.destination}" is a safe internal route`}.
            </div>
          </div>
        );
      })()}
      {tags.length > 0 && <div className="nx-chiprow" style={{ marginTop: 8 }}>{tags.map((t) => <span key={t} className="nx-tag">{t}</span>)}</div>}

      {(reasonsFor.length > 0 || reasonsAgainst.length > 0) && showWhy && (
        <div className="nx-soft" style={{ padding: 10, marginTop: 8, fontSize: 12 }}>
          {reasonsFor.length > 0 && <div><b className="nx-green">Why the score</b>: {reasonsFor.join(', ')}</div>}
          {reasonsAgainst.length > 0 && <div style={{ marginTop: 4 }}><b className="nx-amber">Pulling it down</b>: {reasonsAgainst.join(', ')}</div>}
        </div>
      )}

      <div className="nx-chiprow" style={{ marginTop: 12 }}>
        <button className="nx-btn" onClick={() => onAskHermes(source)}>Review with Hermes</button>
        <button className="nx-btn ghost" onClick={() => setShowWhy((s) => !s)}>Explain Score</button>
        <button className="nx-btn ghost" disabled={busy === 'create_task'} onClick={() => fileTask('create_task', 'Create task request')}>Create Task Request</button>
        {ROUTES.map((r) => (
          <button key={r.key} className="nx-btn ghost" disabled={busy === r.task} onClick={() => fileTask(r.task, r.label)}>{r.label}</button>
        ))}
      </div>
      {msg && <div className="nx-muted" style={{ fontSize: 12, marginTop: 8 }}>{msg}</div>}
      <div className="nx-muted" style={{ fontSize: 11, marginTop: 8 }}>Actions file approval-gated task_requests only — no execute / publish / send / trade / capture, and no external AI on transcript text.</div>
    </div>
  );
}
