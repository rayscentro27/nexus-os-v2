import React, { useEffect, useState } from 'react'
import {
  BadgeCheck, Building2, CheckCircle2, CircleAlert, FileCheck2, FileText, Gauge,
  Landmark, LockKeyhole, Mail, SearchCheck, Settings, TrendingUp, Upload,
  Star, MessageSquare, Lightbulb, CreditCard, ArrowUpCircle, Send,
  Rocket, Shield, Wallet, CircleCheck, ChevronRight, Sparkles,
  ArrowRight, Copy, Users, Lock,
} from 'lucide-react'
import { ClientGuidePanel } from '../../components/client/ClientGuidePanel'
import { DocumentUploadZone } from '../../components/client/DocumentUploadZone'
import {
  ClientActionList, ClientFactorGrid, ClientMetricCard, ClientPageHeader, ClientScoreCard,
  ClientSection, ClientStatusBadge,
} from '../../components/client/ClientPortalUI'
import { usePortalNav } from '../../components/client/ClientPortalShell'
import { clientPortalData as data } from '../../data/clientPortalData'
import { clientDataMode } from '../../data/clientDataMode'
import { loadClientDashboardLiveData } from '../../services/clientDashboardLiveData'
import { supabase } from '../../lib/supabaseClient'
import { resolveClientContextForCurrentUser } from '../../lib/clientAuthContext'

const score = data.readinessScores

const fundingJourneySteps = [
  { label: 'Upload Credit Report', sublabel: 'Credit Report', icon: Upload, status: 'complete', detail: 'Completed', route: '/client/documents' },
  { label: 'AI Credit Analysis', sublabel: 'AI Analysis', icon: SearchCheck, status: 'complete', detail: 'Completed', route: '/client/credit-profile' },
  { label: 'Funding Strategy', sublabel: 'Strategy', icon: Wallet, status: 'complete', detail: '$0-95', route: '/client/funding-readiness' },
  { label: 'Business Opportunities', sublabel: 'Opportunities', icon: Building2, status: 'in_progress', detail: '72% Complete', route: '/client/recommendations' },
]

const businessOpportunities = [
  { title: 'ATM Business', difficulty: 'Easy', investment: '$3,000 – $10,000', desc: 'Low overhead, consistent flow.', color: '#e0f2fe' },
  { title: 'Local Cleaning Service', difficulty: 'Easy', investment: '$4,000 – $8,000', desc: 'Secure start, high demand, cash flow.', color: '#f0fdf4' },
  { title: 'E-commerce Store', difficulty: 'Medium', investment: '$8,000 – $20,000', desc: 'Home-based, scalable online sales.', color: '#fef3c7' },
]

export function ClientDashboard() {
  const navigate = usePortalNav()
  const [live, setLive] = useState(null)
  useEffect(() => {
    if (clientDataMode.liveSupabaseTestClientEnabled) loadClientDashboardLiveData().then(setLive)
  }, [])
  const liveProfile = live?.profile
  const dashboardTasks = live?.tasks?.length ? live.tasks : data.clientTasks
  const badge = liveProfile ? 'Live test data' : 'Demo data'
  return <div className="client-page client-dashboard-page">
    <ClientPageHeader title="Dashboard" subtitle="Your credit, business, and funding-readiness snapshot." badge={badge} />

    {/* Hero: Next Step CTA */}
    <div className="client-card" style={{ marginBottom: 10, padding: '10px 14px', background: 'linear-gradient(135deg, rgba(14,165,233,.06), rgba(20,184,166,.04))', border: '1px solid rgba(14,165,233,.15)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ width: 34, height: 34, borderRadius: 10, background: 'linear-gradient(135deg, var(--cp-cyan), var(--cp-blue))', display: 'grid', placeItems: 'center', color: 'white', flexShrink: 0 }}><Rocket size={16} /></div>
        <div style={{ flex: 1 }}>
          <h3 style={{ margin: 0, fontSize: 13, fontWeight: 700 }}>Upload Your Credit Report</h3>
          <p style={{ margin: '1px 0 0', fontSize: 11, color: 'var(--cp-muted)' }}>Unlocks your funding strategy and estimated range — takes 2 minutes.</p>
        </div>
        <button className="cp-btn-primary" onClick={() => navigate('/client/documents')}>Upload Now</button>
      </div>
    </div>

    {/* Funding Journey */}
    <div className="client-card" style={{ marginBottom: 10, padding: '10px 14px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <h2 style={{ fontSize: 13, fontWeight: 800 }}>Funding Journey</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--cp-blue)' }}>72%</span>
          <div style={{ width: 50, height: 4, borderRadius: 3, background: '#e9edf5', overflow: 'hidden' }}><div style={{ width: '72%', height: '100%', borderRadius: 3, background: 'linear-gradient(90deg, var(--cp-cyan), var(--cp-blue))' }} /></div>
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6 }}>
        {fundingJourneySteps.map((step, i) => {
          const Icon = step.icon
          return <div key={i} onClick={() => navigate(step.route)} style={{ padding: '8px 6px', borderRadius: 8, border: '1px solid var(--cp-border-light)', background: step.status === 'complete' ? 'rgba(16,185,129,.04)' : 'transparent', textAlign: 'center', cursor: 'pointer', transition: 'all .15s' }}>
            <div style={{ width: 28, height: 28, borderRadius: 7, background: step.status === 'complete' ? 'rgba(16,185,129,.1)' : 'rgba(14,165,233,.1)', display: 'grid', placeItems: 'center', margin: '0 auto 3px', color: step.status === 'complete' ? 'var(--cp-green)' : 'var(--cp-cyan)' }}><Icon size={14} /></div>
            <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--cp-navy)' }}>{step.sublabel}</div>
            <div style={{ fontSize: 9, color: step.status === 'complete' ? 'var(--cp-green)' : 'var(--cp-muted)', marginTop: 1 }}>{step.detail}</div>
          </div>
        })}
      </div>
    </div>

    {/* Estimated Funding Range */}
    <div className="client-card" style={{ marginBottom: 10, padding: '10px 14px', background: 'linear-gradient(135deg, rgba(37,99,235,.04), rgba(14,165,233,.03))' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <h2 style={{ fontSize: 13, fontWeight: 800 }}>Estimated Funding Range</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 10, color: 'var(--cp-muted)' }}>Level 2</span>
          <div style={{ width: 40, height: 4, borderRadius: 3, background: '#e9edf5', overflow: 'hidden' }}><div style={{ width: '50%', height: '100%', borderRadius: 3, background: 'var(--cp-blue)' }} /></div>
          <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--cp-blue)' }}>72%</span>
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
        <span style={{ fontSize: 20, fontWeight: 800, color: 'var(--cp-navy)' }}>$25,000 – $80,000</span>
        <span style={{ padding: '3px 8px', borderRadius: 14, background: 'rgba(245,158,11,.1)', color: 'var(--cp-orange)', fontWeight: 700, fontSize: 10 }}>Medium</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <span style={{ fontSize: 11, color: 'var(--cp-green)', fontWeight: 600 }}>✓ 28% ready for funding</span>
        <span style={{ fontSize: 10, color: 'var(--cp-muted)' }}>• Reduce utilization under 30% to improve odds.</span>
      </div>
      <button className="cp-btn-primary" style={{ width: '100%' }} onClick={() => navigate('/client/credit-utilization')}>Improve Approval Odds</button>
      <p style={{ fontSize: 9, color: 'var(--cp-muted-light)', textAlign: 'center', marginTop: 4 }}>Educational estimate only, not a lending decision</p>
    </div>

    {/* Summary metric cards */}
    <div className="client-metric-grid dashboard">
      <ClientScoreCard title="Overall Readiness" value={71} status="Building momentum" text="Complete this month's highest-impact tasks before requesting funding review." onClick={() => navigate('/client/funding-readiness')} />
      <ClientMetricCard icon={BadgeCheck} label="Credit Profile" value={score.creditProfileReadiness} note="Nexus Readiness Score" tone="green" onClick={() => navigate('/client/credit-profile')} />
      <ClientMetricCard icon={Building2} label="Business Profile" value={score.businessProfileReadiness} note="Four gaps remain" tone="purple" onClick={() => navigate('/client/business-setup')} />
      <ClientMetricCard icon={Landmark} label="Funding Readiness" value={score.fundingReadiness} note="Almost Ready" tone="orange" onClick={() => navigate('/client/funding-readiness')} />
    </div>

    {/* Dashboard grid — actions + readiness */}
    <div className="client-dashboard-grid">
      <ClientSection title="Your next actions" action={`${dashboardTasks.length} open`}>
        <ClientActionList rows={dashboardTasks.map(t => ({
          title: t.title,
          status: t.status?.replaceAll('_', ' '),
          _route: t.category === 'documents' ? '/client/documents' : t.category === 'credit_repair' || t.category === 'credit_profile_readiness' ? '/client/credit-profile' : '/client/business-setup',
        }))} onNavigate={navigate} />
      </ClientSection>
      <ClientSection title="Readiness overview">
        {[['Credit profile', score.creditProfileReadiness, '/client/credit-profile'], ['Business profile', score.businessProfileReadiness, '/client/business-setup'], ['Funding readiness', score.fundingReadiness, '/client/funding-readiness'], ['Business opportunities', score.businessOpportunityScore, '/client/recommendations']].map(([name, value, route]) => <div className="client-bar-row" key={name} style={{ cursor: 'pointer' }} onClick={() => navigate(route)}><span>{name}</span><div><i style={{ width: `${value}%` }} /></div><strong>{value}</strong></div>)}
      </ClientSection>
    </div>

    {/* Quick Links Row */}
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 10 }}>
      <div className="client-card" style={{ padding: '10px 12px', cursor: 'pointer' }} onClick={() => navigate('/client/documents')}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 28, height: 28, borderRadius: 7, background: 'rgba(239,68,68,.1)', display: 'grid', placeItems: 'center', color: 'var(--cp-red)' }}><FileText size={14} /></div>
          <div><strong style={{ fontSize: 12 }}>Documents Needed</strong><div style={{ fontSize: 10, color: 'var(--cp-red)' }}>3 pending</div></div>
        </div>
      </div>
      <div className="client-card" style={{ padding: '10px 12px', cursor: 'pointer' }} onClick={() => navigate('/client/business-setup')}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 28, height: 28, borderRadius: 7, background: 'rgba(124,58,237,.1)', display: 'grid', placeItems: 'center', color: 'var(--cp-purple)' }}><Building2 size={14} /></div>
          <div><strong style={{ fontSize: 12 }}>Business Setup</strong><div style={{ fontSize: 10, color: 'var(--cp-muted)' }}>60% complete</div></div>
        </div>
      </div>
      <div className="client-card" style={{ padding: '10px 12px', cursor: 'pointer' }} onClick={() => navigate('/client/messages')}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 28, height: 28, borderRadius: 7, background: 'rgba(37,99,235,.1)', display: 'grid', placeItems: 'center', color: 'var(--cp-blue)' }}><Mail size={14} /></div>
          <div><strong style={{ fontSize: 12 }}>Messages</strong><div style={{ fontSize: 10, color: 'var(--cp-blue)' }}>2 unread</div></div>
        </div>
      </div>
    </div>

    {/* Recommended Tools */}
    <div className="client-card" style={{ padding: '10px 14px', marginBottom: 10 }}>
      <h2 style={{ fontSize: 13, fontWeight: 800, marginBottom: 6 }}>Recommended Tools</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6 }}>
        {[
          { icon: '📊', title: 'Credit Monitoring', desc: 'Track changes across all 3 bureaus.', route: '/client/resources' },
          { icon: '✉️', title: 'Mail Letters Online', desc: 'Send dispute letters securely.', route: '/client/resources' },
          { icon: '🏦', title: 'Business Banking', desc: 'Open a business checking account.', route: '/client/business-setup' },
        ].map(tool => <div key={tool.title} className="client-tool-card" onClick={() => navigate(tool.route)} style={{ cursor: 'pointer' }}>
          <div className="client-tool-icon">{tool.icon}</div>
          <div><strong>{tool.title}</strong><p>{tool.desc}</p></div>
        </div>)}
      </div>
    </div>

    <ClientGuidePanel />
  </div>
}

export function CreditProfilePage() {
  const navigate = usePortalNav()
  const profile = data.creditProfileReadiness
  return <div className="client-page">
    <ClientPageHeader title="Credit Profile" subtitle="Understand your educational Nexus Readiness Score and what may improve readiness." badge="Not FICO" />
    <div className="client-metric-grid compact">
      <ClientScoreCard title="Nexus Readiness Score" value={profile.overallScore} status="Good progress" text={profile.scoreDisclaimer} />
      <ClientMetricCard icon={TrendingUp} label="Progress" value="+14" note="Demo six-month trend" tone="green" />
      <ClientMetricCard icon={CircleAlert} label="Attention Factors" value={profile.negativeFactors.length} note="Review safely" tone="orange" />
    </div>
    <ClientSection title="Score factors" action="Educational only"><ClientFactorGrid rows={profile.scoreFactors} /></ClientSection>
    <div className="client-two-col">
      <ClientSection title="Positive factors"><ul>{profile.positiveFactors.map(x => <li key={x}>{x}</li>)}</ul></ClientSection>
      <ClientSection title="Factors needing attention"><ul>{profile.negativeFactors.map(x => <li key={x}>{x}</li>)}</ul></ClientSection>
    </div>
    <ClientSection title="Top actions">
      <ClientActionList rows={profile.topActions.map(a => ({ title: a, status: 'recommended', _route: a.toLowerCase().includes('utilization') ? '/client/credit-utilization' : a.toLowerCase().includes('document') ? '/client/documents' : '/client/credit-profile' }))} onNavigate={navigate} />
    </ClientSection>
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginTop: 10 }}>
      <button className="cp-btn-primary" onClick={() => navigate('/client/resources')}>Connect Monitoring</button>
      <button className="cp-btn-outline" onClick={() => navigate('/client/documents')}>Upload Report</button>
      <button className="cp-btn-outline" onClick={() => navigate('/client/resources')}>Free Report Options</button>
    </div>
    <div className="client-card" style={{ padding: '10px 14px', marginTop: 10, background: '#f7fbff' }}>
      <strong style={{ color: 'var(--cp-blue)' }}>💡 Did You Know?</strong>
      <span style={{ color: 'var(--cp-muted)', fontSize: 12 }}> Businesses with utilization below 30% are more likely to qualify for stronger funding terms.</span>
    </div>
    <ClientGuidePanel suggestedKeys={['how_to_improve_credit', 'what_do_i_do_next', 'what_goclear_is_reviewing']} />
  </div>
}

export function CreditUtilizationPage() {
  const navigate = usePortalNav()
  const profile = data.creditProfileReadiness
  const utilizationFactor = profile.scoreFactors.find(f => f[0] === 'Utilization')
  const utilizationScore = utilizationFactor ? utilizationFactor[1] : 58
  return <div className="client-page">
    <ClientPageHeader title="Credit Utilization" subtitle="Review your revolving credit utilization and create a pay-down plan." badge="Balance management" />
    <div className="client-metric-grid compact">
      <ClientScoreCard title="Utilization Score" value={utilizationScore} status={utilizationScore >= 70 ? 'On track' : 'Needs attention'} text="Lower utilization may improve your funding readiness." />
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
          { title: 'Pay down Card B first (highest utilization)', status: 'recommended', _route: '/client/documents' },
          { title: 'Keep Card C below 30%', status: 'on_track', _route: '/client/credit-profile' },
          { title: 'Avoid new revolving accounts', status: 'important', _route: '/client/credit-profile' },
          { title: 'Request credit limit increase (optional)', status: 'optional', _route: '/client/resources' },
        ]} onNavigate={navigate} />
      </ClientSection>
    </div>
    <ClientGuidePanel suggestedKeys={['how_to_improve_credit', 'what_do_i_do_next', 'can_i_apply_for_funding_now']} />
  </div>
}

export function ClientDocumentsPage() {
  const navigate = usePortalNav()
  const docs = data.documents
  const [liveDocs, setLiveDocs] = useState(null)
  const [liveDocsLoading, setLiveDocsLoading] = useState(false)
  useEffect(() => {
    if (!clientDataMode.liveSupabaseTestClientEnabled) return
    let cancelled = false
    setLiveDocsLoading(true)
    import('../../services/clientDashboardLiveData').then(m => m.loadClientDashboardLiveData()).then(result => {
      if (!cancelled) {
        setLiveDocs({ data: result.documents || [], source: result.status })
        setLiveDocsLoading(false)
      }
    }).catch(() => { if (!cancelled) setLiveDocsLoading(false) })
    return () => { cancelled = true }
  }, [])

  const displayDocs = liveDocs && liveDocs.data.length > 0 ? liveDocs : null
  const requiredDocuments = displayDocs
    ? Array.from(new Set(displayDocs.data.map(d => d.category || d.title).filter(Boolean)))
    : docs.requiredDocuments
  const uploadedDocuments = displayDocs
    ? displayDocs.data.filter(d => ['uploaded', 'pending_review', 'complete', 'approved'].includes((d.status || '').toLowerCase())).map(d => d.title || d.category).filter(t => t)
    : docs.uploadedDocuments
  const missingDocuments = displayDocs
    ? requiredDocuments.filter(r => !uploadedDocuments.some(u => u === r || r.includes(u) || u.includes(r)))
    : docs.missingDocuments
  const underReviewDocuments = displayDocs
    ? displayDocs.data.filter(d => (d.goclear_review_status || d.status || '').toLowerCase().includes('pending') || (d.goclear_review_status || d.status || '').toLowerCase().includes('review')).map(d => d.title).filter(Boolean)
    : docs.underReviewDocuments
  const sections = [['Required documents', requiredDocuments, 'blue'], ['Uploaded', uploadedDocuments, 'green'], ['Missing', missingDocuments, 'orange'], ['Under GoClear review', underReviewDocuments, 'purple']]
  const badge = displayDocs ? `Live docs (${displayDocs.data.length})` : (docs.uploadState === 'storage_and_rls_pending' ? 'Upload ready' : 'Demo files only')

  return <div className="client-page">
    <ClientPageHeader title="Documents" subtitle="Track readiness documents and upload new files for GoClear review." badge={badge} />
    {displayDocs && <div className="client-card" style={{ padding: '10px 14px', marginBottom: 10, background: 'rgba(16,185,129,.04)', border: '1px solid rgba(16,185,129,.15)' }}><strong style={{ color: 'var(--cp-green)', fontSize: 12 }}>Live data connected</strong><span style={{ fontSize: 11, color: 'var(--cp-muted)', marginLeft: 8 }}>Showing {displayDocs.data.length} document(s) from Supabase client_documents for the current test client. Source: {displayDocs.source}.</span></div>}
    {liveDocsLoading && <div style={{ color: '#8fa3be', fontSize: 12, padding: 8 }}>Loading live documents...</div>}
    <div className="client-four-col documents">{sections.map(([title, rows, tone]) => <ClientSection title={title} key={title}>{rows.map(row => <article className="client-document-row" key={row}><FileText size={19} /><strong>{row}</strong><ClientStatusBadge tone={tone}>{title}</ClientStatusBadge></article>)}</ClientSection>)}</div>
    <ClientSection title="Upload documents"><DocumentUploadZone /><p className="client-upload-note">Uploaded files are stored securely in Supabase Storage. GoClear will review submissions within 2 business days.</p></ClientSection>
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginTop: 10 }}>
      <div className="client-card" style={{ padding: '10px 12px', cursor: 'pointer' }} onClick={() => navigate('/client/documents')}>
        <strong style={{ fontSize: 12 }}>Uploaded Documents</strong>
        <div style={{ fontSize: 10, color: 'var(--cp-green)', marginTop: 4 }}>{uploadedDocuments.length} verified</div>
      </div>
      <div className="client-card" style={{ padding: '10px 12px', cursor: 'pointer' }} onClick={() => navigate('/client/documents')}>
        <strong style={{ fontSize: 12 }}>Signed Forms</strong>
        <div style={{ fontSize: 10, color: 'var(--cp-green)', marginTop: 4 }}>{Math.max(0, uploadedDocuments.length - 1)} signed</div>
      </div>
      <div className="client-card" style={{ padding: '10px 12px', cursor: 'pointer' }} onClick={() => navigate('/client/documents')}>
        <strong style={{ fontSize: 12 }}>Credit Reports</strong>
        <div style={{ fontSize: 10, color: 'var(--cp-green)', marginTop: 4 }}>1 complete</div>
      </div>
    </div>
    <div className="client-card" style={{ padding: '10px 14px', marginTop: 10 }}>
      <strong>🔒 Your information is secure</strong><span style={{ color: 'var(--cp-muted)', fontSize: 12 }}> — Bank-level encryption keeps your data protected and private.</span>
    </div>
    <ClientGuidePanel suggestedKeys={['documents_needed', 'what_goclear_is_reviewing', 'what_do_i_do_next']} />
  </div>
}

export function BusinessSetupPage() {
  const navigate = usePortalNav()
  const business = data.businessProfileReadiness
  return <div className="client-page">
    <ClientPageHeader title="Business Setup" subtitle="Build a consistent, documented business profile before funding review." badge="Profile builder" />
    <div className="client-metric-grid compact">
      <ClientScoreCard title="Business Readiness" value={business.readinessScore} status="Good start" text={business.fundingImpactNotes} />
      <ClientMetricCard icon={CheckCircle2} label="Completed" value={`${business.completedItems}/10`} note="Checklist items" tone="green" />
      <ClientMetricCard icon={CircleAlert} label="Missing / Weak" value={business.missingItems} note="Needs attention" tone="orange" />
      <ClientMetricCard icon={LockKeyhole} label="Funding Blockers" value={business.fundingBlockers} note="Resolve before review" tone="red" />
    </div>
    <div className="client-two-col">
      <ClientSection title="Fundability checklist">
        <div className="client-check-grid">{business.fundabilityChecklist.map(([name, status]) => <article key={name}><span className={status === 'complete' ? 'done' : ''}>{status === 'complete' ? '✓' : '!'}</span><strong>{name}</strong><ClientStatusBadge tone={status === 'complete' ? 'green' : status === 'missing' ? 'red' : 'orange'}>{status.replaceAll('_', ' ')}</ClientStatusBadge></article>)}</div>
      </ClientSection>
      <ClientSection title="Recommended next steps">
        <ClientActionList rows={business.recommendedNextSteps.map(s => ({
          title: s,
          status: 'recommended',
          _route: s.toLowerCase().includes('email') || s.toLowerCase().includes('domain') ? '/client/business-setup' : s.toLowerCase().includes('duns') || s.toLowerCase().includes('bank') ? '/client/business-bankability' : '/client/business-setup',
        }))} onNavigate={navigate} />
      </ClientSection>
    </div>

    {/* Banking Readiness */}
    <div className="client-card" style={{ padding: '10px 14px', marginTop: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <div style={{ width: 28, height: 28, borderRadius: 7, background: 'rgba(124,58,237,.1)', display: 'grid', placeItems: 'center', color: 'var(--cp-purple)' }}><Landmark size={14} /></div>
        <strong style={{ fontSize: 13 }}>Business Banking Readiness</strong>
      </div>
      <p style={{ fontSize: 11, color: 'var(--cp-muted)', marginBottom: 8 }}>A business bank account is essential to access funding and build credibility.</p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6 }}>
        {[
          { title: 'Open Online Bank Account', desc: 'Open a new business checking account.', icon: '🏦' },
          { title: 'Add Existing Account', desc: 'Connect your existing business bank.', icon: '▣' },
          { title: 'Relationship Bank', desc: 'Use your current bank relationship.', icon: '👥' },
        ].map(item => <div key={item.title} className="client-tool-card" onClick={() => navigate('/client/business-bankability')} style={{ cursor: 'pointer' }}>
          <div className="client-tool-icon" style={{ background: 'rgba(124,58,237,.1)', color: 'var(--cp-purple)' }}>{item.icon}</div>
          <div><strong>{item.title}</strong><p>{item.desc}</p></div>
        </div>)}
      </div>
    </div>

    {/* Recommended Providers */}
    <div className="client-card" style={{ padding: '10px 14px', marginTop: 10 }}>
      <h2 style={{ fontSize: 13, fontWeight: 800, marginBottom: 6 }}>Recommended Providers</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6 }}>
        {[
          { icon: '🏛', title: 'Business Formation', desc: 'Form your LLC quickly.', route: '/client/resources' },
          { icon: '🏦', title: 'Business Bank Account', desc: 'Open a business account.', route: '/client/business-bankability' },
          { icon: '☎', title: 'Business Phone & Address', desc: 'Professional phone and address.', route: '/client/resources' },
        ].map(tool => <div key={tool.title} className="client-tool-card" onClick={() => navigate(tool.route)} style={{ cursor: 'pointer' }}>
          <div className="client-tool-icon">{tool.icon}</div>
          <div><strong>{tool.title}</strong><p>{tool.desc}</p></div>
        </div>)}
      </div>
    </div>
    <ClientGuidePanel suggestedKeys={['business_profile_next_step', 'documents_needed', 'what_do_i_do_next']} />
  </div>
}

export function BusinessBankabilityPage() {
  const navigate = usePortalNav()
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
          { title: 'Online business bank (Bluevine, Mercury, Relay)', status: 'recommended', _route: '/client/resources' },
          { title: 'Credit union business account', status: 'alternative', _route: '/client/resources' },
          { title: 'Community bank relationship', status: 'alternative', _route: '/client/resources' },
        ]} onNavigate={navigate} />
        <p className="client-safe-note">Bank recommendations are educational. No account has been opened.</p>
      </ClientSection>
    </div>
    <ClientGuidePanel suggestedKeys={['business_profile_next_step', 'documents_needed', 'what_do_i_do_next']} />
  </div>
}

export function FundingReadinessPage() {
  const navigate = usePortalNav()
  const funding = data.fundingReadiness
  const groups = [['Personal credit blockers', funding.personalCreditBlockers], ['Business profile blockers', funding.businessProfileBlockers], ['Banking blockers', funding.bankingBlockers], ['Document blockers', funding.documentBlockers]]
  return <div className="client-page">
    <ClientPageHeader title="Funding Readiness" subtitle="See what must be completed before GoClear can review an application path." badge={funding.status} />
    <div className="client-metric-grid compact">
      <ClientScoreCard title="Funding Readiness" value={funding.readinessScore} status={funding.status} text={funding.recommendedPath} />
      <ClientMetricCard icon={LockKeyhole} label="Blocker Groups" value={groups.length} note="No application yet" tone="red" />
      <ClientMetricCard icon={FileCheck2} label="GoClear Status" value="Pending" note="Approval required" tone="orange" />
    </div>
    <div className="client-warning"><CircleAlert size={22} /><div><strong>Avoid applying right now</strong><p>{funding.avoidApplicationWarning}</p></div></div>

    {/* Top Blockers */}
    <div className="client-card" style={{ padding: '10px 14px', marginBottom: 10 }}>
      <h2 style={{ fontSize: 13, fontWeight: 800, marginBottom: 6 }}>Top Blockers</h2>
      <div style={{ display: 'grid', gap: 4 }}>
        {[
          { title: 'High Credit Utilization', desc: 'Revolving utilization is too high.', route: '/client/credit-utilization' },
          { title: 'Missing Business Bank Account', desc: 'Lenders want to see active banking.', route: '/client/business-bankability' },
          { title: 'Thin Credit History', desc: 'Business credit history is limited.', route: '/client/credit-profile' },
          { title: 'Missing Revenue Documents', desc: 'Provide proof of revenue.', route: '/client/documents' },
        ].map(blocker => <div key={blocker.title} className="client-tool-card" onClick={() => navigate(blocker.route)} style={{ cursor: 'pointer' }}>
          <div className="client-tool-icon" style={{ background: 'rgba(239,68,68,.1)', color: 'var(--cp-red)' }}>!</div>
          <div><strong>{blocker.title}</strong><p>{blocker.desc}</p></div>
        </div>)}
      </div>
    </div>

    {/* Next Best Actions */}
    <div className="client-card" style={{ padding: '10px 14px', marginBottom: 10 }}>
      <h2 style={{ fontSize: 13, fontWeight: 800, marginBottom: 6 }}>Next Best Actions</h2>
      <ClientActionList rows={[
        { title: 'Open a Business Bank Account', status: 'high priority', _route: '/client/business-bankability' },
        { title: 'Lower Your Credit Utilization', status: 'high priority', _route: '/client/credit-utilization' },
        { title: 'Add Revenue Documentation', status: 'medium priority', _route: '/client/documents' },
        { title: 'Build Business Credit', status: 'medium priority', _route: '/client/recommendations' },
      ]} onNavigate={navigate} />
    </div>

    <div className="client-four-col">{groups.map(([title, rows]) => <ClientSection title={title} key={title}><ul>{rows.map(x => <li key={x}>{x}</li>)}</ul></ClientSection>)}</div>

    {/* Readiness Factors */}
    <div className="client-three-col" style={{ marginTop: 10 }}>
      <ClientSection title="Readiness Factors">
        <div style={{ display: 'grid', gap: 4 }}>
          {[['Personal Credit', 'green', 'Good'], ['Business Setup', 'green', 'Good'], ['Banking', 'orange', 'Needs Work'], ['Revenue Docs', 'orange', 'Needs Work'], ['Time in Business', 'green', 'Good']].map(([name, tone, label]) => <div key={name} className="client-tool-card">
            <div className={`client-tool-icon`} style={{ background: tone === 'green' ? 'rgba(16,185,129,.1)' : 'rgba(245,158,11,.1)', color: tone === 'green' ? 'var(--cp-green)' : 'var(--cp-orange)' }}>{tone === 'green' ? '✓' : '!'}</div>
            <div style={{ flex: 1 }}><strong>{name}</strong></div>
            <ClientStatusBadge tone={tone}>{label}</ClientStatusBadge>
          </div>)}
        </div>
      </ClientSection>
      <ClientSection title="Potential Funding Paths">
        <div style={{ display: 'grid', gap: 4 }}>
          {[['Starter Business Credit', 'green', 'Ready'], ['Business Credit Cards', 'orange', 'Almost'], ['Lender Review', 'red', 'Locked']].map(([name, tone, label]) => <div key={name} className="client-tool-card">
            <div className="client-tool-icon">▣</div>
            <div style={{ flex: 1 }}><strong>{name}</strong></div>
            <ClientStatusBadge tone={tone}>{label}</ClientStatusBadge>
          </div>)}
        </div>
      </ClientSection>
      <ClientSection title="Recommended Tools">
        <div style={{ display: 'grid', gap: 4 }}>
          {[{ title: 'Business Bank Account', desc: 'Establish business banking.', route: '/client/business-bankability', icon: '🏦' }, { title: 'Credit Monitoring', desc: 'Track changes and stay on top.', route: '/client/resources', icon: '📊' }].map(tool => <div key={tool.title} className="client-tool-card" onClick={() => navigate(tool.route)} style={{ cursor: 'pointer' }}>
            <div className="client-tool-icon">{tool.icon}</div>
            <div><strong>{tool.title}</strong><p>{tool.desc}</p></div>
          </div>)}
        </div>
      </ClientSection>
    </div>

    <div className="client-card" style={{ padding: '10px 14px', background: '#f7fbff', marginTop: 10 }}>
      <strong style={{ color: 'var(--cp-blue)' }}>★ Small steps lead to big opportunities.</strong>
      <span style={{ color: 'var(--cp-muted)', fontSize: 12 }}> Keep going — you're building a stronger foundation for funding.</span>
    </div>
    <ClientGuidePanel suggestedKeys={['can_i_apply_for_funding_now', 'why_not_funding_ready', 'documents_needed']} />
  </div>
}

export function RecommendationsPage() {
  const navigate = usePortalNav()
  const opportunities = data.businessOpportunities
  return <div className="client-page">
    <ClientPageHeader title="Recommendations" subtitle="Explore educational paths matched to your current demo readiness — not guaranteed offers." badge="Fit review required" />
    <div className="client-metric-grid compact">
      <ClientScoreCard title="Opportunity Score" value={opportunities.opportunityScore} status="Strong potential" text="Improve readiness gaps before selecting a funding or partner path." />
      <ClientMetricCard icon={BadgeCheck} label="Matched Paths" value={opportunities.matchedOpportunities.length} note="Educational matches" tone="purple" />
      <ClientMetricCard icon={Landmark} label="Funding Paths" value={opportunities.fundingPaths.length} note="GoClear review required" />
    </div>
    <div className="client-three-col">
      <ClientSection title="Matched opportunities">
        <ClientActionList rows={opportunities.matchedOpportunities.map(o => ({ title: o, status: 'opportunity', _route: '/client/recommendations' }))} onNavigate={navigate} />
      </ClientSection>
      <ClientSection title="Funding paths">
        <ClientActionList rows={opportunities.fundingPaths.map(p => ({ title: p, status: 'goClear review required', _route: '/client/funding-readiness' }))} onNavigate={navigate} />
      </ClientSection>
      <ClientSection title="Partner/tool options">
        <ClientActionList rows={opportunities.partnerOffers.map(p => ({ title: p, status: 'partner', _route: '/client/resources' }))} onNavigate={navigate} />
        <p className="client-safe-note">Best client outcome first. Affiliate value second. Free/DIY options remain visible.</p>
      </ClientSection>
    </div>
    <ClientGuidePanel suggestedKeys={['what_opportunity_should_i_focus_on', 'can_i_apply_for_funding_now', 'what_do_i_do_next']} />
  </div>
}

export function ResourcesPage() {
  const navigate = usePortalNav()
  return <div className="client-page">
    <ClientPageHeader title="Resources & Affiliates" subtitle="Tools, services, and options to support your credit and business readiness." badge="Transparency" />
    <div className="client-three-col">
      <ClientSection title="Credit Monitoring">
        <ClientActionList rows={[
          { title: 'SmartCredit — credit monitoring', status: 'paid option', _route: '/client/resources' },
          { title: 'AnnualCreditReport.com — free reports', status: 'free', _route: '/client/resources' },
          { title: 'Credit Karma — free monitoring', status: 'free', _route: '/client/resources' },
        ]} onNavigate={navigate} />
        <p className="client-safe-note">Free options are listed. Affiliate relationships are disclosed.</p>
      </ClientSection>
      <ClientSection title="Mailing Options">
        <ClientActionList rows={[
          { title: 'Online mailing (dispute letters)', status: 'digital', _route: '/client/documents' },
          { title: 'Print and physical mail', status: 'physical', _route: '/client/documents' },
          { title: 'Certified mail (recommended for disputes)', status: 'recommended', _route: '/client/documents' },
        ]} onNavigate={navigate} />
        <p className="client-safe-note">Physical mailing requires GoClear approval and compliance review.</p>
      </ClientSection>
      <ClientSection title="Business Banking">
        <ClientActionList rows={[
          { title: 'Bluevine — online business checking', status: 'recommended', _route: '/client/business-bankability' },
          { title: 'Mercury — startup banking', status: 'option', _route: '/client/business-bankability' },
          { title: 'Relay — business banking', status: 'option', _route: '/client/business-bankability' },
          { title: 'Credit union business account', status: 'alternative', _route: '/client/business-bankability' },
        ]} onNavigate={navigate} />
        <p className="client-safe-note">No account has been opened. These are educational recommendations.</p>
      </ClientSection>
    </div>
    <div className="client-two-col">
      <ClientSection title="Credit Report Upload">
        <ClientActionList rows={[
          { title: 'Upload your credit report (PDF)', status: 'upload required', _route: '/client/documents' },
          { title: 'Connect SmartCredit for live data', status: 'not connected', _route: '/client/resources' },
          { title: 'Request GoClear review of report', status: 'requires upload first', _route: '/client/request-review' },
        ]} onNavigate={navigate} />
      </ClientSection>
      <ClientSection title="Bank Relationship Reminder">
        <div className="client-warning"><CircleAlert size={18} /><div><strong>Open a business bank account</strong><p>A business banking relationship supports funding readiness. Document the account after opening.</p></div></div>
        <button className="cp-btn-primary" style={{ width: '100%', marginTop: 8 }} onClick={() => navigate('/client/business-bankability')}>Go to Business Banking</button>
      </ClientSection>
    </div>
    <ClientGuidePanel suggestedKeys={['what_do_i_do_next', 'documents_needed', 'can_i_apply_for_funding_now']} />
  </div>
}

export function RequestReviewPage() {
  const navigate = usePortalNav()
  const funding = data.fundingReadiness
  const tasks = data.clientTasks
  const openTasks = tasks.filter(t => t.status !== 'complete')
  const [reviewState, setReviewState] = useState('idle')
  const [reviewError, setReviewError] = useState('')
  useEffect(() => {
    if (!clientDataMode.liveSupabaseTestClientEnabled) return
    let cancelled = false
    import('../../services/clientDashboardLiveData').then(m => m.loadClientDashboardLiveData()).then(result => {
      if (!cancelled && result.tasks.length > 0) {
        const hasPendingReview = result.tasks.some(t => (t.category === 'review_request' || t.task_type === 'review_request') && t.status === 'pending_admin_review')
        setReviewState(hasPendingReview ? 'submitted' : 'idle')
      }
    }).catch(() => {})
    return () => { cancelled = true }
  }, [])
  const highPriorityOpen = tasks.filter(t => t.priority === 'high' && t.status !== 'complete')
  const minimumDataMet = highPriorityOpen.length === 0
  const isSubmitting = reviewState === 'submitting'
  const isSubmitted = reviewState === 'submitted' || reviewState === 'error'

  async function handleSubmitReview() {
    if (isSubmitting || isSubmitted) return
    setReviewState('submitting')
    setReviewError('')
    try {
      if (!isSupabaseConfigured || !supabase) {
        setReviewError('Supabase is not configured in this environment.')
        setReviewState('error')
        return
      }
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) {
        setReviewError('You must be signed in to submit a review request.')
        setReviewState('error')
        return
      }

      const ctx = await resolveClientContextForCurrentUser()
      if (!ctx) {
        setReviewError('Could not resolve your client profile. Please sign out and sign back in or contact GoClear.')
        setReviewState('error')
        return
      }

      const requestPayload = {
        id: `${ctx.authUserId}_review_request_${Date.now()}`,
        tenant_id: ctx.tenantId,
        client_id: ctx.clientId,
        category: 'review_request',
        title: 'Client readiness review request',
        summary: 'Client submitted their profile for GoClear readiness review via the client portal.',
        status: 'pending_admin_review',
        priority: 'high',
        risk_level: 'medium',
        automation_level: 'manual',
        client_visible: true,
        approval_required: true,
        goclear_review_status: 'pending_admin_review',
        source: 'client_portal',
        source_concept: 'request_review',
        recommended_next_action: 'Admin review readiness and respond via approved_client_guidance',
        created_at: new Date().toISOString(),
      }
      const { error } = await supabase.from('client_tasks').insert(requestPayload)
      if (error) {
        setReviewError(`Failed to submit: ${error.message}`)
        setReviewState('error')
      } else {
        setReviewState('submitted')
      }
    } catch (err) {
      setReviewError('An unexpected error occurred.')
      setReviewState('error')
    }
  }

  return <div className="client-page">
    <ClientPageHeader title="Request Review" subtitle="Submit your profile for GoClear readiness review when ready." badge="Review gate" />
    <div className="client-metric-grid compact">
      <ClientScoreCard title="Review Readiness" value={funding.readinessScore} status={funding.status} text={funding.recommendedPath} />
      <ClientMetricCard icon={MessageSquare} label="Open Tasks" value={openTasks.length} note="Complete before review" tone={openTasks.length > 0 ? 'orange' : 'green'} />
      <ClientMetricCard icon={Send} label="Review Status" value={isSubmitted ? 'Submitted' : 'Not submitted'} note={isSubmitted ? 'Awaiting admin review' : 'Pending submission'} tone={isSubmitted ? 'green' : 'purple'} />
    </div>
    {!minimumDataMet && <div className="client-warning"><CircleAlert size={22} /><div><strong>Complete high-priority tasks first</strong><p>Request review only after completing all high-priority open tasks. Incomplete submissions may delay processing.</p></div></div>}
    {reviewState === 'error' && <div className="client-warning" style={{ borderColor: 'rgba(239,68,68,.3)' }}><CircleAlert size={22} /><div><strong>Submission failed</strong><p>{reviewError}</p></div></div>}
    {reviewState === 'submitted' && <div className="client-card" style={{ padding: '10px 14px', marginBottom: 10, background: 'rgba(16,185,129,.04)', border: '1px solid rgba(16,185,129,.15)' }}><strong style={{ color: 'var(--cp-green)' }}>Review request submitted</strong><span style={{ fontSize: 11, color: 'var(--cp-muted)', marginLeft: 8 }}>Your profile is now in the GoClear admin review queue. You will receive a status update in Messages when the review is complete.</span></div>}
    <div className="client-two-col">
      <ClientSection title="Open tasks to complete">
        <ClientActionList rows={openTasks.map(t => ({
          title: t.title,
          status: t.status.replaceAll('_', ' '),
          _route: t.category === 'documents' ? '/client/documents' : t.category === 'credit_repair' || t.category === 'credit_profile_readiness' ? '/client/credit-profile' : '/client/business-setup',
        }))} onNavigate={navigate} />
      </ClientSection>
      <ClientSection title="What happens after review">
        <ul>
          <li>GoClear reviews your readiness profile</li>
          <li>You receive a status update in Messages</li>
          <li>Next steps are recommended based on review</li>
          <li>No application is submitted without your approval</li>
        </ul>
        <button
          className="cp-btn-primary"
          style={{ width: '100%', marginTop: 8 }}
          disabled={isSubmitting || isSubmitted || !minimumDataMet}
          onClick={handleSubmitReview}
        >
          {isSubmitting ? 'Submitting...' : isSubmitted ? 'Review Requested' : !minimumDataMet ? 'Complete high-priority tasks first' : 'Request Review'}
        </button>
        <p className="client-safe-note">Review requests are processed in order. Response time varies.</p>
      </ClientSection>
    </div>
    <ClientGuidePanel suggestedKeys={['what_goclear_is_reviewing', 'what_do_i_do_next', 'can_i_apply_for_funding_now']} />
  </div>
}

export function ClientMessagesPage() {
  const navigate = usePortalNav()
  const groups = [['Advisor messages', data.messages.advisorMessages], ['System messages', data.messages.systemMessages], ['GoClear review updates', data.messages.goclearReviewUpdates], ['Action required', data.messages.actionRequiredMessages]]
  return <div className="client-page">
    <ClientPageHeader title="Messages" subtitle="Read approved demo updates. Outbound messaging is not connected." badge="Read-only preview" />
    <div className="client-message-layout">
      <ClientSection title="Inbox" className="client-message-inbox">
        {groups.flatMap(([group, rows]) => rows.map(row => <article key={row.id}><div className="client-message-icon"><Mail size={18} /></div><div><small>{group}</small><strong>{row.title}</strong><p>{row.body}</p></div><time>{row.date}</time></article>))}
      </ClientSection>
      <ClientSection title="Communication safety">
        <p>Nexus Guide cannot send messages or claim an external action occurred.</p>
        <p>Client questions requiring judgment must be routed into the GoClear admin review queue.</p>
        <ClientStatusBadge tone="green">No messages sent</ClientStatusBadge>
      </ClientSection>
    </div>
    <ClientGuidePanel compact />
  </div>
}

export function ClientSettingsPage() {
  const navigate = usePortalNav()
  const profile = data.clientProfile
  return <div className="client-page">
    <ClientPageHeader title="Settings" subtitle="Review demo membership and portal preferences." badge="Preview only" />
    <div className="client-settings-grid">
      <ClientSection title="Demo profile">{Object.entries(profile).map(([key, value]) => <div className="client-setting-row" key={key}><span>{key.replaceAll(/([A-Z])/g, ' $1')}</span><strong>{value}</strong></div>)}</ClientSection>
      <ClientSection title="Privacy and assistant boundaries">
        <div className="client-setting-row"><span>Hermes Advisor</span><strong>Private/admin only</strong></div>
        <div className="client-setting-row"><span>Client assistant</span><strong>Nexus Guide</strong></div>
        <div className="client-setting-row"><span>Real client data</span><strong>Not used</strong></div>
        <div className="client-setting-row"><span>External actions</span><strong>Disabled</strong></div>
      </ClientSection>
      <ClientSection title="Portal status">
        <Settings size={28} />
        <p>This frontend is powered by static demo data and Supabase-ready local exports. Production inserts and private file storage are not connected.</p>
      </ClientSection>
    </div>
    <ClientGuidePanel compact />
  </div>
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
