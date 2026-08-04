import React, { useEffect, useMemo, useState } from 'react'
import {
  Activity,
  AlertTriangle,
  BadgeDollarSign,
  BriefcaseBusiness,
  Building2,
  CheckCircle2,
  ClipboardCheck,
  Clock3,
  Database,
  FileSearch,
  GitBranch,
  HeartPulse,
  LockKeyhole,
  Network,
  Brain,
  BookOpenCheck,
  GitPullRequestArrow,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  UsersRound,
} from 'lucide-react'
import {
  getExecutiveCommandCenterSnapshot,
  loadExecutiveCommandCenterState,
} from '../lib/executive/executiveCommandCenterAdapter'
import { buildHermesConversationHealthSummary } from '../lib/hermes/hermesConversationEngine'
import DepartmentOperationsWorkspace from './DepartmentOperationsWorkspace'

const priorityOrder = { P0: 0, P1: 1, P2: 2, P3: 3, P4: 4 }

function toneForStatus(status) {
  const value = String(status || '').toUpperCase()
  if (value.includes('BLOCK') || value.includes('FAIL') || value.includes('PROHIBITED')) return 'red'
  if (value.includes('DEFER') || value.includes('UNKNOWN') || value.includes('PENDING') || value.includes('PARTIAL')) return 'amber'
  if (value.includes('HEALTH') || value.includes('ACTIVE') || value.includes('LIVE') || value.includes('COMPLETED')) return 'green'
  return 'blue'
}

function Pill({ children, tone = 'blue' }) {
  return <span className={`pill pill-${tone}`}>{children}</span>
}

function Evidence({ evidence }) {
  if (!evidence) return null
  return (
    <span className="exec-evidence" title={evidence.source}>
      {evidence.state} · {evidence.freshness}
    </span>
  )
}

function MetricCard({ metric, icon: Icon }) {
  return (
    <article className="metric glass exec-metric-card" data-testid={`executive-metric-${metric.id}`}>
      <div className={`metric-icon tone-${toneForStatus(metric.status)}`}><Icon size={26} /></div>
      <div>
        <div className="muted">{metric.priority} · {metric.label}</div>
        <div className="metric-value">{metric.value}</div>
        <small>{metric.status}</small>
        <Evidence evidence={metric.evidence} />
      </div>
    </article>
  )
}

function ExecutiveSection({ title, subtitle, children, badge }) {
  return (
    <section className="glass panel executive-panel">
      <div className="panel-head">
        <div>
          <h3>{title}</h3>
          {subtitle && <p className="exec-panel-subtitle">{subtitle}</p>}
        </div>
        {badge && <Pill tone={toneForStatus(badge)}>{badge}</Pill>}
      </div>
      {children}
    </section>
  )
}

function TodayView({ state, onNavigate }) {
  const sorted = useMemo(
    () => [...state.topActions].sort((a, b) => priorityOrder[a.priority] - priorityOrder[b.priority]).slice(0, 3),
    [state.topActions],
  )
  return (
    <ExecutiveSection
      title="Founder Mode Today"
      subtitle={`${state.phoenixDateTime} · prioritized P0 to P4`}
      badge="Evidence backed"
    >
      <div className="exec-today-grid">
        <div className="exec-brief-hero">
          <div className="recommend">P0 first</div>
          <h3>{sorted[0]?.title || 'No urgent action detected'}</h3>
          <p>{sorted[0]?.reason || 'The available evidence did not produce a top action.'}</p>
          <button type="button" onClick={() => onNavigate(sorted[0]?.route || 'rayreview')}>
            Open evidence
          </button>
        </div>
        <div className="exec-action-list">
          {sorted.map((item) => (
            <button type="button" key={item.id} className="exec-action-row" onClick={() => onNavigate(item.route)}>
              <span>{item.priority}</span>
              <strong>{item.title}</strong>
              <small>{item.reason}</small>
              <Evidence evidence={item.evidence} />
            </button>
          ))}
        </div>
      </div>
    </ExecutiveSection>
  )
}

function DailyBrief({ brief }) {
  return (
    <ExecutiveSection title="Daily Operating Brief" subtitle="Facts, interpretations, recommendations, unknowns, and blocked data are separated." badge="Deterministic">
      <div className="exec-brief-grid" data-testid="executive-daily-brief">
        {brief.sections.map((section) => (
          <article className="glass2 exec-brief-card" key={section.id}>
            <h4>{section.title}</h4>
            <p><strong>Facts:</strong> {section.facts.join(' ') || 'None recorded.'}</p>
            <p><strong>Interpretation:</strong> {section.interpretations.join(' ') || 'No interpretation added.'}</p>
            <p><strong>Recommendation:</strong> {section.recommendations.join(' ') || 'No recommendation.'}</p>
            {(section.unknowns.length > 0 || section.blockedData.length > 0) && (
              <p><strong>Unknown or blocked:</strong> {[...section.unknowns, ...section.blockedData].join(' ')}</p>
            )}
          </article>
        ))}
      </div>
    </ExecutiveSection>
  )
}

function ApprovalsPanel({ approvals, onNavigate }) {
  const visible = approvals.slice(0, 6)
  return (
    <ExecutiveSection title="Ray Review and Approvals" subtitle="Normalized executive surface over approvals and task_requests." badge={`${approvals.length} items`}>
      <div className="exec-table" data-testid="executive-approval-queue">
        <div className="exec-table-head"><span>Decision</span><span>Risk</span><span>State</span><span>Evidence</span></div>
        {visible.length ? visible.map((item) => (
          <button type="button" className="exec-table-row" key={item.id} onClick={() => onNavigate('rayreview')}>
            <span><strong>{item.summary}</strong><small>{item.department} · {item.source}</small></span>
            <Pill tone={toneForStatus(item.riskLevel)}>{item.riskLevel}</Pill>
            <Pill tone={toneForStatus(item.state)}>{item.state}</Pill>
            <Evidence evidence={item.evidence} />
          </button>
        )) : <div className="exec-empty">No live approval rows are visible for this authenticated session.</div>}
      </div>
    </ExecutiveSection>
  )
}

function GovernedWorkPanel({ work, onNavigate }) {
  const visible = work.slice(0, 6)
  return (
    <ExecutiveSection title="Governed Work" subtitle="Canonical chain: task_requests to approvals to agent_jobs to nexus_events." badge={`${work.length} records`}>
      <div className="exec-work-list" data-testid="executive-governed-work">
        {visible.length ? visible.map((item) => (
          <button type="button" key={item.id} className="exec-work-card" onClick={() => onNavigate('operations')}>
            <div className="between">
              <strong>{item.title}</strong>
              <Pill tone={toneForStatus(item.lifecycle)}>{item.lifecycle}</Pill>
            </div>
            <p>{item.department} · {item.assignee}</p>
            <small>{item.nextAction}{item.blocker ? ` · ${item.blocker}` : ''}</small>
            <Evidence evidence={item.evidence} />
          </button>
        )) : <div className="exec-empty">No governed work rows are visible. Report-only work-order artifacts are not execution sources.</div>}
      </div>
    </ExecutiveSection>
  )
}

function DepartmentPanel({ departments }) {
  return (
    <ExecutiveSection title="Department Status" subtitle="Truthful activation states, not autonomous agents." badge={`${departments.length} departments`}>
      <div className="department-grid exec-department-grid" data-testid="executive-department-status">
        {departments.map((department) => (
          <article className="department-card glass2" key={department.departmentId}>
            <div className="between">
              <h4>{department.displayName}</h4>
              <Pill tone={toneForStatus(department.currentStatus)}>{department.currentStatus}</Pill>
            </div>
            <p>{department.purpose}</p>
            <div className="three-stats">
              <div><strong>{department.activeGovernedWork}</strong><small>Work</small></div>
              <div><strong>{department.pendingApprovals}</strong><small>Approvals</small></div>
              <div><strong>{department.blockers.length}</strong><small>Blockers</small></div>
            </div>
            <small>{department.activationState}</small>
          </article>
        ))}
      </div>
    </ExecutiveSection>
  )
}

function SummaryPanel({ title, items, icon: Icon, testId }) {
  return (
    <ExecutiveSection title={title} badge={`${items.length} signals`}>
      <div className="exec-summary-grid" data-testid={testId}>
        {items.map((item) => (
          <article className="glass2 exec-summary-card" key={item.id}>
            <Icon size={22} />
            <strong>{item.label}</strong>
            <b>{item.value}</b>
            <small>{item.status}</small>
            <Evidence evidence={item.evidence} />
          </article>
        ))}
      </div>
    </ExecutiveSection>
  )
}

function SystemHealthPanel({ items, onNavigate }) {
  return (
    <ExecutiveSection title="Executive System Health" subtitle="Normalized health over connectors, policy blocks, and system_health rows." badge={`${items.length} checks`}>
      <div className="exec-health-list" data-testid="executive-system-health">
        {items.slice(0, 10).map((item) => (
          <button type="button" key={`${item.component}-${item.status}`} className="exec-health-row" onClick={() => onNavigate('health')}>
            <span className={`exec-dot dot-${toneForStatus(item.status)}`} />
            <strong>{item.component}</strong>
            <Pill tone={toneForStatus(item.status)}>{item.status}</Pill>
            <small>{item.impact}</small>
          </button>
        ))}
      </div>
    </ExecutiveSection>
  )
}

function RepoIntelligencePanel({ candidates, onNavigate }) {
  const visibleCandidates = useMemo(() => {
    const priority = [...candidates].sort((a, b) => {
      const aScore = a.candidateId === 'github_mcp_server' ? -2 : a.decisionRequired === 'PENDING' ? -1 : 0
      const bScore = b.candidateId === 'github_mcp_server' ? -2 : b.decisionRequired === 'PENDING' ? -1 : 0
      return aScore - bScore
    })
    return priority.slice(0, 8)
  }, [candidates])
  return (
    <ExecutiveSection title="Research and Repo Intelligence" subtitle="Read-only candidate registry. No install, clone, or code reuse action exists here." badge={`${candidates.length} candidates`}>
      <div className="exec-repo-list" data-testid="executive-repo-intelligence">
        {visibleCandidates.map((candidate) => (
          <button type="button" key={candidate.candidateId} className="exec-repo-card" onClick={() => onNavigate('reports')}>
            <div className="between">
              <strong>{candidate.repository}</strong>
              <Pill tone={candidate.license === 'UNKNOWN' || candidate.license === 'NOASSERTION' ? 'amber' : 'green'}>{candidate.license}</Pill>
            </div>
            <p>{candidate.category} · {candidate.candidateStatus}</p>
            <small>{candidate.proposedDisposition} · {candidate.blueprintWave} · Ray decision: {candidate.decisionRequired}</small>
          </button>
        ))}
      </div>
    </ExecutiveSection>
  )
}

function CapabilityOSPanel({ capabilityOS, onNavigate }) {
  const modeEntries = Object.entries(capabilityOS?.byActivationMode || {}).sort((a, b) => b[1] - a[1])
  const healthEntries = Object.entries(capabilityOS?.byHealth || {}).sort((a, b) => b[1] - a[1])
  const topCapabilities = capabilityOS?.topCapabilities || []
  return (
    <ExecutiveSection title="Capability OS" subtitle="Canonical capability policy over activation, approval, data access, credentials, dependencies, cost, and health." badge={`${capabilityOS?.total || 0} capabilities`}>
      <div className="exec-capability-os" data-testid="executive-capability-os">
        <div className="exec-capability-summary">
          <article><strong>{capabilityOS?.approvalGated || 0}</strong><small>Approval-gated</small></article>
          <article><strong>{capabilityOS?.awaitingRayApproval || 0}</strong><small>Awaiting Ray</small></article>
          <article><strong>{capabilityOS?.missingCredentials || 0}</strong><small>Missing credentials</small></article>
          <article><strong>{capabilityOS?.dependencyBlocked || 0}</strong><small>Blocked/prohibited</small></article>
          <article><strong>{capabilityOS?.proposals || 0}</strong><small>Proposals</small></article>
        </div>
        <div className="exec-capability-columns">
          <div>
            <h4>Activation</h4>
            {modeEntries.map(([mode, count]) => <p key={mode}><Pill tone={toneForStatus(mode)}>{mode}</Pill><span>{count}</span></p>)}
          </div>
          <div>
            <h4>Health</h4>
            {healthEntries.map(([status, count]) => <p key={status}><Pill tone={toneForStatus(status)}>{status}</Pill><span>{count}</span></p>)}
          </div>
        </div>
        <div className="exec-capability-list">
          {topCapabilities.map((capability) => (
            <button type="button" key={capability.capabilityId} className="exec-capability-card" onClick={() => onNavigate('rayreview')}>
              <div className="between">
                <strong>{capability.name}</strong>
                <Pill tone={toneForStatus(capability.activationMode)}>{capability.activationMode}</Pill>
              </div>
              <p>{capability.departmentId} · {capability.approvalLevel} · {capability.healthStatus}</p>
              <small>
                Dependencies: {capability.dependencies.length || 'none'} · Credentials: {capability.credentialRequirements.length || 'none'} · Ray: {capability.rayApprovalState}
              </small>
            </button>
          ))}
        </div>
      </div>
    </ExecutiveSection>
  )
}

function KnowledgeIntelligencePanel({ knowledgeHealth, onNavigate }) {
  const metrics = [
    ['Approved knowledge', knowledgeHealth?.approvedKnowledge || 0],
    ['Unverified claims', knowledgeHealth?.unverifiedClaims || 0],
    ['Stale records', knowledgeHealth?.staleRecords || 0],
    ['Conflicts', knowledgeHealth?.conflicts || 0],
    ['Missing provenance', knowledgeHealth?.missingProvenance || 0],
    ['Client-safe knowledge', knowledgeHealth?.clientSafeKnowledge || 0],
  ]
  return (
    <ExecutiveSection title="Knowledge and Intelligence" subtitle="Knowledge, evidence, claims, recommendations, memory, and context are separated." badge={`${knowledgeHealth?.totalRecords || 0} records`}>
      <div className="exec-knowledge-panel" data-testid="executive-knowledge-health">
        <div className="exec-knowledge-grid">
          {metrics.map(([label, value]) => (
            <article key={label} className="glass2 exec-knowledge-metric">
              <BookOpenCheck size={20} />
              <strong>{value}</strong>
              <small>{label}</small>
            </article>
          ))}
        </div>
        <div className="exec-knowledge-status">
          <p><strong>Document evidence:</strong> {knowledgeHealth?.documentEvidenceStatus || 'UNKNOWN'}</p>
          <p><strong>Retrieval evaluation:</strong> {knowledgeHealth?.evaluationPassed || 0}/{knowledgeHealth?.evaluationTotal || 0} native fixtures passed</p>
          <p><strong>Policy blocks:</strong> {knowledgeHealth?.recordsBlockedByPolicy || 0} records have brain-specific prohibitions</p>
        </div>
        <button type="button" className="exec-inline-action" onClick={() => onNavigate('reports')}>Open evidence reports</button>
      </div>
    </ExecutiveSection>
  )
}

function BrainRegistryPanel({ brainProfiles }) {
  const visible = brainProfiles || []
  return (
    <ExecutiveSection title="AI Brain Profiles" subtitle="One governed intelligence foundation with separate brain policies." badge={`${visible.length} profiles`}>
      <div className="exec-brain-list" data-testid="executive-brain-profiles">
        {visible.map((brain) => (
          <article className="glass2 exec-brain-card" key={brain.brainId}>
            <div className="between">
              <span><Brain size={18} /><strong>{brain.name}</strong></span>
              <Pill tone={toneForStatus(brain.status)}>{brain.status}</Pill>
            </div>
            <p>{brain.role} · {brain.departmentId || 'unassigned'} · approval: {brain.requiredApprovalLevel}</p>
            <small>
              Supabase: {brain.mayUseSupabase ? 'allowed by policy' : 'blocked'} · Web: {brain.mayUseWeb ? 'allowed by policy' : 'blocked'} · Executes work: {brain.mayExecuteWork ? 'yes' : 'no'}
            </small>
            <small>Blocked data: {brain.prohibitedDataClasses.join(', ') || 'none'}</small>
          </article>
        ))}
      </div>
    </ExecutiveSection>
  )
}

function KnowledgeReviewPanel({ knowledgeHealth, onNavigate }) {
  return (
    <ExecutiveSection title="Knowledge Review" subtitle="Claims and research findings require review before they become approved knowledge." badge={`${knowledgeHealth?.pendingReviews || 0} pending`}>
      <div className="exec-review-panel" data-testid="executive-knowledge-review">
        <div><GitPullRequestArrow size={18} /><strong>{knowledgeHealth?.alphaSubmissionsAwaitingReview || 0}</strong><span>Alpha submissions awaiting review</span></div>
        <div><ShieldCheck size={18} /><strong>{knowledgeHealth?.rejectedFindings || 0}</strong><span>Rejected findings</span></div>
        <div><AlertTriangle size={18} /><strong>{knowledgeHealth?.expiredRecords || 0}</strong><span>Expired records</span></div>
        <button type="button" className="exec-inline-action" onClick={() => onNavigate('rayreview')}>Open Ray Review path</button>
      </div>
    </ExecutiveSection>
  )
}

function HermesExecutiveAdvisor({ state, onAskHermes }) {
  const evidenceLines = [
    `${state.approvals.filter((item) => item.state === 'PENDING').length} pending approvals`,
    `${state.governedWork.filter((item) => item.lifecycle === 'BLOCKED' || item.lifecycle === 'FAILED').length} blocked or failed work items`,
    'Stripe test mode preserved',
    `${state.repoIntelligence.length} repo-intelligence candidates`,
  ]
  return (
    <ExecutiveSection title="Hermes Executive Advisor" subtitle="Facts are separated from recommendations." badge="Read-only">
      <div className="exec-hermes-card" data-testid="executive-hermes-advisor">
        <Sparkles size={28} />
        <div>
          <strong>Suggested order of action</strong>
          <p>{state.topActions.map((item) => item.title).join(' -> ')}</p>
          <small>Based on: {evidenceLines.join(' · ')}</small>
        </div>
      </div>
      <div className="exec-hermes-prompts">
        {['What needs my attention today?', 'Which capabilities are blocked?', 'What is the knowledge status?', 'What repo decisions need review?'].map((prompt) => (
          <button type="button" key={prompt} onClick={() => onAskHermes(prompt)}>{prompt}</button>
        ))}
      </div>
    </ExecutiveSection>
  )
}

function HermesConversationHealthPanel({ onNavigate }) {
  const health = useMemo(() => buildHermesConversationHealthSummary(), [])
  const metrics = [
    ['Certification', `${health.overallScore}%`],
    ['Historical', `${health.historicalRegressionScore}%`],
    ['Action safety', `${health.actionSeparationScore}%`],
    ['Status honesty', `${health.statusHonestyScore}%`],
    ['Memory', `${health.memoryScore}%`],
    ['References', `${health.referenceResolutionScore}%`],
  ]
  return (
    <ExecutiveSection title="Hermes Conversation Health" subtitle="Canonical router, memory continuity, reference resolution, and response-quality certification." badge={`${health.fixtureCount} fixtures`}>
      <div className="exec-hermes-health" data-testid="executive-hermes-conversation-health">
        <div className="exec-hermes-health-grid">
          {metrics.map(([label, value]) => (
            <article key={label} className="glass2 exec-hermes-health-metric">
              <Sparkles size={18} />
              <strong>{value}</strong>
              <small>{label}</small>
            </article>
          ))}
        </div>
        <div className="exec-hermes-health-status">
          <p><strong>Canonical pipeline:</strong> {health.canonicalPipeline}</p>
          <p><strong>Provider availability:</strong> {health.providerAvailability}</p>
          <p><strong>Fallbacks:</strong> {health.fallbackCount} · <strong>Low confidence:</strong> {health.lowConfidenceCount} · <strong>Memory misses:</strong> {health.memoryMisses}</p>
          <p><strong>Known risk:</strong> {health.knownRisks.join(' ')}</p>
        </div>
        <button type="button" className="exec-inline-action" onClick={() => onNavigate('reports')}>Open sanitized trace report</button>
      </div>
    </ExecutiveSection>
  )
}

export default function CommandCenter({ onNavigate, onAskHermes }) {
  const [state, setState] = useState(getExecutiveCommandCenterSnapshot)
  const [loadStatus, setLoadStatus] = useState('Loading live executive evidence...')
  const [alphaLive, setAlphaLive] = useState(null)
  const [tradingLive, setTradingLive] = useState(null)
  const [telegramMissions, setTelegramMissions] = useState(null)

  useEffect(() => {
    let cancelled = false
    loadExecutiveCommandCenterState()
      .then((next) => {
        if (!cancelled) {
          setState(next)
          setLoadStatus('Executive evidence loaded')
        }
      })
      .catch((error) => {
        if (!cancelled) setLoadStatus(`Static snapshot active: ${String(error).slice(0, 90)}`)
      })
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    let cancelled = false
    Promise.allSettled([
      fetch('/runtime/alpha-live-research-status.json', { cache: 'no-store' }).then((r) => r.ok ? r.json() : null),
      fetch('/runtime/oanda-practice-status.json', { cache: 'no-store' }).then((r) => r.ok ? r.json() : null),
      fetch('/runtime/nexus-telegram-missions.json', { cache: 'no-store' }).then((r) => r.ok ? r.json() : null),
    ]).then(([alpha, trading, missions]) => {
      if (cancelled) return
      setAlphaLive(alpha.status === 'fulfilled' ? alpha.value : null)
      setTradingLive(trading.status === 'fulfilled' ? trading.value : null)
      setTelegramMissions(missions.status === 'fulfilled' ? missions.value : null)
    })
    return () => { cancelled = true }
  }, [])

  const icons = [ClipboardCheck, AlertTriangle, UsersRound, BadgeDollarSign, FileSearch, Network]

  return (
    <div className="page nexus-command-center executive-command-center" data-testid="executive-command-center">
      <div className="page-title">
        <h2>Executive Command Center</h2>
        <p>Founder Mode Core · P0 protect the company, P1 protect customers, P2 revenue, P3 operations, P4 research</p>
      </div>

      <div className="exec-topline">
        <Pill tone="green">{loadStatus}</Pill>
        <Pill tone="amber">STRIPE_MODE=test</Pill>
        <Pill tone={tradingLive?.engine_active ? 'green' : 'amber'}>{tradingLive?.engine_active ? `Oanda practice: ${tradingLive.state}` : 'Oanda practice: not checked'}</Pill>
        <Pill tone={alphaLive?.ok ? 'green' : 'amber'}>{alphaLive?.ok ? `Alpha research: ${alphaLive.source_count} sources` : 'Alpha research: not checked'}</Pill>
      </div>

      <div className="metrics-grid executive-metrics-grid">
        {state.metrics.map((item, index) => <MetricCard key={item.id} metric={item} icon={icons[index % icons.length]} />)}
      </div>

      <div className="command-layout executive-layout">
        <div className="main-stack">
          <TodayView state={state} onNavigate={onNavigate} />
          <CapabilityOSPanel capabilityOS={state.capabilityOS} onNavigate={onNavigate} />
          <KnowledgeIntelligencePanel knowledgeHealth={state.knowledgeHealth} onNavigate={onNavigate} />
          <BrainRegistryPanel brainProfiles={state.brainProfiles} />
          <DailyBrief brief={state.dailyBrief} />
          <ApprovalsPanel approvals={state.approvals} onNavigate={onNavigate} />
          <GovernedWorkPanel work={state.governedWork} onNavigate={onNavigate} />
          <DepartmentPanel departments={state.departments} />
          <DepartmentOperationsWorkspace />
          <SummaryPanel title="Customer Operations" items={state.customerSummary} icon={Building2} testId="executive-customer-summary" />
          <SummaryPanel title="Revenue and Opportunities" items={state.revenueSummary} icon={BadgeDollarSign} testId="executive-revenue-summary" />
        </div>
        <aside className="side-stack executive-side-stack">
          <SystemHealthPanel items={state.systemHealth} onNavigate={onNavigate} />
          <ExecutiveSection title="Alpha Live Research" subtitle="Telegram-routed external research with source preservation." badge={alphaLive?.ok ? 'ACTIVE' : 'Not checked'}>
            <div className="exec-release-list" data-testid="executive-alpha-live-research">
              <div><Brain size={18} /><strong>Provider path</strong><span>{alphaLive?.brave_ok ? 'Brave PASS' : 'Brave not checked'} · {alphaLive?.openrouter_ok ? 'OpenRouter PASS' : 'OpenRouter not checked'}</span></div>
              <div><BookOpenCheck size={18} /><strong>Last query</strong><span>{alphaLive?.query || 'No runtime snapshot loaded'}</span></div>
              <div><Network size={18} /><strong>Sources</strong><span>{alphaLive?.source_count ?? 'unknown'}</span></div>
              <div><GitPullRequestArrow size={18} /><strong>Opportunity</strong><span>{alphaLive?.opportunity_stored ? 'Stored for Ray Review' : 'Not stored or not checked'}</span></div>
            </div>
          </ExecutiveSection>
          <ExecutiveSection title="Oanda Practice Trading" subtitle="Demo-account autonomous monitor. Real-money endpoints are blocked." badge={tradingLive?.engine_active ? 'PRACTICE ACTIVE' : 'Not checked'}>
            <div className="exec-release-list" data-testid="executive-oanda-practice-trading">
              <div><TrendingUp size={18} /><strong>State</strong><span>{tradingLive?.state || 'No runtime snapshot loaded'}</span></div>
              <div><ShieldCheck size={18} /><strong>Strategy</strong><span>{tradingLive?.strategy || 'unknown'}</span></div>
              <div><Activity size={18} /><strong>Positions / orders</strong><span>{tradingLive ? `${tradingLive.open_position_count} open · ${tradingLive.pending_order_count} pending` : 'unknown'}</span></div>
              <div><LockKeyhole size={18} /><strong>Kill switch</strong><span>{tradingLive?.kill_switch_active ? 'ACTIVE' : 'Available / not active'}</span></div>
            </div>
          </ExecutiveSection>
          <ExecutiveSection title="Nexus Communications Missions" subtitle="Redacted mission state from the Nexus Telegram worker." badge={telegramMissions?.missions?.length ? `${telegramMissions.missions.length} recent` : 'Not checked'}>
            <div className="exec-release-list" data-testid="executive-nexus-communications-missions">
              {(telegramMissions?.missions || []).slice(0, 4).map((mission) => (
                <div key={mission.mission_id}>
                  <Activity size={18} />
                  <strong>{mission.selected_intent || 'unrouted'}</strong>
                  <span>{mission.state || 'unknown'} · {mission.selected_tool || 'no tool'} · {mission.response_telegram_message_id ? 'delivered' : 'not delivered'}</span>
                </div>
              ))}
              {!telegramMissions?.missions?.length && <div><Clock3 size={18} /><strong>No mission snapshot</strong><span>No current redacted runtime mission file was loaded.</span></div>}
            </div>
          </ExecutiveSection>
          <RepoIntelligencePanel candidates={state.repoIntelligence} onNavigate={onNavigate} />
          <KnowledgeReviewPanel knowledgeHealth={state.knowledgeHealth} onNavigate={onNavigate} />
          <HermesConversationHealthPanel onNavigate={onNavigate} />
          <ExecutiveSection title="Deployments and Releases" subtitle="Current deployment evidence is read-only from repository and reports." badge="Traceable">
            <div className="exec-release-list" data-testid="executive-deployment-status">
              <div><GitBranch size={18} /><strong>Branch</strong><span>main</span></div>
              <div><CheckCircle2 size={18} /><strong>Build</strong><span>Latest local build must pass before release</span></div>
              <div><Database size={18} /><strong>Supabase</strong><span>RLS harness remains required</span></div>
              <div><LockKeyhole size={18} /><strong>External actions</strong><span>Approval-gated</span></div>
            </div>
          </ExecutiveSection>
          <HermesExecutiveAdvisor state={state} onAskHermes={onAskHermes} />
          <ExecutiveSection title="Safety Boundaries" badge="P0">
            <div className="exec-safety-list" data-testid="executive-safety-boundaries">
              <div><ShieldCheck size={18} />Ray remains final authority.</div>
              <div><HeartPulse size={18} />Alpha has no unrestricted Supabase access.</div>
              <div><Clock3 size={18} />Research intake cannot execute automatically.</div>
              <div><Activity size={18} />Client-facing AI stays restricted and customer-safe.</div>
            </div>
          </ExecutiveSection>
        </aside>
      </div>

      <p className="nxos-notice">
        This Command Center is a normalized executive read model. It does not install repositories, activate live Stripe, run real-money trading, publish content, send customer messages, or bypass Ray Review.
      </p>
    </div>
  )
}
