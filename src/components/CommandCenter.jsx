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
  ShieldCheck,
  Sparkles,
  UsersRound,
} from 'lucide-react'
import {
  getExecutiveCommandCenterSnapshot,
  loadExecutiveCommandCenterState,
} from '../lib/executive/executiveCommandCenterAdapter'

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
        {['What needs my attention today?', 'Which capabilities are blocked?', 'Which capabilities need credentials?', 'What repo decisions need review?'].map((prompt) => (
          <button type="button" key={prompt} onClick={() => onAskHermes(prompt)}>{prompt}</button>
        ))}
      </div>
    </ExecutiveSection>
  )
}

export default function CommandCenter({ onNavigate, onAskHermes }) {
  const [state, setState] = useState(getExecutiveCommandCenterSnapshot)
  const [loadStatus, setLoadStatus] = useState('Loading live executive evidence...')

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
        <Pill tone="red">Live trading blocked</Pill>
        <Pill tone="blue">Repo Intelligence read-only</Pill>
      </div>

      <div className="metrics-grid executive-metrics-grid">
        {state.metrics.map((item, index) => <MetricCard key={item.id} metric={item} icon={icons[index % icons.length]} />)}
      </div>

      <div className="command-layout executive-layout">
        <div className="main-stack">
          <TodayView state={state} onNavigate={onNavigate} />
          <CapabilityOSPanel capabilityOS={state.capabilityOS} onNavigate={onNavigate} />
          <DailyBrief brief={state.dailyBrief} />
          <ApprovalsPanel approvals={state.approvals} onNavigate={onNavigate} />
          <GovernedWorkPanel work={state.governedWork} onNavigate={onNavigate} />
          <DepartmentPanel departments={state.departments} />
          <SummaryPanel title="Customer Operations" items={state.customerSummary} icon={Building2} testId="executive-customer-summary" />
          <SummaryPanel title="Revenue and Opportunities" items={state.revenueSummary} icon={BadgeDollarSign} testId="executive-revenue-summary" />
        </div>
        <aside className="side-stack executive-side-stack">
          <SystemHealthPanel items={state.systemHealth} onNavigate={onNavigate} />
          <RepoIntelligencePanel candidates={state.repoIntelligence} onNavigate={onNavigate} />
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
        This Command Center is a normalized executive read model. It does not install repositories, activate live Stripe, run live trading, publish content, send customer messages, or bypass Ray Review.
      </p>
    </div>
  )
}
