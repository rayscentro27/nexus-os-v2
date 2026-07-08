import React, { useEffect, useState } from 'react'
import {
  BadgeCheck, Building2, CheckCircle2, CircleAlert, FileCheck2, FileText, Gauge,
  Landmark, LockKeyhole, Mail, SearchCheck, Settings, TrendingUp, Upload,
  Star, MessageSquare, Lightbulb, CreditCard, ArrowUpCircle, Send,
  Rocket, Shield, Wallet, CircleCheck, ChevronRight, Sparkles,
  ArrowRight, Copy, Users, Lock,
} from 'lucide-react'
import { ClientGuidePanel } from '../../components/client/ClientGuidePanel'
import {
  ClientActionList, ClientFactorGrid, ClientMetricCard, ClientPageHeader, ClientScoreCard,
  ClientSection, ClientStatusBadge,
} from '../../components/client/ClientPortalUI'
import { clientPortalData as data } from '../../data/clientPortalData'
import { clientDataMode } from '../../data/clientDataMode'
import { loadClientDashboardLiveData } from '../../services/clientDashboardLiveData'

const score = data.readinessScores

const fundingJourneySteps = [
  { label: 'Upload Credit Report', sublabel: 'Credit Report', icon: Upload, status: 'complete', detail: 'Completed' },
  { label: 'AI Credit Analysis', sublabel: 'AI Analysis', icon: SearchCheck, status: 'complete', detail: 'Completed' },
  { label: 'Funding Strategy', sublabel: 'Strategy', icon: Wallet, status: 'complete', detail: '$0-95' },
  { label: 'Business Opportunities', sublabel: 'Opportunities', icon: Building2, status: 'in_progress', detail: '72% Complete' },
]

const businessOpportunities = [
  { title: 'ATM Business', difficulty: 'Easy', investment: '$3,000 – $10,000', desc: 'Low overhead, consistent flow.', color: '#e0f2fe' },
  { title: 'Local Cleaning Service', difficulty: 'Easy', investment: '$4,000 – $8,000', desc: 'Secure start, high demand, cash flow.', color: '#f0fdf4' },
  { title: 'E-commerce Store', difficulty: 'Medium', investment: '$8,000 – $20,000', desc: 'Home-based, scalable online sales.', color: '#fef3c7' },
]

export function ClientDashboard() {
  const [live, setLive] = useState(null)
  useEffect(() => {
    if (clientDataMode.liveSupabaseTestClientEnabled) loadClientDashboardLiveData().then(setLive)
  }, [])
  const liveProfile = live?.profile
  const dashboardTasks = live?.tasks?.length ? live.tasks : data.clientTasks
  const badge = liveProfile ? 'Live test data' : 'Demo data'
  return <div className="client-page client-dashboard-page">
    <ClientPageHeader title="Dashboard" subtitle="Your approved credit, business, and funding-readiness snapshot." badge={badge} />

    {/* Hero: Step 1 CTA */}
    <div className="client-card" style={{ marginBottom: 20, background: 'linear-gradient(135deg, rgba(14,165,233,.06), rgba(20,184,166,.04))', border: '1px solid rgba(14,165,233,.15)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <div style={{ width: 48, height: 48, borderRadius: 14, background: 'linear-gradient(135deg, var(--cp-cyan), var(--cp-blue))', display: 'grid', placeItems: 'center', color: 'white', flexShrink: 0 }}><Rocket size={24} /></div>
        <div style={{ flex: 1 }}>
          <h3 style={{ margin: 0, fontSize: 18 }}>Step 1: Upload Your Credit Report</h3>
          <p style={{ margin: '4px 0 0', fontSize: 13 }}>This unlocks your funding strategy and estimated funding range.</p>
        </div>
        <button style={{ padding: '10px 20px', borderRadius: 10, border: 0, background: 'linear-gradient(135deg, var(--cp-blue), var(--cp-purple))', color: 'white', fontWeight: 700, fontSize: 13, cursor: 'pointer', whiteSpace: 'nowrap' }}>Upload Credit Report</button>
      </div>
      <div style={{ display: 'flex', gap: 16, marginTop: 12, fontSize: 12, color: 'var(--cp-muted)' }}>
        <span>✓ Takes 2 minutes</span>
        <span>•</span>
        <span>Secure</span>
        <span>•</span>
        <span>Phone or computer</span>
      </div>
    </div>

    {/* Funding Journey */}
    <div className="client-card" style={{ marginBottom: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ fontSize: 18, fontWeight: 800 }}>Funding Journey</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--cp-blue)' }}>72%</span>
          <div style={{ width: 80, height: 6, borderRadius: 3, background: '#e9edf5', overflow: 'hidden' }}><div style={{ width: '72%', height: '100%', borderRadius: 3, background: 'linear-gradient(90deg, var(--cp-cyan), var(--cp-blue))' }} /></div>
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        {fundingJourneySteps.map((step, i) => {
          const Icon = step.icon
          return <div key={i} style={{ padding: 14, borderRadius: 12, border: '1px solid var(--cp-border-light)', background: step.status === 'complete' ? 'rgba(16,185,129,.04)' : 'transparent', textAlign: 'center' }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: step.status === 'complete' ? 'rgba(16,185,129,.1)' : 'rgba(14,165,233,.1)', display: 'grid', placeItems: 'center', margin: '0 auto 8px', color: step.status === 'complete' ? 'var(--cp-green)' : 'var(--cp-cyan)' }}><Icon size={20} /></div>
            <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--cp-navy)' }}>{step.sublabel}</div>
            <div style={{ fontSize: 11, color: step.status === 'complete' ? 'var(--cp-green)' : 'var(--cp-muted)', marginTop: 4 }}>{step.detail}</div>
            {i < fundingJourneySteps.length - 1 && <div style={{ position: 'absolute', right: -8, top: '50%', width: 16, height: 2, background: 'var(--cp-border)' }} />}
          </div>
        })}
      </div>
    </div>

    {/* Estimated Funding Range */}
    <div className="client-card" style={{ marginBottom: 20, background: 'linear-gradient(135deg, rgba(37,99,235,.04), rgba(14,165,233,.03))' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h2 style={{ fontSize: 18, fontWeight: 800 }}>Estimated Funding Range</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 12, color: 'var(--cp-muted)' }}>Level 2</span>
          <div style={{ width: 60, height: 6, borderRadius: 3, background: '#e9edf5', overflow: 'hidden' }}><div style={{ width: '50%', height: '100%', borderRadius: 3, background: 'var(--cp-blue)' }} /></div>
          <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--cp-blue)' }}>72%</span>
        </div>
      </div>
      <div style={{ padding: '12px 16px', borderRadius: 10, background: 'rgba(16,185,129,.08)', marginBottom: 16 }}>
        <span style={{ fontSize: 13, color: 'var(--cp-green)', fontWeight: 600 }}>Great job! You're <strong>28% ready</strong> for funding.</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginBottom: 12 }}>
        <span style={{ fontSize: 32, fontWeight: 800, color: 'var(--cp-navy)' }}>$25,000 – $80,000</span>
        <span style={{ padding: '6px 14px', borderRadius: 20, background: 'rgba(245,158,11,.1)', color: 'var(--cp-orange)', fontWeight: 700, fontSize: 13 }}>Medium</span>
      </div>
      <p style={{ fontSize: 13, color: 'var(--cp-muted)', marginBottom: 12 }}>✓ Reduce credit utilization under 30% to increase your approval odds.</p>
      <button style={{ width: '100%', padding: '12px 0', borderRadius: 10, border: 0, background: 'linear-gradient(135deg, var(--cp-blue), var(--cp-blue-dark))', color: 'white', fontWeight: 700, fontSize: 14, cursor: 'pointer' }}>Improve Approval Odds</button>
      <p style={{ fontSize: 11, color: 'var(--cp-muted-light)', textAlign: 'center', marginTop: 8 }}>Educational estimate only, not a lending decision</p>
    </div>

    {/* Business Opportunities */}
    <div style={{ marginBottom: 20 }}>
      <h2 style={{ fontSize: 20, fontWeight: 800, color: 'var(--cp-navy)', marginBottom: 4 }}>Business Opportunities</h2>
      <p style={{ fontSize: 13, color: 'var(--cp-muted)', marginBottom: 16 }}>Top Recommendations for You</p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
        {businessOpportunities.map((opp, i) => <div key={i} className="client-card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ height: 100, background: opp.color, display: 'grid', placeItems: 'center', fontSize: 32 }}>🏢</div>
          <div style={{ padding: 16 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, margin: '0 0 4px' }}>{opp.title}</h3>
            <span style={{ fontSize: 12, color: 'var(--cp-green)', fontWeight: 600 }}>{opp.difficulty}</span>
            <div style={{ fontSize: 18, fontWeight: 800, color: 'var(--cp-navy)', margin: '8px 0 4px' }}>{opp.investment}</div>
            <p style={{ fontSize: 12, color: 'var(--cp-muted)', margin: '0 0 12px' }}>{opp.desc}</p>
            <button style={{ width: '100%', padding: '8px 0', borderRadius: 8, border: '1px solid var(--cp-border)', background: 'white', color: 'var(--cp-blue)', fontWeight: 700, fontSize: 12, cursor: 'pointer' }}>Start This Business</button>
          </div>
        </div>)}
      </div>
    </div>

    <div className="client-metric-grid dashboard">
      <ClientScoreCard title="Overall Readiness" value={71} status="Building momentum" text="Complete this month's highest-impact tasks before requesting funding review." />
      <ClientMetricCard icon={Gauge} label="Credit Repair" value={`${score.creditRepairProgress}%`} note="In progress" />
      <ClientMetricCard icon={BadgeCheck} label="Credit Profile" value={score.creditProfileReadiness} note="Nexus Readiness Score" tone="green" />
      <ClientMetricCard icon={Building2} label="Business Profile" value={score.businessProfileReadiness} note="Four gaps remain" tone="purple" />
      <ClientMetricCard icon={Landmark} label="Funding Readiness" value={score.fundingReadiness} note="Almost Ready" tone="orange" />
    </div>
    <div className="client-dashboard-grid">
      <ClientSection title="Your next actions" action={`${dashboardTasks.length} open`}><ClientActionList rows={dashboardTasks} /></ClientSection>
      <ClientSection title="Readiness overview">
        {[['Credit profile', score.creditProfileReadiness], ['Business profile', score.businessProfileReadiness], ['Funding readiness', score.fundingReadiness], ['Business opportunities', score.businessOpportunityScore]].map(([name, value]) => <div className="client-bar-row" key={name}><span>{name}</span><div><i style={{ width: `${value}%` }} /></div><strong>{value}</strong></div>)}
      </ClientSection>
      <ClientSection title="GoClear review status"><p>{data.fundingReadiness.goclearReviewStatus}</p><ClientStatusBadge tone="orange">Review pending</ClientStatusBadge><p className="client-safe-note">Nothing has been sent, submitted, or applied for from this portal.</p></ClientSection>
    </div>
    <ClientGuidePanel />
  </div>
}

export function CreditProfilePage() {
  const profile = data.creditProfileReadiness
  return <div className="client-page">
    <ClientPageHeader title="Credit Profile" subtitle="Understand your educational Nexus Readiness Score and what may improve readiness." badge="Not FICO" />
    <div className="client-metric-grid compact"><ClientScoreCard title="Nexus Readiness Score" value={profile.overallScore} status="Good progress" text={profile.scoreDisclaimer} /><ClientMetricCard icon={TrendingUp} label="Progress" value="+14" note="Demo six-month trend" tone="green" /><ClientMetricCard icon={CircleAlert} label="Attention Factors" value={profile.negativeFactors.length} note="Review safely" tone="orange" /></div>
    <ClientSection title="Score factors" action="Educational only"><ClientFactorGrid rows={profile.scoreFactors} /></ClientSection>
    <div className="client-three-col">
      <ClientSection title="Positive factors"><ul>{profile.positiveFactors.map(x => <li key={x}>{x}</li>)}</ul></ClientSection>
      <ClientSection title="Factors needing attention"><ul>{profile.negativeFactors.map(x => <li key={x}>{x}</li>)}</ul></ClientSection>
      <ClientSection title="Top actions"><ClientActionList rows={profile.topActions} /></ClientSection>
    </div>
    <ClientGuidePanel suggestedKeys={['how_to_improve_credit', 'what_do_i_do_next', 'what_goclear_is_reviewing']} />
  </div>
}

export function CreditUtilizationPage() {
  const profile = data.creditProfileReadiness
  const utilizationFactor = profile.scoreFactors.find(f => f[0] === 'Utilization')
  const utilizationScore = utilizationFactor ? utilizationFactor[1] : 58
  return <div className="client-page">
    <ClientPageHeader title="Credit Utilization" subtitle="Review your revolving credit utilization and create a pay-down plan." badge="Balance management" />
    <div className="client-metric-grid compact">
      <ClientScoreCard title="Utilization Score" value={utilizationScore} status={utilizationScore >= 70 ? 'On track' : 'Needs attention'} text="Lower utilization may improve your funding readiness. Pay down revolving balances where practical." />
      <ClientMetricCard icon={CreditCard} label="Revolving Accounts" value="3" note="Demo accounts" />
      <ClientMetricCard icon={ArrowUpCircle} label="Target" value="30%" note="Recommended max" tone="green" />
    </div>
    <div className="client-two-col">
      <ClientSection title="Utilization breakdown">
        <div className="client-bar-row"><span>Card A — Demo</span><div><i style={{ width: '45%' }} /></div><strong>45%</strong></div>
        <div className="client-bar-row"><span>Card B — Demo</span><div><i style={{ width: '62%' }} /></div><strong>62%</strong></div>
        <div className="client-bar-row"><span>Card C — Demo</span><div><i style={{ width: '28%' }} /></div><strong>28%</strong></div>
        <p className="client-safe-note">Demo values only. Connect live credit monitoring for real utilization data.</p>
      </ClientSection>
      <ClientSection title="Recommended actions">
        <ClientActionList rows={[
          { title: 'Pay down Card B first (highest utilization)', status: 'recommended' },
          { title: 'Keep Card C below 30%', status: 'on_track' },
          { title: 'Avoid new revolving accounts', status: 'important' },
          { title: 'Request credit limit increase (optional)', status: 'optional' },
        ]} />
      </ClientSection>
    </div>
    <ClientGuidePanel suggestedKeys={['how_to_improve_credit', 'what_do_i_do_next', 'can_i_apply_for_funding_now']} />
  </div>
}

export function ClientDocumentsPage() {
  const docs = data.documents
  const sections = [['Required documents', docs.requiredDocuments, 'blue'], ['Uploaded', docs.uploadedDocuments, 'green'], ['Missing', docs.missingDocuments, 'orange'], ['Under GoClear review', docs.underReviewDocuments, 'purple']]
  return <div className="client-page"><ClientPageHeader title="Documents" subtitle="Track demo readiness documents and GoClear review status." badge="Demo files only" /><div className="client-four-col documents">{sections.map(([title, rows, tone]) => <ClientSection title={title} key={title}>{rows.map(row => <article className="client-document-row" key={row}><FileText size={19} /><strong>{row}</strong><ClientStatusBadge tone={tone}>{title}</ClientStatusBadge></article>)}</ClientSection>)}</div><div className="client-upload-placeholder"><Upload size={28} /><strong>Upload is disabled in this prototype</strong><p>Production document upload requires private storage, consent, tenant isolation, and GoClear approval.</p></div><ClientGuidePanel suggestedKeys={['documents_needed', 'what_goclear_is_reviewing', 'what_do_i_do_next']} /></div>
}

export function BusinessSetupPage() {
  const business = data.businessProfileReadiness
  return <div className="client-page">
    <ClientPageHeader title="Business Setup" subtitle="Build a consistent, documented business profile before funding review." badge="Profile builder" />
    <div className="client-metric-grid"><ClientScoreCard title="Business Readiness" value={business.readinessScore} status="Good start" text={business.fundingImpactNotes} /><ClientMetricCard icon={CheckCircle2} label="Completed" value={`${business.completedItems}/10`} note="Checklist items" tone="green" /><ClientMetricCard icon={CircleAlert} label="Missing / Weak" value={business.missingItems} note="Needs attention" tone="orange" /><ClientMetricCard icon={LockKeyhole} label="Funding Blockers" value={business.fundingBlockers} note="Resolve before review" tone="red" /></div>
    <div className="client-two-col wide-left">
      <ClientSection title="Fundability checklist"><div className="client-check-grid">{business.fundabilityChecklist.map(([name, status]) => <article key={name}><span className={status === 'complete' ? 'done' : ''}>{status === 'complete' ? '✓' : '!'}</span><strong>{name}</strong><ClientStatusBadge tone={status === 'complete' ? 'green' : status === 'missing' ? 'red' : 'orange'}>{status.replaceAll('_', ' ')}</ClientStatusBadge></article>)}</div></ClientSection>
      <ClientSection title="Recommended next steps"><ClientActionList rows={business.recommendedNextSteps} /></ClientSection>
    </div>
    <ClientGuidePanel suggestedKeys={['business_profile_next_step', 'documents_needed', 'what_do_i_do_next']} />
  </div>
}

export function BusinessBankabilityPage() {
  const business = data.businessProfileReadiness
  return <div className="client-page">
    <ClientPageHeader title="Business Bankability" subtitle="Review banking readiness and revenue documentation for funding paths." badge="Banking readiness" />
    <div className="client-metric-grid compact">
      <ClientScoreCard title="Bankability Score" value={business.readinessScore} status="Building" text="Open a business bank account and document the banking relationship to improve readiness." />
      <ClientMetricCard icon={Landmark} label="Bank Account" value="In progress" note="Business account needed" tone="orange" />
      <ClientMetricCard icon={FileCheck2} label="Revenue Docs" value="Missing" note="Upload required" tone="red" />
    </div>
    <div className="client-two-col">
      <ClientSection title="Banking checklist">
        <div className="client-check-grid">
          {[
            ['Business bank account', 'in_progress'],
            ['Bank relationship documented', 'missing'],
            ['3 months bank statements', 'complete'],
            ['Revenue summary', 'missing'],
            ['Online banking access', 'in_progress'],
          ].map(([name, status]) => <article key={name}><span className={status === 'complete' ? 'done' : ''}>{status === 'complete' ? '✓' : '!'}</span><strong>{name}</strong><ClientStatusBadge tone={status === 'complete' ? 'green' : status === 'missing' ? 'red' : 'orange'}>{status.replaceAll('_', ' ')}</ClientStatusBadge></article>)}
        </div>
      </ClientSection>
      <ClientSection title="Recommended banks">
        <ClientActionList rows={[
          { title: 'Online business bank (Bluevine, Mercury, Relay)', status: 'recommended' },
          { title: 'Credit union business account', status: 'alternative' },
          { title: 'Community bank relationship', status: 'alternative' },
        ]} />
        <p className="client-safe-note">Bank recommendations are educational. No account has been opened.</p>
      </ClientSection>
    </div>
    <ClientGuidePanel suggestedKeys={['business_profile_next_step', 'documents_needed', 'what_do_i_do_next']} />
  </div>
}

export function FundingReadinessPage() {
  const funding = data.fundingReadiness
  const groups = [['Personal credit blockers', funding.personalCreditBlockers], ['Business profile blockers', funding.businessProfileBlockers], ['Banking blockers', funding.bankingBlockers], ['Document blockers', funding.documentBlockers]]
  return <div className="client-page">
    <ClientPageHeader title="Funding Readiness" subtitle="See what must be completed before GoClear can review an application path." badge={funding.status} />
    <div className="client-metric-grid compact"><ClientScoreCard title="Funding Readiness" value={funding.readinessScore} status={funding.status} text={funding.recommendedPath} /><ClientMetricCard icon={LockKeyhole} label="Blocker Groups" value={groups.length} note="No application yet" tone="red" /><ClientMetricCard icon={FileCheck2} label="GoClear Status" value="Pending" note="Approval required" tone="orange" /></div>
    <div className="client-warning"><CircleAlert size={22} /><div><strong>Avoid applying right now</strong><p>{funding.avoidApplicationWarning}</p></div></div>
    <div className="client-four-col">{groups.map(([title, rows]) => <ClientSection title={title} key={title}><ul>{rows.map(x => <li key={x}>{x}</li>)}</ul></ClientSection>)}</div>
    <ClientGuidePanel suggestedKeys={['can_i_apply_for_funding_now', 'why_not_funding_ready', 'documents_needed']} />
  </div>
}

export function RecommendationsPage() {
  const opportunities = data.businessOpportunities
  return <div className="client-page">
    <ClientPageHeader title="Recommendations" subtitle="Explore educational paths matched to your current demo readiness — not guaranteed offers." badge="Fit review required" />
    <div className="client-metric-grid compact"><ClientScoreCard title="Opportunity Score" value={opportunities.opportunityScore} status="Strong potential" text="Improve readiness gaps before selecting a funding or partner path." /><ClientMetricCard icon={BadgeCheck} label="Matched Paths" value={opportunities.matchedOpportunities.length} note="Educational matches" tone="purple" /><ClientMetricCard icon={Landmark} label="Funding Paths" value={opportunities.fundingPaths.length} note="GoClear review required" /></div>
    <div className="client-three-col"><ClientSection title="Matched opportunities"><ClientActionList rows={opportunities.matchedOpportunities} /></ClientSection><ClientSection title="Funding paths"><ClientActionList rows={opportunities.fundingPaths} /></ClientSection><ClientSection title="Partner/tool options"><ClientActionList rows={opportunities.partnerOffers} /><p className="client-safe-note">Best client outcome first. Affiliate value second. Free/DIY options remain visible.</p></ClientSection></div>
    <ClientGuidePanel suggestedKeys={['what_opportunity_should_i_focus_on', 'can_i_apply_for_funding_now', 'what_do_i_do_next']} />
  </div>
}

export function ResourcesPage() {
  return <div className="client-page">
    <ClientPageHeader title="Resources & Affiliates" subtitle="Tools, services, and options to support your credit and business readiness." badge="Transparency" />
    <div className="client-three-col">
      <ClientSection title="Credit Monitoring">
        <ClientActionList rows={[
          { title: 'SmartCredit — credit monitoring', status: 'paid option' },
          { title: 'AnnualCreditReport.com — free reports', status: 'free' },
          { title: 'Credit Karma — free monitoring', status: 'free' },
        ]} />
        <p className="client-safe-note">Free options are listed. Affiliate relationships are disclosed.</p>
      </ClientSection>
      <ClientSection title="Mailing Options">
        <ClientActionList rows={[
          { title: 'Online mailing (dispute letters)', status: 'digital' },
          { title: 'Print and physical mail', status: 'physical' },
          { title: 'Certified mail (recommended for disputes)', status: 'recommended' },
        ]} />
        <p className="client-safe-note">Physical mailing requires GoClear approval and compliance review.</p>
      </ClientSection>
      <ClientSection title="Business Banking">
        <ClientActionList rows={[
          { title: 'Bluevine — online business checking', status: 'recommended' },
          { title: 'Mercury — startup banking', status: 'option' },
          { title: 'Relay — business banking', status: 'option' },
          { title: 'Credit union business account', status: 'alternative' },
        ]} />
        <p className="client-safe-note">No account has been opened. These are educational recommendations.</p>
      </ClientSection>
    </div>
    <div className="client-two-col">
      <ClientSection title="Credit Report Upload">
        <ClientActionList rows={[
          { title: 'Upload your credit report (PDF)', status: 'disabled in prototype' },
          { title: 'Connect SmartCredit for live data', status: 'not connected' },
          { title: 'Request GoClear review of report', status: 'requires upload first' },
        ]} />
      </ClientSection>
      <ClientSection title="Bank Relationship Reminder">
        <div className="client-warning"><CircleAlert size={18} /><div><strong>Open a business bank account</strong><p>A business banking relationship supports funding readiness. Document the account after opening.</p></div></div>
      </ClientSection>
    </div>
    <ClientGuidePanel suggestedKeys={['what_do_i_do_next', 'documents_needed', 'can_i_apply_for_funding_now']} />
  </div>
}

export function RequestReviewPage() {
  const funding = data.fundingReadiness
  const tasks = data.clientTasks
  const openTasks = tasks.filter(t => t.status !== 'complete')
  return <div className="client-page">
    <ClientPageHeader title="Request Review" subtitle="Submit your profile for GoClear readiness review when ready." badge="Review gate" />
    <div className="client-metric-grid compact">
      <ClientScoreCard title="Review Readiness" value={funding.readinessScore} status={funding.status} text={funding.recommendedPath} />
      <ClientMetricCard icon={MessageSquare} label="Open Tasks" value={openTasks.length} note="Complete before review" tone="orange" />
      <ClientMetricCard icon={Send} label="Review Status" value="Not submitted" note="Pending completion" tone="purple" />
    </div>
    <div className="client-warning"><CircleAlert size={22} /><div><strong>Complete open tasks first</strong><p>Request review only after completing all high-priority tasks. Incomplete submissions may delay processing.</p></div></div>
    <div className="client-two-col">
      <ClientSection title="Open tasks to complete">
        <ClientActionList rows={openTasks.map(t => ({ title: t.title, status: t.status.replaceAll('_', ' ') }))} />
      </ClientSection>
      <ClientSection title="What happens after review">
        <ul>
          <li>GoClear reviews your readiness profile</li>
          <li>You receive a status update in Messages</li>
          <li>Next steps are recommended based on review</li>
          <li>No application is submitted without your approval</li>
        </ul>
        <p className="client-safe-note">Review requests are processed in order. Response time varies.</p>
      </ClientSection>
    </div>
    <ClientGuidePanel suggestedKeys={['what_goclear_is_reviewing', 'what_do_i_do_next', 'can_i_apply_for_funding_now']} />
  </div>
}

export function ClientMessagesPage() {
  const groups = [['Advisor messages', data.messages.advisorMessages], ['System messages', data.messages.systemMessages], ['GoClear review updates', data.messages.goclearReviewUpdates], ['Action required', data.messages.actionRequiredMessages]]
  return <div className="client-page"><ClientPageHeader title="Messages" subtitle="Read approved demo updates. Outbound messaging is not connected." badge="Read-only preview" /><div className="client-message-layout"><ClientSection title="Inbox" className="client-message-inbox">{groups.flatMap(([group, rows]) => rows.map(row => <article key={row.id}><div className="client-message-icon"><Mail size={18} /></div><div><small>{group}</small><strong>{row.title}</strong><p>{row.body}</p></div><time>{row.date}</time></article>))}</ClientSection><ClientSection title="Communication safety"><p>Nexus Guide cannot send messages or claim an external action occurred.</p><p>Client questions requiring judgment must be routed into the GoClear admin review queue.</p><ClientStatusBadge tone="green">No messages sent</ClientStatusBadge></ClientSection></div><ClientGuidePanel compact /></div>
}

export function ClientSettingsPage() {
  const profile = data.clientProfile
  return <div className="client-page"><ClientPageHeader title="Settings" subtitle="Review demo membership and portal preferences." badge="Preview only" /><div className="client-settings-grid"><ClientSection title="Demo profile">{Object.entries(profile).map(([key, value]) => <div className="client-setting-row" key={key}><span>{key.replaceAll(/([A-Z])/g, ' $1')}</span><strong>{value}</strong></div>)}</ClientSection><ClientSection title="Privacy and assistant boundaries"><div className="client-setting-row"><span>Hermes Advisor</span><strong>Private/admin only</strong></div><div className="client-setting-row"><span>Client assistant</span><strong>Nexus Guide</strong></div><div className="client-setting-row"><span>Real client data</span><strong>Not used</strong></div><div className="client-setting-row"><span>External actions</span><strong>Disabled</strong></div></ClientSection><ClientSection title="Portal status"><Settings size={28} /><p>This frontend is powered by static demo data and Supabase-ready local exports. Production inserts and private file storage are not connected.</p></ClientSection></div><ClientGuidePanel compact /></div>
}

export const clientPageMap = {
  '/client/dashboard': <ClientDashboard />,
  '/client/credit-profile': <CreditProfilePage />,
  '/client/credit-utilization': <CreditUtilizationPage />,
  '/client/documents': <ClientDocumentsPage />,
  '/client/business-setup': <BusinessSetupPage />,
  '/client/business-bankability': <BusinessBankabilityPage />,
  '/client/funding-readiness': <FundingReadinessPage />,
  '/client/recommendations': <RecommendationsPage />,
  '/client/resources': <ResourcesPage />,
  '/client/request-review': <RequestReviewPage />,
  '/client/messages': <ClientMessagesPage />,
  '/client/settings': <ClientSettingsPage />,
}
