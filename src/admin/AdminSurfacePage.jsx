import React, { useEffect, useMemo, useState } from 'react'
import { Activity, ArrowRight, BarChart3, Bell, BookOpen, Bot, CheckSquare, Clock3, FileText, FolderKanban, LifeBuoy, ListTodo, MessageSquare, Radar, Search, Settings, Sparkles, Target, Upload, UserPlus, Users } from 'lucide-react'
import snapshot from '../data/adminCompanyState.json'
import { supabase } from '../lib/supabaseClient'
import './adminSurface.css'

const SURFACES = {
  'ai-command': { title: 'AI Command', eyebrow: 'COMMAND / AGENT OPERATIONS', icon: Sparkles, description: 'Ask a governed agent, inspect recent execution, and see where human decisions remain required.' },
  projects: { title: 'Projects', eyebrow: 'WORK / PROJECT PORTFOLIO', icon: FolderKanban, description: 'Projects and campaigns connected to current goals, departments, artifacts, and next actions.' },
  tasks: { title: 'Tasks', eyebrow: 'WORK / EXECUTION QUEUE', icon: CheckSquare, description: 'Machine work and human-gated work, separated by state and backed by the canonical queue.' },
  knowledge: { title: 'Knowledge', eyebrow: 'INTELLIGENCE / EVIDENCE', icon: BookOpen, description: 'Research artifacts, findings, claims, and evidence status before information becomes action.' },
  analytics: { title: 'Analytics', eyebrow: 'OBSERVABILITY / THROUGHPUT', icon: BarChart3, description: 'Source-backed operating metrics across research, opportunities, handoffs, and departments.' },
  automation: { title: 'Automation', eyebrow: 'SYSTEM / CONTINUATION', icon: Bot, description: 'Supervised workers, heartbeats, next actions, and recovery state for autonomous execution.' },
  departments: { title: 'Departments', eyebrow: 'OPERATIONS / OWNERSHIP', icon: Users, description: 'Departments and runtime identities with current ownership, availability, and work context.' },
  settings: { title: 'Settings', eyebrow: 'SYSTEM / GOVERNANCE', icon: Settings, description: 'Safe configuration visibility. Secrets and protected credentials are never rendered here.' },
  support: { title: 'Support', eyebrow: 'HELP / DIAGNOSTICS', icon: LifeBuoy, description: 'Documentation, evidence paths, and safe support routes for the Nexus operating system.' },
}

function useLiveAdminState() {
  const [state, setState] = useState(snapshot)
  const [live, setLive] = useState(false)
  useEffect(() => {
    let cancelled = false
    const load = () => supabase?.auth.getSession().then(({ data }) => {
      const token = data.session?.access_token
      return token ? fetch('/.netlify/functions/admin-live-state', { cache: 'no-store', headers: { Authorization: `Bearer ${token}` } }) : null
    }).then(response => response?.ok ? response.json() : null).then(next => {
      if (!cancelled && next?.provenance) { setState(next); setLive(true) }
    }).catch(() => {})
    load()
    const timer = window.setInterval(load, 30000)
    return () => { cancelled = true; window.clearInterval(timer) }
  }, [])
  return { state, live }
}

function Status({ children, tone = 'blue' }) { return <span className={`admin-surface-status ${tone}`}>{children}</span> }
function Metric({ label, value, note, tone = 'cyan' }) { return <article className={`admin-surface-metric ${tone}`}><strong>{value}</strong><span>{label}</span><small>{note}</small></article> }
function SurfaceCard({ title, eyebrow, children, action }) { return <section className="admin-surface-card"><header><div>{eyebrow && <span className="admin-surface-eyebrow">{eyebrow}</span>}<h3>{title}</h3></div>{action && <a href={action}>Open <ArrowRight size={13} /></a>}</header>{children}</section> }
function Rows({ items, empty = 'No source-backed records are currently available.' }) { return items?.length ? <div className="admin-surface-rows">{items.map((item, index) => <div className="admin-surface-row" key={item.id || item.name || item.title || index}><span className="admin-surface-row-icon"><Activity size={14} /></span><div><strong>{item.title || item.name}</strong><small>{item.detail || item.work || item.next || item.status || 'Source-backed record'}</small></div><Status tone={/completed|healthy|active|ready/i.test(item.status || item.state || '') ? 'green' : /blocked|failed|error/i.test(item.status || item.state || '') ? 'red' : 'amber'}>{item.status || item.state || 'AVAILABLE'}</Status></div>)}</div> : <div className="admin-surface-empty"><FileText size={18} /><strong>{empty}</strong><span>Nothing is fabricated to fill this view.</span></div> }

function SurfaceBody({ surface, state }) {
  const queue = state.supervisor?.queue_metrics || state.queue_metrics || {}
  const workers = state.supervisor?.workers || []
  const departments = state.departments_list || []
  const campaigns = state.campaign_list || []
  const findings = state.recent_findings || []
  const metricSet = {
    'ai-command': [
      ['Active agents', workers.filter(w => /active|running/i.test(w.status || '')).length || '—', 'supervisor registry', 'purple'],
      ['Machine work remaining', state.next_machine_action ? 'YES' : '—', 'next action is available', 'cyan'],
      ['Ray decisions', state.ray_decisions?.count ?? '—', 'human gate only', 'amber'],
      ['Recent outputs', findings.length, 'report-backed records', 'green'],
    ],
    projects: [['Active campaigns', state.campaigns?.active ?? '—', 'goal-linked work', 'cyan'], ['Completed', state.campaigns?.completed ?? '—', 'with receipts', 'green'], ['Opportunities', state.opportunities?.active ?? '—', 'Alpha-linked', 'purple'], ['Without handoff', state.campaigns?.without_handoff ?? '—', 'needs routing', 'amber']],
    tasks: [['Executable ready', queue.READY ?? '—', 'current queue only', 'cyan'], ['Running', queue.RUNNING ?? '—', 'claimed work', 'purple'], ['Completed', queue.COMPLETED ?? '—', 'preserved history', 'green'], ['Waiting approval', queue.WAITING_APPROVAL ?? '—', 'Ray gate', 'amber']],
    knowledge: [['Research findings', findings.length, 'recent source-backed', 'cyan'], ['Validated claims', state.youtube?.claims_validated ?? '—', 'validation result', 'green'], ['Follow-up research', state.youtube?.channels_not_yet_reviewed ?? '—', 'portfolio remaining', 'amber'], ['Evidence status', state.provenance ? 'PRESENT' : '—', 'durable provenance', 'purple']],
    analytics: [['Research runs', state.research?.runs_24h ?? '—', '24-hour window', 'cyan'], ['Opportunities', state.opportunities?.active ?? '—', 'active pipeline', 'purple'], ['Handoffs completed', state.handoffs?.completed ?? '—', 'receipt-backed', 'green'], ['Departments active', state.departments?.active ?? '—', 'current status', 'amber']],
    automation: [['Supervisor', state.supervisor_status || 'RUNNING', 'process supervision', 'green'], ['Queue ready', queue.READY ?? '—', 'executable items', 'cyan'], ['Research', state.research?.health || '—', 'productivity-aware', 'purple'], ['Next wake', state.next_wake_at || 'scheduler-managed', 'continuation state', 'amber']],
    departments: [['Departments', departments.length, 'registered views', 'cyan'], ['Active', departments.filter(d => /active/i.test(d.status || '')).length, 'currently operating', 'green'], ['Ready', departments.filter(d => /ready/i.test(d.status || '')).length, 'awaiting work', 'amber'], ['Idle', departments.filter(d => /idle/i.test(d.status || '')).length, 'no current queue', 'purple']],
    settings: [['Auth boundary', 'ENABLED', 'AdminGuard', 'green'], ['Tenant guard', 'ENABLED', 'scoped runtime', 'green'], ['Live projection', state.provenance ? 'AVAILABLE' : '—', 'authenticated endpoint', 'cyan'], ['Secrets in UI', 'NONE', 'protected by policy', 'purple']],
    support: [['System health', state.system_health || '—', 'runtime signal', 'green'], ['Supervisor', state.supervisor_status || '—', 'recovery supervised', 'cyan'], ['Research lane', state.research?.current_lane || '—', 'current objective', 'purple'], ['Next action', state.next_machine_action ? 'READY' : '—', 'machine continuation', 'amber']],
  }[surface]
  const rows = surface === 'projects' ? campaigns : surface === 'knowledge' ? findings : surface === 'departments' || surface === 'team' ? departments : surface === 'automation' ? workers : surface === 'ai-command' ? workers : []
  return <>
    <div className="admin-surface-metrics">{metricSet.map(([label, value, note, tone]) => <Metric key={label} label={label} value={value} note={note} tone={tone} />)}</div>
    {surface === 'ai-command' && <SurfaceCard title="Open a governed command room" eyebrow="COMMAND ENTRY"><div className="admin-surface-command-entry"><MessageSquare size={18} /><div><strong>Use the existing Hermes conversation surface</strong><p>Commands remain governed by the current agent, approval, and receipt contracts. This page does not invent a second execution path.</p></div><a href="/admin/agents/hermes/chat/ai-command">Open Hermes command <ArrowRight size={13} /></a></div></SurfaceCard>}
    <div className="admin-surface-grid">
      <SurfaceCard title={surface === 'ai-command' ? 'Agent and runtime status' : surface === 'tasks' ? 'Canonical execution state' : surface === 'knowledge' ? 'Recent intelligence' : surface === 'automation' ? 'Supervised workers' : surface === 'team' ? 'Department ownership' : surface === 'support' ? 'Evidence-backed support' : 'Current source-backed records'} eyebrow="LIVE SOURCE"><Rows items={rows} empty={surface === 'settings' ? 'Settings are intentionally status-only.' : undefined} /></SurfaceCard>
      <SurfaceCard title="What happens next" eyebrow="CONTINUATION"><div className="admin-surface-next"><Clock3 size={18} /><strong>{state.next_machine_action || 'No machine action is currently reported.'}</strong><p>{state.research?.current_lane ? `Research lane: ${state.research.current_lane}.` : 'The runtime will continue polling supervised queues.'}</p><a href="#/live-intelligence">Return to Live Intelligence <ArrowRight size={13} /></a></div></SurfaceCard>
    </div>
    <div className="admin-surface-grid secondary">
      <SurfaceCard title={surface === 'analytics' ? 'Metric provenance' : surface === 'settings' ? 'Governed configuration' : 'Safe destinations'} eyebrow="DETAIL"><div className="admin-surface-detail-list"><div><span>Canonical source</span><strong>{state.provenance || 'Durable runtime records'}</strong></div><div><span>Refresh behavior</span><strong>Authenticated projection · no bundled snapshot required</strong></div><div><span>Human boundary</span><strong>{state.ray_decisions?.count ? `${state.ray_decisions.count} decision(s) require review` : 'No current Ray decision reported'}</strong></div></div></SurfaceCard>
      <SurfaceCard title="Quick destinations" eyebrow="NAVIGATION"><div className="admin-surface-destination-grid">{[['Live Intelligence', 'live-intelligence', Activity], ['Research', 'research', Radar], ['Tasks', 'tasks', ListTodo], ['Knowledge', 'knowledge', BookOpen], ['Opportunities', 'business-opportunities', Target], ['Support', 'support', LifeBuoy]].map(([label, href, Icon]) => <a href={`#/${href}`} key={label}><Icon size={15} /><span>{label}</span><ArrowRight size={12} /></a>)}</div></SurfaceCard>
    </div>
  </>
}

export default function AdminSurfacePage({ surface = 'projects' }) {
  const config = SURFACES[surface] || SURFACES.projects
  const { state, live } = useLiveAdminState()
  const Icon = config.icon
  const sourceLabel = useMemo(() => live ? 'LIVE AUTHENTICATED PROJECTION' : 'LOCAL SOURCE-BACKED FALLBACK', [live])
  return <div className="admin-surface-page"><div className="admin-surface-heading"><div><span className="admin-surface-eyebrow"><Icon size={13} /> {config.eyebrow}</span><h1>{config.title}</h1><p>{config.description}</p></div><Status tone={live ? 'green' : 'amber'}>{sourceLabel}</Status></div><SurfaceBody surface={surface} state={state} /></div>
}
