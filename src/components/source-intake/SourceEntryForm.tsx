/** Source Entry — submitting NEVER captures in the browser.
 *  Policy (NEXUS_SOURCE_CAPTURE_POLICY.md): a public YouTube URL (or a plain idea/transcript) that
 *  Ray submits is SAFE → it becomes a Capture Queue item (approval_required=false), no Approvals
 *  clutter. Risky/uncategorized inputs (e.g. website crawl) ALSO file an approvals row so they show
 *  in the Approvals tab for Ray. Capture itself runs later via the local CLI wrapper after the
 *  worker picks it up. No yt-dlp in the browser, no external AI, no publish/send/trade/deploy. */
import { useEffect, useState } from 'react';
import { createTaskRequest } from '../../lib/taskRequests';
import { createEvent, createApproval } from '../../lib/ledger';
import { containsSensitive } from '../../lib/dataScopes';
import type { SourceType } from './AddSourcePanel';

const YT_RE = /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=[\w-]{6,}|youtu\.be\/[\w-]{6,})/i;
const SAFE_TYPES = new Set(['youtube_video', 'manual_idea', 'transcript_file']);

function captureCommand(url: string): string {
  return `python3 scripts/intake/run_existing_youtube_monitor.py --source-url "${url}" --once --limit 1 --no-external-ai --write-events --no-dry-run`;
}

/** Returns null when the submission is safe (Capture Queue, no approval), else a review trigger. */
function reviewTrigger(type: string, sensitive: boolean): string | null {
  if (sensitive) return 'sensitive_data';
  if (type === 'website_url') return 'risky_destination';   // web crawl needs review
  if (!SAFE_TYPES.has(type)) return 'uncategorized';
  return null;                                              // youtube_video / manual_idea / transcript_file = safe
}

const TRIGGER_ITEM: Record<string, string> = {
  risky_destination: 'risky_destination_review',
  uncategorized: 'uncategorized_source_review',
  sensitive_data: 'source_capture_review',
};

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
    const sensitive = !!containsSensitive(`${title} ${url} ${snippet}`);
    if (sensitive) { setMsg({ ok: false, text: 'That looks like private/customer data — not submitting.' }); return; }
    if (!url && !snippet) { setMsg({ ok: false, text: 'Add a URL or a text snippet.' }); return; }
    if (type === 'youtube_video' && url && !YT_RE.test(url.trim())) {
      setMsg({ ok: false, text: 'That does not look like a public YouTube video URL (youtube.com/watch?v=… or youtu.be/…).' }); return;
    }

    setBusy(true);
    const tagList = tags.split(',').map((t) => t.trim()).filter(Boolean);
    const trigger = reviewTrigger(type, sensitive);
    const reviewRequired = trigger !== null;
    const isYouTube = type === 'youtube_video';
    const taskType = isYouTube ? 'youtube_capture_request' : 'source_capture_request';

    const id = await createTaskRequest({
      task_type: taskType, sensitivity: 'internal_summary',
      allowed_data_scope: ['public', 'internal_summary'], forbidden_data: ['customer_private', 'secrets'],
      assigned_worker_type: 'research_worker', hermes_visibility: 'summary',
      payload: {
        action_type: taskType, source_type: type, source_url: url.trim() || null, title: title || null,
        snippet: snippet ? snippet.slice(0, 500) : null, target_use: targetUse, priority, tags: tagList,
        requested_by: email ?? 'operator', requested_by_admin: true, created_at: new Date().toISOString(),
        approval_required: reviewRequired, review_trigger: trigger,
        source_capture_policy: 'safe_admin_submitted_capture_v1', capture_status: reviewRequired ? 'needs_review' : 'queued',
        capture_command_preview: isYouTube ? captureCommand(url.trim()) : null,
        external_ai: false, scheduler: false, v1_jobs_touched: false,
        note: 'Browser capture is disabled. A worker runs the CLI wrapper after the capture is queued/approved.',
      },
      summary: reviewRequired
        ? `Source needs Ray review (${trigger}): ${(title || url || type).slice(0, 60)}`
        : `Safe Capture Queue: ${(title || url || type).slice(0, 60)} — runs via CLI wrapper, no approval needed`,
    }, email);

    // Review-required items ALSO get an approvals row so they appear in the Approvals tab.
    let approvalId: string | null = null;
    if (id && reviewRequired) {
      approvalId = await createApproval({
        lane: 'research', item_type: TRIGGER_ITEM[trigger!] ?? 'source_capture_review',
        title: `Review source: ${(title || url || type).slice(0, 60)}`,
        summary: `Reason: ${trigger}. Requested action: capture + route. task_request ${id}.`,
        payload: { task_request_id: id, source_url: url, source_type: type, review_trigger: trigger, requested_action: 'capture_and_route', created_at: new Date().toISOString() },
      });
    }

    if (id) {
      await createEvent({
        lane: 'research', action: reviewRequired ? 'source_capture_review_requested' : 'source_capture_queued',
        status: 'pending', title: (title || url || type).slice(0, 80),
        summary: `${taskType} ${id}${approvalId ? ` · approval ${approvalId}` : ''} · approval_required=${reviewRequired}`,
        payload: { task_request_id: id, approval_id: approvalId, source_url: url, browser_capture: false, review_trigger: trigger },
      });
    }
    setBusy(false);
    onSubmitted?.();
    if (!id) { setMsg({ ok: false, text: 'Could not file request (check sign-in / RLS).' }); return; }
    setMsg(reviewRequired
      ? { ok: true, text: `Filed for Ray review — appears in Approvals (reason: ${trigger}). task_request ${id.slice(0, 8)}…` }
      : { ok: true, text: `Queued for safe capture — Ray approval is only required if Nexus cannot categorize the source or if the next action is risky. (queue id ${id.slice(0, 8)}…)` });
  }

  return (
    <div className="nx-glass">
      <div className="nx-row" style={{ marginBottom: 12 }}>
        <span className="nx-pill nx-violet">2</span>
        <div><h3 style={{ margin: 0 }}>Source Entry</h3>
          <div className="nx-muted" style={{ fontSize: 12 }}>Safe sources you submit are queued automatically. Risky/uncertain ones go to Approvals.</div></div>
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
        <div className="nx-muted" style={{ fontSize: 11 }}>🔒 Browser capture is disabled. Approved/queued capture runs through the local CLI wrapper. No publish/send/trade, no external AI on transcript text. Hermes can recommend, but Ray approves risky actions.</div>
      </div>
    </div>
  );
}
