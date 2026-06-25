/** Capture Queue — reads task_requests (the capture/intake requests Ray submitted). Read-only.
 *  Safe items wait for the local runner; review-required items also appear in Approvals.
 *  No capture runs from here. */
import { listTable, type Row } from '../../services/db';
import { useData } from '../ui';

const CAPTURE_TYPES = new Set(['youtube_capture_request', 'source_capture_request', 'research_source_intake']);

export function PendingCaptureRequests({ refresh }: { refresh: number }) {
  const { data } = useData<Row[]>(
    () => listTable('task_requests', { eq: ['status', 'requested'], order: 'created_at', limit: 15 }),
    [], refresh);
  const rows = data.filter((r) => CAPTURE_TYPES.has(r.task_type));

  return (
    <div className="nx-glass">
      <div className="nx-between" style={{ marginBottom: 8 }}>
        <h3 style={{ margin: 0 }}>Capture Queue <span className="nx-muted" style={{ fontSize: 12 }}>({rows.length})</span></h3>
      </div>
      {rows.length === 0 ? (
        <div className="nx-muted" style={{ fontSize: 12 }}>Nothing queued. Submit a YouTube URL above — safe sources queue automatically (no approval).</div>
      ) : rows.map((r) => {
        const p = (r.payload ?? {}) as Record<string, unknown>;
        const approvalRequired = p.approval_required === true;
        return (
          <div key={r.id} className="nx-soft" style={{ padding: 10, marginBottom: 6, fontSize: 12 }}>
            <div className="nx-between">
              <b className="nx-truncate" style={{ maxWidth: 200, display: 'inline-block' }}>{String(p.title || p.source_url || r.task_type)}</b>
              <span className={`nx-badge ${approvalRequired ? 'warnb' : 'ok'}`}>{approvalRequired ? 'Approval required' : 'Safe capture'}</span>
            </div>
            <div className="nx-muted" style={{ marginTop: 4, wordBreak: 'break-all' }}>{String(p.source_url ?? '')}</div>
            <div className={approvalRequired ? 'nx-amber' : 'nx-green'} style={{ marginTop: 4 }}>
              {approvalRequired
                ? `Needs Ray review in Approvals${p.review_trigger ? ` (${p.review_trigger})` : ''}.`
                : 'Waiting for local runner — capture runs via the CLI wrapper.'}
            </div>
            {typeof p.capture_command_preview === 'string' && (
              <details className="nx-collapse" style={{ marginTop: 4 }}>
                <summary className="nx-muted">command preview</summary>
                <code style={{ fontSize: 11, wordBreak: 'break-all' }}>{p.capture_command_preview as string}</code>
              </details>
            )}
            <div className="nx-muted" style={{ marginTop: 4 }}>queue {r.id.slice(0, 8)}… · {r.created_at ? new Date(r.created_at).toLocaleString() : ''}</div>
          </div>
        );
      })}
    </div>
  );
}
