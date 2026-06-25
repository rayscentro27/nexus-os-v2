/** Source Entry — details for a source. Submit does NOT capture in the browser; it files an
 *  approval-gated task_request (research worker) so Ray approves the capture. Safe by design. */
import { useEffect, useState } from 'react';
import { createTaskRequest } from '../../lib/taskRequests';
import { containsSensitive } from '../../lib/dataScopes';
import type { SourceType } from './AddSourcePanel';

export function SourceEntryForm({ picked, email }: { picked: SourceType | null; email: string | null }) {
  const [type, setType] = useState('youtube_video');
  const [title, setTitle] = useState('');
  const [url, setUrl] = useState('');
  const [snippet, setSnippet] = useState('');
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => { if (picked) setType(picked.key); }, [picked]);

  async function submit() {
    setMsg('');
    if (containsSensitive(`${title} ${url} ${snippet}`)) { setMsg('That looks like private data — not submitting.'); return; }
    if (!url && !snippet) { setMsg('Add a URL or a text snippet.'); return; }
    setBusy(true);
    const id = await createTaskRequest({
      task_type: 'research_source_intake', sensitivity: 'internal_summary',
      allowed_data_scope: ['public', 'internal_summary'], forbidden_data: ['customer_private', 'secrets'],
      assigned_worker_type: 'research_worker', hermes_visibility: 'summary',
      payload: { source_type: type, title, url, snippet: snippet.slice(0, 500), via: 'source_intake_ui' },
      summary: `a research-source intake task (${type}) for Ray-approved capture into v2 tables`,
    }, email);
    setBusy(false);
    setMsg(id ? `Filed task request ${id.slice(0, 8)}… — capture runs only after your approval (no browser capture).`
              : 'Could not file task request (check sign-in / RLS).');
  }

  return (
    <div className="nx-glass">
      <div className="nx-row" style={{ marginBottom: 12 }}>
        <span className="nx-pill nx-violet">2</span>
        <div><h3 style={{ margin: 0 }}>Source Entry</h3>
          <div className="nx-muted" style={{ fontSize: 12 }}>Submitting files a task request — it never captures from the browser.</div></div>
      </div>
      <div style={{ display: 'grid', gap: 10 }}>
        <label className="nx-muted" style={{ fontSize: 12 }}>Source type
          <input className="nx-input" value={type} onChange={(e) => setType(e.target.value)} /></label>
        <label className="nx-muted" style={{ fontSize: 12 }}>Title
          <input className="nx-input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Optional title" /></label>
        <label className="nx-muted" style={{ fontSize: 12 }}>Source URL
          <input className="nx-input" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://…" /></label>
        <label className="nx-muted" style={{ fontSize: 12 }}>Text snippet (optional, public only)
          <textarea className="nx-input" style={{ minHeight: 56 }} value={snippet} onChange={(e) => setSnippet(e.target.value)} /></label>
        <button className="nx-btn" disabled={busy} onClick={submit}>{busy ? 'Filing…' : '✈ Submit (files task request)'}</button>
        {msg && <div className="nx-muted" style={{ fontSize: 12 }}>{msg}</div>}
        <div className="nx-muted" style={{ fontSize: 11 }}>🔒 No capture/publish/send from the browser. Approved capture runs via the CLI wrapper.</div>
      </div>
    </div>
  );
}
