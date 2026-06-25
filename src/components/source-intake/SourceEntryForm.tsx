/** Source Entry — submitting NEVER captures in the browser. A YouTube URL files an approval-gated
 *  task_request (youtube_capture_request) carrying the exact CLI command a worker runs after Ray
 *  approves. Other types file a generic research_source_intake request. Writes a nexus_events proof. */
import { useEffect, useState } from 'react';
import { createTaskRequest } from '../../lib/taskRequests';
import { createEvent } from '../../lib/ledger';
import { containsSensitive } from '../../lib/dataScopes';
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
    if (containsSensitive(`${title} ${url} ${snippet}`)) { setMsg({ ok: false, text: 'That looks like private data — not submitting.' }); return; }
    if (!url && !snippet) { setMsg({ ok: false, text: 'Add a URL or a text snippet.' }); return; }

    const isYouTube = type === 'youtube_video' && YT_RE.test(url.trim());
    if (type === 'youtube_video' && url && !isYouTube) {
      setMsg({ ok: false, text: 'That does not look like a public YouTube video URL (youtube.com/watch?v=… or youtu.be/…).' }); return;
    }
    setBusy(true);
    const tagList = tags.split(',').map((t) => t.trim()).filter(Boolean);

    const id = isYouTube
      ? await createTaskRequest({
          task_type: 'youtube_capture_request', sensitivity: 'internal_summary',
          allowed_data_scope: ['public', 'internal_summary'], forbidden_data: ['customer_private', 'secrets'],
          assigned_worker_type: 'research_worker', hermes_visibility: 'summary',
          payload: {
            action_type: 'youtube_capture_request', source_type: 'youtube_video', source_url: url.trim(),
            title: title || null, target_use: targetUse, priority, tags: tagList,
            requested_by: email ?? 'operator', created_at: new Date().toISOString(),
            capture_command_preview: captureCommand(url.trim()),
            approval_required: true, risk_level: 'medium', external_ai: false, scheduler: false, v1_jobs_touched: false,
            note: 'Browser capture is disabled. A worker runs the CLI wrapper after Ray approval.',
          },
          summary: `Approved-capture request for a YouTube video (${url.trim().slice(0, 60)}). Runs the CLI wrapper after approval; no browser capture, no external AI.`,
        }, email)
      : await createTaskRequest({
          task_type: 'research_source_intake', sensitivity: 'internal_summary',
          allowed_data_scope: ['public', 'internal_summary'], forbidden_data: ['customer_private', 'secrets'],
          assigned_worker_type: 'research_worker', hermes_visibility: 'summary',
          payload: { action_type: 'research_source_intake', source_type: type, title, source_url: url, snippet: snippet.slice(0, 500), target_use: targetUse, priority, tags: tagList, requested_by: email ?? 'operator' },
          summary: `Research-source intake (${type}) for Ray-approved handling. No browser capture.`,
        }, email);

    if (id) {
      await createEvent({
        lane: 'research', action: isYouTube ? 'youtube_capture_requested' : 'research_source_requested',
        status: 'pending', title: (title || url || type).slice(0, 80),
        summary: `task_request ${id} · awaiting approval · ${isYouTube ? 'youtube_capture_request' : 'research_source_intake'}`,
        payload: { task_request_id: id, source_url: url, source_type: type, browser_capture: false },
      });
    }
    setBusy(false);
    onSubmitted?.();
    setMsg(id
      ? { ok: true, text: `Pending approval — capture will run through the local CLI wrapper after approval. (task_request ${id.slice(0, 8)}…)` }
      : { ok: false, text: 'Could not file task request (check sign-in / RLS).' });
  }

  return (
    <div className="nx-glass">
      <div className="nx-row" style={{ marginBottom: 12 }}>
        <span className="nx-pill nx-violet">2</span>
        <div><h3 style={{ margin: 0 }}>Source Entry</h3>
          <div className="nx-muted" style={{ fontSize: 12 }}>Submitting files an approval-gated request — it never captures from the browser.</div></div>
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
        <button className="nx-btn" disabled={busy} onClick={submit}>{busy ? 'Filing…' : '✈ Submit Source (files approval request)'}</button>
        {msg && <div className={msg.ok ? 'nx-green' : 'nx-amber'} style={{ fontSize: 12 }}>{msg.text}</div>}
        <div className="nx-muted" style={{ fontSize: 11 }}>🔒 Browser capture is disabled. Approved capture runs through the local CLI wrapper after Ray approval. No publish/send/trade, no external AI on transcript text.</div>
      </div>
    </div>
  );
}
