/** Recent Sources — REAL v2 Supabase data (research_sources). Shows the captured YouTube source. */
import { listTable, type Row } from '../../services/db';
import { useData } from '../ui';

export interface SourceRow {
  id: string; title: string; source_type: string; url: string; created_at: string;
  transcript_status: string; review_status: string; score: number | null;
  category: string; destination: string; meta: Record<string, unknown>;
}

export function normalize(r: Row): SourceRow {
  const m = (r.metadata ?? {}) as Record<string, unknown>;
  return {
    id: r.id, title: r.title ?? '(untitled)', source_type: r.source_type ?? 'unknown', url: r.url ?? '',
    created_at: r.created_at, transcript_status: String(m.transcript_status ?? 'unknown'),
    review_status: String(m.review_status ?? 'queued'),
    score: typeof m.total_opportunity_score === 'number' ? (m.total_opportunity_score as number) : null,
    category: String(m.primary_category ?? '—'), destination: String(m.recommended_destination ?? '—'), meta: m,
  };
}

const TYPE_ICON: Record<string, string> = {
  youtube_video: '▶', youtube_channel: '📺', youtube_playlist: '☰', article_url: '🌐',
  website_url: '🌐', transcript_file: '📄', notebooklm_export: '◈', manual_idea: '💡',
};

function badge(status: string): string {
  const s = status.toLowerCase();
  if (s.includes('captured') || s.includes('reviewed') || s.includes('scored')) return 'ok';
  if (s.includes('needs') || s.includes('partial') || s.includes('queued') || s.includes('park')) return 'warnb';
  if (s.includes('reject') || s.includes('failed') || s.includes('unavailable')) return 'warnb';
  return 'infob';
}

export function RecentSourcesTable({ selectedId, onSelect }: { selectedId: string | null; onSelect: (s: SourceRow) => void }) {
  const { data, reload } = useData<Row[]>(() => listTable('research_sources', { order: 'created_at', limit: 30 }), []);
  const rows = data.map(normalize);

  return (
    <div className="nx-glass">
      <div className="nx-between" style={{ marginBottom: 10 }}>
        <h3 style={{ margin: 0 }}>Recent Sources <span className="nx-muted" style={{ fontSize: 12 }}>({rows.length} from research_sources)</span></h3>
        <button className="nx-btn ghost" onClick={reload}>⟳ Refresh</button>
      </div>
      {rows.length === 0 ? (
        <div className="nx-muted" style={{ fontSize: 13 }}>No sources captured yet. Run an approved capture, then they appear here from Supabase.</div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table className="nx-table">
            <thead><tr>
              <th>Title</th><th>Type</th><th>Transcript</th><th>Review</th><th>Score</th><th>Category</th><th>Destination</th><th>Captured</th>
            </tr></thead>
            <tbody>
              {rows.map((s) => (
                <tr key={s.id} className={selectedId === s.id ? 'sel' : ''} style={{ cursor: 'pointer' }} onClick={() => onSelect(s)}>
                  <td style={{ maxWidth: 260 }}><span style={{ marginRight: 6 }}>{TYPE_ICON[s.source_type] ?? '•'}</span>{s.title}</td>
                  <td className="nx-muted">{s.source_type}</td>
                  <td><span className={`nx-badge ${badge(s.transcript_status)}`}>{s.transcript_status}</span></td>
                  <td><span className={`nx-badge ${badge(s.review_status)}`}>{s.review_status}</span></td>
                  <td>{s.score == null ? '—' : `${s.score}/100`}
                    {s.score != null && <div className="nx-mini-progress" style={{ width: 60, marginTop: 3 }}><span style={{ width: `${s.score}%` }} /></div>}</td>
                  <td><span className="nx-tag">{s.category}</span></td>
                  <td><span className="nx-tag blue">{s.destination}</span></td>
                  <td className="nx-muted">{s.created_at ? new Date(s.created_at).toLocaleString() : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
