/** Pending Capture Requests — reads task_requests (the approval-gated capture/intake requests).
 *  Read-only; shows what is waiting for Ray's approval. No capture runs from here. */
import { listTable, type Row } from '../../services/db';
import { useData } from '../ui';

export function PendingCaptureRequests({ refresh }: { refresh: number }) {
  const { data } = useData<Row[]>(
    () => listTable('task_requests', { eq: ['status', 'requested'], order: 'created_at', limit: 12 }),
    [], refresh);
  const rows = data.filter((r) => r.task_type === 'youtube_capture_request' || r.task_type === 'research_source_intake');

  return (
    <div className="nx-glass">
      <div className="nx-between" style={{ marginBottom: 8 }}>
        <h3 style={{ margin: 0 }}>Pending Capture Requests <span className="nx-muted" style={{ fontSize: 12 }}>({rows.length})</span></h3>
        <span className="nx-badge warnb">awaiting approval</span>
      </div>
      {rows.length === 0 ? (
        <div className="nx-muted" style={{ fontSize: 12 }}>No pending requests. Submit a YouTube URL above to file one.</div>
      ) : rows.map((r) => {
        const p = (r.payload ?? {}) as Record<string, unknown>;
        return (
          <div key={r.id} className="nx-soft" style={{ padding: 10, marginBottom: 6, fontSize: 12 }}>
            <div className="nx-between">
              <b>{String(p.title || p.source_url || r.task_type)}</b>
              <span className="nx-badge infob">{r.task_type === 'youtube_capture_request' ? 'youtube' : 'source'}</span>
            </div>
            <div className="nx-muted" style={{ marginTop: 4, wordBreak: 'break-all' }}>{String(p.source_url ?? '')}</div>
            <div className="nx-amber" style={{ marginTop: 4 }}>Pending approval — capture runs via local CLI wrapper after approval.</div>
            {typeof p.capture_command_preview === 'string' && (
              <details className="nx-collapse" style={{ marginTop: 4 }}>
                <summary className="nx-muted">command preview</summary>
                <code style={{ fontSize: 11, wordBreak: 'break-all' }}>{p.capture_command_preview as string}</code>
              </details>
            )}
            <div className="nx-muted" style={{ marginTop: 4 }}>req {r.id.slice(0, 8)}… · {r.created_at ? new Date(r.created_at).toLocaleString() : ''}</div>
          </div>
        );
      })}
    </div>
  );
}
