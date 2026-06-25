/** Source Intake & Review — converted + polished from the HTML mockup. Reads REAL v2 Supabase
 *  (research_sources). Row selection populates the Hermes Review rail. Actions are safe
 *  (task_requests only). No browser capture, no publish/send/trade. */
import { useState } from 'react';
import { AddSourcePanel, type SourceType } from './AddSourcePanel';
import { SourceEntryForm } from './SourceEntryForm';
import { RecentSourcesTable, type SourceRow } from './RecentSourcesTable';
import { ReviewDetailPanel } from './ReviewDetailPanel';
import { PendingCaptureRequests } from './PendingCaptureRequests';

function ConnectionStatusCard() {
  const works = [['Scoring Model v1', 'Active'], ['Routing (canonical map)', 'Active'], ['Hermes Review', 'Available'], ['Proof events', 'On']];
  const sources = [['YouTube (yt-dlp, approved)', 'CLI'], ['research_sources', 'Live'], ['transcript_reviews', 'Live'], ['nexus_events', 'Live']];
  const notYet = [['Browser capture', 'CLI-only'], ['Auto schedule', 'Off'], ['Reddit / X / News API', 'Planned'], ['File upload parse', 'Planned']];
  const block = (title: string, cls: string, rows: string[][]) => (
    <div style={{ marginBottom: 8 }}>
      <div className={cls} style={{ fontSize: 12, fontWeight: 600 }}>● {title}</div>
      <ul style={{ margin: '4px 0 0', paddingLeft: 14, fontSize: 12 }} className="nx-muted">
        {rows.map(([k, v]) => <li key={k} className="nx-between"><span>{k}</span><span>{v}</span></li>)}
      </ul>
    </div>
  );
  return (
    <div className="nx-glass">
      <details className="nx-collapse">
        <summary>Connection Status <span className="nx-muted" style={{ fontWeight: 400, fontSize: 11 }}>(tap to expand)</span></summary>
        <div style={{ marginTop: 8 }}>
          {block('What works now', 'nx-green', works)}
          {block('Data sources', 'nx-green', sources)}
          {block('Not connected yet', 'nx-red', notYet)}
        </div>
      </details>
    </div>
  );
}

export function SourceIntakeReviewPage({ email, onNavigate }: { email: string | null; onNavigate?: (id: string) => void }) {
  const [picked, setPicked] = useState<SourceType | null>(null);
  const [selected, setSelected] = useState<SourceRow | null>(null);
  const [captureRefresh, setCaptureRefresh] = useState(0);

  return (
    <div className="nx-scope">
      <div className="nx-row" style={{ marginBottom: 12 }}>
        <span className="nx-pill nx-amber">● Research Engine: Partial</span>
        <span className="nx-pill nx-green">● YouTube Capture (CLI): Approved</span>
        <span className="nx-pill nx-blue">♟ Hermes Review: Available</span>
        <span className="nx-pill nx-green">● Rating Model v1: Active</span>
      </div>

      <div className="nx-si-grid">
        {/* Main column — add source + entry, then full-width recent sources */}
        <div className="nx-col">
          <div className="nx-grid" style={{ gridTemplateColumns: 'repeat(auto-fit,minmax(300px,1fr))' }}>
            <AddSourcePanel onPick={setPicked} picked={picked?.key ?? null} />
            <SourceEntryForm picked={picked} email={email} onSubmitted={() => setCaptureRefresh((n) => n + 1)} />
          </div>
          <RecentSourcesTable selectedId={selected?.id ?? null} onSelect={setSelected} />
        </div>
        {/* Right rail — Hermes Review (populated on selection) + pending captures + compact Connection Status */}
        <div className="nx-col">
          <ReviewDetailPanel source={selected} email={email}
            onAskHermes={(s) => { setSelected(s); onNavigate?.('command'); }} />
          <PendingCaptureRequests refresh={captureRefresh} />
          <ConnectionStatusCard />
        </div>
      </div>
    </div>
  );
}
