import { useEffect, useRef, useState } from 'react';
import { loadMessages, saveMessages, loadMode, saveMode, type StoredMsg } from '../lib/hermesChatStore';
import {
  getAdminDiagnostic,
  listTable,
  listTableDetailed,
  type AdminDiagnostic,
  type Row,
  type TableQueryResult,
} from '../services/db';
import { createEvent, createJob, decideApproval } from '../lib/ledger';
import { Card, Stat, Pill, SectionTitle, timeAgo, useData } from './ui';
import {
  classify, proposeTask, detectModeSwitch, isApproval, isCancel, isModification, MODE_DESC,
  type HermesMode, type ProposedTask,
} from '../lib/hermesIntent';
import { containsSensitive } from '../lib/dataScopes';
import { hermesChat, publicSearch, CHAT_NOT_CONFIGURED_MSG, SEARCH_NOT_CONFIGURED_MSG, type HermesContext, type HermesHistoryTurn, type HermesPendingActionContext } from '../lib/hermesProviders';
import { readLatestReport, summaryForPrompt } from '../lib/reportReader';
import { createTaskRequest, latestStatusForPrompt } from '../lib/taskRequests';
import {
  approvalRefFromPrompt,
  findApprovalReview,
  formatApprovalReviewDetail,
  formatApprovalReviewList,
  isApprovalDirectAction,
  isApprovalReviewPrompt,
  loadPendingApprovalReviews,
  type ApprovalReviewItem,
} from '../lib/approvalReview';
import { DepartmentWorkspace } from './common/DepartmentWorkspace';
import { DEPARTMENT_WORKSPACES } from '../config/nexusProjectTypes';

// ── reusable list ──
function DataList({ table, render, what, order }: {
  table: string; what: string; order?: string;
  render: (r: Row) => React.ReactNode;
}) {
  const { data } = useData<TableQueryResult>(() => listTableDetailed(table, { order }), emptyTableResult(table, order));
  if (data.data.length === 0) return <ConnectionEmpty result={data} what={what} />;
  return (
    <>
      <ConnectionLine result={data} />
      <div className="list">{data.data.map((r) => <div className="item" key={r.id}>{render(r)}</div>)}</div>
    </>
  );
}

function emptyTableResult(table: string, order?: string): TableQueryResult {
  return {
    table,
    filter: `limit=50 order=${order ?? 'created_at'}.desc`,
    supabaseConfigured: true,
    authSessionPresent: false,
    userEmail: null,
    userIdPrefix: null,
    status: 'no_authenticated_session',
    resultCount: 0,
    errorCategory: null,
    errorMessage: null,
    data: [],
  };
}

function statusLabel(status: string): string {
  return status.replaceAll('_', ' ');
}

function ConnectionLine({ result }: { result: TableQueryResult }) {
  return <div className="meta">Connection: {statusLabel(result.status)} · {result.table} · {result.resultCount} rows</div>;
}

function ConnectionEmpty({ result, what }: { result: TableQueryResult; what: string }) {
  if (result.status === 'no_records') {
    return <div className="empty">Connected to {result.table}, but no {what} records matched. Filter: {result.filter}.</div>;
  }
  const message = result.errorMessage ? ` Safe error: ${result.errorMessage}` : '';
  return (
    <div className="empty">
      No {what} visible. Status: {statusLabel(result.status)}. Table: {result.table}. Filter: {result.filter}.{message}
    </div>
  );
}

// ── Command Center (Hermes — conversation-first) ──
interface ChatMsg { role: 'user' | 'hermes'; text: string; meta?: string; }
interface PendingAction {
  action_type: string;
  title: string;
  safe_summary: string;
  sensitivity: ProposedTask['sensitivity'];
  proposed_worker_type: string;
  allowed_data_scope: ProposedTask['allowed_data_scope'];
  forbidden_data: string[];
  hermes_visibility: ProposedTask['hermes_visibility'];
  requires_approval: true;
  source_assistant_message_id?: string;
  source_timestamp: string;
  task: ProposedTask;
}

const PLACEHOLDER =
  "Talk to Hermes naturally… e.g. ‘Good morning’, ‘What do you think about GoClear?’, ‘Who won last night?’, or ‘Read the latest Nexus report.’";

const MODES: HermesMode[] = ['conversation', 'report_reader', 'task_request']; // Operator Mode hidden for now

const HERMES_GREETING: ChatMsg = { role: 'hermes', text: "Hi Ray — I'm a conversational advisor. I can talk, look up public info, read safe Nexus reports, and (only after you approve) set up task requests. I never see SSNs, credit reports, passwords, or secrets, and I never publish/send/trade/deploy directly." };

export function CommandCenter({ email }: { email: string | null }) {
  // Persisted across tab navigation + reloads via localStorage (sensitive text never stored).
  const [mode, setMode] = useState<HermesMode>(() => (loadMode() as HermesMode) || 'conversation');
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [showAware, setShowAware] = useState(false);              // awareness collapsed by default
  const [pendingTask, setPendingTask] = useState<ProposedTask | null>(null); // awaiting Ray's approval
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);
  const [approvalReviewItems, setApprovalReviewItems] = useState<ApprovalReviewItem[]>([]);
  const [messages, setMessages] = useState<ChatMsg[]>(() => {
    const saved = loadMessages() as ChatMsg[] | null;
    return saved && saved.length ? saved : [HERMES_GREETING];
  });
  const chatEndRef = useRef<HTMLDivElement | null>(null);

  // Persist chat + mode so switching tabs / reloading does not reset Hermes.
  useEffect(() => { saveMessages(messages as StoredMsg[]); }, [messages]);
  useEffect(() => { saveMode(mode); }, [mode]);
  // Keep the latest message in view inside the scrollable panel.
  useEffect(() => { chatEndRef.current?.scrollIntoView({ block: 'end' }); }, [messages]);

  const aware = useData<{ approvals: number; jobs: number; incidents: number; campaigns: number; receipts: number }>(
    async () => ({
      approvals: (await listTable('approvals', { eq: ['status', 'pending'], limit: 200 })).length,
      jobs: (await listTable('agent_jobs', { eq: ['status', 'queued'], limit: 200 })).length,
      incidents: (await listTable('ops_incidents', { eq: ['status', 'open'], limit: 200 })).length,
      campaigns: (await listTable('creative_campaigns', { eq: ['status', 'active'], limit: 200 })).length,
      receipts: (await listTable('social_publish_receipts', { limit: 200 })).length,
    }), { approvals: 0, jobs: 0, incidents: 0, campaigns: 0, receipts: 0 });

  function push(m: ChatMsg) { setMessages((prev) => [...prev, m]); }

  function pendingContext(action: PendingAction | null): HermesPendingActionContext | undefined {
    if (!action) return undefined;
    return {
      action_type: action.action_type,
      title: action.title,
      safe_summary: action.safe_summary,
      sensitivity: action.sensitivity,
      proposed_worker_type: action.proposed_worker_type,
      allowed_data_scope: action.allowed_data_scope,
      forbidden_data: action.forbidden_data,
      hermes_visibility: action.hermes_visibility,
      requires_approval: true,
      source_assistant_message_id: action.source_assistant_message_id,
      source_timestamp: action.source_timestamp,
    };
  }

  function makePendingAction(task: ProposedTask, title: string, summary: string, source?: string): PendingAction {
    return {
      action_type: task.task_type === 'public_build_task' ? 'draft_private_worker_task_request' : `create_${task.task_type}`,
      title,
      safe_summary: summary.slice(0, 600),
      sensitivity: task.sensitivity,
      proposed_worker_type: task.assigned_worker_type,
      allowed_data_scope: task.allowed_data_scope,
      forbidden_data: task.forbidden_data,
      hermes_visibility: task.hermes_visibility,
      requires_approval: true,
      source_assistant_message_id: source,
      source_timestamp: new Date().toISOString(),
      task: { ...task, payload: { ...task.payload, safe_summary: summary.slice(0, 600) } },
    };
  }

  function inferPendingAction(userText: string, assistantText: string): PendingAction | null {
    if (containsSensitive(userText) || containsSensitive(assistantText)) return null;
    const offer = /\b(i can|want me to|if you want|i can also|i'll|i will)\b[\s\S]{0,180}\b(draft|create|set up|file|prepare)\b[\s\S]{0,120}\b(task request|private worker|worker task|request)\b/i;
    if (!offer.test(assistantText)) return null;
    const task: ProposedTask = {
      task_type: 'public_build_task',
      sensitivity: 'internal_summary',
      allowed_data_scope: ['public', 'internal_summary'],
      forbidden_data: ['customer_private', 'credit_sensitive', 'funding_sensitive', 'auth_sensitive', 'secrets'],
      assigned_worker_type: 'general_worker',
      hermes_visibility: 'summary',
      payload: { request: userText, source: 'hermes_conversation_offer' },
      summary: 'a safe task request for the concept we just discussed. Hermes will not access private customer data or execute the work directly.',
    };
    return makePendingAction(task, 'Draft task request from current conversation', userText, `assistant_${Date.now()}`);
  }

  function safeHistoryForModel(extraUser?: string): HermesHistoryTurn[] {
    const turns: HermesHistoryTurn[] = messages
      .slice(-10)
      .map((m) => ({ role: m.role === 'hermes' ? 'assistant' as const : 'user' as const, content: m.text.slice(0, 700) }))
      .filter((m) => m.content.trim() && !containsSensitive(m.content));
    if (extraUser && !containsSensitive(extraUser)) turns.push({ role: 'user', content: extraUser.slice(0, 700) });
    return turns.slice(-10);
  }

  function updatePendingAction(action: PendingAction, content: string): PendingAction {
    const summary = `${action.safe_summary}; requested change: ${content}`.slice(0, 600);
    return {
      ...action,
      safe_summary: summary,
      task: { ...action.task, payload: { ...action.task.payload, requested_change: content, safe_summary: summary } },
    };
  }

  // Create a Ray-approved task request and confirm it. Hermes never executes — it only files it.
  async function fileTask(task: ProposedTask, action?: PendingAction) {
    const id = await createTaskRequest(task, email);
    await createEvent({
      lane: 'communication', action: 'hermes_task_request', status: 'pending',
      title: task.task_type, summary: `${task.sensitivity} · worker ${task.assigned_worker_type}`,
      payload: { task_type: task.task_type, sensitivity: task.sensitivity, assigned_worker_type: task.assigned_worker_type },
    });
    push({
      role: 'hermes',
      text: action
        ? `Approved. I’m drafting the ${action.proposed_worker_type} task request for the concept we just discussed: ${action.safe_summary}. It will be ${action.hermes_visibility} for Hermes and will not expose private customer data. ${id ? `Ref ${id}.` : ''}`
        : `Created a task request: ${task.task_type} (sensitivity: ${task.sensitivity}). It’s assigned to ${task.assigned_worker_type}, I’ll only see ${task.hermes_visibility} updates, and I won’t execute it. ${id ? `Ref ${id}.` : ''}`,
      meta: 'task_request created · approved',
    });
    setPendingTask(null);
    setPendingAction(null);
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

      if (isApprovalDirectAction(content)) {
        push({ role: 'hermes', text: 'I can review approvals and explain the risk, but I cannot approve, reject, publish, send, trade, deploy, or set publish_enabled from chat. Use the Approvals tab buttons after reviewing the preview card.', meta: 'approval review · read only' });
        return;
      }

      const requestedApprovalRef = approvalRefFromPrompt(content);
      if (requestedApprovalRef && approvalReviewItems.length > 0) {
        const item = findApprovalReview(approvalReviewItems, requestedApprovalRef);
        push({
          role: 'hermes',
          text: item ? formatApprovalReviewDetail(item, approvalReviewItems.indexOf(item) + 1) : `I don’t see approval ${requestedApprovalRef} in the current pending approval review list. Ask me to review approvals again to refresh the queue.`,
          meta: 'approval review · read only',
        });
        return;
      }

      if (pendingAction && isCancel(content)) {
        setPendingAction(null);
        setPendingTask(null);
        push({ role: 'hermes', text: `Canceled the pending task request: ${pendingAction.title}. I won’t create anything.`, meta: 'pending action cleared' });
        return;
      }

      if (pendingAction && isModification(content)) {
        const next = updatePendingAction(pendingAction, content);
        setPendingAction(next);
        setPendingTask(next.task);
        push({ role: 'hermes', text: `Updated the pending task request: ${next.safe_summary}. Say “approved” or “yes please” when you want me to file it.`, meta: 'pending action updated' });
        return;
      }

      // Approval of the pending proposed task — the ONLY path that creates work.
      if (pendingAction && isApproval(content)) { await fileTask(pendingAction.task, pendingAction); return; }
      if (pendingTask && isApproval(content)) { await fileTask(pendingTask); return; }

      const intent = classify(content);

      if (intent === 'approval_review' || isApprovalReviewPrompt(content)) {
        const review = await loadPendingApprovalReviews(20);
        setApprovalReviewItems(review.items);
        const ref = approvalRefFromPrompt(content);
        const item = ref ? findApprovalReview(review.items, ref) : null;
        push({
          role: 'hermes',
          text: item ? formatApprovalReviewDetail(item, review.items.indexOf(item) + 1) : formatApprovalReviewList(review.items),
          meta: review.query.errorMessage ? `approval review · ${review.query.status}` : 'approval review · read only',
        });
        return;
      }

      if (intent === 'sensitive_refusal') {
        push({ role: 'hermes', text: "I can't help with that — it would mean viewing private data (SSN, full credit report, bank/tax docs, passwords, tokens, or secrets). I never read that kind of data. If you want an action taken with it, I can set up a private task request for an internal worker instead.", meta: 'firewall · refused' });
        return;
      }

      if (intent === 'privileged_action' || intent === 'public_action') {
        const task = proposeTask(content);
        if (!task) { push({ role: 'hermes', text: "I’m not sure what to set up — tell me the action and I’ll propose a task request.", meta: 'no task' }); return; }
        const action = makePendingAction(task, task.task_type, task.summary || content, `deterministic_${Date.now()}`);
        setPendingTask(task);
        setPendingAction(action);
        const forbids = task.forbidden_data.length ? task.forbidden_data.join(', ') : 'any private data';
        push({ role: 'hermes', text: `I can set up ${task.summary}\nI won’t do it directly, and I won’t access ${forbids}. Approve and I’ll file the task request — just say “approved”.`, meta: `proposed · ${task.assigned_worker_type}` });
        return;
      }

      if (intent === 'action_approval') {
        const task = pendingAction?.task ?? pendingTask ?? proposeTask(content);
        if (!task) { push({ role: 'hermes', text: "I don’t have a pending action to create. Tell me what you’d like set up.", meta: 'no pending task' }); return; }
        await fileTask(task, pendingAction ?? undefined);
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
        pending: pendingAction ? pendingAction.title : (pendingTask ? pendingTask.task_type : undefined),
        facts: `approvals_pending=${a.approvals}, queued_jobs=${a.jobs}, open_incidents=${a.incidents}, active_campaigns=${a.campaigns}`,
        report: report || undefined,
        taskStatus: taskStatus || undefined,
        pendingAction: pendingContext(pendingAction),
        history: safeHistoryForModel(),
      };
      const res = await hermesChat(content, mode, ctx);
      if (res.blocked) { push({ role: 'hermes', text: res.text, meta: 'firewall · refused' }); return; }
      const reply = res.configured ? res.text : CHAT_NOT_CONFIGURED_MSG;
      push({ role: 'hermes', text: reply, meta: res.configured ? 'chat provider' : 'chat not configured' });
      if (res.configured) {
        const inferred = inferPendingAction(content, reply);
        if (inferred) {
          setPendingAction(inferred);
          setPendingTask(inferred.task);
        }
      }
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
          {(pendingAction || pendingTask) && <span style={{ color: 'var(--text)' }}> · awaiting your approval for “{pendingAction?.title ?? pendingTask?.task_type}”</span>}
        </div>
        {showAware && (
          <div className="meta" style={{ marginTop: 8, borderTop: '1px solid var(--border)', paddingTop: 8 }}>
            pending approvals {aware.data.approvals} · queued jobs {aware.data.jobs} · open incidents {aware.data.incidents}
            {' '}· active campaigns {aware.data.campaigns} · publish receipts {aware.data.receipts}
            <span className="muted"> · firewall: Hermes reads public + internal_summary only; no publish/send/trade/deploy without approval</span>
          </div>
        )}
      </div>

      {/* Chat — bounded height; messages scroll INSIDE the card, composer pinned at the bottom. */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', height: 'min(64vh, 720px)', minHeight: 360 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
          <h3 style={{ margin: 0 }}>Hermes</h3>
          <span className="meta muted" style={{ fontSize: 11 }}>Hermes can recommend, but Ray approves risky actions.</span>
        </div>
        <div className="list" style={{ flex: 1, overflowY: 'auto', margin: '10px 0' }}>
          {messages.map((m, i) => (
            <div key={i} className={m.role === 'hermes' ? 'hermes' : 'item'}>
              <div className="body" style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>
              {m.meta && <div className="meta muted" style={{ marginTop: 4 }}>{m.role === 'hermes' ? 'Hermes' : 'You'} · {m.meta}</div>}
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>
        <div style={{ flexShrink: 0 }}>
          <textarea className="cmd" placeholder={PLACEHOLDER} value={text}
            onChange={(e) => setText(e.target.value)} onKeyDown={handleKey} rows={2} />
          <div style={{ marginTop: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="meta muted" style={{ fontSize: 11 }}>History persists across tabs. No publish/send/trade/deploy without your approval.</span>
            <button className="btn" onClick={send} disabled={busy || !text.trim()}>{busy ? 'Thinking…' : 'Send'}</button>
          </div>
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
  const { data: result } = useData<TableQueryResult>(() => listTableDetailed('system_health', { limit: 100 }), { ...emptyTableResult('system_health'), filter: 'limit=100 order=created_at.desc' });
  const data = result.data;
  const latest = new Map<string, Row>();
  for (const r of data) if (!latest.has(r.component)) latest.set(r.component, r);
  const rows = [...latest.values()];
  if (rows.length === 0) return <ConnectionEmpty result={result} what="health rows" />;
  return (
    <>
      <ConnectionLine result={result} />
      <div className="grid">{rows.map((r) => (
        <div className="card" key={r.component}><h3>{r.component.replaceAll('_', ' ')}</h3>
          <Pill status={r.status} /><div className="meta muted" style={{ marginTop: 8 }}>{r.summary}</div></div>
      ))}</div>
    </>
  );
}

// ── Agent Jobs (+ registry + runner) ──
export function AgentJobsView() {
  return (
    <DepartmentWorkspace
      config={DEPARTMENT_WORKSPACES.jobs}
      email={null}
      leading={(
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
      )}
    />
  );
}

// ── Approval Center ──
export function ApprovalCenter({ email }: { email: string | null }) {
  const { data: diag, reload } = useData<{ approvals: TableQueryResult; admin: AdminDiagnostic; reviews: ApprovalReviewItem[] }>(
    async () => {
      const [review, admin] = await Promise.all([loadPendingApprovalReviews(30), getAdminDiagnostic()]);
      return { approvals: review.query, reviews: review.items, admin };
    },
    {
      approvals: { ...emptyTableResult('approvals'), filter: 'limit=30 order=created_at.desc' },
      admin: { found: null, active: null, role: null, status: 'unknown', errorMessage: null },
      reviews: [],
    },
    email ?? 'anonymous',
  );
  const data = diag.approvals.data;
  const reviewById = new Map(diag.reviews.map((item) => [item.id, item]));
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

  const panel = <ApprovalDiagnosticPanel approvals={diag.approvals} admin={diag.admin} />;

  if (data.length === 0) return (
    <>
      {panel}
      <div className="empty">
        No approvals are visible for this session. Status: {statusLabel(diag.approvals.status)}.
        {diag.admin.status === 'not_found'
          ? ' The signed-in user is not mapped in admin_users, so admin-only RLS will hide approvals.'
          : diag.approvals.errorMessage ? ` Safe error: ${diag.approvals.errorMessage}` : ''}
      </div>
    </>
  );
  return (
    <>
      {panel}
      <div className="list">
        {data.map((a) => {
        const isSocial = a.item_type === 'social_publish' || a.payload?.platform === 'facebook';
        return (
        <div className="item" key={a.id}>
          <div className="t">{a.title ?? a.item_type} <Pill status={a.status} />{isSocial && <span className="pill info" style={{ marginLeft: 6 }}>facebook</span>}</div>
          <div className="meta">{a.lane} · {a.item_type} · {timeAgo(a.created_at)}{a.approved_by ? ` · by ${a.approved_by}` : ''}{isSocial ? ' · target: Clear Credentials (131069194210954)' : ''}</div>
          {a.summary && <div className="body">{a.summary}</div>}
          <ApprovalPreviewCard item={reviewById.get(String(a.id)) ?? null} approval={a} />
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
    </>
  );
}

function ApprovalDiagnosticPanel({ approvals, admin }: { approvals: TableQueryResult; admin: AdminDiagnostic }) {
  const adminFound = admin.found == null ? 'unknown' : admin.found ? 'yes' : 'no';
  const adminSuffix = admin.role ? ` · role ${admin.role}` : '';
  const err = approvals.errorMessage || admin.errorMessage;
  return (
    <div className="note" style={{ marginBottom: 12 }}>
      <div className="t">Approvals connection diagnostics</div>
      <div className="meta">Supabase configured: {approvals.supabaseConfigured ? 'yes' : 'no'} · Auth session: {approvals.authSessionPresent ? 'yes' : 'no'}</div>
      <div className="meta">User: {approvals.userEmail ?? 'none'} · id prefix: {approvals.userIdPrefix ?? 'none'}</div>
      <div className="meta">Admin mapping found: {adminFound}{admin.active != null ? ` · active ${admin.active ? 'yes' : 'no'}` : ''}{adminSuffix} · admin check {statusLabel(admin.status)}</div>
      <div className="meta">Table queried: {approvals.table} · filter: {approvals.filter} · count: {approvals.resultCount}</div>
      <div className="meta">Query status: {statusLabel(approvals.status)}{approvals.errorCategory ? ` · category ${statusLabel(approvals.errorCategory)}` : ''}</div>
      {err && <div className="meta">Safe error: {err}</div>}
    </div>
  );
}

function isImageUrl(url: string): boolean {
  return /\.(png|jpe?g|gif|webp|avif|svg)(\?.*)?$/i.test(url);
}

function isVideoUrl(url: string): boolean {
  return /\.(mp4|webm|mov|m4v)(\?.*)?$/i.test(url);
}

function ApprovalPreviewCard({ item, approval }: { item: ApprovalReviewItem | null; approval: Row }) {
  const p = item?.preview;
  const payload = approval.payload || {};
  const caption = p?.caption || p?.packageCopy || p?.body || payload.caption || payload.copy || payload.body || payload.text;
  const urls = [
    p?.imageUrl,
    p?.videoUrl,
    p?.thumbnailUrl,
    p?.assetUrl,
    p?.previewUrl,
    p?.landingPageUrl,
  ].filter((u): u is string => Boolean(u));
  const primaryUrl = urls[0];
  const platform = p?.platform || payload.platform;
  const target = p?.targetAccount || payload.account_name || payload.account_id;
  const cta = p?.cta || payload.cta || payload.cta_url;
  const risk = p?.riskNotes?.filter(Boolean) ?? [];
  const missing = p?.missingFields ?? [];
  const packageType = p?.packageType || (approval.item_type === 'publish_package' ? 'manual_publish_package' : null);

  return (
    <div className="card" style={{ marginTop: 10, padding: 12 }}>
      <h3 style={{ marginBottom: 6 }}>Preview</h3>
      <div className="meta">
        {platform ? `platform: ${platform}` : 'platform: unknown'}
        {target ? ` · target: ${target}` : ''}
        {packageType ? ` · package: ${packageType}` : ''}
        {p?.assetType ? ` · asset: ${p.assetType}` : ''}
        {p?.score ? ` · score: ${p.score}` : ''}
      </div>

      {caption ? (
        <div className="body" style={{ marginTop: 8, whiteSpace: 'pre-wrap' }}>{String(caption)}</div>
      ) : (
        <div className="empty" style={{ marginTop: 8 }}>Preview not available. Missing: {missing.join(', ') || 'caption/body/preview_url'}.</div>
      )}

      {cta && <div className="meta" style={{ marginTop: 8, color: 'var(--accent)' }}>CTA: {String(cta)}</div>}

      {primaryUrl && (
        <div style={{ marginTop: 10 }}>
          {isImageUrl(primaryUrl) && <img src={primaryUrl} alt="Approval preview" style={{ maxWidth: '100%', borderRadius: 8, border: '1px solid var(--border)' }} />}
          {isVideoUrl(primaryUrl) && <video src={primaryUrl} controls preload="metadata" style={{ maxWidth: '100%', borderRadius: 8, border: '1px solid var(--border)' }} />}
          {!isImageUrl(primaryUrl) && !isVideoUrl(primaryUrl) && <a className="btn ghost" href={primaryUrl} target="_blank" rel="noreferrer">Open preview</a>}
        </div>
      )}

      {p?.landingPageUrl && (
        <div style={{ marginTop: 8 }}>
          <a className="btn ghost" href={p.landingPageUrl} target="_blank" rel="noreferrer">Open landing page preview</a>
        </div>
      )}

      {risk.length > 0 && <div className="meta" style={{ marginTop: 8 }}>Risk/compliance: {risk.join(' · ')}</div>}
      {item?.recommendation && <div className="meta" style={{ marginTop: 8 }}>Hermes review note: {item.recommendation}</div>}
      {missing.length > 0 && caption && <div className="meta muted" style={{ marginTop: 8 }}>Missing preview fields: {missing.join(', ')}</div>}
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
    <DepartmentWorkspace
      config={DEPARTMENT_WORKSPACES.opportunities}
      email={null}
      leading={(
      <div className="note">Every idea is scored, not rejected: can it make money, become a tool, an offer, content, a lead source, or an affiliate path? What's the smallest low/no-cost test?</div>
      )}
    />
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
    <DepartmentWorkspace
      config={DEPARTMENT_WORKSPACES.creative}
      email={email}
      leading={(
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
      <div className="note">Design + publish pipeline (manual/jobs): <code>create_design_brief</code> → <code>generate_design_variants</code> → <code>score</code> → <code>compare</code> → <code>create_publish_readiness_package</code> → <code>review</code> → <code>export</code>. Credit/funding copy is compliance-gated (no guarantees); a package still needs approval before any real publish. No auto-publish, no external image/model calls.</div>
        </>
      )}
    />
  );
}

// ── Design Library (Day 9) ──
export function DesignLibrary() {
  return (
    <DepartmentWorkspace
      config={DEPARTMENT_WORKSPACES.design}
      email={null}
      leading={(
      <div className="note">Inspiration is stored as <b>reference only</b> — Nexus does not clone, import, or depend on external repos/assets. Deterministic; no external image/model calls.</div>
      )}
    />
  );
}

// ── Trading Lab ──
export function TradingLab() {
  return (
    <DepartmentWorkspace
      config={DEPARTMENT_WORKSPACES.trading}
      email={null}
      leading={(
        <div className="note">Paper/demo research only. Live and funded trading, broker execution, auto_executor, and schedulers are blocked. Backtest/report actions are disabled unless connected through the paper-only adapter.</div>
      )}
    />
  );
}

// ── SEO / Marketing OS ──
export function SeoOs() {
  return (
    <DepartmentWorkspace
      config={DEPARTMENT_WORKSPACES.seo}
      email={null}
      leading={(
      <div className="note">Hermes asks for Ray's real experience before finalizing important client-facing content. GSC / GA / DataForSEO are registered only (no OAuth/keys yet).</div>
      )}
    />
  );
}

// ── Model Router ──
export function ModelRouter() {
  const providers = useData<TableQueryResult>(() => listTableDetailed('model_providers', { order: 'provider_key', ascending: true }), { ...emptyTableResult('model_providers', 'provider_key'), filter: 'limit=50 order=provider_key.asc' });
  return (
    <>
      <div className="note">Free cloud models handle public/non-sensitive work. Sensitive client/credit/financial/secret data must use local/private or manual premium routes — never free cloud.</div>
      <SectionTitle count={providers.data.resultCount}>Providers</SectionTitle>
      {providers.data.data.length === 0 ? <ConnectionEmpty result={providers.data} what="model providers" /> : <div className="grid">{providers.data.data.map((p) => (
        <div className="card" key={p.id}><h3>{p.name}</h3><Pill status={p.enabled ? 'enabled' : 'registered'} />
          <div className="meta muted" style={{ marginTop: 6 }}>{p.provider_type} · privacy: {p.privacy_level} · env: {p.secret_env_name || '—'}</div></div>
      ))}</div>}
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
    <DepartmentWorkspace
      config={DEPARTMENT_WORKSPACES.ops}
      email={null}
      leading={(
      <div className="note">Detect/diagnose later. Safe repairs only; risky repairs require approval. Never auto-change code, deploy, trade, post, or expose secrets.</div>
      )}
    />
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
