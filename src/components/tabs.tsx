import { useEffect, useState } from 'react';
import { isSupabaseConfigured } from '../lib/supabaseClient';
import { Card, Pill, SetupState, Empty, timeAgo } from './ui';
import { listRecentEvents } from '../services/events';
import { listJobs } from '../services/jobs';
import { listApprovals } from '../services/approvals';
import { listSocialAccounts, listSocialPosts } from '../services/social';
import { listSystemHealth } from '../services/health';
import type {
  NexusEvent, AgentJob, Approval, SocialAccount, SocialPost, SystemHealth,
} from '../types/db';

function useAsync<T>(fn: () => Promise<T>, fallback: T): T {
  const [v, setV] = useState<T>(fallback);
  useEffect(() => {
    let alive = true;
    fn().then((r) => { if (alive) setV(r); }).catch(() => {});
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return v;
}

function healthFor(rows: SystemHealth[], component: string): string {
  return rows.find((r) => r.component === component)?.status ?? 'unknown';
}

// ── Overview ──
export function Overview() {
  if (!isSupabaseConfigured) return <SetupState what="System overview" />;
  const events = useAsync<NexusEvent[]>(() => listRecentEvents(1), []);
  const health = useAsync<SystemHealth[]>(listSystemHealth, []);
  const approvals = useAsync<Approval[]>(() => listApprovals(50, 'pending'), []);
  const lanes = ['communication', 'monetization', 'automation', 'social', 'trading'];
  return (
    <div className="grid">
      {lanes.map((l) => (
        <Card key={l} title={l}>
          <Pill status={healthFor(health, l)} />
        </Card>
      ))}
      <Card title="Last event">
        {events[0] ? <div>{events[0].title ?? events[0].action}<div className="meta">{timeAgo(events[0].created_at)}</div></div> : <Empty what="events" />}
      </Card>
      <Card title="Open approvals">
        <div className="big">{approvals.length}</div>
      </Card>
    </div>
  );
}

// ── Communication ──
export function Communication() {
  if (!isSupabaseConfigured) return <SetupState what="Communication status" />;
  const health = useAsync<SystemHealth[]>(listSystemHealth, []);
  const events = useAsync<NexusEvent[]>(() => listRecentEvents(15, 'communication'), []);
  return (
    <>
      <div className="grid">
        <Card title="Hermes"><Pill status={healthFor(health, 'hermes')} /></Card>
        <Card title="TheChoseone"><Pill status={healthFor(health, 'telegram')} /></Card>
        <Card title="Telegram guard"><Pill status="ok" label="dedup + rate active" /></Card>
      </div>
      <div className="section-title">Recent communication events</div>
      <EventList events={events} />
    </>
  );
}

// ── Monetization ──
export function Monetization() {
  if (!isSupabaseConfigured) return <SetupState what="Monetization status" />;
  const events = useAsync<NexusEvent[]>(() => listRecentEvents(15, 'monetization'), []);
  return (
    <>
      <div className="grid">
        <Card title="$97 offer"><div className="big">Starter Review</div><div className="meta">ladder $97 / $197 / $297</div></Card>
        <Card title="Next money action"><div className="muted">Approve a queued post → publish → $97 funnel</div></Card>
      </div>
      <div className="section-title">Recent monetization events</div>
      <EventList events={events} />
    </>
  );
}

// ── Automation ──
export function Automation() {
  if (!isSupabaseConfigured) return <SetupState what="Automation jobs" />;
  const jobs = useAsync<AgentJob[]>(() => listJobs(20), []);
  const health = useAsync<SystemHealth[]>(listSystemHealth, []);
  return (
    <>
      <div className="grid">
        <Card title="Jobs"><div className="big">{jobs.length}</div></Card>
        <Card title="Failed jobs"><div className="big">{jobs.filter((j) => j.status === 'failed').length}</div></Card>
        <Card title="System health"><Pill status={healthFor(health, 'dashboard')} /></Card>
      </div>
      <div className="section-title">Agent jobs</div>
      <div className="list">
        {jobs.length === 0 ? <Empty what="jobs" /> : jobs.map((j) => (
          <div className="item" key={j.id}>
            <div><b>{j.job_type}</b> <Pill status={j.status} /></div>
            <div className="meta">{j.lane} · {timeAgo(j.created_at)}{j.error ? ` · ${j.error}` : ''}</div>
          </div>
        ))}
      </div>
    </>
  );
}

// ── Social ──
export function Social() {
  if (!isSupabaseConfigured) return <SetupState what="Social accounts + queue" />;
  const accounts = useAsync<SocialAccount[]>(listSocialAccounts, []);
  const posts = useAsync<SocialPost[]>(() => listSocialPosts(20), []);
  return (
    <>
      <div className="section-title">Accounts</div>
      <div className="list">
        {accounts.length === 0 ? <Empty what="accounts" /> : accounts.map((a) => (
          <div className="item" key={a.id}>
            <div><b>{a.account_name}</b> ({a.platform}) <Pill status={a.publish_enabled ? 'ok' : 'unknown'} label={a.publish_enabled ? 'publish on' : 'publish off'} /></div>
            <div className="meta">{a.account_id}{a.username ? ` · @${a.username}` : ''} · token via {a.token_env_key} (not stored)</div>
          </div>
        ))}
      </div>
      <div className="section-title">Queue</div>
      <div className="list">
        {posts.length === 0 ? <Empty what="queued posts" /> : posts.map((p) => (
          <div className="item" key={p.id}>
            <div><Pill status={p.status} /> {p.score != null ? `· ${p.score}/100` : ''}</div>
            <div className="meta">{(p.content || '').slice(0, 120)}</div>
          </div>
        ))}
      </div>
    </>
  );
}

// ── Trading ──
export function Trading() {
  if (!isSupabaseConfigured) return <SetupState what="Trading signals + demo trades" />;
  return (
    <div className="grid">
      <Card title="Execution"><Pill status="unknown" label="disabled until Day 6" /></Card>
      <Card title="Demo loss cap"><div className="big">$0 / $500</div></Card>
      <Card title="Signals"><div className="muted">Research only at first; signal-router ported later.</div></Card>
    </div>
  );
}

// ── Approvals / Proof Log ──
export function Approvals() {
  if (!isSupabaseConfigured) return <SetupState what="Approvals + proof log" />;
  const approvals = useAsync<Approval[]>(() => listApprovals(25), []);
  const events = useAsync<NexusEvent[]>(() => listRecentEvents(25), []);
  return (
    <>
      <div className="section-title">Approvals</div>
      <div className="list">
        {approvals.length === 0 ? <Empty what="approvals" /> : approvals.map((a) => (
          <div className="item" key={a.id}>
            <div><b>{a.title ?? a.item_type}</b> <Pill status={a.status} /></div>
            <div className="meta">{a.lane} · {timeAgo(a.created_at)} · approve/reject/revise wired Day 2</div>
          </div>
        ))}
      </div>
      <div className="section-title">Proof Log (nexus_events)</div>
      <EventList events={events} />
    </>
  );
}

function EventList({ events }: { events: NexusEvent[] }) {
  if (events.length === 0) return <Empty what="events" />;
  return (
    <div className="list">
      {events.map((e) => (
        <div className="item" key={e.id}>
          <div><Pill status={e.status} /> <b>{e.title ?? e.action}</b></div>
          <div className="meta">{e.lane} · {e.source ?? 'system'} · {timeAgo(e.created_at)}{e.summary ? ` · ${e.summary}` : ''}</div>
        </div>
      ))}
    </div>
  );
}
