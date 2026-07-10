import React, { useEffect, useMemo, useState } from 'react'
import { clientPortalData } from '../../data/clientPortalData'
import { clientDataMode, shouldShowInternalDataBadge } from '../../data/clientDataMode'
import { supabase, isSupabaseConfigured } from '../../lib/supabaseClient'
import { DocumentUploadZone } from '../../components/client/DocumentUploadZone'
import { generateClientGuidance } from '../../clientPortal/clientGuidance'
import { resolveClientContextForCurrentUser } from '../../lib/clientAuthContext'
import { loadCreditRepairJourney } from '../../lib/creditRepairWorkflow'
import { loadClientPortalLiveData, loadClientProfileIntake, saveClientProfileIntake, checkProfileIntakeComplete } from '../../lib/clientPortalDataAdapter'
import '../../styles/world-class-client-portal.css'

const HERO_SRC = '/assets/client-portal/nexus-funding-path-hero.png'

const pageMeta = {
  '/client/dashboard': { key: 'home', title: 'Home' },
  '/client/profile': { key: 'profile', title: 'Profile & Info' },
  '/client/credit-profile': { key: 'credit', title: 'Credit Health' },
  '/client/credit-utilization': { key: 'credit', title: 'Credit Health' },
  '/client/documents': { key: 'documents', title: 'Documents' },
  '/client/business-setup': { key: 'business', title: 'Business Setup' },
  '/client/business-bankability': { key: 'business', title: 'Business Setup' },
  '/client/funding-readiness': { key: 'funding', title: 'Funding Readiness' },
  '/client/credit-repair-journey': { key: 'repair', title: 'Credit Repair Journey' },
  '/client/dispute-review': { key: 'repair', title: 'Credit Repair Journey' },
  '/client/recommendations': { key: 'resources', title: 'Resources' },
  '/client/resources': { key: 'resources', title: 'Resources' },
  '/client/request-review': { key: 'review', title: 'Request Review' },
  '/client/messages': { key: 'review', title: 'Request Review' },
  '/client/settings': { key: 'profile', title: 'Profile & Info' },
}

const navItems = [
  ['/client/dashboard', 'Home', '⌂'],
  ['/client/profile', 'Profile & Info', '♟'],
  ['/client/credit-profile', 'Credit Health', '〽'],
  ['/client/documents', 'Documents', '▤'],
  ['/client/business-setup', 'Business Setup', '▥'],
  ['/client/funding-readiness', 'Funding Readiness', '⚑'],
  ['/client/credit-repair-journey', 'Credit Repair Journey', '↻'],
  ['/client/resources', 'Resources', '▥'],
  ['/client/request-review', 'Request Review', '▱'],
]

function useWorldClassLiveData() {
  const [live, setLive] = useState(null)
  const [profileComplete, setProfileComplete] = useState(null)
  const [status, setStatus] = useState(clientDataMode.liveSupabaseTestClientEnabled ? 'loading' : 'idle')
  const [refreshIndex, setRefreshIndex] = useState(0)

  useEffect(() => {
    if (!clientDataMode.liveSupabaseTestClientEnabled) return
    let cancelled = false
    setStatus('loading')
    loadClientPortalLiveData().then(result => {
      if (cancelled) return
      setLive(result)
      setStatus(result?.profile ? 'connected' : 'fallback')
    }).catch(() => setStatus('error'))
    loadClientProfileIntake().then(result => {
      if (!cancelled && result.source === 'supabase') setProfileComplete(checkProfileIntakeComplete(result.data))
    }).catch(() => {})
    return () => { cancelled = true }
  }, [refreshIndex])

  return { live, profileComplete, status, refreshLiveData: () => setRefreshIndex(i => i + 1) }
}

function getScores(live) {
  const rows = live?.scores || []
  const mapped = {}
  for (const row of rows) {
    const key = row.score_type || row.category
    if (key) mapped[key] = Number(row.score ?? 0)
  }
  return {
    credit: mapped.credit_profile || clientPortalData.readinessScores.creditProfileReadiness || 74,
    business: mapped.business_profile || clientPortalData.readinessScores.businessProfileReadiness || 68,
    funding: mapped.funding_readiness || clientPortalData.readinessScores.fundingReadiness || 72,
    repair: mapped.credit_repair || clientPortalData.readinessScores.creditRepairProgress || 28,
  }
}

function getLiveDocuments(live) {
  const rows = live?.documents?.data || []
  if (rows.length) {
    const uploaded = rows
      .filter(d => ['uploaded', 'pending_review', 'complete', 'approved'].includes((d.status || '').toLowerCase()))
      .map(d => d.title || d.filename || d.category)
      .filter(Boolean)
    const underReview = rows
      .filter(d => /(pending|review)/i.test(d.goclear_review_status || d.status || ''))
      .map(d => d.title || d.filename || d.category)
      .filter(Boolean)
    const required = Array.from(new Set(rows.map(d => d.category || d.title || d.filename).filter(Boolean)))
    const missing = required.filter(r => !uploaded.some(u => u === r || String(r).includes(u) || String(u).includes(r)))
    return { uploaded, underReview, missing, total: rows.length, source: live.documents.source || 'supabase' }
  }

  const docs = live?.documents || clientPortalData.documents
  return {
    uploaded: docs.uploadedDocuments || [],
    underReview: docs.underReviewDocuments || [],
    missing: docs.missingDocuments || [],
    total: docs.uploadedDocuments?.length || 0,
    source: 'fallback',
  }
}

function getBusinessChecklist(live) {
  const rows = live?.businessProfile || []
  if (rows.length) {
    return rows.slice(0, 9).map(row => ({
      icon: /bank/i.test(row.requirement_type || row.title || '') ? '🏦' : /ein|tax/i.test(row.requirement_type || row.title || '') ? '🧾' : /address/i.test(row.requirement_type || row.title || '') ? '📍' : '🏢',
      title: (row.requirement_type || row.title || 'Business item').replaceAll('_', ' '),
      status: row.status || 'pending',
    }))
  }
  return [
    ['🏢', 'Business Name', 'Complete'], ['📜', 'Entity Formation', 'In Progress'], ['🧾', 'EIN (Tax ID)', 'In Progress'], ['📍', 'Business Address', 'Complete'], ['☎', 'Phone & Email', 'Complete'], ['🌐', 'Website', 'Recommended'], ['🏙', 'Industry / NAICS', 'Complete'], ['🏦', 'Bank Account Setup', 'Missing'], ['📁', 'Required Documents', 'In Progress'],
  ].map(([icon, title, status]) => ({ icon, title, status }))
}

function buildClientStatuses(live, profileComplete, scores) {
  const docs = getLiveDocuments(live)
  const uploadedText = docs.uploaded.join(' ')
  return {
    creditReportUploaded: /credit|report/i.test(uploadedText),
    addressVerified: /address|utility/i.test(uploadedText),
    identityVerified: /id|identity|license|passport/i.test(uploadedText),
    utilizationHigh: scores.credit < 70,
    negativeItemsIdentified: scores.repair < 50,
    businessBankAccount: /bank/i.test(uploadedText),
    revenueDocuments: /revenue|statement|income|profit|loss/i.test(uploadedText),
    documentsComplete: docs.missing.length === 0,
    adminReviewRequired: docs.underReview.length > 0,
    readinessScore: scores.funding,
    profileIncomplete: profileComplete ? !profileComplete.complete : false,
  }
}

function routeFromGuidance(item) {
  if (!item) return '/client/dashboard'
  if (item.category === 'profile') return '/client/profile'
  if (item.category === 'documents') return '/client/documents'
  if (item.category === 'business') return '/client/business-setup'
  if (item.category === 'credit') return '/client/credit-profile'
  return '/client/funding-readiness'
}

function Hero() {
  return <div className="wc-heroExact"><img src={HERO_SRC} alt="Your Path to Funding hero" /></div>
}

function SectionHead({ title, action }) {
  return <div className="wc-sectionHead"><h3>{title}</h3>{action && <span>{action}</span>}</div>
}

function ActionCard({ icon, title, text, button, onClick }) {
  return <div className="wc-actionCard"><div className="wc-softIcon">{icon}</div><b>{title}</b><p>{text}</p><button onClick={onClick}>{button}</button></div>
}

function MiniCard({ icon, title, tag, text, button, onClick }) {
  return <div className="wc-miniCard"><div className="wc-miniIcon">{icon}</div><div className="wc-miniBody"><div className="wc-miniTop"><b>{title}</b>{tag && <span className="wc-miniTag">{tag}</span>}</div><p>{text}</p>{button && <button onClick={onClick}>{button}</button>}</div></div>
}

function WcProfileIntakeForm({ onSaved }) {
  const [form, setForm] = useState({
    legal_name: '', preferred_name: '', phone: '',
    mailing_address_line1: '', city: '', state: '', postal_code: '',
    business_name: '', entity_type: '', ein_status: '', industry: '',
    business_address_line1: '', business_city: '', business_state: '', business_postal_code: '',
    time_in_business: '', monthly_revenue_range: '', funding_goal_range: '',
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    loadClientProfileIntake().then(result => {
      if (cancelled) return
      if (result.data) setForm(prev => ({ ...prev, ...result.data }))
      setLoading(false)
    }).catch(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  function updateField(key, value) {
    setForm(prev => ({ ...prev, [key]: value }))
    setMessage('')
    setError('')
  }

  async function handleSave() {
    if (saving) return
    setSaving(true)
    setMessage('')
    setError('')
    const result = await saveClientProfileIntake(form)
    setSaving(false)
    if (result.ok) {
      setMessage('Profile saved for GoClear review.')
      onSaved?.()
    } else {
      setError(result.error || 'Save failed')
    }
  }

  const completeness = checkProfileIntakeComplete(form)
  const field = (key, label, placeholder = '') => <label><span>{label}</span><input value={form[key] || ''} onChange={e => updateField(key, e.target.value)} placeholder={placeholder} /></label>
  const select = (key, label, options) => <label><span>{label}</span><select value={form[key] || ''} onChange={e => updateField(key, e.target.value)}><option value="">Select</option>{options.map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select></label>

  return <div className="wc-card wc-profileForm"><div className="wc-sectionHead"><h3>Live Profile & Business Info</h3><span>{loading ? 'Loading...' : `${completeness.percent}% complete`}</span></div>
    <div className="wc-formGrid">
      {field('legal_name', 'Legal name', 'First and last name')}
      {field('preferred_name', 'Preferred name', 'Optional')}
      {field('phone', 'Phone', '(555) 123-4567')}
      {field('mailing_address_line1', 'Mailing address', 'Street address')}
      {field('city', 'City')}
      {field('state', 'State')}
      {field('postal_code', 'Postal code')}
      {field('business_name', 'Business name')}
      {select('entity_type', 'Entity type', [['llc', 'LLC'], ['corporation', 'Corporation'], ['sole_proprietorship', 'Sole Proprietorship'], ['partnership', 'Partnership'], ['s_corp', 'S Corporation'], ['nonprofit', 'Nonprofit'], ['other', 'Other']])}
      {select('ein_status', 'EIN status', [['active', 'Active - EIN obtained'], ['pending', 'Pending'], ['not_applicable', 'Not applicable']])}
      {field('industry', 'Industry')}
      {field('business_address_line1', 'Business address')}
      {field('business_city', 'Business city')}
      {field('business_state', 'Business state')}
      {field('business_postal_code', 'Business postal code')}
      {select('time_in_business', 'Time in business', [['less_than_1_year', 'Less than 1 year'], ['1_to_2_years', '1-2 years'], ['2_to_5_years', '2-5 years'], ['5_plus_years', '5+ years']])}
      {select('monthly_revenue_range', 'Monthly revenue range', [['under_10k', 'Under $10K'], ['10k_to_25k', '$10K-$25K'], ['25k_to_50k', '$25K-$50K'], ['50k_plus', '$50K+']])}
      {select('funding_goal_range', 'Funding goal range', [['under_25k', 'Under $25K'], ['25k_to_100k', '$25K-$100K'], ['100k_to_250k', '$100K-$250K'], ['250k_plus', '$250K+']])}
    </div>
    {message && <p className="wc-successText">{message}</p>}
    {error && <p className="wc-errorText">{error}</p>}
    <button className="wc-primaryWide" disabled={saving || loading} onClick={handleSave}>{saving ? 'Saving...' : 'Save Profile'}</button>
  </div>
}

function ListItem({ tone = 'green', mark = '✓', title, text }) {
  return <div className="wc-listItem"><span className={`wc-dot ${tone}`}>{mark}</span><div><b>{title}</b><p>{text}</p></div></div>
}

function Donut({ value = 72, small = false, tone = 'green' }) {
  const deg = Math.max(0, Math.min(100, value)) * 3.6
  return <div className={`wc-donut ${small ? 'wc-smallDonut' : ''}`} style={{ '--wc-donut': `${deg}deg`, '--wc-donut-color': tone === 'blue' ? 'var(--wc-blue2)' : 'var(--wc-green)' }}><b>{small ? `${value}%` : value}</b>{!small && <span>/100</span>}</div>
}

function HomePanel({ scores, live, profileComplete, navigate }) {
  const uploaded = live?.documents?.uploadedDocuments?.length ?? 13
  const missing = live?.documents?.missingDocuments?.length ?? 3
  return <section className="wc-panel wc-panel-home">
    <Hero />
    <div className="wc-homeGrid">
      <div className="wc-card wc-journeyCard"><SectionHead title="Journey Progress" /><div className="wc-steps"><div className="wc-step"><span className="wc-stepDot done">✓</span><b>Profile & Info</b><p>{profileComplete?.complete === false ? `${profileComplete.percent}%` : 'Complete'}</p></div><div className="wc-step"><span className="wc-stepDot done">✓</span><b>Credit Health</b><p>Good</p></div><div className="wc-step"><span className="wc-stepDot active">3</span><b>Funding Readiness</b><p>In Progress</p></div><div className="wc-step"><span className="wc-stepDot">4</span><b>Funding Access</b><p>Upcoming</p></div></div></div>
      <div className="wc-card wc-recSteps"><SectionHead title="Recommended Next Steps" /><div className="wc-actionRow">
        <ActionCard icon="💳" title="Pay down high utilization" text="Focus on Card B to get below 30%." button="Take Action" onClick={() => navigate('/client/credit-profile')} />
        <ActionCard icon="🏦" title="Upload bank statement" text="Helps verify cash flow and stability." button="Upload Now" onClick={() => navigate('/client/documents')} />
        <ActionCard icon="🪪" title="Verify your identity" text="Securely verify your ID to stay on track." button="Verify Now" onClick={() => navigate('/client/profile')} />
        <ActionCard icon="📈" title="Request credit limit increase" text="Optional step to improve available credit." button="Learn More" onClick={() => navigate('/client/resources')} />
      </div></div>
    </div>
    <div className="wc-statusGrid">
      <MiniCard icon="〽" title="Credit Health" tag="Good" text="Payment history and utilization are moving in the right direction." button="View details" onClick={() => navigate('/client/credit-profile')} />
      <MiniCard icon="🏢" title="Business Setup" tag="On Track" text="Entity verified, EIN verified, and foundation is almost complete." button="View details" onClick={() => navigate('/client/business-setup')} />
      <MiniCard icon="▤" title="Documents" tag={`${missing} Missing`} text={`${uploaded} uploaded documents, ${missing} missing, and 2 items need review.`} button="Manage" onClick={() => navigate('/client/documents')} />
      <MiniCard icon="⚑" title="Funding Readiness" tag="In Progress" text={`Score ${scores.funding}/100 with next milestone at 80+.`} button="Improve" onClick={() => navigate('/client/funding-readiness')} />
    </div>
    <div className="wc-card wc-uploadStrip"><div className="wc-uploadLead"><div className="wc-softIcon">☁</div><div><b>Upload documents to improve your readiness.</b><p>Credit report, bank statements, and proof of address help Clyde guide your next move.</p></div></div><div className="wc-uploadBtns"><button onClick={() => navigate('/client/documents')}>Upload Files</button><button onClick={() => navigate('/client/request-review')}>Request Review</button></div></div>
  </section>
}

function ProfilePanel({ navigate, onSaved }) {
  return <section className="wc-panel wc-panel-profile"><Hero /><div className="wc-profileCards">
    {[
      ['👤', 'Personal Details', 'Complete', 'Personal and identification details.'],
      ['📞', 'Contact Information', 'Complete', 'Phone, email, and contact methods.'],
      ['🏠', 'Home Address', '80%', 'Primary residential address.'],
      ['💼', 'Business Information', 'Complete', 'Legal name, industry, and key details.'],
      ['📍', 'Business Address', '60%', 'Physical address for operations.'],
      ['🪪', 'EIN / Entity Details', '40%', 'Tax ID, entity type, and formation info.'],
    ].map(([icon, title, tag, text]) => <MiniCard key={title} icon={icon} title={title} tag={tag} text={text} button="Edit" onClick={() => document.querySelector('.wc-profileForm input')?.focus()} />)}
    </div><div className="wc-supportDocs"><SectionHead title="Supporting Documents" action="Upload documents to verify your identity and business." /><div className="wc-docTileRow">
      {[
        ['📄', 'Government ID', 'Complete', 'driver_license.pdf', 'Replace file', 'greenText'],
        ['📄', 'Proof of Address', 'Pending', 'Upload Document', 'Upload Document', 'orangeText'],
        ['📄', 'Business Formation Docs', 'Pending', 'Upload Document', 'Upload Document', 'orangeText'],
      ].map(([icon, title, status, text, button, cls]) => <div className="wc-card wc-docTile" key={title}><div className="wc-softIcon">{icon}</div><b>{title}</b><span className={`wc-${cls}`}>{status}</span><p>{text}</p><button onClick={() => navigate('/client/documents')}>{button}</button></div>)}
    </div></div><WcProfileIntakeForm onSaved={onSaved} /></section>
}

function CreditPanel({ navigate }) {
  return <section className="wc-panel wc-panel-credit"><Hero /><div className="wc-scoreFactors"><SectionHead title="Score Factors" action="Updated May 20, 2025" /><div className="wc-factorRow">
    {[
      ['✅', 'Payment History', 'Excellent', '100% · Excellent'],
      ['◔', 'Credit Utilization', 'Good', '32% · Good'],
      ['◔', 'Credit Age', 'Good', '4 yrs 8 mos · Good'],
      ['💳', 'Credit Mix', 'Good', '5 Types · Good'],
      ['📄', 'New Credit', 'Needs Work', '2 · Needs Work'],
    ].map(([icon, title, tag, text]) => <MiniCard key={title} icon={icon} title={title} tag={tag} text={text} />)}
    </div></div><div className="wc-creditMid"><div className="wc-card wc-util"><h3>Utilization Breakdown by Card</h3>{[['Chase Ink Business', 48], ['Capital One Spark', 28], ['Amex Blue Business', 12], ['Discover It', 8]].map(([name, value]) => <div className="wc-barLine" key={name}><b>{name}</b><span>{value}%</span><i><em style={{ width: `${value}%` }} /></i></div>)}<div className="wc-totalBar"><b>Total Utilization</b><span>32%</span></div></div>
    <div className="wc-card wc-listCard"><SectionHead title="Factors Needing Attention" action="View all →" /><ListItem tone="orange" mark="!" title="High utilization on 1 card" text="Lower balance first" /><ListItem tone="orange" mark="!" title="Recent hard inquiries" text="Review inquiries" /><ListItem tone="orange" mark="!" title="Limited credit age" text="Average age is below 5 years" /></div>
    <div className="wc-card wc-listCard"><SectionHead title="Positive Factors" action="View all →" /><ListItem title="Excellent payment history" text="No missed payments reported" /><ListItem title="Low overall utilization" text="Great job keeping balances low" /><ListItem title="Healthy credit mix" text="Strong mix of credit types" /></div>
    <div className="wc-card wc-uploadBig"><div className="wc-cloud">☁</div><h3>Upload Credit Report</h3><p>Get the most accurate picture of your credit health.</p><button onClick={() => navigate('/client/documents')}>Upload Report</button></div>
    </div><div className="wc-card wc-moveBar"><b>Top Next Moves</b><span>1 Pay down balances below 30%</span><span>2 Review recent inquiries</span><span>3 Continue on-time payments</span><button onClick={() => navigate('/client/funding-readiness')}>Continue to Funding Readiness →</button></div></section>
}

function DocumentsPanel({ live, refreshLiveData, withSuggestedUpload, navigate }) {
  const docs = getLiveDocuments(live)
  const uploadedDocs = docs.uploaded.length ? docs.uploaded : ['Bank Statement - Chase', 'Pay Stub - April 2025', 'ID - Driver License', 'Utility Bill - April 2025']
  const missingDocs = docs.missing.length ? docs.missing : ['Credit Report', 'Bank Statement', 'Proof of Address']
  const underReviewDocs = docs.underReview.length ? docs.underReview : ['Tax Return - 2023', 'Business License', 'Profit & Loss Statement']
  return <section className="wc-panel wc-panel-documents"><Hero /><div className="wc-docHub"><div className="wc-card wc-drop"><div className="wc-uploadIcon">↑</div><h3>Drag & drop files here to upload</h3><p>or choose an option below</p><DocumentUploadZone onUploadComplete={refreshLiveData} /><small>Accepted: PDF, JPG, PNG, HEIC, TXT, DOCX · Max 10MB</small></div><div className="wc-card wc-scanner"><h3>Smart Scanner Flow</h3>{[['↑', 'Uploaded', 'Your document is securely uploaded'], ['✦', 'Scanning', 'We scan and read the contents'], ['✓', 'Categorized', 'We identify the document type'], ['⌂', 'Routed', 'Stored in the right place automatically']].map(([icon, title, text]) => <div className="wc-scanStep" key={title}><span>{icon}</span><div><b>{title}</b><p>{text}</p></div></div>)}</div></div>
    <div className="wc-quickUpload"><b>Quick Upload</b>{['Credit Report', 'ID Document', 'Proof of Address', 'Bank Statement', 'Tax Return', 'Business License', 'Other'].map(x => <button key={x} onClick={() => withSuggestedUpload('quick-upload', x)}>{x}</button>)}</div>
    <div className="wc-docLists"><div className="wc-card wc-listCard"><SectionHead title="Recently Uploaded" action={docs.source === 'supabase' ? 'Live data' : 'View all →'} />{uploadedDocs.slice(0, 4).map((doc, i) => <ListItem key={`${doc}-${i}`} title={doc} text="Categorized" />)}</div><div className="wc-card wc-listCard"><SectionHead title="Needs Review" action="View all →" />{underReviewDocs.slice(0, 3).map(doc => <ListItem key={doc} tone="orange" mark="!" title={doc} text="Pending GoClear review" />)}</div><div className="wc-card wc-listCard"><SectionHead title="Missing Documents" action="View all →" />{missingDocs.slice(0, 3).map(doc => <ListItem key={doc} tone="orange" mark="!" title={doc} text="High Impact" />)}</div><div className="wc-card wc-recommended"><h3>Recommended for You</h3><p>Upload Proof of Income</p><p>Add More Bank Statements</p><p>Submit Business License</p><button onClick={() => navigate('/client/resources')}>See recommendations →</button></div></div>
    <div className="wc-card wc-secure"><b>🛡 Your documents are safe & secure</b><span>Bank-level encryption protects your data.</span><button onClick={() => navigate('/client/resources')}>Learn about security →</button></div></section>
}

function BusinessPanel({ live, navigate }) {
  const checklist = getBusinessChecklist(live)
  return <section className="wc-panel wc-panel-business"><Hero /><div className="wc-card wc-checklist"><SectionHead title="Your Business Setup Checklist" action={`${checklist.length} steps`} /><div className="wc-checkGrid">{checklist.map(({ icon, title, status }) => <div className="wc-checkTile" key={title}><div className="wc-softIcon">{icon}</div><div><b>{title}</b><p>Business foundation item</p><span>{String(status).replaceAll('_', ' ')}</span></div></div>)}</div></div><div className="wc-businessBottom"><div className="wc-card wc-why"><h3>Why this matters for Funding Readiness</h3><div className="wc-whyRow"><span>🛡<b>Builds credibility</b></span><span>🎯<b>Unlocks opportunities</b></span><span>📈<b>Improves trust</b></span></div></div><div className="wc-card wc-next"><h3>Ready for the next step?</h3><p>Once your business foundation is solid, move into Funding Readiness.</p><button onClick={() => navigate('/client/funding-readiness')}>Go to Funding Readiness →</button></div></div></section>
}

function FundingPanel({ scores, navigate }) {
  return <section className="wc-panel wc-panel-funding"><Hero /><div className="wc-card wc-flow"><SectionHead title="How Your Data Builds Your Readiness" /><div className="wc-flowLine">{['Profile & Info', 'Credit Health', 'Documents', 'Business Setup', 'Credit Repair Journey', 'Funding Readiness'].map((title, i) => <div key={title}><span>{i === 5 ? '⚑' : '✓'}</span><b>{title}</b><p>{i === 5 ? 'Unlock offers' : 'Build readiness'}</p></div>)}</div></div><div className="wc-fundingGrid"><div className="wc-card wc-summary"><h3>Readiness Summary</h3><Donut value={scores.funding} /><p><b className="wc-orangeText">Moderate</b><br />You're making solid progress. Complete a few key items to reach Strong.</p><button onClick={() => navigate('/client/request-review')}>View full breakdown</button></div><div className="wc-card wc-listCard"><SectionHead title="Factors Helping You" action="View all →" /><ListItem title="Business years in operation: 7 yrs" text="Strong history" /><ListItem title="On-time payments: 90%" text="Positive credit profile" /><ListItem title="Verified business info" text="Complete" /><ListItem title="Documents uploaded: 13" text="Good record" /></div><div className="wc-card wc-listCard"><SectionHead title="Factors Holding You Back" action="View all →" /><ListItem tone="orange" mark="!" title="Limited business credit history" text="Short" /><ListItem tone="orange" mark="!" title="D-U-N-S number missing" text="Required by many lenders" /><ListItem tone="orange" mark="!" title="Credit inquiries" text="High" /><ListItem tone="orange" mark="!" title="Trade lines reported" text="Low" /></div><div className="wc-card wc-required"><h3>Required Items to Unlock Better Terms</h3>{['D-U-N-S Number', 'Business Bank Statements', 'Tax Return', 'Profit & Loss Statement', 'Business License'].map((title, i) => <div className="wc-req" key={title}><b>{title}</b><p>Impact: {i < 3 ? 'High' : 'Medium'}</p><button onClick={() => navigate(i === 0 ? '/client/business-setup' : '/client/documents')}>{i === 0 ? 'Add Now' : 'Upload'}</button></div>)}</div></div><div className="wc-card wc-opportunityRow"><b>Ready Opportunities for You</b><span>Business Credit · $1K-$250K</span><span>Startup Funding · $5K-$500K</span><span>Equipment Financing · $2K-$1M+</span><span>Monitoring Tools · Recommended</span><button onClick={() => navigate('/client/resources')}>Explore</button></div></section>
}

function RepairPanel({ scores, navigate }) {
  const [journey, setJourney] = useState(null)
  useEffect(() => {
    let cancelled = false
    loadCreditRepairJourney().then(data => { if (!cancelled) setJourney(data) }).catch(() => {})
    return () => { cancelled = true }
  }, [])
  const stepKeys = ['profile', 'upload_report', 'specialist_review', 'dispute_items', 'draft_letters', 'approve_send', 'track_results']
  const completed = journey?.stepsCompleted || []
  const current = journey?.currentStep || 'upload_report'
  const percent = Math.max(scores.repair, Math.round(((completed.length || 1) / stepKeys.length) * 100))
  return <section className="wc-panel wc-panel-repair"><Hero /><div className="wc-card wc-repairJourney"><div className="wc-repairLine">{['Profile Complete', 'Upload Credit Report', 'Specialist Review', 'Dispute Items', 'Draft Letters', 'Approve & Send', 'Track Results'].map((title, i) => <div key={title}><span className={`wc-stepDot ${completed.includes(stepKeys[i]) ? 'done' : current === stepKeys[i] ? 'active' : ''}`}>{i + 1}</span><div className="wc-softIcon">{['👤', '☁', '🔍', '⚖', '✎', '✈', '📊'][i]}</div><b>{title}</b><p>{completed.includes(stepKeys[i]) ? 'Complete' : current === stepKeys[i] ? 'In Progress' : 'Upcoming'}</p></div>)}</div></div><div className="wc-repairMid"><div className="wc-card"><SectionHead title="Your Next Actions" action="View all" /><div className="wc-actionRow three"><ActionCard icon="☁" title="Upload your credit report" text="This helps us analyze your file." button="Upload Now" onClick={() => navigate('/client/documents?from=credit-repair&suggested=Credit%20Report')} /><ActionCard icon="👥" title="Answer a few questions" text="Help us understand your goals." button="Continue Profile" onClick={() => navigate('/client/profile')} /><ActionCard icon="➕" title="Review dispute letters" text={`${journey?.letters?.length || 0} letter(s) in workflow.`} button="Review" onClick={() => navigate('/client/dispute-review')} /></div></div><div className="wc-card wc-progressBox"><h3>Progress Overview</h3><Donut value={percent} small tone="blue" /><p>{completed.length} completed · current step: {current.replaceAll('_', ' ')}</p></div></div><div className="wc-repairBottom"><MiniCard icon="✉" title="Send From Home with DocuPost" tag="Approval gated" text="No letter is sent until specialist review and your explicit approval." button="Review gate" onClick={() => navigate('/client/dispute-review')} /><MiniCard icon="📝" title="Draft Letters" tag={`${journey?.letters?.length || 0} Ready`} text="Clyde and your specialist draft custom dispute letters." button="View drafts" onClick={() => navigate('/client/dispute-review')} /><MiniCard icon="⚑" title="Dispute Items" tag={`${journey?.disputeItems?.length || 0} Active`} text="Track identified items and specialist review status." button="Open" onClick={() => navigate('/client/dispute-review')} /></div></section>
}

function ResourcesPanel({ live, navigate }) {
  const offers = live?.partnerOffers || []
  const cards = offers.length
    ? offers.slice(0, 4).map(o => [o.category || 'Recommended Tools', o.title || 'Recommended resource', 'Open →'])
    : [
      ['Continue Learning', 'Understanding Your Funding Readiness Score', 'Read →'],
      ['Next Step', 'Build Strong Business Credit', 'Start →'],
      ['In Progress', 'Credit Repair Action Plan', 'Continue →'],
      ['Tool Recommendation', 'Monitor Credit with Confidence', 'Compare →'],
    ]
  return <section className="wc-panel wc-panel-resources"><Hero /><div className="wc-resourceRec">{cards.map(([tag, title, button]) => <div className="wc-card wc-resCard" key={title}><span>{tag}</span><h3>{title}</h3><p>Recommended based on your current goals.</p><button onClick={() => navigate('/client/resources')}>{button}</button></div>)}</div><div className="wc-card wc-resourceBanner"><h3>Resources connect to real progress.</h3><p>Every article, video, guide, and tool helps you take action and move closer to funding.</p><div><span>✓ Learn proven strategies</span><span>✓ Take action with confidence</span><span>✓ Unlock more opportunities</span></div></div><div className="wc-catRow">{[['🎓', 'Learning Center', 18], ['📘', 'Funding Education', 22], ['📈', 'Credit Repair Tips', 15], ['💼', 'Business Setup Guides', 17], ['🧰', 'Recommended Tools', 12]].map(([icon, title, count]) => <MiniCard key={title} icon={icon} title={title} text={`${count} resources available.`} button="Explore" onClick={() => navigate('/client/resources')} />)}</div><div className="wc-partnerRow">{(offers.length ? offers.slice(0, 4).map(o => [o.title || 'Recommended Tool', o.category || 'Recommended Tools']) : [['LiveWell', 'Credit Monitoring'], ['Nav', 'Business Credit Builder'], ['Relay', 'Business Banking'], ['D&B', 'Business Credit Profile']]).map(([name, text]) => <div className="wc-card wc-partner" key={name}><b>{name}</b><p>{text}</p><button onClick={() => navigate('/client/resources')}>Learn more →</button></div>)}</div></section>
}

function ReviewPanel({ live, scores, refreshLiveData, withSuggestedUpload }) {
  const [reviewType, setReviewType] = useState('Standard Review')
  const [topic, setTopic] = useState('Funding Readiness & Profile Strength')
  const [notes, setNotes] = useState('')
  const [state, setState] = useState('idle')
  const [error, setError] = useState('')
  const tasks = live?.tasks || []
  const pendingReview = tasks.some(t => (t.category === 'review_request' || t.task_type === 'review_request') && t.status === 'pending_admin_review')
  const isSubmitted = state === 'submitted' || pendingReview
  const checklist = [
    ['Basic Profile & Business Info', true, 'Complete'],
    ['Credit Health Overview', scores.credit > 0, `${scores.credit}/100`],
    ['Identity Verification', buildClientStatuses(live, null, scores).identityVerified, 'Required'],
    ['Bank Account Verified', buildClientStatuses(live, null, scores).businessBankAccount, 'Recommended'],
    ['Credit Report Uploaded', buildClientStatuses(live, null, scores).creditReportUploaded, 'Required'],
    ['Funding Readiness Score', scores.funding >= 70, `${scores.funding}/100 · Recommended 80+`],
  ]

  async function submitReview() {
    if (state === 'submitting' || isSubmitted) return
    setState('submitting')
    setError('')
    try {
      if (!isSupabaseConfigured || !supabase) throw new Error('Supabase is not configured in this environment.')
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) throw new Error('You must be signed in to submit a review request.')
      const ctx = await resolveClientContextForCurrentUser()
      if (!ctx) throw new Error('Could not resolve your client profile. Please sign out and sign back in or contact GoClear.')
      const { error: insertError } = await supabase.from('client_tasks').insert({
        id: `${ctx.authUserId}_review_request_${Date.now()}`,
        tenant_id: ctx.tenantId,
        client_id: ctx.clientId,
        category: 'review_request',
        title: `${reviewType}: ${topic}`,
        summary: notes || 'Client submitted their profile for GoClear readiness review via the client portal.',
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
      })
      if (insertError) throw insertError
      setState('submitted')
      refreshLiveData?.()
    } catch (err) {
      setError(err.message || 'Review request failed.')
      setState('error')
    }
  }

  return <section className="wc-panel wc-panel-review"><Hero /><div className="wc-reviewGrid"><div className="wc-card wc-listCard"><SectionHead title="Review Readiness Checklist" action="View all →" />{checklist.map(([title, ok, text]) => <ListItem key={title} tone={ok ? 'green' : 'orange'} mark={ok ? '✓' : '!'} title={title} text={text} />)}</div><div className="wc-card wc-formCard"><h3>Request Review</h3><p>Tell us what you'd like reviewed.</p><div className="wc-choiceRow">{['Standard Review', 'Final Review', 'Rescore Review', 'Custom Review'].map(x => <button className={reviewType === x ? 'active' : ''} key={x} onClick={() => setReviewType(x)}>{x}</button>)}</div><input className="wc-inputBox" value={topic} onChange={e => setTopic(e.target.value)} /><textarea className="wc-textarea" value={notes} onChange={e => setNotes(e.target.value)} placeholder="Share anything specific you'd like our team to know..." /><button className="wc-dropMini" onClick={() => withSuggestedUpload('request-review', 'Supporting Review File')}>☁ Upload supporting files</button>{error && <p className="wc-errorText">{error}</p>}{isSubmitted && <p className="wc-successText">Review request submitted. Your profile is now in the GoClear admin review queue.</p>}<button className="wc-submitBtn" disabled={state === 'submitting' || isSubmitted} onClick={submitReview}>{state === 'submitting' ? 'Submitting...' : isSubmitted ? 'Review Requested' : 'Submit Review Request'}</button></div><div className="wc-card wc-nextSteps"><h3>What Happens Next</h3>{['Review Submitted', 'Under Review', 'Results Delivered', 'Take Action'].map((title, i) => <ListItem key={title} tone="blue" mark={String(i + 1)} title={title} text={['Confirmation email with next steps.', 'Specialists review your profile.', 'Feedback and recommendations.', 'Improve your profile.'][i]} />)}</div></div></section>
}

function IconSystemPanel() {
  return <section className="wc-panel wc-panel-icons"><div className="wc-iconLayout"><div className="wc-card wc-iconIntro"><div className="wc-brandLine"><div className="wc-brandMark">N</div><div><b>NEXUS</b><span>CLIENT PORTAL</span></div></div><h2>ICON SYSTEM</h2><p>A cohesive modern icon set that reflects clarity, progress, and trust with rounded containers and soft shadows.</p><div className="wc-guidelines"><b>Usage Guidelines</b><p>Use consistently across navigation, feature cards, and actions.</p><p>Maintain clear spacing and proportions.</p><p>Use for navigation, features, and actions.</p></div></div><div className="wc-card wc-iconMain">{[
    ['Navigation & Account', [['⌂', 'Home'], ['♟', 'Profile & Info'], ['〽', 'Credit Health'], ['▤', 'Documents'], ['▥', 'Business Setup']]],
    ['Journey & Progress', [['⚑', 'Funding Readiness'], ['↻', 'Credit Repair Journey'], ['▥', 'Resources'], ['▱', 'Request Review'], ['🔔', 'Notifications']]],
    ['Tools & Actions', [['🎧', 'Support'], ['☁', 'Upload'], ['📄', 'Credit Report'], ['🛡', 'Identity Verification'], ['🏦', 'Bank Statement']]],
    ['Documents & Offers', [['📜', 'Business License'], ['⭐', 'Funding Offer'], ['👤', 'Specialist Review'], ['✉', 'Dispute Letters'], ['✈', 'Approve & Send']]],
  ].map(([group, icons]) => <div className="wc-iconGroup" key={group}><h3>{group}</h3><div className="wc-iconGrid">{icons.map(([icon, label]) => <div className="wc-iconDemo" key={label}><div>{icon}</div><b>{label}</b></div>)}</div></div>)}</div></div></section>
}

function ClydePanel({ navigate, guidance }) {
  const recommendations = guidance.length ? guidance.slice(0, 3) : [
    { title: 'Complete profile & business info', description: 'Expires in 7 days', priority: 'high', category: 'profile' },
    { title: 'Upload credit report', description: 'Strongly recommended', priority: 'medium', category: 'documents' },
    { title: 'Verify identity', description: 'Completed', priority: 'low', category: 'documents' },
  ]
  return <aside className="wc-advisor"><div className="wc-advisorCard"><div className="wc-botTop"><div className="wc-bot">🤖</div><div><h3>Clyde • Credit Specialist</h3><div className="wc-online">● Online</div></div></div><p>Hi Alex! I'm Clyde, your funding coach. I'm here to help you improve your profile and reach your funding goals.</p><div className="wc-advisorBox"><h4>Top Recommendations</h4>{recommendations.map((item, i) => <button className="wc-clydeItem" key={item.id || item.title} onClick={() => navigate(routeFromGuidance(item))}><ListItem tone={item.priority === 'high' ? 'orange' : item.priority === 'medium' ? 'blue' : 'green'} mark={item.priority === 'low' ? '✓' : String(i + 1)} title={item.title} text={item.description} /></button>)}</div><div className="wc-advisorBox"><h4>Clyde's Tip</h4><p>Keeping utilization below 30% can have one of the biggest positive impacts on your score.</p></div><div className="wc-suggestions"><button onClick={() => navigate('/client/credit-profile')}>What can improve my score fastest?</button><button onClick={() => navigate('/client/documents')}>Which documents do I need?</button></div><button className="wc-chatBtn" onClick={() => navigate('/client/resources')}>💬 Chat with Clyde</button></div></aside>
}

export default function WorldClassClientPortal({ path, onNavigate }) {
  const { live, profileComplete, status, refreshLiveData } = useWorldClassLiveData()
  const [showIcons, setShowIcons] = useState(false)
  const meta = pageMeta[path] || pageMeta['/client/dashboard']
  const scores = useMemo(() => getScores(live), [live])
  const clientStatuses = useMemo(() => buildClientStatuses(live, profileComplete, scores), [live, profileComplete, scores])
  const clydeGuidance = useMemo(() => generateClientGuidance(clientStatuses), [clientStatuses])
  const profile = clientPortalData.clientProfile
  const liveStatusLabel = status === 'connected' ? 'Live data connected' : status === 'loading' ? 'Live data pending' : 'Demo/fallback data'

  useEffect(() => setShowIcons(false), [path])

  const routeTo = (nextPath) => {
    setShowIcons(false)
    if (typeof onNavigate === 'function') {
      onNavigate(nextPath)
      return
    }
    if (typeof window !== 'undefined') window.location.assign(nextPath)
  }

  const withSuggestedUpload = (from, suggested) => {
    routeTo(`/client/documents?from=${encodeURIComponent(from)}&suggested=${encodeURIComponent(suggested)}`)
  }

  const panel = showIcons ? <IconSystemPanel /> : {
    home: <HomePanel scores={scores} live={live} profileComplete={profileComplete} navigate={routeTo} />,
    profile: <ProfilePanel navigate={routeTo} onSaved={refreshLiveData} />,
    credit: <CreditPanel navigate={routeTo} />,
    documents: <DocumentsPanel live={live} refreshLiveData={refreshLiveData} withSuggestedUpload={withSuggestedUpload} navigate={routeTo} />,
    business: <BusinessPanel live={live} navigate={routeTo} />,
    funding: <FundingPanel scores={scores} navigate={routeTo} />,
    repair: <RepairPanel scores={scores} navigate={routeTo} />,
    resources: <ResourcesPanel live={live} navigate={routeTo} />,
    review: <ReviewPanel live={live} scores={scores} refreshLiveData={refreshLiveData} withSuggestedUpload={withSuggestedUpload} />,
  }[meta.key]

  return <div className="wc-client-portal">
    <aside className="wc-sidebar"><div className="wc-brandButton"><div className="wc-brandMark">N</div><div className="wc-brandText"><b>NEXUS</b><span>CLIENT PORTAL</span></div></div><nav className="wc-sideNav">{navItems.map(([route, label, icon]) => <button key={route} className={`wc-navLabel ${!showIcons && pageMeta[route]?.key === meta.key ? 'active' : ''}`} onClick={() => routeTo(route)}><span className="wc-navIcon">{icon}</span><span>{label}</span></button>)}</nav><button className={`wc-sideAction ${showIcons ? 'active' : ''}`} onClick={() => setShowIcons(true)}>View icon system →</button><div className="wc-help"><strong>Need help?</strong><p>Our team is here to support you.</p></div>{shouldShowInternalDataBadge && <div className="wc-live"><strong>●</strong> {liveStatusLabel}<p>as of today, 9:41 AM</p></div>}<button className="wc-signOut" onClick={async () => { await supabase?.auth.signOut(); window.location.assign('/client/login') }}>Sign Out</button></aside>
    <main className="wc-main"><header className="wc-topbar"><div className="wc-pill">💎 {profile.membershipTier || 'GoClear Readiness Member'}</div><button className="wc-bell" onClick={() => routeTo('/client/resources')}>🔔<span>2</span></button><div className="wc-userPill"><div className="wc-avatar">👨🏻</div>{profile.name || 'Alex Morgan'}⌄</div></header><div className="wc-pageHost">{panel}</div></main>
    <ClydePanel navigate={routeTo} guidance={clydeGuidance} />
  </div>
}
