import snapshot from '../../../public/runtime/nexus-mission-control.json';

type MissionControlSnapshot = typeof snapshot;

function tone(value: string) {
  const normalized = value.toUpperCase();
  return ['HEALTHY', 'CURRENT', 'PASS', 'NO_ACTION_REQUIRED', 'AVAILABLE'].includes(normalized) ? 'good' : ['STALE', 'DEGRADED', 'UNKNOWN', 'NOT_ENABLED', 'NOT_CONFIGURED'].includes(normalized) ? 'warn' : 'info';
}

function Status({ value }: { value: unknown }) {
  const text = String(value ?? 'UNKNOWN');
  return <span className={`hermes-mc-status ${tone(text)}`}>{text}</span>;
}

function Metric({ label, value }: { label: string; value: unknown }) {
  return <div className="hermes-mc-metric"><span>{label}</span><strong>{String(value ?? '—')}</strong></div>;
}

function SystemCard({ title, value, reason, updated, freshness }: { title: string; value: unknown; reason?: unknown; updated?: unknown; freshness?: unknown }) {
  return <article className="hermes-mc-card" data-testid={`mission-card-${title.toLowerCase().replace(/\s+/g, '-')}`}>
    <header className="hermes-mc-card-head"><h3>{title}</h3><Status value={value} /></header>
    <div className="hermes-mc-answers">
      <div><b>Status</b><span><Status value={value} /></span></div>
      <div><b>Last updated</b><span>{String(updated ?? 'Not recorded')}</span></div>
      <div><b>Freshness</b><span>{String(freshness ?? 'UNKNOWN')}</span></div>
      <div><b>Evidence</b><span>{String(reason ?? 'Canonical runtime artifact')}</span></div>
    </div>
  </article>;
}

export function HermesMissionControlV2() {
  const data = snapshot as MissionControlSnapshot;
  const systems = data.system as any;
  const activity = data.activity as any;
  const needsRay = data.needs_ray as any;
  const safety = data.safety as any;
  const optional = data.optional_integrations as any;
  const recent = (activity.recent ?? []) as Array<any>;
  const schedules = data.schedule as any;
  return (
    <section className="hermes-mc-v2" data-testid="hermes-mission-control-v2">
      <div className="hermes-mc-hero">
        <div>
          <div className="hermes-mc-eyebrow">Nexus operating surface · read-only canonical evidence</div>
          <h1>Mission Control</h1>
          <p>What Nexus is doing, what needs attention, what needs Ray, what happened, and what happens next.</p>
          <div className="hermes-mc-source">Generated {String(data.generated_at)} · {String(data.source)}</div>
        </div>
        <div className="hermes-mc-hero-state"><Status value={systems.overall_status} /><span>Read-only aggregation</span></div>
      </div>

      <div className="hermes-mc-overview">
        <Metric label="Overall health" value={systems.overall_status} />
        <Metric label="Needs Ray" value={needsRay.count} />
        <Metric label="Open work" value={data.work.open_work_orders} />
        <Metric label="Approvals" value={needsRay.pending_approvals} />
        <Metric label="P0 / P1 work" value={`${needsRay.p0_work} / ${needsRay.p1_work}`} />
        <Metric label="Core runtime" value={systems.core_runtime.status} />
      </div>

      <div className="hermes-mc-grid-v2">
        <SystemCard title="Core Runtime" value={systems.core_runtime.status} reason={systems.core_runtime.reason} updated={systems.core_runtime.last_updated} freshness={systems.core_runtime.freshness} />
        <SystemCard title="Active Operator" value={systems.active_operator.status} reason={systems.active_operator.reason} updated={systems.active_operator.last_updated} freshness={systems.active_operator.freshness} />
        <SystemCard title="Recovery Check" value={systems.recovery_check.status} reason={systems.recovery_check.reason} updated={systems.recovery_check.last_updated} freshness={systems.recovery_check.freshness} />
        <SystemCard title="Hermes Telegram" value={systems.hermes.status} reason={systems.hermes.reason} updated={systems.hermes.last_updated} freshness={systems.hermes.freshness} />

        <article className="hermes-mc-card" data-testid="mission-card-needs-ray">
          <header className="hermes-mc-card-head"><h3>NEEDS RAY</h3><Status value={needsRay.count ? 'PENDING' : 'CLEAR'} /></header>
          <div className="hermes-mc-metrics"><Metric label="Pending approvals" value={needsRay.pending_approvals} /><Metric label="P0 work" value={needsRay.p0_work} /><Metric label="P1 work" value={needsRay.p1_work} /><Metric label="Recovery escalations" value={needsRay.recovery_escalations} /></div>
          {!needsRay.count && <p className="hermes-mc-source">No governed decision or high-priority work currently requires Ray.</p>}
        </article>

        <article className="hermes-mc-card" data-testid="mission-card-schedules">
          <header className="hermes-mc-card-head"><h3>SCHEDULES</h3><Status value="OBSERVE" /></header>
          <div className="hermes-mc-worker-table">{Object.entries(schedules).map(([name, schedule]: [string, any]) => <div className="hermes-mc-worker-row" key={name}><b>{name.replace(/_/g, ' ')}</b><span>{schedule.next ?? schedule.cadence ?? 'Not recorded'}</span><span>{schedule.cadence}</span></div>)}</div>
        </article>

        <article className="hermes-mc-card" data-testid="mission-card-work-orders">
          <header className="hermes-mc-card-head"><h3>GOVERNED WORK</h3><Status value={`${data.work.open_work_orders} OPEN`} /></header>
          <div className="hermes-mc-metrics">{Object.entries(data.work.by_priority as Record<string, unknown>).map(([priority, count]) => <Metric key={priority} label={priority} value={count} />)}</div>
          <p className="hermes-mc-source">Canonical governed work-order store only. Mission Control creates no work.</p>
        </article>

        <article className="hermes-mc-card" data-testid="mission-card-activity">
          <header className="hermes-mc-card-head"><h3>RECENT ACTIVITY</h3><Status value="EVIDENCE" /></header>
          <div className="hermes-mc-worker-table">{recent.length ? recent.slice(0, 8).map((item) => <div className="hermes-mc-worker-row" key={`${item.receipt_id}-${item.timestamp}`}><b>{String(item.receipt_id)}</b><Status value={item.status} /><span>{String(item.timestamp ?? 'Not recorded')}</span></div>) : <span className="hermes-mc-source">No recent receipts recorded.</span>}</div>
        </article>

        <article className="hermes-mc-card" data-testid="mission-card-safety">
          <header className="hermes-mc-card-head"><h3>SAFETY AUTHORITY</h3><Status value="PRESERVED" /></header>
          <div className="hermes-mc-answers"><div><b>Live money</b><span>{safety.stripe_autonomy}</span></div><div><b>Arbitrary shell</b><span>{safety.arbitrary_shell}</span></div><div><b>External actions</b><span>{safety.external_actions}</span></div></div>
        </article>

        <article className="hermes-mc-card" data-testid="mission-card-optional-integrations">
          <header className="hermes-mc-card-head"><h3>OPTIONAL INTEGRATIONS</h3><Status value="SEPARATE READINESS" /></header>
          <div className="hermes-mc-worker-table">{Object.entries(optional).map(([name, value]: [string, any]) => <div className="hermes-mc-worker-row" key={name}><b>{name}</b><Status value={value.status} /><span>{value.reason}</span></div>)}</div>
        </article>
      </div>
    </section>
  );
}
