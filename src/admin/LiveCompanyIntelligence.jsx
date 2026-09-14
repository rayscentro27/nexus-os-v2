import React, { useEffect, useState } from 'react'
import snapshot from '../data/adminCompanyState.json'

const statusClass = (value) => String(value || '').toLowerCase().replaceAll('_', '-')
function Card({ label, value, note }) { return <div className="glass2 admin-live-card"><small>{label}</small><strong>{value}</strong>{note && <span>{note}</span>}</div> }
function Section({ title, children }) { return <section className="glass admin-live-section"><div className="panel-head"><h3>{title}</h3></div>{children}</section> }

export default function LiveCompanyIntelligence() {
  const [state, setState] = useState(snapshot)
  const [refreshed, setRefreshed] = useState(snapshot.generated_at)
  useEffect(() => {
    let cancelled = false
    const load = () => fetch('/admin-company-state.json', { cache: 'no-store' }).then(r => r.ok ? r.json() : null).then(next => { if (!cancelled && next?.provenance) { setState(next); setRefreshed(next.generated_at) } }).catch(() => {})
    load(); const timer = window.setInterval(load, 30000)
    return () => { cancelled = true; window.clearInterval(timer) }
  }, [])
  const s = state
  return <section className="page active simple-page"><PageTitle title="Live Company Intelligence" sub={`Canonical operating read model · refreshed ${refreshed}`} />
    <div className="metrics-grid admin-live-metrics">
      <Card label="Nexus operating status" value={s.system_health} note="runtime evidence" />
      <Card label="Research" value={s.research.health} note={`${s.research.current_lane} · next ${s.research.next_lane}`} />
      <Card label="Opportunities" value={s.opportunities.active} note={`${s.opportunities.alpha_reviews} Alpha reviews`} />
      <Card label="Handoffs" value={`${s.handoffs.active} active · ${s.handoffs.waiting} waiting`} note={`${s.handoffs.completed} completed`} />
      <Card label="Departments" value={`${s.departments.active} active · ${s.departments.ready} ready`} note={`${s.departments.legitimately_idle} legitimately idle`} />
      <Card label="Ray decisions" value={s.ray_decisions.count} note="routine machine work excluded" />
    </div>
    <Section title="Intelligence supply chain"><div className="admin-live-pipeline">{s.pipeline.map((item, i) => <React.Fragment key={item.name}><div className={`admin-live-stage ${statusClass(item.status)}`}><b>{item.name}</b><span>{item.status}</span></div>{i < s.pipeline.length - 1 && <span className="admin-live-arrow">→</span>}</React.Fragment>)}</div></Section>
    <div className="admin-live-columns">
      <Section title="Research & recent findings"><p className="nx-muted">Current lane: <b>{s.research.current_lane}</b> · next: <b>{s.research.next_lane}</b></p><p className="nx-muted">Last real run: {s.research.last_real_run} · YouTube {s.research.youtube} · backfill {s.research.backfill}</p>{s.recent_findings.map(x => <div className="admin-live-row" key={x.title}><b>{x.title}</b><span>{x.lane} · Alpha {x.alpha} · {x.owner} · {x.state}</span></div>)}</Section>
      <Section title="YouTube intelligence"><p className="nx-muted">{s.youtube.active_monitored}/{s.youtube.total_channels} monitored · {s.youtube.channels_with_backfill} with backfill</p><p className="nx-muted">Older reviewed: {s.youtube.older_videos_reviewed} · transcripts: {s.youtube.transcripts_reviewed} · validated claims: {s.youtube.claims_validated}</p><p className="nx-muted">Opportunities: {s.youtube.opportunities_created} · handoffs: {s.youtube.handoffs_created}</p></Section>
      <Section title="SEO / current intelligence"><p className="nx-muted">{s.seo.status} · last scan {s.seo.last_scan_at}</p><p className="nx-muted">Signals: {s.seo.signals_found} · opportunities: {s.seo.opportunities_created} · experiments: {s.seo.experiments_created}</p><p className="nx-muted">Search volume: {s.seo.search_volume} · CPC: {s.seo.cpc}</p></Section>
    </div>
    <Section title="Campaigns"><div className="admin-live-campaign-grid">{s.campaign_list.map(x => <div className="nx-soft admin-live-campaign" key={x.name}><b>{x.name}</b><span>{x.status} · {x.department}</span><small>{x.next}</small></div>)}</div></Section>
    <Section title="Department utilization"><div className="admin-live-departments">{s.departments_list.map(x => <div className="admin-live-dept" key={x.name}><b>{x.name}</b><span className={`admin-live-badge ${statusClass(x.status)}`}>{x.status}</span><small>{x.work}</small></div>)}</div></Section>
    <Section title="Next machine action"><p className="admin-live-next">{s.next_machine_action}</p><p className="nx-muted">No Ray decision is currently required. Human/external gates remain persisted separately.</p></Section>
  </section>
}

function PageTitle({ title, sub }) { return <div className="page-title"><div><div className="eyebrow">NEXUS / ADMIN</div><h2>{title}</h2><p>{sub}</p></div></div> }
