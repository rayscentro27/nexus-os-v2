import React, { useEffect, useState } from 'react'
import {
  BadgeCheck, Building2, CheckCircle2, CircleAlert, FileCheck2, FileText, Gauge,
  Landmark, LockKeyhole, Mail, SearchCheck, Settings, TrendingUp, Upload,
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
    <div className="client-metric-grid dashboard">
      <ClientScoreCard title="Overall Readiness" value={71} status="Building momentum" text="Complete this month’s highest-impact tasks before requesting funding review." />
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

export function CreditRepairPage() {
  const repair = data.creditRepair
  return <div className="client-page">
    <ClientPageHeader title="Credit Repair" subtitle="Track reviewed items, draft status, and your safe next actions." badge="No automatic disputes" />
    <div className="client-metric-grid">
      <ClientScoreCard title="Repair Progress" value={repair.progressPercent} label="%" status="In progress" text="GoClear is reviewing demo records and draft materials. No external contact has occurred." />
      <ClientMetricCard icon={SearchCheck} label="Items Under Review" value={repair.negativeItemsUnderReview} note="Demo records" tone="purple" />
      <ClientMetricCard icon={FileText} label="Draft Letters" value={repair.draftLettersReady} note="Not sent" />
      <ClientMetricCard icon={CheckCircle2} label="GoClear Reviews" value={repair.goclearReviewsPending} note="Pending" tone="orange" />
    </div>
    <div className="client-workflow-strip">{repair.workflowStages.map(([name, status], index) => <article key={name}><span className={status === 'complete' ? 'done' : ''}>{status === 'complete' ? '✓' : index + 1}</span><strong>{name}</strong><small>{status.replaceAll('_', ' ')}</small></article>)}</div>
    <div className="client-two-col">
      <ClientSection title="Negative items under review" action="Demo only"><div className="client-record-list">{repair.negativeItems.map(item => <article key={item.id}><div><strong>{item.title}</strong><small>{item.summary}</small></div><ClientStatusBadge tone={item.status === 'draft_ready' ? 'purple' : 'orange'}>{item.status.replaceAll('_', ' ')}</ClientStatusBadge></article>)}</div></ClientSection>
      <ClientSection title="Your next actions"><ClientActionList rows={repair.nextActions} /></ClientSection>
    </div>
    <ClientGuidePanel suggestedKeys={['what_do_i_do_next', 'what_goclear_is_reviewing', 'how_to_improve_credit']} />
  </div>
}

export function CreditProfileReadinessPage() {
  const profile = data.creditProfileReadiness
  return <div className="client-page">
    <ClientPageHeader title="Credit Profile Readiness" subtitle="Understand your educational Nexus Readiness Score and what may improve readiness." badge="Not FICO" />
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

export function BusinessProfileReadinessPage() {
  const business = data.businessProfileReadiness
  return <div className="client-page">
    <ClientPageHeader title="Business Profile Readiness" subtitle="Build a consistent, documented business profile before funding review." badge="Profile builder" />
    <div className="client-metric-grid"><ClientScoreCard title="Business Readiness" value={business.readinessScore} status="Good start" text={business.fundingImpactNotes} /><ClientMetricCard icon={CheckCircle2} label="Completed" value={`${business.completedItems}/10`} note="Checklist items" tone="green" /><ClientMetricCard icon={CircleAlert} label="Missing / Weak" value={business.missingItems} note="Needs attention" tone="orange" /><ClientMetricCard icon={LockKeyhole} label="Funding Blockers" value={business.fundingBlockers} note="Resolve before review" tone="red" /></div>
    <div className="client-two-col wide-left">
      <ClientSection title="Fundability checklist"><div className="client-check-grid">{business.fundabilityChecklist.map(([name, status]) => <article key={name}><span className={status === 'complete' ? 'done' : ''}>{status === 'complete' ? '✓' : '!'}</span><strong>{name}</strong><ClientStatusBadge tone={status === 'complete' ? 'green' : status === 'missing' ? 'red' : 'orange'}>{status.replaceAll('_', ' ')}</ClientStatusBadge></article>)}</div></ClientSection>
      <ClientSection title="Recommended next steps"><ClientActionList rows={business.recommendedNextSteps} /></ClientSection>
    </div>
    <ClientGuidePanel suggestedKeys={['business_profile_next_step', 'documents_needed', 'what_do_i_do_next']} />
  </div>
}

export function BusinessOpportunitiesPage() {
  const opportunities = data.businessOpportunities
  return <div className="client-page">
    <ClientPageHeader title="Business Opportunities" subtitle="Explore educational paths matched to your current demo readiness—not guaranteed offers." badge="Fit review required" />
    <div className="client-metric-grid compact"><ClientScoreCard title="Opportunity Score" value={opportunities.opportunityScore} status="Strong potential" text="Improve readiness gaps before selecting a funding or partner path." /><ClientMetricCard icon={BadgeCheck} label="Matched Paths" value={opportunities.matchedOpportunities.length} note="Educational matches" tone="purple" /><ClientMetricCard icon={Landmark} label="Funding Paths" value={opportunities.fundingPaths.length} note="GoClear review required" /></div>
    <div className="client-three-col"><ClientSection title="Matched opportunities"><ClientActionList rows={opportunities.matchedOpportunities} /></ClientSection><ClientSection title="Funding paths"><ClientActionList rows={opportunities.fundingPaths} /></ClientSection><ClientSection title="Partner/tool options"><ClientActionList rows={opportunities.partnerOffers} /><p className="client-safe-note">Best client outcome first. Affiliate value second. Free/DIY options remain visible.</p></ClientSection></div>
    <ClientGuidePanel suggestedKeys={['what_opportunity_should_i_focus_on', 'can_i_apply_for_funding_now', 'what_do_i_do_next']} />
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

export function ClientDocumentsPage() {
  const docs = data.documents
  const sections = [['Required documents', docs.requiredDocuments, 'blue'], ['Uploaded', docs.uploadedDocuments, 'green'], ['Missing', docs.missingDocuments, 'orange'], ['Under GoClear review', docs.underReviewDocuments, 'purple']]
  return <div className="client-page"><ClientPageHeader title="Documents" subtitle="Track demo readiness documents and GoClear review status." badge="Demo files only" /><div className="client-four-col documents">{sections.map(([title, rows, tone]) => <ClientSection title={title} key={title}>{rows.map(row => <article className="client-document-row" key={row}><FileText size={19} /><strong>{row}</strong><ClientStatusBadge tone={tone}>{title}</ClientStatusBadge></article>)}</ClientSection>)}</div><div className="client-upload-placeholder"><Upload size={28} /><strong>Upload is disabled in this prototype</strong><p>Production document upload requires private storage, consent, tenant isolation, and GoClear approval.</p></div><ClientGuidePanel suggestedKeys={['documents_needed', 'what_goclear_is_reviewing', 'what_do_i_do_next']} /></div>
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
  '/client/credit-repair': <CreditRepairPage />,
  '/client/credit-profile-readiness': <CreditProfileReadinessPage />,
  '/client/business-profile-readiness': <BusinessProfileReadinessPage />,
  '/client/business-opportunities': <BusinessOpportunitiesPage />,
  '/client/funding-readiness': <FundingReadinessPage />,
  '/client/documents': <ClientDocumentsPage />,
  '/client/messages': <ClientMessagesPage />,
  '/client/settings': <ClientSettingsPage />,
}
