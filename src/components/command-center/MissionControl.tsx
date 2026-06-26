/** Command Center "Mission Control" — converted from the HTML mockup. WRAPS the existing Hermes
 *  CommandCenter (Conversation / Report Reader / Task Request preserved) and adds visual cards.
 *  Jarvis buttons are SAFE: no Mac command execution — they open tabs or show "not connected".
 *  Oracle / Recent Outputs / Memory show REAL Supabase data where available. */
import { CommandCenter } from '../sections';
import { SystemStatusOverview } from '../TabStatus';
import { listTable, type Row } from '../../services/db';
import { useData } from '../ui';
import { DEPARTMENT_WORKSPACES } from '../../config/nexusProjectTypes';
import { getProjectHermesRecommendation, loadDepartmentProjects } from '../../lib/nexusProjects';
import type { NexusProject } from '../../config/nexusProjectTypes';
import { feederStateCounts, NEXUS_DEPARTMENT_FEEDERS } from '../../config/nexusDepartmentFeeders';
import { NEXUS_RESEARCH_REPORTS, researchReportStatusSummary } from '../../lib/nexusResearchReports';
import { loadRayReviewQueue, summarizeRayReviewCounts } from '../../lib/rayReviewQueue';
import { RAY_YOUTUBE_WATCHLIST } from '../../config/youtubeChannelWatchlist';

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

function ExecutiveOfficePanel({ onNavigate }: { onNavigate?: (id: string) => void }) {
  const workspaces = [
    DEPARTMENT_WORKSPACES.intake,
    DEPARTMENT_WORKSPACES.opportunities,
    DEPARTMENT_WORKSPACES.design,
    DEPARTMENT_WORKSPACES.creative,
    DEPARTMENT_WORKSPACES.seo,
    DEPARTMENT_WORKSPACES.ops,
    DEPARTMENT_WORKSPACES.jobs,
    DEPARTMENT_WORKSPACES.command,
    DEPARTMENT_WORKSPACES.approvals,
    DEPARTMENT_WORKSPACES.events,
    DEPARTMENT_WORKSPACES.integrations,
    DEPARTMENT_WORKSPACES.trading,
  ];
  const { data } = useData<Record<string, NexusProject[]>>(
    async () => {
      const entries = await Promise.all(workspaces.map(async (w) => [w.tabId, await loadDepartmentProjects(w.tabId)] as const));
      return Object.fromEntries(entries);
    },
    {},
  );
  const { data: reviewItems } = useData(() => loadRayReviewQueue(50), []);
  const reviewCounts = summarizeRayReviewCounts(reviewItems);
  const youtubeEnabled = RAY_YOUTUBE_WATCHLIST.filter((x) => x.enabled).length;
  const youtubeFoundationStatus = [
    ['metadata connector', 'not configured'],
    ['metadata check', 'dry-run'],
    ['backfill', 'dry-run'],
    ['transcript path', 'dry-run'],
    ['Hermes prep', 'manual'],
    ['SEO/affiliate plan', 'manual'],
    ['content experiments', 'manual'],
    ['scheduler candidates', 'approval only'],
    ['pre-UI audit', 'manual'],
  ];
  const all = Object.values(data).flat();
  const needs = all.filter((p) => p.status === 'needs_review' || p.approval_required).length;
  const blocked = all.filter((p) => p.status === 'blocked').length;
  const scheduled = all.filter((p) => p.status === 'scheduled').length;
  const enriched = all.filter((p) => ['enriched', 'scored', 'needs_review'].includes(p.enrichment_status)).length;
  const missingEnrichment = all.filter((p) => p.enrichment_status.startsWith('pending') || p.enrichment_status === 'metadata_saved').length;
  const top = all.find((p) => p.approval_required || p.status === 'needs_review' || p.status === 'blocked') ?? all[0] ?? null;
  const feederCounts = feederStateCounts();
  const watchedFeederCount = NEXUS_DEPARTMENT_FEEDERS.filter((f) => f.feeder_id.includes('watched_resource')).length;
  const researchFeederCount = NEXUS_DEPARTMENT_FEEDERS.filter((f) => /research|content|affiliate|seo/i.test(`${f.feeder_id} ${f.name}`)).length;
  const internalResearchCount = all.filter((p) => !p.approval_required && ['researching', 'summarized', 'scored', 'proposed', 'paper_demo', 'backtested'].includes(p.status)).length;
  const approvalNeededCount = all.filter((p) => p.approval_required).length;
  const topFeeder = NEXUS_DEPARTMENT_FEEDERS.find((f) => f.enabled_state === 'needs_connector' || f.enabled_state === 'blocked')
    ?? NEXUS_DEPARTMENT_FEEDERS.find((f) => f.enabled_state === 'manual_only');

  return (
    <div className="nx-glass">
      <div className="nx-between" style={{ marginBottom: 10 }}>
        <div>
          <h3 style={{ margin: 0 }}>Executive Office</h3>
          <div className="nx-muted" style={{ fontSize: 12 }}>Department overview, decisions, blocks, schedule, and Hermes recommendation.</div>
        </div>
        <span className="nx-badge infob">{all.length} active work items</span>
      </div>
      <div className="nx-chiprow" style={{ marginBottom: 10 }}>
        <span className="nx-pill">needs review {needs}</span>
        <span className="nx-pill">blocked {blocked}</span>
        <span className="nx-pill">scheduled {scheduled}</span>
        <span className="nx-pill">enriched {enriched}</span>
        <span className="nx-pill">missing enrichment {missingEnrichment}</span>
      </div>
      <div className="nx-chiprow" style={{ marginBottom: 10 }}>
        <span className="nx-pill">feeders manual {feederCounts.manual_only}</span>
        <span className="nx-pill">ready {feederCounts.ready_for_schedule}</span>
        <span className="nx-pill">blocked {feederCounts.blocked}</span>
        <span className="nx-pill">needs connector {feederCounts.needs_connector}</span>
        <span className="nx-pill">watched resources {watchedFeederCount}</span>
        <span className="nx-pill">research/content {researchFeederCount}</span>
        <span className="nx-pill">internal research {internalResearchCount}</span>
        <span className="nx-pill">approval needed {approvalNeededCount}</span>
        <span className="nx-pill">Ray review {reviewCounts.total}</span>
        <span className="nx-pill">urgent review {reviewCounts.urgent}</span>
        <span className="nx-pill">campaign decisions {reviewCounts.campaign}</span>
        <span className="nx-pill">revenue decisions {reviewCounts.revenue}</span>
        <span className="nx-pill">scheduler decisions {reviewCounts.scheduler}</span>
        <span className="nx-pill">connector decisions {reviewCounts.connector}</span>
        <span className="nx-pill">top reports {NEXUS_RESEARCH_REPORTS.length}</span>
        <span className="nx-pill">watched YouTube {RAY_YOUTUBE_WATCHLIST.length}</span>
        <span className="nx-pill">enabled channels {youtubeEnabled}</span>
        <span className="nx-pill">YouTube report manual</span>
        <span className="nx-pill">metadata connector not configured</span>
        <span className="nx-pill">scheduler candidates approval-only</span>
      </div>
      <div className="nx-chiprow" style={{ marginBottom: 10 }}>
        {youtubeFoundationStatus.map(([label, status]) => <span key={label} className="nx-pill">{label}: {status}</span>)}
      </div>
      <div className="note" style={{ marginBottom: 10 }}>
        Research autonomy: {researchReportStatusSummary()}
      </div>
      <div className="note" style={{ marginBottom: 10 }}>
        Hermes top recommendation: {top ? getProjectHermesRecommendation(top) : 'No live department projects yet. Start with Source Intake or run the manual watch report.'}
      </div>
      {topFeeder && (
        <div className="note" style={{ marginBottom: 10 }}>
          Top feeder recommendation: {topFeeder.name} · {topFeeder.next_action}
        </div>
      )}
      <div className="dept-exec-grid">
        {workspaces.map((workspace) => {
          const projects = data[workspace.tabId] ?? [];
          const last = projects.map((p) => Date.parse(p.updated_at || p.created_at)).filter(Boolean).sort((a, b) => b - a)[0];
          return (
            <button key={workspace.tabId} className="dept-exec-card" onClick={() => onNavigate?.(workspace.tabId)}>
              <div className="dept-project-title">{workspace.title}</div>
              <div className="dept-project-meta">
                <span>active {projects.length}</span>
                <span>review {projects.filter((p) => p.status === 'needs_review' || p.approval_required).length}</span>
                <span>blocked {projects.filter((p) => p.status === 'blocked').length}</span>
                <span>scheduled {projects.filter((p) => p.status === 'scheduled').length}</span>
                <span>enriched {projects.filter((p) => ['enriched', 'scored', 'needs_review'].includes(p.enrichment_status)).length}</span>
              </div>
              <div className="meta muted" style={{ marginTop: 8 }}>
                Last update: {last ? new Date(last).toLocaleDateString() : 'none'}.
              </div>
              <div className="meta" style={{ marginTop: 6 }}>
                Next decision: {projects.find((p) => p.approval_required || p.status === 'needs_review')?.next_action || 'No decision pending.'}
              </div>
              <div className="meta" style={{ marginTop: 6 }}>
                Top recommendation: {projects[0] ? getProjectHermesRecommendation(projects[0]) : 'No live projects yet.'}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function CommandCenterMissionControl({ email, onNavigate }: { email: string | null; onNavigate?: (id: string) => void }) {
  return (
    <div className="nx-scope">
      <ExecutiveOfficePanel onNavigate={onNavigate} />
      <div style={{ height: 14 }} />
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
