import { useState } from 'react';
import { listTable, type Row } from '../services/db';
import { createEvent, createJob, decideApproval } from '../lib/ledger';
import { Card, Stat, Pill, Empty, SectionTitle, timeAgo, useData } from './ui';

// ── reusable list ──
function DataList({ table, render, what, order }: {
  table: string; what: string; order?: string;
  render: (r: Row) => React.ReactNode;
}) {
  const { data } = useData<Row[]>(() => listTable(table, { order }), []);
  if (data.length === 0) return <Empty what={what} />;
  return <div className="list">{data.map((r) => <div className="item" key={r.id}>{render(r)}</div>)}</div>;
}

// ── 1 + Command Center (Hermes plain-language operator) ──
const CMD_CATEGORIES: Record<string, string> = {
  system_status: 'Summarize current system status',
  monetization_review: 'Review monetization opportunities',
  opportunity_research: 'Research a new money opportunity',
  creative_campaign: 'Plan a creative campaign',
  approval_review: "What's waiting for my approval?",
  trading_research: 'Research a trading strategy',
  seo_recommendation: 'Find SEO/content opportunities',
  ops_diagnostic: 'Run an ops diagnostic',
};

function classify(text: string): string {
  const t = text.toLowerCase();
  if (/approve|approval|review queue/.test(t)) return 'approval_review';
  if (/money|monetiz|offer|revenue|\$/.test(t)) return 'monetization_review';
  if (/opportunit|idea|repo|video|transcript/.test(t)) return 'opportunity_research';
  if (/post|reel|campaign|creative|content|caption/.test(t)) return 'creative_campaign';
  if (/trade|trading|strategy|backtest|oanda/.test(t)) return 'trading_research';
  if (/seo|keyword|search console|rank/.test(t)) return 'seo_recommendation';
  if (/ops|incident|health|broken|fail/.test(t)) return 'ops_diagnostic';
  return 'system_status';
}

export function CommandCenter({ email }: { email: string | null }) {
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const events = useData<Row[]>(() => listTable('nexus_events', { limit: 8 }), []);
  const jobs = useData<Row[]>(() => listTable('agent_jobs', { limit: 6 }), []);
  const [last, setLast] = useState<{ category: string; reply: string } | null>(null);

  async function send(t?: string) {
    const content = (t ?? text).trim();
    if (!content || busy) return;
    setBusy(true);
    const category = classify(content);
    const jobId = await createJob({ lane: 'communication', job_type: `hermes_${category}`, status: 'stubbed', input: { command: content, requested_by: email } });
    await createEvent({ lane: 'communication', action: 'hermes_command', status: 'pending', title: content.slice(0, 80), summary: `Routed to ${category}`, job_id: jobId, payload: { category } });
    setLast({
      category,
      reply: `Got it. I read this as a **${category.replace('_', ' ')}** request. I've queued a job (no external action taken). `
        + `When the executor + model route for this task type are wired, I'll do the work and report receipts here. `
        + `I won't pretend work happened — right now this is a queued job, not a finished result.`,
    });
    setText(''); setBusy(false);
    events.reload(); jobs.reload();
  }

  const aware = useData<{ approvals: number; jobs: number; incidents: number; campaigns: number; receipts: number }>(
    async () => ({
      approvals: (await listTable('approvals', { eq: ['status', 'pending'], limit: 200 })).length,
      jobs: (await listTable('agent_jobs', { eq: ['status', 'queued'], limit: 200 })).length,
      incidents: (await listTable('ops_incidents', { eq: ['status', 'open'], limit: 200 })).length,
      campaigns: (await listTable('creative_campaigns', { eq: ['status', 'active'], limit: 200 })).length,
      receipts: (await listTable('social_publish_receipts', { limit: 200 })).length,
    }), { approvals: 0, jobs: 0, incidents: 0, campaigns: 0, receipts: 0 });

  return (
    <>
      <div className="note">Hermes is Ray's private advisor. It can recommend and queue work, but it cannot publish, send, trade, or deploy without approvals and runner gates. Client agents are separate: Supabase-approved-knowledge only — no web, no external API by default.</div>
      <SectionTitle>Hermes system awareness</SectionTitle>
      <div className="grid">
        <Stat title="Pending approvals" value={aware.data.approvals} />
        <Stat title="Queued jobs" value={aware.data.jobs} />
        <Stat title="Open incidents" value={aware.data.incidents} />
        <Stat title="Active campaigns" value={aware.data.campaigns} />
        <Stat title="Publish receipts" value={aware.data.receipts} />
        <Stat title="Safety" value="gated" sub="no publish/send/trade/deploy without approval" />
      </div>
      <div className="card">
        <h3>Hermes — plain-language operator</h3>
        <textarea className="cmd" placeholder="Tell Hermes what you want in normal words… e.g. “what should we do to make money this week?”"
          value={text} onChange={(e) => setText(e.target.value)} />
        <div className="chips">
          {Object.entries(CMD_CATEGORIES).map(([k, label]) => (
            <button className="chip" key={k} onClick={() => send(label)} disabled={busy}>{label}</button>
          ))}
        </div>
        <button className="btn" onClick={() => send()} disabled={busy || !text.trim()}>{busy ? 'Routing…' : 'Send to Hermes'}</button>
        {last && (
          <div className="hermes">
            <Pill status="info" label={last.category.replace('_', ' ')} />
            <div className="body" style={{ marginTop: 6 }}>{last.reply}</div>
            <div className="meta" style={{ marginTop: 6 }}>Safety: queued a job + ledger event only. No publish, no trade, no send.</div>
          </div>
        )}
      </div>

      <SectionTitle>Recent jobs</SectionTitle>
      {jobs.data.length === 0 ? <Empty what="jobs" /> : (
        <div className="list">{jobs.data.map((j) => (
          <div className="item" key={j.id}><div className="t">{j.job_type} <Pill status={j.status} /></div>
            <div className="meta">{j.lane} · {timeAgo(j.created_at)}</div></div>
        ))}</div>
      )}

      <SectionTitle>Proof log</SectionTitle>
      {events.data.length === 0 ? <Empty what="events" /> : (
        <div className="list">{events.data.map((e) => (
          <div className="item" key={e.id}><div className="t"><Pill status={e.status} /> {e.title ?? e.action}</div>
            <div className="meta">{e.lane} · {e.source} · {timeAgo(e.created_at)}</div></div>
        ))}</div>
      )}
    </>
  );
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
      <div className="note">Run order (manual scripts): <code>seed_day4_creative_studio.py</code> → <code>generate_campaign_assets.py</code> → <code>score_creative_assets.py</code> → <code>create_creative_approvals.py</code> → <code>create_social_post_drafts.py</code>. Frontend buttons create jobs/ledger rows only — never publish.</div>
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
      <SectionTitle>Routes</SectionTitle>
      <DataList table="model_routes" what="routes" order="route_key" render={(r) => (
        <><div className="t">{r.route_key} <Pill status={r.sensitive_data_allowed ? 'ok' : 'registered'} label={r.sensitive_data_allowed ? 'sensitive ok' : 'public only'} /></div>
          <div className="meta">{r.task_type} → {r.primary_provider_key} · policy {r.policy}</div></>
      )} />
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

// ── Events Feed ──
export function EventsFeed() {
  return (
    <DataList table="nexus_events" what="events" render={(e) => (
      <><div className="t"><Pill status={e.status} /> {e.title ?? e.action}</div>
        <div className="meta">{e.lane} · {e.source} · {timeAgo(e.created_at)}{e.summary ? ` · ${e.summary}` : ''}</div></>
    )} />
  );
}
