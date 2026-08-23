import React, { useEffect, useMemo, useState } from 'react'
import { Activity, ArrowRight, Bot, BriefcaseBusiness, CheckCircle2, ChevronRight, CircleAlert, FileText, FolderKanban, HeartPulse, Layers3, Menu, Network, Plus, Search, Settings2, Sparkles, Target, UsersRound, X } from 'lucide-react'
import NexusAgentConversation from '../components/NexusAgentConversation'
import NexusUniversalComposer from '../components/NexusUniversalComposer'
import ClientsPanel from '../components/ClientsPanel'
import CreditFundingPanel from '../components/CreditFundingPanel'
import BusinessOpportunitiesPanel from '../components/BusinessOpportunitiesPanel'
import ResearchEnginePanel from '../components/ResearchEnginePanel'
import MarketingDraftsPanel from '../components/MarketingDraftsPanel'
import RayReviewCenter from '../components/RayReviewCenter'
import { HermesMissionControlV2 } from '../components/command-center/HermesMissionControlV2'
import SystemHealthPanel from '../components/SystemHealthPanel'
import AutomationSchedulerPanel from '../components/AutomationSchedulerPanel'
import { buildHermesOperatingContext } from '../lib/hermes/hermesOperatingContext'
import { getExecutiveCommandCenterSnapshot } from '../lib/executive/executiveCommandCenterAdapter'
import ErrorBoundary from '../components/ErrorBoundary'

const nav = [
  { id: 'command', label: 'Command', icon: Sparkles },
  { id: 'work', label: 'Work', icon: FolderKanban },
  { id: 'agents', label: 'Agents', icon: Bot },
  { id: 'business', label: 'Business', icon: BriefcaseBusiness },
  { id: 'studio', label: 'Studio', icon: Layers3 },
  { id: 'system', label: 'System', icon: Network },
]

const agentMeta = {
  hermes: { label: 'Nexus / Hermes', role: 'Operator · COO · Chief of Staff', icon: 'N', tone: 'hermes' },
  nova: { label: 'Nova', role: 'Strategic Adviser · Critic', icon: 'N', tone: 'nova' },
  alpha: { label: 'Alpha', role: 'Research · Evidence · Intelligence', icon: 'A', tone: 'alpha' },
}

function getStoredAgent() { try { return sessionStorage.getItem('nexus-experience-agent') || 'hermes' } catch { return 'hermes' } }
function setStoredAgent(agent) { try { sessionStorage.setItem('nexus-experience-agent', agent) } catch { /* browser policy */ } }
function routeFromLocation() {
  const path = window.location.pathname
  const match = path.match(/^\/admin\/agents\/(hermes|nova|alpha)\/chat\/([^/]+)/)
  if (match) return { area: 'agents', agent: match[1], conversationId: match[2] }
  const hash = window.location.hash.replace(/^#\/?/, '')
  const oldMap = { hermes: 'agents', nova: 'agents', alpha: 'agents', 'mission-control-v2': 'system', operations: 'work', rayreview: 'work', reports: 'studio', clients: 'business', credit: 'business', 'credit-specialist': 'business', research: 'studio', creative: 'studio', health: 'system', automation: 'system' }
  return { area: oldMap[hash] || (nav.some(item => item.id === hash) ? hash : 'command'), agent: hash === 'nova' ? 'nova' : hash === 'alpha' ? 'alpha' : getStoredAgent(), conversationId: null, legacyHash: hash }
}

function statusPill(value, tone = 'blue') { return <span className={`nx2-status nx2-status-${tone}`}>{value}</span> }
function Section({ title, eyebrow, action, children, className = '' }) { return <section className={`nx2-card ${className}`}><div className="nx2-card-head"><div>{eyebrow && <div className="nx2-eyebrow">{eyebrow}</div>}<h3>{title}</h3></div>{action}</div>{children}</section> }
function EmptyState({ title, text, action }) { return <div className="nx2-empty-state"><CircleAlert size={18} /><strong>{title}</strong><span>{text}</span>{action}</div> }

function CommandPage({ onNavigate, onAsk }) {
  const context = useMemo(() => buildHermesOperatingContext(), [])
  const executive = useMemo(() => getExecutiveCommandCenterSnapshot(), [])
  const priorities = context.priorities.slice(0, 3)
  return <div className="nx2-page nx2-command-page">
    <div className="nx2-hero"><div><div className="nx2-eyebrow">COMMAND / FOUNDER BRIEF</div><h2>Good afternoon, Ray.</h2><p>What matters, what changed, and where Nexus needs your attention.</p></div><div className="nx2-hero-status">{statusPill('Core systems · report-backed', 'green')}<small>Technical detail lives under System.</small></div></div>
    <div className="nx2-attention-grid"><Section title="Needs You" eyebrow="ATTENTION" action={<button className="nx2-text-action" onClick={() => onNavigate('work')}>Open Work <ArrowRight size={14} /></button>}><div className="nx2-attention-count">{executive.approvals.length || 'UNKNOWN'}</div><p className="nx2-muted">Ray Review, approvals, exceptions, and decisions appear here when their sources are available.</p><button className="nx2-outline-button" onClick={() => onNavigate('work')}>View Needs You</button></Section><Section title="Today" eyebrow="OPERATING CONTEXT"><ol className="nx2-priority-list">{priorities.map((item, index) => <li key={item.id}><b>{index + 1}</b><div><strong>{item.title}</strong><span>{item.summary}</span><small>{item.source}</small></div></li>)}</ol>{priorities.length === 0 && <EmptyState title="No priorities loaded" text="Operating Context returned no current priorities." />}</Section><Section title="Nexus status" eyebrow="TRUTH"><div className="nx2-stat-line"><span>System health</span>{statusPill(executive.systemHealth?.length ? 'Report-backed' : 'UNKNOWN', executive.systemHealth?.length ? 'green' : 'amber')}</div><div className="nx2-stat-line"><span>Revenue truth</span>{statusPill('UNKNOWN', 'amber')}</div><div className="nx2-stat-line"><span>Opportunities</span>{statusPill('Canonical source', 'blue')}</div><div className="nx2-stat-line"><span>Authority</span><b>Governed</b></div></Section></div>
    <Section title="Working now" eyebrow="NEXUS ACTIVITY" action={<button className="nx2-text-action" onClick={() => onNavigate('work')}>All work <ArrowRight size={14} /></button>}><div className="nx2-working-grid"><div><div className="nx2-agent-line"><span className="nx2-agent-dot hermes">N</span><div><strong>Nexus / Hermes</strong><small>Operating context · active when sourced</small></div>{statusPill('Available', 'blue')}</div></div><div><div className="nx2-agent-line"><span className="nx2-agent-dot alpha">A</span><div><strong>Alpha</strong><small>Research lane · local/evidence boundary</small></div>{statusPill('Available', 'green')}</div></div><div><div className="nx2-agent-line"><span className="nx2-agent-dot nova">N</span><div><strong>Nova</strong><small>Strategic browser transport</small></div>{statusPill('Connected', 'violet')}</div></div></div></Section>
    <Section title="Business" eyebrow="BUSINESS SNAPSHOT"><div className="nx2-business-grid"><button onClick={() => onNavigate('business')}><span>Revenue truth</span><strong>UNKNOWN</strong><small>Open Business</small></button><button onClick={() => onNavigate('business')}><span>Opportunities</span><strong>Canonical</strong><small>Open Business</small></button><button onClick={() => onNavigate('business')}><span>Clients</span><strong>Authenticated view</strong><small>Open Business</small></button></div></Section>
    <div className="nx2-command-composer"><NexusUniversalComposer agent="hermes" context="Command brief" onSend={text => onAsk('hermes', text)} /></div>
  </div>
}

function WorkPage({ onNavigate }) {
  const work = [
    ['Client Live Data Verification', 'Nexus / Hermes', 'Needs You', 'The canonical operating context identifies a dependency.', 'work-item-1'],
    ['Readiness campaign review', 'Creative Studio', 'Needs Review', 'Artifact is available for Ray Review.', 'work-item-2'],
    ['Funding market research', 'Alpha', 'Running', 'Source-backed research is in progress.', 'work-item-3'],
    ['Evening operating cycle', 'Nexus', 'Scheduled', 'Next dispatch is sourced from runtime cadence.', 'work-item-4'],
  ]
  return <div className="nx2-page"><div className="nx2-hero"><div><div className="nx2-eyebrow">WORK / ATTENTION QUEUE</div><h2>What is Nexus doing?</h2><p>One human-readable view over work, approvals, receipts, and outputs.</p></div><button className="nx2-primary-button" onClick={() => onNavigate('agents')}>Ask an agent <ArrowRight size={15} /></button></div><div className="nx2-filter-row">{['Needs You','Running','Scheduled','Completed','Failed','Approvals','All'].map((filter, i) => <button className={i === 0 ? 'active' : ''} key={filter}>{filter}</button>)}</div><div className="nx2-work-layout"><Section title="Needs You and active work" className="nx2-work-list">{work.map(([title, owner, status, reason, id]) => <button key={id} className="nx2-work-item" onClick={() => onNavigate('work-detail')}><div className="nx2-work-main"><span className="nx2-work-icon"><FolderKanban size={17} /></span><div><strong>{title}</strong><small>{owner} · {reason}</small><span>{status === 'Needs You' ? 'Next: review evidence and choose a governed step.' : 'Last activity: source-backed update'}</span></div></div><div>{statusPill(status, status === 'Needs You' || status === 'Needs Review' ? 'amber' : status === 'Running' ? 'blue' : 'green')}<ChevronRight size={15} /></div></button>)}</Section><Section title="Needs Ray" eyebrow="APPROVAL BOUNDARY"><div className="nx2-attention-count">3</div><p className="nx2-muted">Sample aggregation over Ray Review, approvals, and exceptions. Open the canonical review source before acting.</p><button className="nx2-primary-button" onClick={() => onNavigate('ray-review')}>Open Ray Review</button></Section></div></div>
}

function WorkDetailPage({ onNavigate }) { return <div className="nx2-page"><div className="nx2-hero"><div><div className="nx2-eyebrow">WORK / DETAIL</div><h2>Client Live Data Verification</h2><p>Human-readable work thread · source and authority remain canonical.</p></div>{statusPill('Needs You', 'amber')}</div><div className="nx2-detail-grid"><Section title="Work thread" className="nx2-timeline"><Timeline title="Hermes started work" text="Operating context requested a verification pass." /><Timeline title="Evidence checked" text="Supabase and adapter checks remain read-only." /><Timeline title="Dependency found" text="Client live-data flag remains the blocking condition." /><Timeline title="Recommendation prepared" text="Next step is ready for Ray Review." /></Section><Section title="Next step" eyebrow="GOVERNED"><p className="nx2-lead">Review the evidence and choose a governed next step.</p><div className="nx2-stat-line"><span>Source</span><b>Hermes Operating Context</b></div><div className="nx2-stat-line"><span>Evidence</span>{statusPill('Available where sourced', 'blue')}</div><div className="nx2-stat-line"><span>Authority</span><b>No autonomous execution</b></div><div className="nx2-button-row"><button className="nx2-primary-button" onClick={() => onNavigate('ray-review')}>Open Ray Review</button><button className="nx2-outline-button">View Evidence</button></div></Section></div></div> }
function Timeline({ title, text }) { return <div className="nx2-timeline-event"><span className="nx2-timeline-dot" /><div><strong>{title}</strong><p>{text}</p><small>Sample presentation · source truth remains canonical</small></div></div> }

function AgentsPage({ onOpenAgent }) { return <div className="nx2-page"><div className="nx2-hero"><div><div className="nx2-eyebrow">AGENTS / NEXUS TEAM</div><h2>Who should I talk to?</h2><p>Three distinct agents inside one operating system.</p></div></div><div className="nx2-agent-grid">{Object.entries(agentMeta).map(([id, item]) => <button key={id} className="nx2-agent-card" onClick={() => onOpenAgent(id)}><span className={`nx2-agent-orb ${item.tone}`}>{item.icon}</span><div><h3>{item.label}</h3><p>{item.role}</p>{statusPill(id === 'nova' ? 'Connected' : 'Available', id === 'alpha' ? 'green' : id === 'nova' ? 'violet' : 'blue')}</div><ChevronRight size={17} /></button>)}</div><Section title="Agent boundary" eyebrow="NEXUS RULE"><p className="nx2-lead">Shared interaction mechanics. Separate brains, memory scopes, tools, sources, and authority.</p></Section></div> }

function BusinessPage({ subpage, onNavigate }) { const body = subpage === 'clients' ? <ClientsPanel onAskHermes={() => onNavigate('agents')} /> : subpage === 'credit' ? <CreditFundingPanel onAskHermes={() => onNavigate('agents')} /> : subpage === 'opportunities' ? <BusinessOpportunitiesPanel onAskHermes={() => onNavigate('agents')} /> : <div className="nx2-business-overview"><div className="nx2-kpi-row"><Kpi label="Revenue truth" value="UNKNOWN" note="No-source is not zero." tone="amber" /><Kpi label="Opportunities" value="Canonical" note="Opportunity Engine" tone="green" /><Kpi label="Clients" value="Authenticated" note="Tenant-scoped view" tone="blue" /></div><Section title="Connected readiness journey" eyebrow="BUSINESS"><div className="nx2-journey-row">{['Credit','Foundation','Bankability','Funding Readiness','Recommendations'].map((x,i) => <button key={x} onClick={() => onNavigate(i === 0 ? 'business-credit' : i === 3 ? 'business-funding' : 'business') }><span>{i + 1}</span><strong>{x}</strong><small>{i < 2 ? 'Available' : 'Source dependent'}</small></button>)}</div></Section><Section title="Business destinations"><div className="nx2-link-grid">{[['Clients','business-clients'],['Credit & Funding','business-credit'],['Revenue','business'],['Opportunities','business-opportunities'],['Growth','business']].map(([x,id]) => <button key={x} onClick={() => onNavigate(id)}>{x}<ArrowRight size={14} /></button>)}</div></Section></div>; return <div className="nx2-page"><div className="nx2-hero"><div><div className="nx2-eyebrow">BUSINESS / {subpage ? subpage.toUpperCase() : 'OVERVIEW'}</div><h2>{subpage ? subpage.replace('-', ' ') : 'How is GoClear doing?'}</h2><p>Business context grouped around decisions, clients, and funding readiness.</p></div></div>{body}</div> }
function Kpi({ label, value, note, tone }) { return <div className="nx2-kpi"><span>{label}</span><strong className={`nx2-${tone}`}>{value}</strong><small>{note}</small></div> }

function StudioPage({ subpage, onNavigate }) { const body = subpage === 'research' ? <ResearchEnginePanel onAskHermes={() => onNavigate('agents')} /> : subpage === 'campaigns' ? <MarketingDraftsPanel onAskHermes={() => onNavigate('agents')} /> : <><div className="nx2-output-grid"><Output title="Funding market comparison" type="Research artifact" status="Evidence pending" tone="green" /><Output title="Readiness campaign concept" type="Creative artifact" status="Needs Review" tone="violet" /><Output title="Operating priority brief" type="Report" status="Available" tone="blue" /></div><Section title="Studio destinations"><div className="nx2-link-grid">{['Research','Creative','Campaigns','Artifacts','Reports'].map(x => <button key={x} onClick={() => onNavigate(x === 'Research' ? 'studio-research' : x === 'Campaigns' ? 'studio-campaigns' : 'studio')}>{x}<ArrowRight size={14} /></button>)}</div></Section></>; return <div className="nx2-page"><div className="nx2-hero"><div><div className="nx2-eyebrow">STUDIO / {subpage ? subpage.toUpperCase() : 'OUTPUTS'}</div><h2>{subpage || 'What has Nexus produced?'}</h2><p>Research, creative, campaigns, artifacts, and reports organized around outputs.</p></div></div>{body}</div> }
function Output({ title, type, status, tone }) { return <article className="nx2-output-card"><span className={`nx2-output-icon ${tone}`}><FileText size={18} /></span><div><strong>{title}</strong><small>{type} · {status}</small></div><ChevronRight size={15} /></article> }

function SystemPage({ subpage, email, onNavigate }) { const body = subpage === 'mission-control' ? <HermesMissionControlV2 email={email} onNavigate={onNavigate} /> : subpage === 'health' ? <SystemHealthPanel onNavigate={onNavigate} onAskHermes={() => onNavigate('agents')} /> : subpage === 'workers' ? <AutomationSchedulerPanel onOpenReport={() => onNavigate('studio')} onReview={() => onNavigate('work')} /> : <><div className="nx2-kpi-row"><Kpi label="Core" value="Healthy" note="Mission Control source" tone="green" /><Kpi label="Optional capacity" value="Deferred" note="GPU worker remains deferred" tone="amber" /><Kpi label="Runtime cost" value="UNKNOWN" note="No source, no zero" tone="blue" /></div><Section title="System destinations"><div className="nx2-link-grid">{['Mission Control','Workers','Integrations','Costs','Runtime','Diagnostics'].map(x => <button key={x} onClick={() => onNavigate(x === 'Mission Control' ? 'system-mission-control' : x === 'Workers' ? 'system-workers' : 'system')}>{x}<ArrowRight size={14} /></button>)}</div></Section></>; return <div className="nx2-page"><div className="nx2-hero"><div><div className="nx2-eyebrow">SYSTEM / {subpage ? subpage.toUpperCase() : 'OVERVIEW'}</div><h2>{subpage || 'Is Nexus machinery working?'}</h2><p>Human-readable summary first. Technical evidence second.</p></div></div>{body}</div> }

export default function NexusExperienceAdmin({ email, initialPage = 'command' }) {
  const initial = useMemo(routeFromLocation, [])
  const [area, setArea] = useState(initial.area)
  const [subpage, setSubpage] = useState(initial.area === 'agents' ? null : null)
  const [selectedAgent, setSelectedAgent] = useState(initial.agent || getStoredAgent())
  const [conversationId, setConversationId] = useState(initial.conversationId)
  const [mobileOpen, setMobileOpen] = useState(false)

  function navigate(next, options = {}) {
    const target = next || 'command'
    if (target.startsWith('agent-')) { const agent = target.replace('agent-', ''); openAgent(agent); return }
    const mapped = { 'work-detail': ['work', 'detail'], 'ray-review': ['work', 'approvals'], 'business-clients': ['business', 'clients'], 'business-credit': ['business', 'credit'], 'business-opportunities': ['business', 'opportunities'], 'business-funding': ['business', 'funding'], 'studio-research': ['studio', 'research'], 'studio-campaigns': ['studio', 'campaigns'], 'system-mission-control': ['system', 'mission-control'], 'system-workers': ['system', 'workers'] }[target]
    const [nextArea, nextSubpage] = mapped || [target, null]
    setArea(nextArea); setSubpage(nextSubpage); setMobileOpen(false)
    const hash = nextSubpage ? `${nextArea}-${nextSubpage}` : nextArea
    window.history.pushState({}, '', `/admin#${hash}`); window.scrollTo({ top: 0, behavior: 'smooth' })
  }
  const [pendingPrompt, setPendingPrompt] = useState('')
  function openAgent(agent, id = null, initialPrompt = '') { setSelectedAgent(agent); setStoredAgent(agent); setArea('agents'); setSubpage(null); setConversationId(id); setPendingPrompt(initialPrompt); setMobileOpen(false); const target = id || `${agent}-${Date.now()}`; window.history.pushState({}, '', `/admin/agents/${agent}/chat/${target}`); }
  function onConversationChange(id, nextAgent) { if (nextAgent) { openAgent(nextAgent); return } setConversationId(id); window.history.replaceState({}, '', `/admin/agents/${selectedAgent}/chat/${id}`) }
  function askAgent(agent = 'hermes', initialPrompt = '') { openAgent(agent, null, initialPrompt) }
  useEffect(() => { const sync = () => { const next = routeFromLocation(); setArea(next.area); setSelectedAgent(next.agent); setConversationId(next.conversationId); setSubpage(null) }; window.addEventListener('popstate', sync); window.addEventListener('hashchange', sync); return () => { window.removeEventListener('popstate', sync); window.removeEventListener('hashchange', sync) } }, [])

  let page
  if (area === 'command') page = <CommandPage onNavigate={navigate} onAsk={askAgent} />
  else if (area === 'work') page = subpage === 'detail' ? <WorkDetailPage onNavigate={navigate} /> : <WorkPage onNavigate={navigate} />
  else if (area === 'agents') page = conversationId || window.location.pathname.includes('/agents/') ? <NexusAgentConversation agent={selectedAgent} conversationId={conversationId} initialPrompt={pendingPrompt} onConversationChange={onConversationChange} context="Current Admin surface" /> : <AgentsPage onOpenAgent={askAgent} />
  else if (area === 'business') page = <BusinessPage subpage={subpage} onNavigate={navigate} />
  else if (area === 'studio') page = <StudioPage subpage={subpage} onNavigate={navigate} />
  else page = <SystemPage subpage={subpage} email={email} onNavigate={navigate} />

  return <div className="nx2-root"><header className="nx2-top-banner"><span> NEXUS </span><small>Operating system</small></header><div className="nx2-shell"><aside className={`nx2-sidebar ${mobileOpen ? 'open' : ''}`}><div className="nx2-brand"><span className="nx2-brand-mark">N</span><div><strong>NEXUS</strong><small>Founder mode</small></div></div><button className="nx2-mobile-close" onClick={() => setMobileOpen(false)} aria-label="Close navigation"><X size={20} /></button><nav aria-label="Primary navigation">{nav.map(item => { const Icon = item.icon; return <button key={item.id} className={`nx2-nav-item ${area === item.id ? 'active' : ''}`} onClick={() => navigate(item.id)}><Icon size={18} /><span>{item.label}</span>{item.id === 'work' && <em>3</em>}</button> })}</nav><div className="nx2-sidebar-footer"><div className="nx2-ray-avatar">R</div><div><strong>{email || 'Ray'}</strong><small>Admin · governed</small></div></div></aside><main className="nx2-main"><header className="nx2-header"><button className="nx2-menu" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu size={20} /></button><div className="nx2-breadcrumb">NEXUS / {area.toUpperCase()}</div><div className="nx2-header-actions"><button className="nx2-search"><Search size={17} /> Search Nexus <kbd>⌘K</kbd></button><a href="/client">View Client Portal</a><span className="nx2-live-dot" /> <small>Authenticated</small></div></header><div className="nx2-content">{page}</div></main></div></div>
}
