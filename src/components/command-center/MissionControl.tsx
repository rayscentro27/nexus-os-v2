/** Command Center "Mission Control" — converted from the HTML mockup. WRAPS the existing Hermes
 *  CommandCenter (Conversation / Report Reader / Task Request preserved) and adds visual cards.
 *  Jarvis buttons are SAFE: no Mac command execution — they open tabs or show "not connected".
 *  Oracle / Recent Outputs / Memory show REAL Supabase data where available. */
import { CommandCenter } from '../sections';
import { SystemStatusOverview } from '../TabStatus';
import { listTable, type Row } from '../../services/db';
import { useData } from '../ui';

function HermesJarvisCard({ onNavigate }: { onNavigate?: (id: string) => void }) {
  const btn = (icon: string, label: string, onClick: () => void) => (
    <button className="nx-soft" style={{ display: 'block', width: '100%', textAlign: 'left', padding: '10px 14px', marginBottom: 6, cursor: 'pointer', color: 'var(--nx-text)' }} onClick={onClick}>{icon} {label}</button>
  );
  return (
    <div className="nx-glass">
      <div className="nx-row" style={{ marginBottom: 8 }}>
        <div className="nx-orb" style={{ width: 40, height: 40 }} />
        <div><h3 style={{ margin: 0 }}>Hermes Jarvis</h3><div className="nx-muted" style={{ fontSize: 12 }}>Computer-control assistant</div></div>
        <span className="nx-badge warnb" style={{ marginLeft: 'auto' }}>● bridge off</span>
      </div>
      {btn('🌐', 'Open Browser', () => alert('Mac bridge: not yet connected end-to-end.'))}
      {btn('📈', 'Open TradingView', () => alert('Mac bridge: not yet connected end-to-end.'))}
      {btn('💠', 'Open VS Code', () => alert('Mac bridge: not yet connected end-to-end.'))}
      {btn('📘', 'Summarize Latest Report', () => onNavigate?.('command'))}
      {btn('⌕', 'Open Integrations', () => onNavigate?.('integrations'))}
      <div className="nx-soft" style={{ padding: 10, marginTop: 6, fontSize: 12 }}>
        <span className="nx-amber">●</span> <span className="nx-muted">Mac bridge: not yet connected end-to-end (read-only). No commands run from the browser.</span>
      </div>
    </div>
  );
}

function HermesOracleCard() {
  const { data } = useData<Row[]>(() => listTable('research_sources', { order: 'created_at', limit: 5 }), []);
  return (
    <div className="nx-glass">
      <div className="nx-between" style={{ marginBottom: 8 }}>
        <div className="nx-row"><span style={{ fontSize: 22 }} className="nx-amber">☊</span>
          <div><h3 style={{ margin: 0 }}>Hermes Oracle</h3><div className="nx-muted" style={{ fontSize: 12 }}>Research / Intel (real sources)</div></div></div>
      </div>
      {data.length === 0 ? <div className="nx-muted" style={{ fontSize: 12 }}>No research sources yet.</div> : data.map((r, i) => {
        const m = (r.metadata ?? {}) as Record<string, unknown>;
        return (
          <div key={r.id} className="nx-soft" style={{ padding: 10, marginBottom: 6 }}>
            <div className="nx-row"><span className="nx-muted">{i + 1}</span>
              <span className="nx-badge ok">{String(m.total_opportunity_score ?? '—')}</span>
              <span style={{ fontSize: 13, fontWeight: 600 }}>{r.title}</span></div>
            <div className="nx-muted" style={{ fontSize: 11, marginTop: 4 }}>{String(m.primary_category ?? '—')} → {String(m.recommended_destination ?? '—')}</div>
          </div>
        );
      })}
    </div>
  );
}

function MemoryGalaxyCard() {
  const { data } = useData<number>(async () => (await listTable('nexus_lessons', { limit: 500 })).length, 0);
  const nodes = [[52, 43], [40, 28], [62, 22], [70, 52], [35, 58], [56, 70], [47, 62], [76, 33]];
  const labels = ['Marketing', 'Trading', 'Competitor Intel', 'Content', 'Roadmap'];
  return (
    <div className="nx-glass">
      <div className="nx-between"><div><h3 style={{ margin: 0 }}>Memory Galaxy</h3><div className="nx-muted" style={{ fontSize: 12 }}>Shared knowledge map</div></div></div>
      <div style={{ position: 'relative', height: 160, marginTop: 8 }}>
        {nodes.map(([l, t], i) => <div key={i} className="nx-memory-node" style={{ left: `${l}%`, top: `${t}%` }} />)}
        <div className="nx-glow" style={{ position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%,-50%)', width: 64, height: 64, borderRadius: '50%', background: 'linear-gradient(135deg,#2D7EFF,#0A1D48)', border: '1px solid rgba(125,211,252,.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 700, textAlign: 'center' }}>Nexus<br />OS v2</div>
        {labels.map((lab, i) => <span key={lab} className="nx-soft" style={{ position: 'absolute', fontSize: 10, padding: '2px 6px', left: `${8 + i * 16}%`, top: i % 2 ? 14 : 120 }}>{lab}</span>)}
      </div>
      <div className="nx-between" style={{ fontSize: 12 }}><span className="nx-muted">{data} lessons (nexus_lessons)</span></div>
    </div>
  );
}

function RecentOutputsPanel() {
  const { data } = useData<Row[]>(() => listTable('nexus_events', { order: 'created_at', limit: 8 }), []);
  return (
    <div className="nx-glass">
      <h3 style={{ margin: '0 0 8px' }}>Latest reports & recent outputs <span className="nx-muted" style={{ fontSize: 12 }}>(nexus_events)</span></h3>
      {data.length === 0 ? <div className="nx-muted" style={{ fontSize: 12 }}>No events yet.</div> : (
        <div style={{ display: 'grid', gap: 6 }}>
          {data.map((e) => (
            <div key={e.id} className="nx-soft" style={{ padding: 8, fontSize: 12 }}>
              <span className="nx-badge infob">{e.lane ?? '—'}</span> <b>{e.action ?? 'event'}</b>
              <span className="nx-muted"> · {e.title ?? ''} · {e.status ?? ''}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function CommandCenterMissionControl({ email, onNavigate }: { email: string | null; onNavigate?: (id: string) => void }) {
  return (
    <div className="nx-scope">
      <div className="nx-mc-grid">
        {/* Column 1 — Hermes workspace + source notebook + recent outputs */}
        <div className="nx-col">
          {/* Existing Hermes workspace — Conversation / Report Reader / Task Request preserved */}
          <CommandCenter email={email} />
          <SourceNotebookCard onNavigate={onNavigate} />
          <RecentOutputsPanel />
        </div>
        {/* Column 2 — Jarvis + compact System Awareness */}
        <div className="nx-col">
          <HermesJarvisCard onNavigate={onNavigate} />
          <SystemStatusOverview onOpenTab={onNavigate} compact />
        </div>
        {/* Column 3 — Oracle + Memory Galaxy */}
        <div className="nx-col">
          <HermesOracleCard />
          <MemoryGalaxyCard />
        </div>
      </div>
    </div>
  );
}

function SourceNotebookCard({ onNavigate }: { onNavigate?: (id: string) => void }) {
  const { data } = useData<Row[]>(() => listTable('research_sources', { order: 'created_at', limit: 3 }), []);
  return (
    <div className="nx-glass">
      <div className="nx-between" style={{ marginBottom: 8 }}>
        <div><h3 style={{ margin: 0 }}>Source Intake / Notebook</h3>
          <div className="nx-muted" style={{ fontSize: 12 }}>Give Hermes context. Capture runs via approved CLI only.</div></div>
        <button className="nx-btn ghost" onClick={() => onNavigate?.('intake')}>Open Source Intake</button>
      </div>
      <div className="nx-chiprow">
        {['▶ YouTube', '📄 Transcript', '💡 Idea', '🌐 Website', '◈ NotebookLM'].map((s) => <span key={s} className="nx-pill">{s}</span>)}
      </div>
      <div className="nx-muted" style={{ fontSize: 12, marginTop: 10 }}>Recent sources ({data.length}):</div>
      <div style={{ display: 'grid', gap: 4, marginTop: 4 }}>
        {data.map((r) => <div key={r.id} className="nx-soft" style={{ padding: '6px 10px', fontSize: 12 }}>
          <span className="nx-truncate">{r.title}</span></div>)}
        {data.length === 0 && <div className="nx-muted" style={{ fontSize: 12 }}>None yet — capture an approved source.</div>}
      </div>
    </div>
  );
}
