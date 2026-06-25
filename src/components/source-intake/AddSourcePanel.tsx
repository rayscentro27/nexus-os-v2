/** Add Source — six source-type tiles. UI only: selecting a type fills the entry form. Real capture
 *  stays CLI/approved-only (no capture is triggered from the browser). */
export interface SourceType { key: string; icon: string; label: string; note: string; supported: boolean; }

export const SOURCE_TYPES: SourceType[] = [
  { key: 'youtube_video', icon: '▶', label: 'YouTube URL', note: 'Capture via approved CLI', supported: true },
  { key: 'transcript_file', icon: '📄', label: 'Transcript File', note: '.txt, .md, .pdf', supported: false },
  { key: 'manual_idea', icon: '💡', label: 'Pasted Text / Idea', note: 'Paste or write', supported: true },
  { key: 'website_url', icon: '🌐', label: 'Website URL', note: 'Capture webpage', supported: false },
  { key: 'notebooklm_export', icon: '◈', label: 'NotebookLM Export', note: '.zip / .json', supported: false },
  { key: 'youtube_channel', icon: '📺', label: 'YouTube Channel', note: 'Allowlist only', supported: false },
];

export function AddSourcePanel({ onPick, picked }: { onPick: (t: SourceType) => void; picked: string | null }) {
  return (
    <div className="nx-glass">
      <div className="nx-row" style={{ marginBottom: 12 }}>
        <span className="nx-pill nx-violet">1</span>
        <div><h3 style={{ margin: 0 }}>Add Source</h3>
          <div className="nx-muted" style={{ fontSize: 12 }}>Pick a type. We normalize, score (v1), and route it.</div></div>
      </div>
      <div className="nx-grid" style={{ gridTemplateColumns: 'repeat(auto-fit,minmax(120px,1fr))' }}>
        {SOURCE_TYPES.map((t) => (
          <button key={t.key} className="nx-source-card" style={{ outline: picked === t.key ? '1px solid #8b5cf6' : 'none' }} onClick={() => onPick(t)}>
            <div style={{ fontSize: 22 }}>{t.icon}</div>
            <div style={{ fontWeight: 600, fontSize: 13, marginTop: 6 }}>{t.label}</div>
            <div className="nx-muted" style={{ fontSize: 11, marginTop: 4 }}>{t.note}</div>
            <div style={{ fontSize: 11, marginTop: 6 }} className={t.supported ? 'nx-green' : 'nx-amber'}>
              {t.supported ? 'Supported' : 'Coming soon'}</div>
          </button>
        ))}
      </div>
      <div className="nx-pill" style={{ marginTop: 12, display: 'block', padding: 10 }}>
        ⓘ Supported types capture via an <b>approved CLI run</b> (no browser capture). "Coming soon" types are saved for manual review only.
      </div>
    </div>
  );
}
