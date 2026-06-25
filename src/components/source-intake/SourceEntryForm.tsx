/** Source Entry — thin form over the universal request helper. Submitting NEVER captures in the
 *  browser; it files a request that the universal policy (nexusActionPolicy) classifies as a safe
 *  Capture Queue item or a review-required item (which also lands in Approvals). */
import { useEffect, useState } from 'react';
import { submitSourceCapture } from '../../lib/nexusRequests';
import { containsSensitive } from '../../lib/dataScopes';
import { ACTION_COPY } from '../../config/nexusActionPolicy';
import type { SourceType } from './AddSourcePanel';

const YT_RE = /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=[\w-]{6,}|youtu\.be\/[\w-]{6,})/i;

function captureCommand(url: string): string {
  return `python3 scripts/intake/run_existing_youtube_monitor.py --source-url "${url}" --once --limit 1 --no-external-ai --write-events --no-dry-run`;
}

export function SourceEntryForm({ picked, email, onSubmitted }: { picked: SourceType | null; email: string | null; onSubmitted?: () => void }) {
  const [type, setType] = useState('youtube_video');
  const [title, setTitle] = useState('');
  const [url, setUrl] = useState('');
  const [snippet, setSnippet] = useState('');
  const [targetUse, setTargetUse] = useState('Auto-route (by score)');
  const [priority, setPriority] = useState('Medium');
  const [tags, setTags] = useState('');
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { if (picked) setType(picked.key); }, [picked]);

  async function submit() {
    setMsg(null);
    if (containsSensitive(`${title} ${url} ${snippet}`)) { setMsg({ ok: false, text: 'That looks like private/customer data — not submitting.' }); return; }
    if (!url && !snippet) { setMsg({ ok: false, text: 'Add a URL or a text snippet.' }); return; }
    if (type === 'youtube_video' && url && !YT_RE.test(url.trim())) {
      setMsg({ ok: false, text: 'That does not look like a public YouTube video URL (youtube.com/watch?v=… or youtu.be/…).' }); return;
    }
    setBusy(true);
    const res = await submitSourceCapture({
      source_type: type, source_url: url.trim() || null, title: title || null, snippet: snippet || null,
      target_use: targetUse, priority, tags: tags.split(',').map((t) => t.trim()).filter(Boolean),
      capture_command_preview: type === 'youtube_video' && url ? captureCommand(url.trim()) : null,
    }, email);
    setBusy(false);
    onSubmitted?.();
    setMsg({ ok: res.ok, text: res.message });
  }

  return (
    <div className="nx-glass">
      <div className="nx-row" style={{ marginBottom: 12 }}>
        <span className="nx-pill nx-violet">2</span>
        <div><h3 style={{ margin: 0 }}>Source Entry</h3>
          <div className="nx-muted" style={{ fontSize: 12 }}>{ACTION_COPY.safeQueue} Risky/uncertain ones go to Approvals.</div></div>
      </div>
      <div style={{ display: 'grid', gap: 10 }}>
        <label className="nx-muted" style={{ fontSize: 12 }}>Source type
          <input className="nx-input" value={type} onChange={(e) => setType(e.target.value)} /></label>
        <label className="nx-muted" style={{ fontSize: 12 }}>Title
          <input className="nx-input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Optional title" /></label>
        <label className="nx-muted" style={{ fontSize: 12 }}>Source URL (public YouTube for capture)
          <input className="nx-input" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://www.youtube.com/watch?v=…" /></label>
        <div style={{ display: 'grid', gap: 10, gridTemplateColumns: '1fr 1fr' }}>
          <label className="nx-muted" style={{ fontSize: 12 }}>Target use
            <input className="nx-input" value={targetUse} onChange={(e) => setTargetUse(e.target.value)} /></label>
          <label className="nx-muted" style={{ fontSize: 12 }}>Priority
            <select className="nx-input" value={priority} onChange={(e) => setPriority(e.target.value)}>
              <option>Low</option><option>Medium</option><option>High</option></select></label>
        </div>
        <label className="nx-muted" style={{ fontSize: 12 }}>Tags (comma-separated)
          <input className="nx-input" value={tags} onChange={(e) => setTags(e.target.value)} placeholder="ai_tooling, credit_funding_readiness" /></label>
        <label className="nx-muted" style={{ fontSize: 12 }}>Text snippet (optional, public only)
          <textarea className="nx-input" style={{ minHeight: 48 }} value={snippet} onChange={(e) => setSnippet(e.target.value)} /></label>
        <button className="nx-btn" disabled={busy} onClick={submit}>{busy ? 'Filing…' : '✈ Submit Source'}</button>
        {msg && <div className={msg.ok ? 'nx-green' : 'nx-amber'} style={{ fontSize: 12 }}>{msg.text}</div>}
        <div className="nx-muted" style={{ fontSize: 11 }}>🔒 Browser capture is disabled. Approved/queued capture runs through the local CLI wrapper. {ACTION_COPY.hermesRecommends}</div>
      </div>
    </div>
  );
}
