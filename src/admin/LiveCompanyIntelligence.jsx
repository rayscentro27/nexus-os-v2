import React, { useEffect, useState } from 'react'
import {
  Activity, ArrowUpRight, BarChart3, Bell, BookOpen, Bot, CheckSquare, ChevronRight,
  Clock3, FolderKanban, FolderPlus, LayoutDashboard, LifeBuoy, ListTodo,
  MessageSquare, Radar, Search, Settings, Sparkles, Target, Upload, UserPlus,
  Users, TrendingUp, Layers3, ShieldCheck,
} from 'lucide-react'
import snapshot from '../data/adminCompanyState.json'
import reviewQueue from '../data/adminResearchReviewQueue.json'
import { supabase } from '../lib/supabaseClient'
import AdminSurfacePage from './AdminSurfacePage'
import { AutomationPage, AnalyticsPage, DepartmentsPage, KnowledgePage, SettingsPage, SupportPage, TasksPage } from './CanonicalAdminPages'
import NexusAgentConversation from '../components/NexusAgentConversation'
import { tradingLabData } from '../data/tradingLabData'
import './liveCompanyIntelligence.css'

const iconMap = {
  dashboard: LayoutDashboard, ai: Sparkles, projects: FolderKanban, tasks: CheckSquare,
  knowledge: BookOpen, analytics: BarChart3, automation: Bot, team: Users,
  settings: Settings, support: LifeBuoy, search: Search, notifications: Bell,
  newProject: FolderPlus, askAi: MessageSquare, createTask: ListTodo,
  research: Radar, upload: Upload, invite: UserPlus, opportunity: Target,
  campaigns: Target, decisions: CheckSquare, trading: TrendingUp, departments: Users,
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

const canonicalNav = [
  ['live-intelligence', 'Dashboard', 'dashboard'], ['ai-command', 'AI Command', 'ai'],
  ['projects', 'Projects', 'projects'], ['tasks', 'Tasks', 'tasks'], ['research', 'Research', 'research'],
  ['knowledge', 'Knowledge', 'knowledge'], ['analytics', 'Analytics', 'analytics'], ['automation', 'Automation', 'automation'],
  ['campaigns', 'Campaigns', 'campaigns'], ['decisions', 'Decisions', 'decisions'], ['departments', 'Departments', 'departments'],
  ['trading', 'Trading', 'trading'], ['settings', 'Settings', 'settings'], ['support', 'Support', 'support'],
]

function SurfaceHeader({ eyebrow, title, description, quote, children }) {
  return <section className="live-surface-header"><div><span className="live-command-eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div><div className="live-surface-header-art"><img src="/creative/admin-artifacts/mountain-top.png" alt="" /><div><strong>{quote || 'A clearer tomorrow.'}</strong><small>— GoClear Nexus OS</small></div><b>SMARTER BUSINESS.<br />A CLEARER TOMORROW.</b></div>{children}</section>
}

function SurfaceStat({ label, value, tone = 'cyan' }) { return <div className={`live-surface-stat tone-${tone}`}><span>{label}</span><strong>{value ?? '—'}</strong></div> }

function ProjectSurface({ state }) {
  const projects = state.campaign_list || []
  const [tab, setTab] = useState('All'); const [query, setQuery] = useState('')
  const visibleProjects = projects.filter(project => (tab === 'All' || String(project.status || '').toLowerCase().includes(tab.toLowerCase())) && String(project.name || '').toLowerCase().includes(query.toLowerCase()))
  return <div className="live-surface-page"><SurfaceHeader eyebrow="WORK / PROJECT PORTFOLIO" title="Projects" description="Turn ideas into real progress." quote="Progress you can see." /><div className="live-surface-toolbar"><div className="live-surface-tabs">{['All', 'Active', 'Planning', 'Completed'].map(item => <button type="button" className={tab === item ? 'active' : ''} onClick={() => setTab(item)} key={item}>{item}</button>)}</div><div className="live-surface-toolbar-actions"><label><Search size={14} /><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search projects" aria-label="Search projects" /></label><button type="button" className="live-surface-primary" disabled title="NOT_YET_AVAILABLE: no governed project-creation write path"><FolderPlus size={14} /> New Project</button></div></div><div className="live-project-grid">{visibleProjects.map((project, index) => <article className={`live-project-card accent-${['green', 'blue', 'purple', 'amber'][index % 4]}`} key={project.name}><div className="live-project-card-top"><span>{project.status || 'STATUS UNAVAILABLE'}</span><Target size={16} /></div><h3>{project.name}</h3><p>{project.next || 'Project detail is not currently available.'}</p><div className="live-project-progress"><div><span>Progress</span><b>—</b></div><i><em style={{ width: '0%' }} /></i></div><footer><span>Team · {project.department || 'Unavailable'}</span><span>Due date · Unavailable</span></footer></article>)}</div>{!visibleProjects.length && <div className="live-honest-empty"><FolderKanban size={20} /><strong>No matching project records currently available</strong><span>Live project data will appear here when the governed source returns it.</span></div>}<div className="live-project-overview"><CommandPanel title="Project Health Overview" eyebrow="PORTFOLIO HEALTH"><div className="live-project-health"><div className="live-health-donut"><strong>{projects.length}</strong><small>Projects</small></div><div className="live-health-legend"><span><i className="green" />On Track <b>Unavailable</b></span><span><i className="amber" />At Risk <b>Unavailable</b></span><span><i className="red" />Delayed <b>Unavailable</b></span><span><i className="purple" />Completed <b>{state.campaigns?.completed ?? '—'}</b></span></div><div className="live-health-kpis"><SurfaceStat label="Avg Progress" value="—" /><SurfaceStat label="Active Projects" value={state.campaigns?.active} tone="teal" /><SurfaceStat label="Completed" value={state.campaigns?.completed} tone="purple" /></div></div></CommandPanel></div></div>
}

function ResearchSurface({ state }) {
  const research = state.research || {}; const findings = state.recent_findings || []; const v2 = state.research_v2 || {};
  return <div className="live-surface-page"><SurfaceHeader eyebrow="INTELLIGENCE / RESEARCH REVIEW" title="Research" description="See what Nexus is studying, what it found, and what still needs proof." quote="Evidence before action." /><div className="live-research-status"><SurfaceStat label="Current objective" value={research.current_objective || state.next_machine_action || 'Unavailable'} /><SurfaceStat label="Current lane" value={research.current_lane || 'Unavailable'} tone="teal" /><SurfaceStat label="Process health" value={research.process_health || research.health || 'Unavailable'} tone="green" /><SurfaceStat label="Productivity health" value={research.productivity_health || (v2.productive_research ? 'PRODUCTIVE' : 'Unavailable')} tone="purple" /><SurfaceStat label="Last successful wake" value={research.last_successful_wake || research.last_real_run || 'Unavailable'} tone="amber" /><SurfaceStat label="Next wake" value={research.next_wake || state.next_wake_at || 'Scheduler-managed'} /></div><div className="live-review-grid"><CommandPanel title="Active investigations" eyebrow="V2 INTELLIGENCE"><div className="live-review-stat-list"><SurfaceStat label="Open questions" value={v2.open_questions ?? '—'} tone="cyan" /><SurfaceStat label="Follow-ups" value={v2.follow_ups ?? '—'} tone="orange" /><SurfaceStat label="Opportunity theses" value={v2.opportunity_theses ?? state.opportunities?.active} tone="teal" /><SurfaceStat label="Strategy theses" value={v2.strategy_theses ?? '—'} tone="purple" /></div></CommandPanel><CommandPanel title="Recent Findings" eyebrow="SOURCE-BACKED"><div>{findings.map((item, i) => <DetailRow key={item.title || i} icon="research" title={item.title || 'Finding'} detail={`${item.lane || 'Lane unavailable'} · ${item.owner || 'Owner unavailable'}`} meta={item.state || 'STATUS UNAVAILABLE'} tone={i % 2 ? 'teal' : 'cyan'} />)}</div>{!findings.length && <div className="live-honest-empty">No findings currently available.</div>}</CommandPanel></div><div className="live-review-grid"><CommandPanel title="Validation status" eyebrow="EVIDENCE"><div className="live-review-stat-list"><SurfaceStat label="Validated claims" value={research.validated_claims ?? state.youtube?.claims_validated} tone="green" /><SurfaceStat label="Partially supported" value={research.partially_supported_claims ?? '—'} tone="amber" /><SurfaceStat label="Unverified" value={research.unverified_claims ?? '—'} tone="purple" /><SurfaceStat label="Follow-up queue" value={research.follow_up_queue_depth ?? v2.follow_ups ?? '—'} tone="orange" /></div></CommandPanel><CommandPanel title="Research continuation" eyebrow="NEXT ACTION"><p className="live-surface-copy">{state.next_machine_action || 'No next Research action is currently reported.'}</p><a className="live-surface-link" href="#/knowledge">Open Knowledge <ArrowUpRight size={13} /></a></CommandPanel></div></div>
}

function CampaignsSurface({ state }) {
  const campaigns = state.campaign_list || []
  const [tab, setTab] = useState('All')
  return <div className="live-surface-page"><SurfaceHeader eyebrow="STUDIO / CREATIVE REVIEW" title="Campaigns" description="Review campaigns, videos, images, landing pages, social posts, and email content." quote="Make the work visible." /><div className="live-surface-toolbar"><div className="live-surface-tabs">{['All', 'Campaigns', 'Videos', 'Images', 'Landing Pages', 'Social', 'Email', 'Needs Review', 'Approved'].map(item => <button type="button" className={tab === item ? 'active' : ''} onClick={() => setTab(item)} key={item}>{item}</button>)}</div></div><div className="live-asset-grid">{campaigns.map(item => <article className="live-asset-card" key={item.name}><div className="live-asset-preview"><Layers3 size={22} /><span>{item.status || 'STATUS UNAVAILABLE'}</span></div><div className="live-asset-copy"><span>Campaign · {item.department || 'Unavailable'}</span><h3>{item.name}</h3><p>{item.next || 'Creative detail is not currently available.'}</p><footer><small>Approval · Unavailable</small><small>Performance · Unavailable</small></footer><div className="live-asset-actions"><button type="button" disabled title="READ_ONLY: no governed asset detail path">View</button><button type="button" disabled title="NOT_YET_AVAILABLE: opening this asset is not wired">Open</button></div></div></article>)}</div>{!campaigns.length && <div className="live-honest-empty"><Layers3 size={20} /><strong>No campaign assets currently available</strong><span>Unsupported approval and publishing actions are not fabricated.</span></div>}</div>
}

function TradingSurface() {
  const [tab, setTab] = React.useState('Overview')
  const tabs = ['Overview', 'Strategies', 'Experiments', 'Backtests', 'Paper', 'Replay', 'Learning']
  const selected = tradingLabData.experiments?.[0]
  return <div className="live-surface-page"><SurfaceHeader eyebrow="TRADING / RESEARCH REVIEW" title="Trading" description="Review strategies, experiments, backtests, paper research, and replay evidence." quote="Evidence before authority." /><div className="live-trading-safety"><ShieldCheck size={15} /><strong>PAPER / REPLAY ONLY</strong><span>Live trading authority: NONE</span></div><div className="live-surface-tabs live-trading-tabs">{tabs.map(item => <button key={item} className={tab === item ? 'active' : ''} onClick={() => setTab(item)}>{item}</button>)}</div><div className="live-trading-grid"><CommandPanel title={tab === 'Replay' ? 'Experiment replay' : 'Research evidence'} eyebrow={tab.toUpperCase()}><div className="live-trading-list">{(tradingLabData.experiments || []).map(item => <div className="live-trading-row" key={item.id}><span>{item.family?.replaceAll('_', ' ') || 'Strategy'}</span><strong>{item.strategy || 'Unavailable'}</strong><small>{item.params || 'Parameters unavailable'} · OOS trades {item.oos?.trades ?? '—'}</small><em>{item.decision || 'READ / RESEARCH'}</em></div>)}</div>{!tradingLabData.experiments?.length && <div className="live-honest-empty">No trading research records currently available.</div>}</CommandPanel><CommandPanel title="Research controls" eyebrow="GOVERNANCE"><div className="live-trading-facts"><div><span>Market</span><strong>FOREX / EUR_USD</strong></div><div><span>Timeframe</span><strong>H1</strong></div><div><span>Data bars</span><strong>{tradingLabData.bars ?? '—'}</strong></div><div><span>Live authority</span><strong>NONE</strong></div></div><p className="live-surface-copy">{selected?.id ? `Selected evidence: ${selected.id}. OOS samples remain research evidence and do not establish profitability.` : 'Trading evidence is unavailable.'}</p></CommandPanel></div></div>
}

function canonicalSurfaceFromHash() {
  const value = window.location.hash.replace(/^#\/?/, '')
  return value === 'dashboard' || !value ? 'live-intelligence' : value
}

function DecisionsSurface({ state }) {
  const items = state.ray_decisions?.items || []
  return <div className="live-surface-page"><SurfaceHeader eyebrow="GOVERNANCE / HUMAN GATE" title="Ray Decision Queue" description="Review decisions that require Ray before Nexus can continue." quote="Clarity at the right moment." /><div className="live-decision-continuation"><span><i /> Global machine work remains active</span><small>Human review is item-level; pending decisions do not stop Research.</small></div><div className="live-review-source">{state.review_data_source === 'GOVERNED_LIVE_READ_MODEL' ? 'Authenticated governed read model' : 'Local development fallback — live review data unavailable'}</div><div className="live-surface-toolbar"><div className="live-surface-tabs">{['Needs Review', 'Approved', 'Rejected', 'Deferred', 'Completed'].map((tab, i) => <button className={i === 0 ? 'active' : ''} key={tab}>{tab}</button>)}</div></div><div className="live-decision-grid">{items.map((item, i) => <CommandPanel key={item.review_item_id || item.id || i} title={item.title || 'Decision item'} eyebrow={item.type || 'REVIEW'}><div className="live-decision-meta"><SurfaceStat label="Review item" value={item.review_item_id || item.id || '—'} /><SurfaceStat label="Source object" value={item.source_object || '—'} tone="purple" /><SurfaceStat label="Status" value={item.status || 'DRAFT_REVIEW_REQUIRED'} tone="amber" /></div><p className="live-surface-copy">{item.why_human_review_required || item.reason || 'Ray review is required for this item.'}</p><div className="live-decision-detail"><strong>Ray is deciding</strong><span>{item.what_ray_is_deciding || item.recommended_next_step || 'Review available options.'}</span></div><div className="live-decision-options">{(item.options || ['approve','modify','decline','defer']).map(option => <span key={option}>{option.replaceAll('_',' ')}</span>)}</div><div className="live-decision-safety"><span>External execution frozen: YES</span><small>{item.external_action_if_approved || 'No external action is wired from this surface.'}</small></div></CommandPanel>)}{!items.length && <CommandPanel title="No decisions waiting" eyebrow="CURRENT QUEUE"><div className="live-honest-empty"><CheckSquare size={20} /><strong>No decisions waiting</strong><span>Routine machine work is continuing; no Ray action is currently reported.</span></div></CommandPanel>}</div></div>
}

function AiCommandSurface({ state }) {
  return <div className="live-surface-page live-ai-page"><SurfaceHeader eyebrow="COMMAND / NOVA" title="AI Command" description="A dependable conversation space for questions, decisions, and next actions." quote="Turn your questions into progress." /><NexusAgentConversation agent="nova" /></div>
}

/** @param {{ surface?: string | null }} props */
export default function LiveCompanyIntelligence({ surface = null }) {
  const fallbackState = { ...snapshot, review_data_source: 'LOCAL_DEV_FALLBACK', ray_decisions: { ...(snapshot.ray_decisions || {}), count: reviewQueue.length, items: reviewQueue }, research_v2: { human_review_queue_count: reviewQueue.length, machine_work_remains: true, global_stop_required: false } }
  const [state, setState] = useState(fallbackState)
  const [refreshed, setRefreshed] = useState(snapshot.generated_at)
  const [activeSurface, setActiveSurface] = useState(surface || canonicalSurfaceFromHash())

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
  useEffect(() => { const onHash = () => setActiveSurface(canonicalSurfaceFromHash()); window.addEventListener('hashchange', onHash); return () => window.removeEventListener('hashchange', onHash) }, [])

  const s = state
  const route = (path) => { const destination = { work: 'analytics', opportunity: 'research', youtube: 'research', seo: 'research' }[path] || path; return { href: `#/` + destination, label: 'View all' } }
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
        {canonicalNav.map(([id, label, icon]) => <a className={(activeSurface === id || (id === 'live-intelligence' && !activeSurface)) ? 'active' : ''} href={`#/${id}`} key={id}><Icon name={icon} />{label}</a>)}
      </nav>
      <div className="live-command-promo"><img src="/creative/admin-artifacts/mountain-promo.png" alt="Mountain landscape" /><div className="live-command-promo-overlay"><strong>A clearer<br />tomorrow.</strong><small>Smarter tools. Clearer decisions.<br />A brighter future.</small><a href="#/live-intelligence">View what&apos;s new <ChevronRight size={13} /></a></div></div>
    </aside>

    <div className="live-command-main">
      <header className="live-command-topbar"><button type="button" disabled className="live-command-search" aria-label="Global search not yet available" title="NOT_YET_AVAILABLE: global search is not wired"><Icon name="search" size={14} /><span>Search unavailable</span></button><div className="live-command-system"><i />All Systems Operational</div><span className="live-command-market">S&amp;P 5,472.83&nbsp;&nbsp;↗ +1.26%</span><span className="live-command-avatar" aria-label="Ray profile">R</span></header>

      <div className="live-command-content">
        {activeSurface !== 'live-intelligence' ? <div className="live-command-surface">{activeSurface === 'ai-command' ? <AiCommandSurface state={s} /> : activeSurface === 'projects' ? <ProjectSurface state={s} /> : activeSurface === 'research' ? <ResearchSurface state={s} /> : activeSurface === 'campaigns' ? <CampaignsSurface state={s} /> : activeSurface === 'decisions' ? <DecisionsSurface state={s} /> : activeSurface === 'trading' ? <TradingSurface /> : activeSurface === 'tasks' ? <TasksPage state={s} /> : activeSurface === 'knowledge' ? <KnowledgePage state={s} /> : activeSurface === 'analytics' ? <AnalyticsPage state={s} /> : activeSurface === 'automation' ? <AutomationPage state={s} /> : activeSurface === 'departments' ? <DepartmentsPage state={s} /> : activeSurface === 'settings' ? <SettingsPage state={s} /> : activeSurface === 'support' ? <SupportPage state={s} /> : <AdminSurfacePage surface={activeSurface === 'team' ? 'departments' : activeSurface} />}</div> : <>
        <section className="live-dashboard-header"><div className="live-dashboard-greeting"><span className="live-command-eyebrow">NEXUS / ADMIN COMMAND CENTER</span><h1>Good morning, Ray</h1><p>Clear insights. Stronger decisions. A clearer tomorrow.</p><small>Live read model · refreshed {refreshed}</small></div><div className="live-dashboard-quote"><strong>Discipline today.<br />A clearer tomorrow.</strong><span>— GoClear Nexus OS</span></div><div className="live-dashboard-art"><img src="/creative/admin-artifacts/mountain-top.png" alt="Mountain landscape" /><b>SMARTER BUSINESS.<br />A CLEARER TOMORROW.</b></div></section>

        <div className="live-command-metrics">{metrics.map(([icon, label, value, note, tone]) => <CommandMetric key={label} icon={icon} label={label} value={value} note={note} tone={tone} />)}</div>

        <div className="live-command-hero-grid"><section className="live-command-hero"><img src="/creative/admin-artifacts/mountain-main-clean4.png" alt="Mountain landscape" /><div className="live-command-hero-copy"><span className="live-command-eyebrow">GOCLEAR NEXUS OS</span><h2>Smarter Decisions.<br />A Clearer Tomorrow.</h2><p>Turn intelligence into opportunity. Nexus helps you move faster, see further, and build what comes next.</p><a href="#/research" className="live-command-primary"><Sparkles size={14} /> Explore intelligence</a></div><div className="live-command-hero-bullets"><span><Target size={13} /> More insight.</span><span><CheckSquare size={13} /> Less noise.</span><span><ArrowUpRight size={13} /> Greater impact.</span></div></section><CommandPanel title="What Matters Next" eyebrow="RAY'S PRIORITIES" className="live-command-priorities"><ol>{(s.pipeline || []).slice(0, 4).map((item, i) => <li key={item.name}><b>{i + 1}</b><div><strong>{item.name}</strong><small>{item.status}</small></div></li>)}</ol></CommandPanel></div>

        <div className="live-command-three-grid"><CommandPanel title="Recent Activity" action={route('knowledge')}><div>{(s.recent_findings || []).slice(0, 5).map((item, i) => <DetailRow key={item.title} icon={i % 2 ? 'automation' : 'research'} title={item.title} detail={`${item.lane} · Alpha ${item.alpha} · ${item.owner}`} meta={item.state} tone={i % 2 ? 'teal' : 'cyan'} />)}</div></CommandPanel><CommandPanel title="Quick Actions" eyebrow="SHORTCUTS"><div className="live-command-actions"><button type="button" disabled title="NOT_YET_AVAILABLE: no governed project-creation path"><Icon name="newProject" /><span><strong>New Project</strong><small>Not yet available</small></span></button><a href="#/ai-command"><Icon name="askAi" /><span><strong>Ask AI</strong><small>Open Nova</small></span></a><button type="button" disabled title="NOT_YET_AVAILABLE: no governed task-creation path"><Icon name="createTask" /><span><strong>Create Task</strong><small>Not yet available</small></span></button><button type="button" disabled title="NOT_YET_AVAILABLE: no governed upload/import path"><Icon name="upload" /><span><strong>Upload File</strong><small>Not yet available</small></span></button><a href="#/research"><Icon name="research" /><span><strong>Research Market</strong><small>Open Research</small></span></a><button type="button" disabled title="NOT_YET_AVAILABLE: no governed member-invite path"><Icon name="invite" /><span><strong>Invite Department Member</strong><small>Not yet available</small></span></button></div></CommandPanel><CommandPanel title="Research Pipeline" action={route('research')}><div className="live-command-pipeline-stats"><b>{s.research.runs_24h || 0}<small>Total Research</small></b><b>{s.research.in_progress || 0}<small>In Progress</small></b><b>{s.research.under_review || 0}<small>Under Review</small></b><b>{s.research.completed_24h || 0}<small>Completed</small></b></div><div className="live-command-bars">{(s.pipeline || []).slice(0, 5).map(item => <div key={item.name}><span>{item.name}</span><i><em style={{ width: `${item.progress || 48}%` }} /></i></div>)}</div></CommandPanel></div>

        <div className="live-command-three-grid"><CommandPanel title="Opportunities Snapshot" action={route('opportunity')}><div className="live-command-opportunity"><div className="live-command-ring"><strong>{s.opportunities.active}</strong><small>Opportunities</small></div><div className="live-command-legend"><span><i className="cyan" />High potential</span><span><i className="teal" />Validated / moving</span><span><i className="purple" />Early stage</span><span><i className="muted" />Follow-up required</span></div><div className="live-command-value"><strong>{s.opportunities.total_value || '—'}</strong><small>Total potential value</small></div></div></CommandPanel><CommandPanel title="Department Utilization"><div className="live-command-bars departments">{(s.departments_list || []).slice(0, 5).map(item => <div key={item.name}><span>{item.name}</span><i><em style={{ width: `${item.utilization || item.progress || 58}%` }} /></i><small>{item.status}</small></div>)}</div></CommandPanel><CommandPanel title="Ray Decision Queue" action={route('decisions')}><div>{(s.ray_decisions.items || []).slice(0, 5).map(item => <DetailRow key={item.title || item} icon="notifications" title={item.title || item} detail="Review required" meta="Open" tone="amber" />)}{!s.ray_decisions.items?.length && <div className="live-command-empty"><CheckSquare size={20} /><strong>No decisions waiting</strong><span>Routine machine work is continuing.</span></div>}</div></CommandPanel></div>

        <div className="live-command-footer-grid"><CommandPanel title="Handoffs & Campaigns" action={route('campaigns')}><div className="live-command-mini-grid">{(s.campaign_list || []).slice(0, 4).map(item => <div key={item.name}><strong>{item.name}</strong><small>{item.status} · {item.department}</small></div>)}</div></CommandPanel><CommandPanel title="YouTube Intelligence" action={route('youtube')}><p className="live-command-copy">{s.youtube.active_monitored}/{s.youtube.total_channels} channels monitored. {s.youtube.transcripts_reviewed} transcripts reviewed and {s.youtube.claims_validated} claims validated.</p></CommandPanel><CommandPanel title="SEO / Current Intelligence" action={route('seo')}><p className="live-command-copy">{s.seo.status} · {s.seo.signals_found} signals found · {s.seo.search_volume || 'Current demand'}.</p></CommandPanel></div>
        <CommandPanel title="Next machine action" eyebrow="AUTONOMOUS CONTINUATION" className="live-command-next"><p>{s.next_machine_action}</p><span><Clock3 size={13} /> Nexus continues independently; Ray decisions are shown only when required.</span></CommandPanel>
        </>}
      </div>
    </div>
  </main>
}
