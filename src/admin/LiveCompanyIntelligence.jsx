import React, { useEffect, useState } from 'react'
import {
  Activity, ArrowUpRight, BarChart3, Bell, BookOpen, Bot, CheckSquare, ChevronRight,
  Clock3, FolderKanban, FolderPlus, LayoutDashboard, LifeBuoy, ListTodo,
  MessageSquare, Radar, Search, Settings, Sparkles, Target, Upload, UserPlus,
  Users,
} from 'lucide-react'
import snapshot from '../data/adminCompanyState.json'
import { supabase } from '../lib/supabaseClient'
import AdminSurfacePage from './AdminSurfacePage'
import './liveCompanyIntelligence.css'

const iconMap = {
  dashboard: LayoutDashboard, ai: Sparkles, projects: FolderKanban, tasks: CheckSquare,
  knowledge: BookOpen, analytics: BarChart3, automation: Bot, team: Users,
  settings: Settings, support: LifeBuoy, search: Search, notifications: Bell,
  newProject: FolderPlus, askAi: MessageSquare, createTask: ListTodo,
  research: Radar, upload: Upload, invite: UserPlus, opportunity: Target,
}

function Icon({ name, size = 16, strokeWidth = 1.8 }) {
  const Component = iconMap[name] || Activity
  return <Component size={size} strokeWidth={strokeWidth} aria-hidden="true" />
}

function CommandMetric({ icon, label, value, note, tone = 'cyan' }) {
  return <article className={`live-command-metric tone-${tone}`}>
    <div className="live-command-metric-icon"><Icon name={icon} size={15} /></div>
    <div className="live-command-metric-copy"><span>{label}</span><strong>{value}</strong><small>{note}</small></div>
  </article>
}

function CommandPanel({ title, eyebrow, action, children, className = '' }) {
  return <section className={`live-command-panel ${className}`}>
    <div className="live-command-panel-head"><div><span className="live-command-eyebrow">{eyebrow || 'LIVE OPERATIONS'}</span><h3>{title}</h3></div>{action && <a href={action.href}>{action.label}<ArrowUpRight size={13} /></a>}</div>
    {children}
  </section>
}

function DetailRow({ icon, title, detail, meta, tone = 'cyan' }) {
  return <div className="live-command-detail-row"><span className={`live-command-row-icon tone-${tone}`}><Icon name={icon} size={14} /></span><div><strong>{title}</strong><small>{detail}</small></div>{meta && <em>{meta}</em>}</div>
}

export default function LiveCompanyIntelligence({ surface = null }) {
  const [state, setState] = useState(snapshot)
  const [refreshed, setRefreshed] = useState(snapshot.generated_at)

  useEffect(() => {
    let cancelled = false
    const load = () => supabase?.auth.getSession().then(({ data }) => {
      const token = data.session?.access_token
      return token ? fetch('/.netlify/functions/admin-live-state', { cache: 'no-store', headers: { Authorization: `Bearer ${token}` } }) : null
    }).then(response => response?.ok ? response.json() : null).then(next => {
      if (!cancelled && next?.provenance) { setState(next); setRefreshed(next.generated_at) }
    }).catch(() => {})
    load()
    const timer = window.setInterval(load, 30000)
    return () => { cancelled = true; window.clearInterval(timer) }
  }, [])

  const s = state
  const route = (path) => ({ href: `#/` + path, label: 'View all' })
  const metrics = [
    ['dashboard', 'Nexus status', s.system_health, 'runtime evidence', 'teal'],
    ['research', 'Research pulse', s.research.health, `${s.research.current_lane} · next ${s.research.next_lane}`, 'cyan'],
    ['opportunity', 'Opportunities', s.opportunities.active, `${s.opportunities.alpha_reviews} Alpha reviews`, 'cyan'],
    ['automation', 'Handoffs', s.handoffs.active, `${s.handoffs.waiting} waiting · ${s.handoffs.completed} completed`, 'teal'],
    ['team', 'Departments', s.departments.active, `${s.departments.ready} ready · ${s.departments.legitimately_idle} idle`, 'purple'],
    ['notifications', 'Ray decisions', s.ray_decisions.count, 'routine machine work excluded', s.ray_decisions.count ? 'orange' : 'amber'],
    ['research', 'YouTube', `${s.youtube.active_monitored}/${s.youtube.total_channels}`, `${s.youtube.older_videos_reviewed} older videos reviewed`, 'cyan'],
    ['analytics', 'SEO signals', s.seo.signals_found, `${s.seo.opportunities_created} opportunities · ${s.seo.experiments_created} experiments`, 'purple'],
  ]

  return <main className="live-command-page">
    <aside className="live-command-sidebar">
      <div className="live-command-brand"><div className="live-command-brand-lockup"><img className="live-command-brand-mark" src="/brand/GoClearMark.svg" alt="" /><span className="live-command-brand-wordmark"><img src="/brand/GoClearLogo.svg" alt="GoClear" /></span></div><span>NEXUS OS</span></div>
      <nav aria-label="Admin navigation">
        <a className={!surface ? 'active' : ''} href="#/live-intelligence"><Icon name="dashboard" />Dashboard</a>
        <a className={surface === 'ai-command' ? 'active' : ''} href="#/ai-command"><Icon name="ai" />AI Command</a><a className={surface === 'projects' ? 'active' : ''} href="#/projects"><Icon name="projects" />Projects</a>
        <a className={surface === 'tasks' ? 'active' : ''} href="#/tasks"><Icon name="tasks" />Tasks</a><a className={surface === 'knowledge' ? 'active' : ''} href="#/knowledge"><Icon name="knowledge" />Knowledge</a>
        <a className={surface === 'analytics' ? 'active' : ''} href="#/analytics"><Icon name="analytics" />Analytics</a><a className={surface === 'automation' ? 'active' : ''} href="#/automation"><Icon name="automation" />Automation</a>
        <a className={surface === 'team' ? 'active' : ''} href="#/team"><Icon name="team" />Team</a><a className={surface === 'settings' ? 'active' : ''} href="#/settings"><Icon name="settings" />Settings</a>
        <a className={surface === 'support' ? 'active' : ''} href="#/support"><Icon name="support" />Support</a>
      </nav>
      <div className="live-command-promo"><img src="/creative/admin-artifacts/mountain-promo.png" alt="Mountain landscape" /><div className="live-command-promo-overlay"><strong>A clearer<br />tomorrow.</strong><small>Smarter tools. Clearer decisions.</small><a href="#/live-intelligence">View now <ChevronRight size={13} /></a></div></div>
    </aside>

    <div className="live-command-main">
      <header className="live-command-topbar"><div className="live-command-search"><Icon name="search" size={14} /><span>Search projects, knowledge, people, or anything</span></div><div className="live-command-system"><i />All Systems Operational</div><span className="live-command-market">S&amp;P 5,472.83&nbsp;&nbsp;↗ +1.26%</span><button className="live-command-avatar" aria-label="Ray profile">R</button></header>

      <div className="live-command-content">
        <section className="live-command-brand-strip"><img src="/creative/admin-artifacts/mountain-top.png" alt="Mountain landscape" /><div><span>Discipline today.</span><strong>A clearer tomorrow.</strong></div><b>SMARTER BUSINESS. A CLEARER TOMORROW.</b></section>
        {surface ? <div className="live-command-surface"><AdminSurfacePage surface={surface} /></div> : <>
        <div className="live-command-heading"><div><span className="live-command-eyebrow">NEXUS / ADMIN COMMAND CENTER</span><h1>Good morning, Ray</h1><p>Clear insights. Stronger decisions. A clearer tomorrow.</p></div><small>Live read model · refreshed {refreshed}</small></div>

        <div className="live-command-metrics">{metrics.map(([icon, label, value, note, tone]) => <CommandMetric key={label} icon={icon} label={label} value={value} note={note} tone={tone} />)}</div>

        <div className="live-command-hero-grid"><section className="live-command-hero"><img src="/creative/admin-artifacts/mountain-main-clean4.png" alt="Mountain landscape" /><div className="live-command-hero-copy"><span className="live-command-eyebrow">GOCLEAR NEXUS OS</span><h2>Smarter Decisions.<br />A Clearer Tomorrow.</h2><p>Turn intelligence into opportunity. Nexus helps you move faster, see further, and build what comes next.</p><a href="#/research" className="live-command-primary"><Sparkles size={14} /> Explore intelligence</a></div><div className="live-command-hero-bullets"><span><Target size={13} /> More insight.</span><span><CheckSquare size={13} /> Less noise.</span><span><ArrowUpRight size={13} /> Greater impact.</span></div></section><CommandPanel title="What Matters Next" eyebrow="RAY'S PRIORITIES" className="live-command-priorities"><ol>{(s.pipeline || []).slice(0, 4).map((item, i) => <li key={item.name}><b>{i + 1}</b><div><strong>{item.name}</strong><small>{item.status}</small></div></li>)}</ol></CommandPanel></div>

        <div className="live-command-three-grid"><CommandPanel title="Recent Activity" action={route('work')}><div>{(s.recent_findings || []).slice(0, 5).map((item, i) => <DetailRow key={item.title} icon={i % 2 ? 'automation' : 'research'} title={item.title} detail={`${item.lane} · Alpha ${item.alpha} · ${item.owner}`} meta={item.state} tone={i % 2 ? 'teal' : 'cyan'} />)}</div></CommandPanel><CommandPanel title="Quick Actions" eyebrow="SHORTCUTS"><div className="live-command-actions"><a href="#/projects"><Icon name="newProject" /><span><strong>New Project</strong><small>Start an initiative</small></span></a><a href="#/ai-command"><Icon name="askAi" /><span><strong>Ask AI</strong><small>Get instant insights</small></span></a><a href="#/tasks"><Icon name="createTask" /><span><strong>Create Task</strong><small>Add to your team</small></span></a><a href="#/knowledge"><Icon name="upload" /><span><strong>Upload File</strong><small>Analyze with AI</small></span></a><a href="#/research"><Icon name="research" /><span><strong>Research Market</strong><small>Deep market analysis</small></span></a><a href="#/team"><Icon name="invite" /><span><strong>Invite Team Member</strong><small>Grow your team</small></span></a></div></CommandPanel><CommandPanel title="Research Pipeline" action={route('research')}><div className="live-command-pipeline-stats"><b>{s.research.runs_24h || 0}<small>Total Research</small></b><b>{s.research.in_progress || 0}<small>In Progress</small></b><b>{s.research.under_review || 0}<small>Under Review</small></b><b>{s.research.completed_24h || 0}<small>Completed</small></b></div><div className="live-command-bars">{(s.pipeline || []).slice(0, 5).map(item => <div key={item.name}><span>{item.name}</span><i><em style={{ width: `${item.progress || 48}%` }} /></i></div>)}</div></CommandPanel></div>

        <div className="live-command-three-grid"><CommandPanel title="Opportunities Snapshot" action={route('opportunity')}><div className="live-command-opportunity"><div className="live-command-ring"><strong>{s.opportunities.active}</strong><small>Opportunities</small></div><div className="live-command-legend"><span><i className="cyan" />High potential</span><span><i className="teal" />Validated / moving</span><span><i className="purple" />Early stage</span><span><i className="muted" />Follow-up required</span></div><div className="live-command-value"><strong>{s.opportunities.total_value || '—'}</strong><small>Total potential value</small></div></div></CommandPanel><CommandPanel title="Department Utilization"><div className="live-command-bars departments">{(s.departments_list || []).slice(0, 5).map(item => <div key={item.name}><span>{item.name}</span><i><em style={{ width: `${item.utilization || item.progress || 58}%` }} /></i><small>{item.status}</small></div>)}</div></CommandPanel><CommandPanel title="Ray Decision Queue" action={route('rayreview')}><div>{(s.ray_decisions.items || []).slice(0, 5).map(item => <DetailRow key={item.title || item} icon="notifications" title={item.title || item} detail="Review required" meta="Open" tone="amber" />)}{!s.ray_decisions.items?.length && <div className="live-command-empty"><CheckSquare size={20} /><strong>No decisions waiting</strong><span>Routine machine work is continuing.</span></div>}</div></CommandPanel></div>

        <div className="live-command-footer-grid"><CommandPanel title="Handoffs & Campaigns" action={route('campaigns')}><div className="live-command-mini-grid">{(s.campaign_list || []).slice(0, 4).map(item => <div key={item.name}><strong>{item.name}</strong><small>{item.status} · {item.department}</small></div>)}</div></CommandPanel><CommandPanel title="YouTube Intelligence" action={route('youtube')}><p className="live-command-copy">{s.youtube.active_monitored}/{s.youtube.total_channels} channels monitored. {s.youtube.transcripts_reviewed} transcripts reviewed and {s.youtube.claims_validated} claims validated.</p></CommandPanel><CommandPanel title="SEO / Current Intelligence" action={route('seo')}><p className="live-command-copy">{s.seo.status} · {s.seo.signals_found} signals found · {s.seo.search_volume || 'Current demand'}.</p></CommandPanel></div>
        <CommandPanel title="Next machine action" eyebrow="AUTONOMOUS CONTINUATION" className="live-command-next"><p>{s.next_machine_action}</p><span><Clock3 size={13} /> Nexus continues independently; Ray decisions are shown only when required.</span></CommandPanel>
        </>}
      </div>
    </div>
  </main>
}
