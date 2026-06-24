import { useState } from 'react';
import { listTable, type Row } from '../services/db';
import { createEvent, createJob, decideApproval } from '../lib/ledger';
import { Card, Stat, Pill, Empty, SectionTitle, timeAgo, useData } from './ui';
import {
  classify, proposeTask, detectModeSwitch, isApproval, MODE_DESC,
  type HermesMode, type ProposedTask,
} from '../lib/hermesIntent';
import { containsSensitive } from '../lib/dataScopes';
import { hermesChat, publicSearch, CHAT_NOT_CONFIGURED_MSG, SEARCH_NOT_CONFIGURED_MSG, type HermesContext } from '../lib/hermesProviders';
import { readLatestReport, summaryForPrompt } from '../lib/reportReader';
import { createTaskRequest, latestStatusForPrompt } from '../lib/taskRequests';

// ── reusable list ──
function DataList({ table, render, what, order }: {
  table: string; what: string; order?: string;
  render: (r: Row) => React.ReactNode;
}) {
  const { data } = useData<Row[]>(() => listTable(table, { order }), []);
  if (data.length === 0) return <Empty what={what} />;
  return <div className="list">{data.map((r) => <div className="item" key={r.id}>{render(r)}</div>)}</div>;
}

// ── Command Center (Hermes — conversation-first) ──
interface ChatMsg { role: 'user' | 'hermes'; text: string; meta?: string; }

const PLACEHOLDER =
  "Talk to Hermes naturally… e.g. ‘Good morning’, ‘What do you think about GoClear?’, ‘Who won last night?’, or ‘Read the latest Nexus report.’";

const MODES: HermesMode[] = ['conversation', 'report_reader', 'task_request']; // Operator Mode hidden for now

export function CommandCenter({ email }: { email: string | null }) {
  const [mode, setMode] = useState<HermesMode>('conversation');   // DEFAULT: conversation
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [showAware, setShowAware] = useState(false);              // awareness collapsed by default
  const [pendingTask, setPendingTask] = useState<ProposedTask | null>(null); // awaiting Ray's approval
  const [messages, setMessages] = useState<ChatMsg[]>([
    { role: 'hermes', text: "Hi Ray — I'm a conversational advisor. I can talk, look up public info, read safe Nexus reports, and (only after you approve) set up task requests. I never see SSNs, credit reports, passwords, or secrets, and I never publish/send/trade/deploy directly." },
  ]);

  const aware = useData<{ approvals: number; jobs: number; incidents: number; campaigns: number; receipts: number }>(
    async () => ({
      approvals: (await listTable('approvals', { eq: ['status', 'pending'], limit: 200 })).length,
      jobs: (await listTable('agent_jobs', { eq: ['status', 'queued'], limit: 200 })).length,
      incidents: (await listTable('ops_incidents', { eq: ['status', 'open'], limit: 200 })).length,
      campaigns: (await listTable('creative_campaigns', { eq: ['status', 'active'], limit: 200 })).length,
      receipts: (await listTable('social_publish_receipts', { limit: 200 })).length,
    }), { approvals: 0, jobs: 0, incidents: 0, campaigns: 0, receipts: 0 });

  function push(m: ChatMsg) { setMessages((prev) => [...prev, m]); }

  // Create a Ray-approved task request and confirm it. Hermes never executes — it only files it.
  async function fileTask(task: ProposedTask) {
    const id = await createTaskRequest(task, email);
    await createEvent({
      lane: 'communication', action: 'hermes_task_request', status: 'pending',
      title: task.task_type, summary: `${task.sensitivity} · worker ${task.assigned_worker_type}`,
      payload: { task_type: task.task_type, sensitivity: task.sensitivity, assigned_worker_type: task.assigned_worker_type },
    });
    push({
      role: 'hermes',
      text: `Created a task request: ${task.task_type} (sensitivity: ${task.sensitivity}). It’s assigned to ${task.assigned_worker_type}, I’ll only see ${task.hermes_visibility} updates, and I won’t execute it. ${id ? `Ref ${id}.` : ''}`,
      meta: 'task_request created · approved',
    });
    setPendingTask(null);
  }

  async function send() {
    const content = text.trim();
    if (!content || busy) return;
    setBusy(true);
    push({ role: 'user', text: content });
    setText('');

    try {
      // Explicit mode switch — changes the conversation surface, never executes anything.
      const target = detectModeSwitch(content);
      if (target) {
        setMode(target);
        push({ role: 'hermes', text: `Switched to ${labelFor(target)} — ${MODE_DESC[target]}.`, meta: 'mode change' });
        return;
      }

      // Approval of the pending proposed task — the ONLY path that creates work.
      if (pendingTask && isApproval(content)) { await fileTask(pendingTask); return; }

      const intent = classify(content);

      if (intent === 'sensitive_refusal') {
        push({ role: 'hermes', text: "I can't help with that — it would mean viewing private data (SSN, full credit report, bank/tax docs, passwords, tokens, or secrets). I never read that kind of data. If you want an action taken with it, I can set up a private task request for an internal worker instead.", meta: 'firewall · refused' });
        return;
      }

      if (intent === 'privileged_action' || intent === 'public_action') {
        const task = proposeTask(content);
        if (!task) { push({ role: 'hermes', text: "I’m not sure what to set up — tell me the action and I’ll propose a task request.", meta: 'no task' }); return; }
        setPendingTask(task);
        const forbids = task.forbidden_data.length ? task.forbidden_data.join(', ') : 'any private data';
        push({ role: 'hermes', text: `I can set up ${task.summary}\nI won’t do it directly, and I won’t access ${forbids}. Approve and I’ll file the task request — just say “approved”.`, meta: `proposed · ${task.assigned_worker_type}` });
        return;
      }

      if (intent === 'action_approval') {
        const task = pendingTask ?? proposeTask(content);
        if (!task) { push({ role: 'hermes', text: "I don’t have a pending action to create. Tell me what you’d like set up.", meta: 'no pending task' }); return; }
        await fileTask(task);
        return;
      }

      if (intent === 'report_read') {
        const r = await readLatestReport();
        push({ role: 'hermes', text: r.text, meta: r.ok ? 'report reader · safe summary' : 'report reader · nothing yet' });
        return;
      }

      if (intent === 'public_info') {
        if (containsSensitive(content)) {
          push({ role: 'hermes', text: "That looks like private data — I won’t search public sources for it.", meta: 'firewall · refused' });
          return;
        }
        const res = await publicSearch(content);
        if (res.blocked) { push({ role: 'hermes', text: res.text, meta: 'firewall · refused' }); return; }
        push({ role: 'hermes', text: res.configured ? res.text : SEARCH_NOT_CONFIGURED_MSG, meta: res.configured ? 'public search' : 'search not configured' });
        return;
      }

      // Default: normal conversation via the real chat provider (or not-configured).
      // Assemble a small, safe (public/internal_summary only) context for the model.
      const a = aware.data;
      const [report, taskStatus] = await Promise.all([summaryForPrompt(), latestStatusForPrompt()]);
      const ctx: HermesContext = {
        pending: pendingTask ? pendingTask.task_type : undefined,
        facts: `approvals_pending=${a.approvals}, queued_jobs=${a.jobs}, open_incidents=${a.incidents}, active_campaigns=${a.campaigns}`,
        report: report || undefined,
        taskStatus: taskStatus || undefined,
      };
      const res = await hermesChat(content, mode, ctx);
      if (res.blocked) { push({ role: 'hermes', text: res.text, meta: 'firewall · refused' }); return; }
      push({ role: 'hermes', text: res.configured ? res.text : CHAT_NOT_CONFIGURED_MSG, meta: res.configured ? 'chat provider' : 'chat not configured' });
    } finally {
      setBusy(false);
    }
  }

  function handleKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  }

  return (
    <>
      {/* Mode selector + current mode */}
      <div className="card" style={{ marginBottom: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', gap: 6 }}>
            {MODES.map((m) => (
              <button key={m} className={`tab ${mode === m ? 'active' : ''}`} onClick={() => setMode(m)}>
                {labelFor(m)}
              </button>
            ))}
          </div>
          <button className="btn ghost" onClick={() => setShowAware((s) => !s)}>{showAware ? 'Hide' : 'Show'} system awareness</button>
        </div>
        <div className="meta muted" style={{ marginTop: 8 }}>
          Current mode: <b style={{ color: 'var(--text)' }}>{labelFor(mode)}</b> — {MODE_DESC[mode]}.
          {pendingTask && <span style={{ color: 'var(--text)' }}> · awaiting your approval for a “{pendingTask.task_type}” task</span>}
        </div>
        {showAware && (
          <div className="meta" style={{ marginTop: 8, borderTop: '1px solid var(--border)', paddingTop: 8 }}>
            pending approvals {aware.data.approvals} · queued jobs {aware.data.jobs} · open incidents {aware.data.incidents}
            {' '}· active campaigns {aware.data.campaigns} · publish receipts {aware.data.receipts}
            <span className="muted"> · firewall: Hermes reads public + internal_summary only; no publish/send/trade/deploy without approval</span>
          </div>
        )}
      </div>

      {/* Chat — the main focus of the page */}
      <div className="card" style={{ minHeight: 360 }}>
        <h3>Hermes</h3>
        <div className="list" style={{ marginBottom: 12 }}>
          {messages.map((m, i) => (
            <div key={i} className={m.role === 'hermes' ? 'hermes' : 'item'}>
              <div className="body" style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>
              {m.meta && <div className="meta muted" style={{ marginTop: 4 }}>{m.role === 'hermes' ? 'Hermes' : 'You'} · {m.meta}</div>}
            </div>
          ))}
        </div>
        <textarea className="cmd" placeholder={PLACEHOLDER} value={text}
          onChange={(e) => setText(e.target.value)} onKeyDown={handleKey} rows={3} />
        <div style={{ marginTop: 8 }}>
          <button className="btn" onClick={send} disabled={busy || !text.trim()}>{busy ? 'Thinking…' : 'Send'}</button>
        </div>
      </div>
    </>
  );
}

function labelFor(m: HermesMode): string {
  return m === 'conversation' ? 'Conversation' : m === 'report_reader' ? 'Report Reader' : 'Task Request';
}

// ── System Health ──
export function SystemHealth() {
  const { data } = useData<Row[]>(() => listTable('system_health', { limit: 100 }), []);
  const latest = new Map<string, Row>();
  for (const r of data) if (!latest.has(r.component)) latest.set(r.component, r);
  const rows = [...latest.values()];
  if (rows.length === 0) return <Empty what="health rows" />;
  return <div className="grid">{rows.map((r) => (
    <div className="card" key={r.component}><h3>{r.component.replaceAll('_', ' ')}</h3>
      <Pill status={r.status} /><div className="meta muted" style={{ marginTop: 8 }}>{r.summary}</div></div>
  ))}</div>;
}

// ── Agent Jobs (+ registry + runner) ──
export function AgentJobsView() {
  const agents = useData<Row[]>(() => listTable('agent_registry', { order: 'agent_key', ascending: true }), []);
  return (
    <>
      <div className="card" style={{ marginBottom: 6 }}>
        <h3>Manual Runner Commands (no scheduler — run by hand)</h3>
        <div className="list">
          <div className="item"><code>python3 scripts/nexus_runner.py --once --limit 1 --dry-run</code></div>
          <div className="item"><code>python3 scripts/nexus_runner.py --once --limit 5 --dry-run</code></div>
          <div className="item"><code>python3 scripts/nexus_runner.py --job-id &lt;id&gt; --dry-run</code></div>
          <div className="item"><code>python3 scripts/nexus_runner.py --list-handlers</code></div>
        </div>
        <div className="meta muted" style={{ marginTop: 6 }}>Default is dry-run. Real Facebook publish needs --real-publish + all Day 3 gates. Unknown job types are blocked, not guessed. The frontend only queues jobs.</div>
      </div>
      <SectionTitle count={agents.data.length}>Agent permission matrix</SectionTitle>
      <div className="grid two">{agents.data.map((a) => (
        <div className="card" key={a.id}>
          <h3>{a.name} <Pill status={a.agent_class || 'worker'} /></h3>
          <div className="meta muted" style={{ marginBottom: 6 }}>audience: {a.audience_type || 'internal'} · {a.role}</div>
          <div className="meta">web: {a.web_access_allowed ? '✅' : '⛔'} · external API: {a.external_api_allowed ? '✅' : '⛔'} · create jobs: {a.can_create_jobs ? '✅' : '⛔'} · create approvals: {a.can_create_approvals ? '✅' : '⛔'} · execute: {a.can_execute_actions ? '✅' : '⛔'}</div>
          <div className="meta muted" style={{ marginTop: 4 }}>cost: {a.cost_policy || '—'} · compliance: {a.compliance_policy || '—'}</div>
          {a.requires_approval_for?.length > 0 && <div className="meta muted">approval required for: {(a.requires_approval_for || []).join(', ')}</div>}
        </div>
      ))}</div>
      <SectionTitle>Jobs</SectionTitle>
      <DataList table="agent_jobs" what="jobs" render={(j) => (
        <><div className="t">{j.job_type} <Pill status={j.status} />{j.attempts ? <span className="muted"> · attempt {j.attempts}/{j.max_attempts ?? 1}</span> : null}</div>
          <div className="meta">{j.lane} · {timeAgo(j.created_at)}{j.claimed_by ? ` · ${j.claimed_by}` : ''}{j.completed_at ? ` · done ${timeAgo(j.completed_at)}` : ''}</div>
          {(j.last_error || j.error) && <div className="meta" style={{ color: 'var(--bad)' }}>{j.last_error || j.error}</div>}
          {j.output && Object.keys(j.output).length > 0 && <div className="body" style={{ opacity: .8 }}>{JSON.stringify(j.output).slice(0, 160)}</div>}</>
      )} />
    </>
  );
}

// ── Approval Center ──
export function ApprovalCenter({ email }: { email: string | null }) {
  const { data, reload } = useData<Row[]>(() => listTable('approvals', { limit: 30 }), []);
  const [fb, setFb] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string>('');
  const [jobMsg, setJobMsg] = useState<Record<string, string>>({});

  async function act(a: Row, decision: 'approved' | 'rejected' | 'revise') {
    setBusy(a.id);
    await decideApproval(a.id, decision, email ?? undefined);
    await createEvent({ lane: a.lane || 'system', action: `approval_${decision}`, status: 'success',
      title: `${decision}: ${a.title ?? a.item_type}`, approval_id: a.id, payload: { feedback: fb[a.id] || null } });
    if (decision === 'revise') {
      await createJob({ lane: a.lane || 'system', job_type: 'revision_request', status: 'queued',
        input: { approval_id: a.id, feedback: fb[a.id] || '', item_type: a.item_type } });
    }
    setBusy(''); reload();
  }

  // Create a DRY-RUN publish job for an approved social post (frontend creates the job row
  // only — it never publishes; a server-side script runs the gated dry-run).
  async function createDryRunJob(a: Row) {
    setBusy(a.id);
    const posts = await listTable('social_posts', { eq: ['approval_id', a.id], limit: 1 });
    const post = posts[0];
    if (!post) { setJobMsg({ ...jobMsg, [a.id]: 'No linked social_posts row found.' }); setBusy(''); return; }
    const jobId = await createJob({ lane: 'social', job_type: 'social_publish', status: 'queued',
      input: { post_id: post.id, mode: 'dry_run', requested_by: email } });
    await createEvent({ lane: 'social', action: 'social_publish_job_queued', status: 'pending',
      title: 'Queued dry-run Facebook publish job', approval_id: a.id, job_id: jobId, payload: { post_id: post.id } });
    setJobMsg({ ...jobMsg, [a.id]: jobId ? 'Dry-run job queued. Run scripts/run_social_publish_job.py --dry-run.' : 'Could not create job (RLS?).' });
    setBusy('');
  }

  if (data.length === 0) return <Empty what="approvals" />;
  return (
    <div className="list">
      {data.map((a) => {
        const isSocial = a.item_type === 'social_publish' || a.payload?.platform === 'facebook';
        return (
        <div className="item" key={a.id}>
          <div className="t">{a.title ?? a.item_type} <Pill status={a.status} />{isSocial && <span className="pill info" style={{ marginLeft: 6 }}>facebook</span>}</div>
          <div className="meta">{a.lane} · {a.item_type} · {timeAgo(a.created_at)}{a.approved_by ? ` · by ${a.approved_by}` : ''}{isSocial ? ' · target: Clear Credentials (131069194210954)' : ''}</div>
          {a.summary && <div className="body">{a.summary}</div>}
          {a.payload?.caption && <div className="body">“{a.payload.caption}”</div>}
          {a.payload?.preview_url && <a href={a.payload.preview_url} target="_blank" rel="noreferrer">preview asset ↗</a>}
          {isSocial && a.status === 'approved' && (
            <div style={{ marginTop: 8 }}>
              <div className="meta" style={{ marginBottom: 6 }}>Ready for dry-run publish job. Real publish stays gated (token + publish_enabled + server script).</div>
              <button className="btn ghost" disabled={busy === a.id} onClick={() => createDryRunJob(a)}>Create dry-run publish job</button>
              {jobMsg[a.id] && <div className="meta" style={{ marginTop: 6 }}>{jobMsg[a.id]}</div>}
            </div>
          )}
          {a.status === 'pending' && (
            <>
              <textarea className="cmd" style={{ minHeight: 44, marginTop: 8 }} placeholder="Feedback (for request changes)…"
                value={fb[a.id] || ''} onChange={(e) => setFb({ ...fb, [a.id]: e.target.value })} />
              <div className="chips" style={{ marginTop: 8 }}>
                <button className="btn ok" disabled={busy === a.id} onClick={() => act(a, 'approved')}>Approve</button>
                <button className="btn bad" disabled={busy === a.id} onClick={() => act(a, 'rejected')}>Reject</button>
                <button className="btn warn" disabled={busy === a.id} onClick={() => act(a, 'revise')}>Request changes</button>
              </div>
              <div className="meta" style={{ marginTop: 6 }}>Approve = approved in ledger only. Nothing is published.</div>
            </>
          )}
        </div>
        );
      })}
    </div>
  );
}

// ── GoClear / Apex Funding ──
export function GoClearWorkspace() {
  return (
    <>
      <div className="grid">
        <Stat title="Funding Readiness" value="Score model" sub="Readiness scoring (foundation)" />
        <Stat title="Primary offer" value="$97" sub="Credit/Funding Readiness Starter Review" />
        <Stat title="Ladder" value="$97 / $197 / $297" sub="Basic · Guided · Concierge" />
        <Card title="Top blockers (concept)"><div className="meta muted">Entity/EIN, bank behavior, credit readiness, documentation, web presence.</div></Card>
        <Card title="Next best action"><div className="meta muted">Per-client recommendation tied to readiness blockers + partner offers.</div></Card>
        <Card title="Compliance"><div className="meta muted">No guaranteed funding/approval/credit-repair/score claims.</div></Card>
      </div>
      <SectionTitle>Partner offers</SectionTitle>
      <DataList table="partner_offers" what="partner offers" order="created_at" render={(o) => (
        <><div className="t">{o.name} <Pill status={o.approval_status} /></div>
          <div className="meta">{o.category} · risk {o.risk_level} · token via {o.secret_env_name || '—'} (not stored)</div>
          {o.why_it_matters && <div className="body">{o.why_it_matters}</div>}
          <div className="meta muted" style={{ marginTop: 4 }}>{o.affiliate_disclosure}</div></>
      )} />
      <SectionTitle>Client recommendations</SectionTitle>
      <DataList table="client_recommendations" what="client recommendations" render={(r) => (
        <><div className="t">{r.title} <Pill status={r.status} /></div><div className="meta">{r.recommendation_type}</div>{r.reason && <div className="body">{r.reason}</div>}</>
      )} />
    </>
  );
}

// ── Business Opportunity Lab ──
export function OpportunityLab() {
  return (
    <>
      <div className="note">Every idea is scored, not rejected: can it make money, become a tool, an offer, content, a lead source, or an affiliate path? What's the smallest low/no-cost test?</div>
      <SectionTitle>Opportunity inbox</SectionTitle>
      <DataList table="monetization_opportunities" what="opportunities" order="created_at" render={(o) => (
        <><div className="t">{o.title} <Pill status={o.decision} /> {o.overall_score != null && <span className="muted">· {o.overall_score}/100</span>}</div>
          {o.money_angle && <div className="body">{o.money_angle}</div>}
          {o.smallest_test && <div className="meta">Smallest test: {o.smallest_test}</div>}</>
      )} />
    </>
  );
}

// ── Creative Intelligence Studio ──
export function CreativeStudio({ email }: { email: string | null }) {
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  async function queue(jobType: string) {
    setBusy(true);
    const id = await createJob({ lane: 'creative', job_type: jobType, status: 'queued', input: { campaign_key: 'goclear_funding_readiness_review', requested_by: email } });
    await createEvent({ lane: 'monetization', action: 'creative_job_queued', status: 'pending', title: `Queued ${jobType}`, job_id: id });
    setMsg(id ? `Queued ${jobType}. Run the matching script to execute.` : 'Could not queue (RLS?).');
    setBusy(false);
  }
  return (
    <>
      <div className="note">Nexus never makes random content. Every asset ties to a campaign, offer, CTA, audience, and money goal — and passes compliance QA before publishing.</div>
      <div className="card" style={{ marginBottom: 6 }}>
        <h3>Actions (queue jobs only — never publishes)</h3>
        <div className="chips">
          <button className="chip" disabled={busy} onClick={() => queue('creative_generate_assets')}>Create sample campaign assets</button>
          <button className="chip" disabled={busy} onClick={() => queue('creative_score_assets')}>Score assets</button>
          <button className="chip" disabled={busy} onClick={() => queue('creative_create_approvals')}>Create approvals</button>
          <button className="chip" disabled={busy} onClick={() => queue('creative_create_social_drafts')}>Create Facebook drafts</button>
        </div>
        {msg && <div className="meta" style={{ marginTop: 6 }}>{msg}</div>}
      </div>
      <SectionTitle>Campaigns</SectionTitle>
      <DataList table="creative_campaigns" what="campaigns" render={(c) => (
        <><div className="t">{c.name} <Pill status={c.status} /></div><div className="meta">{c.goal} · {c.offer}</div></>
      )} />
      <SectionTitle>Briefs</SectionTitle>
      <DataList table="creative_briefs" what="briefs" render={(b) => (
        <><div className="t">{b.title} <Pill status={b.status} /></div><div className="meta">{b.platform} · {b.audience}</div>{b.hook && <div className="body">Hook: {b.hook}</div>}</>
      )} />
      <SectionTitle>Generated assets</SectionTitle>
      <DataList table="creative_assets" what="assets" render={(a) => (
        <><div className="t">{a.title || a.asset_type} <Pill status={a.status} />{a.score != null && <span className="muted"> · {a.score}/100</span>}{a.approval_id && <span className="pill info" style={{ marginLeft: 6 }}>approval created</span>}</div>
          <div className="meta">{a.asset_type} · {a.platform} · {(a.payload?.campaign_key) || ''}</div>
          {a.hook && <div className="body">Hook: {a.hook}</div>}
          {(a.body || a.content) && <div className="body" style={{ opacity: .85 }}>{String(a.body || a.content).slice(0, 180)}{String(a.body || a.content).length > 180 ? '…' : ''}</div>}</>
      )} />
      <SectionTitle>Creative QA</SectionTitle>
      <DataList table="creative_scores" what="QA scores" render={(s) => (
        <><div className="t">Overall {s.overall_score}/100 <Pill status={(s.notes || '').startsWith('blocked') ? 'failed' : 'ok'} /></div>
          <div className="meta">hook {s.hook_strength} · clarity {s.clarity} · compliance {s.compliance_safety} · CTA {s.cta_strength} · unique {s.uniqueness}</div>
          {s.notes && <div className="meta muted">{s.notes}</div>}</>
      )} />
      <SectionTitle>Studio outputs (NotebookLM-style)</SectionTitle>
      <DataList table="studio_outputs" what="studio outputs" render={(s) => (
        <><div className="t">{s.title} <Pill status={s.status} /></div><div className="meta">{s.output_type}</div>{s.script_text && <div className="body" style={{ opacity: .85 }}>{String(s.script_text).slice(0, 160)}…</div>}</>
      )} />
      <SectionTitle>Creative Design Department — briefs</SectionTitle>
      <DataList table="creative_design_briefs" what="design briefs" render={(b) => (
        <><div className="t">{b.title} <Pill status={b.status} /></div>
          <div className="meta">{b.platform} · {b.audience}{b.visual_metaphor ? ` · metaphor: ${b.visual_metaphor}` : ''}</div>
          {b.compliance_rules?.length > 0 && <div className="meta muted">compliance: {(b.compliance_rules || []).join(', ')}</div>}</>
      )} />
      <SectionTitle>Design variants</SectionTitle>
      <DataList table="creative_design_variants" what="design variants" render={(v) => (
        <><div className="t">{v.title} <Pill status="info" label={v.route_key} /></div>
          {v.post_copy && <div className="body" style={{ opacity: .85 }}>{String(v.post_copy).slice(0, 160)}</div>}
          {v.image_prompt && <div className="meta muted">image prompt: {String(v.image_prompt).slice(0, 120)}</div>}</>
      )} />
      <SectionTitle>Design comparisons (winner)</SectionTitle>
      <DataList table="creative_asset_comparisons" what="comparisons" render={(c) => (
        <><div className="t">{c.summary} <Pill status={c.next_action} /></div>
          <div className="meta">{c.reason}{c.approval_required ? ' · approval required before publish' : ''}</div></>
      )} />
      <SectionTitle>Publish readiness packages (manual only)</SectionTitle>
      <DataList table="publish_readiness_packages" what="publish packages" render={(p) => (
        <><div className="t">{p.package_title} <Pill status={p.approval_status} /><span className="pill info" style={{ marginLeft: 6 }}>{p.platform}</span>{p.compliance_status === 'ok' ? <span className="pill ok" style={{ marginLeft: 6 }}>compliant</span> : <span className="pill warn" style={{ marginLeft: 6 }}>{p.compliance_status}</span>}</div>
          <div className="body" style={{ opacity: .9 }}>{String(p.final_post_copy || '').slice(0, 200)}</div>
          {p.cta && <div className="meta" style={{ color: 'var(--accent)' }}>{p.cta}</div>}
          {p.risk_flags?.length > 0 && <div className="meta" style={{ color: 'var(--warn)' }}>risk flags: {(p.risk_flags || []).join(', ')}</div>}
          <div className="meta muted">Manual publish only — approval required before any real post. No auto-publish.</div></>
      )} />
      <SectionTitle>Publish package reviews</SectionTitle>
      <DataList table="publish_package_reviews" what="package reviews" render={(r) => (
        <><div className="t"><Pill status={r.decision === 'approve_manual_use' ? 'ok' : 'warn'} label={r.decision} /> {r.score}/100</div>
          <div className="meta">{r.review_type} · {r.reason}{r.risk_flags?.length ? ` · flags: ${(r.risk_flags || []).join(', ')}` : ''}</div>
          {r.revision_notes?.length > 0 && <div className="meta muted">{(r.revision_notes || []).join(' ')}</div>}</>
      )} />
      <SectionTitle>Manual publish receipts</SectionTitle>
      <DataList table="manual_publish_receipts" what="manual receipts" render={(m) => (
        <><div className="t"><Pill status={m.receipt_type === 'dry_run' ? 'info' : 'ok'} label={m.receipt_type} /> {m.platform}</div>
          <div className="meta">{m.summary}{m.external_url ? ` · ${m.external_url}` : ''}</div></>
      )} />
      <div className="note">Design + publish pipeline (manual/jobs): <code>create_design_brief</code> → <code>generate_design_variants</code> → <code>score</code> → <code>compare</code> → <code>create_publish_readiness_package</code> → <code>review</code> → <code>export</code>. Credit/funding copy is compliance-gated (no guarantees); a package still needs approval before any real publish. No auto-publish, no external image/model calls.</div>
    </>
  );
}

// ── Design Library (Day 9) ──
export function DesignLibrary() {
  return (
    <>
      <div className="note">Inspiration is stored as <b>reference only</b> — Nexus does not clone, import, or depend on external repos/assets. Deterministic; no external image/model calls.</div>
      <SectionTitle>Inspiration sources</SectionTitle>
      <DataList table="design_inspiration_sources" what="inspiration sources" render={(s) => (
        <><div className="t">{s.source_name} <Pill status="info" label={s.category} /></div>
          <div className="meta">{s.source_type} · usefulness {s.usefulness_score} · risk {s.risk_level} · reference only</div>
          {s.summary && <div className="body" style={{ opacity: .85 }}>{s.summary}</div>}</>
      )} />
      <SectionTitle>Pattern registry</SectionTitle>
      <DataList table="design_pattern_registry" what="design patterns" render={(p) => (
        <><div className="t">{p.pattern_name} <Pill status="info" label={p.pattern_category} /></div>
          <div className="meta">{p.use_case}</div><div className="body" style={{ opacity: .85 }}>{p.description}</div></>
      )} />
      <SectionTitle>Feature design packets</SectionTitle>
      <DataList table="feature_design_packets" what="feature packets" render={(f) => (
        <><div className="t">{f.feature_name} <Pill status={f.status} /></div>
          <div className="meta">{f.target_surface} · goal: {f.user_goal}</div>
          <div className="meta muted">sections: {(f.required_sections || []).join(', ')}</div></>
      )} />
      <SectionTitle>UI quality reviews</SectionTitle>
      <DataList table="ui_quality_reviews" what="UI reviews" render={(u) => (
        <><div className="t">{u.review_title} <Pill status={u.overall_score >= 80 ? 'ok' : 'warn'} label={`${u.overall_score}/100`} /></div>
          <div className="meta">layout {u.layout_score} · readability {u.readability_score} · mobile {u.mobile_score} · a11y {u.accessibility_score} · compliance {u.compliance_score} · {u.recommendation}</div>
          {u.revision_notes?.length > 0 && <div className="meta muted">notes: {(u.revision_notes || []).join(' ')}</div>}</>
      )} />
    </>
  );
}

// ── Trading Lab ──
export function TradingLab() {
  return (
    <>
      <div className="note">Research/testing only. Live + funded trading disabled. No execution this pass. All actions route through jobs/signals/demo_trades/events. No client performance claims without proof + approval.</div>
      <SectionTitle>Strategy candidates</SectionTitle>
      <DataList table="trading_strategy_candidates" what="strategy candidates" render={(c) => (
        <><div className="t">{c.title} <Pill status={c.status} /></div><div className="meta">{c.market} · {c.timeframe} · hype risk {c.hype_risk ?? '—'}</div></>
      )} />
      <SectionTitle>Risk rules</SectionTitle>
      <DataList table="trading_risk_rules" what="risk rules" order="created_at" render={(r) => (
        <><div className="t">{r.rule_key} <Pill status={r.enabled ? 'enabled' : 'registered'} /></div><div className="meta">{r.description}</div></>
      )} />
    </>
  );
}

// ── SEO / Marketing OS ──
export function SeoOs() {
  return (
    <>
      <div className="note">Hermes asks for Ray's real experience before finalizing important client-facing content. GSC / GA / DataForSEO are registered only (no OAuth/keys yet).</div>
      <SectionTitle>Sites</SectionTitle>
      <DataList table="seo_sites" what="sites" render={(s) => (<><div className="t">{s.name}</div><div className="meta">{s.domain} · {s.status}</div></>)} />
      <SectionTitle>SEO opportunities</SectionTitle>
      <DataList table="seo_opportunities" what="SEO opportunities" render={(o) => (
        <><div className="t">{o.title} <Pill status={o.status} /></div><div className="meta">{o.opportunity_type}{o.keyword ? ` · ${o.keyword}` : ''}</div></>
      )} />
    </>
  );
}

// ── Model Router ──
export function ModelRouter() {
  const providers = useData<Row[]>(() => listTable('model_providers', { order: 'provider_key', ascending: true }), []);
  return (
    <>
      <div className="note">Free cloud models handle public/non-sensitive work. Sensitive client/credit/financial/secret data must use local/private or manual premium routes — never free cloud.</div>
      <SectionTitle count={providers.data.length}>Providers</SectionTitle>
      <div className="grid">{providers.data.map((p) => (
        <div className="card" key={p.id}><h3>{p.name}</h3><Pill status={p.enabled ? 'enabled' : 'registered'} />
          <div className="meta muted" style={{ marginTop: 6 }}>{p.provider_type} · privacy: {p.privacy_level} · env: {p.secret_env_name || '—'}</div></div>
      ))}</div>
      <SectionTitle>Routes (policy-gated)</SectionTitle>
      <DataList table="model_routes" what="routes" order="priority" render={(r) => (
        <><div className="t">{r.route_key} <Pill status={r.route_type === 'blocked' ? 'failed' : (r.active ? 'active' : 'registered')} label={r.route_type || r.policy} />{!r.active && r.route_type !== 'blocked' && <span className="pill warn" style={{ marginLeft: 6 }}>candidate</span>}</div>
          <div className="meta">provider: {r.provider_key || r.primary_provider_key || '—'} · external call: {r.external_call_allowed ? '✅' : '⛔'} · sensitive: {r.sensitive_data_allowed ? '✅' : '⛔'} · approval: {r.requires_approval ? '✅' : '—'} · cost: {r.cost_tier || '—'}</div>
          {r.notes && <div className="meta muted">{r.notes}</div>}</>
      )} />
      <SectionTitle>Recent route decisions</SectionTitle>
      <DataList table="model_route_decisions" what="route decisions" render={(d) => (
        <><div className="t"><Pill status={d.decision === 'blocked' ? 'failed' : (d.decision === 'selected' ? 'ok' : 'pending')} label={d.decision} /> {d.sensitivity}</div>
          <div className="meta">{d.task_type} → {d.selected_route_key || '—'}{d.requires_approval ? ' · approval required' : ''}</div>
          {d.reason && <div className="meta muted">{d.reason}</div>}</>
      )} />
      <SectionTitle>Recent Hermes model requests</SectionTitle>
      <DataList table="hermes_model_requests" what="Hermes requests" render={(h) => (
        <><div className="t"><Pill status={h.status === 'blocked' ? 'failed' : 'info'} label={h.status} /> {h.sensitivity}</div>
          <div className="meta">{h.task_type} → {h.selected_route_key || '—'} · dry_run {String(h.dry_run)}</div>
          {h.response_summary && <div className="body" style={{ opacity: .85 }}>{String(h.response_summary).slice(0, 160)}</div>}</>
      )} />
      <div className="note">External model calls are OFF by default (need <code>NEXUS_ALLOW_EXTERNAL_MODEL_CALLS=true</code> + approval). Sensitive GoClear/client/credit/funding data never routes to public/free cloud. Manual Claude/OpenCode/Codex packets are supported.</div>
    </>
  );
}

// ── Integration Registry ──
export function Integrations() {
  return (
    <>
      <div className="note">Registered, not activated. Each integration lists its secret env names (never the secret) and risk level. Enabling happens later, deliberately.</div>
      <DataList table="integration_registry" what="integrations" order="integration_key" render={(i) => (
        <><div className="t">{i.name} <Pill status={i.enabled ? 'enabled' : 'registered'} /></div>
          <div className="meta">{i.category} · risk {i.risk_level}{i.requires_secret ? ` · secrets: ${(i.secret_env_names || []).join(', ')}` : ' · no secret'}</div>
          {i.purpose && <div className="body">{i.purpose}</div>}</>
      )} />
    </>
  );
}

// ── Ops & Improvements ──
export function OpsImprovements() {
  return (
    <>
      <SectionTitle>Incidents (Ops Doctor)</SectionTitle>
      <div className="note">Detect/diagnose later. Safe repairs only; risky repairs require approval. Never auto-change code, deploy, trade, post, or expose secrets.</div>
      <DataList table="ops_incidents" what="incidents" render={(i) => (
        <><div className="t">{i.title} <Pill status={i.status} /></div><div className="meta">{i.component} · {i.severity}{i.approval_required ? ' · approval required' : ''}</div></>
      )} />
      <SectionTitle>Improvement candidates</SectionTitle>
      <DataList table="improvement_candidates" what="improvement candidates" render={(c) => (
        <><div className="t">{c.title} <Pill status={c.decision} /></div><div className="meta">{c.capability_area} · effort {c.implementation_effort ?? '—'} · risk {c.security_risk ?? '—'}</div></>
      )} />
    </>
  );
}

// ── Intake & Orientation (Day 8) ──
export function IntakeOrientation() {
  return (
    <>
      <div className="note">Paste videos/transcripts/ideas → Nexus decides what to do (use now / phase 2 / improvement candidate / GoClear test / content / research / park / reject). Deterministic + compliance-gated; no external model calls. High-compliance items (credit/funding/trading) require human review.</div>
      <SectionTitle>Transcript reviews</SectionTitle>
      <DataList table="transcript_reviews" what="transcript reviews" render={(r) => (
        <><div className="t">{r.title} <Pill status={r.decision} /> {r.score != null ? '' : ''}<span className="pill info" style={{ marginLeft: 6 }}>{r.category}</span></div>
          <div className="meta">use {r.usefulness_score} · money {r.money_now_score} · auto {r.automation_score} · risk {r.risk_score} · compliance: <b style={{ color: (r.compliance_risk === 'very_high' || r.compliance_risk === 'high') ? 'var(--bad)' : 'var(--muted)' }}>{r.compliance_risk}</b></div>
          <div className="body" style={{ opacity: .85 }}>{r.recommended_action}</div>
          {r.claim_flags?.length > 0 && <div className="meta" style={{ color: 'var(--warn)' }}>claim flags: {(r.claim_flags || []).join(', ')}</div>}</>
      )} />
      <SectionTitle>Claim risk / compliance queue</SectionTitle>
      <DataList table="orientation_notes" what="orientation notes" render={(o) => (
        <><div className="t">{o.summary} <Pill status={o.decision} /></div>
          <div className="meta">{o.category}{o.risk_flags?.length ? ` · flags: ${(o.risk_flags || []).join(', ')}` : ''}</div>
          {o.reason && <div className="body" style={{ opacity: .8 }}>{o.reason}</div>}</>
      )} />
      <SectionTitle>Intake inbox</SectionTitle>
      <DataList table="intake_events" what="intake events" render={(e) => (
        <><div className="t">{e.title} <Pill status={e.status} /></div>
          <div className="meta">{e.source_type}{e.category ? ` · ${e.category}` : ''} · {timeAgo(e.created_at)}</div></>
      )} />
      <div className="note">Improvement candidates (AI resource / GoClear / trading / workforce) appear in <b>Ops &amp; Improvements</b>; service opportunities appear in <b>Opportunity Lab</b>. Manual run order: <code>capture_intake_event.py</code> → <code>review_transcript.py</code> → <code>extract_service_opportunity.py</code> (or queue jobs for the runner).</div>
    </>
  );
}

// ── Events Feed ──
export function EventsFeed() {
  return (
    <DataList table="nexus_events" what="events" render={(e) => (
      <><div className="t"><Pill status={e.status} /> {e.title ?? e.action}</div>
        <div className="meta">{e.lane} · {e.source} · {timeAgo(e.created_at)}{e.summary ? ` · ${e.summary}` : ''}</div></>
    )} />
  );
}
