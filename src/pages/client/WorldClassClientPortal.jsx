import React, { useEffect, useMemo, useState } from 'react'
import { clientPortalData } from '../../data/clientPortalData'
import { clientDataMode, shouldShowInternalDataBadge } from '../../data/clientDataMode'
import { supabase, isSupabaseConfigured } from '../../lib/supabaseClient'
import { DocumentUploadZone } from '../../components/client/DocumentUploadZone'
import { InlineDocumentRequirement } from '../../components/client/InlineDocumentRequirement'
import { generateClientGuidance } from '../../clientPortal/clientGuidance'
import { getClientResources } from '../../clientPortal/clientResources'
import { resolveClientContextForCurrentUser } from '../../lib/clientAuthContext'
import { loadCreditRepairJourney, clientApproveLetter, createDocuPostSendRequest } from '../../lib/creditRepairWorkflow'
import { getOrCreateCreditRepairCase, listCreditReportItems, createManualReportItem, markItemForChallenge, selectDisputeReason, generateDisputeLetterOptions, createLetterDraftFromOption } from '../../lib/creditRepairCaseEngine'
import { DISPUTE_REASON_LABELS } from '../../lib/disputeStrategyKnowledge'
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
  '/client/dispute-review': { key: 'dispute', title: 'Review & Send Dispute Letters' },
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

function getDocumentRows(live) {
  const rows = live?.documents?.data || []
  if (rows.length) return rows
  const docs = live?.documents || clientPortalData.documents
  return [
    ...(docs.uploadedDocuments || []).map(title => ({ title, category: title, status: 'uploaded', goclear_review_status: 'pending_review' })),
    ...(docs.underReviewDocuments || []).map(title => ({ title, category: title, status: 'pending_review', goclear_review_status: 'pending_review' })),
  ]
}

function getRequirementStatus(existingDocuments, keys) {
  const joined = existingDocuments.map(doc => `${doc.category || ''} ${doc.title || ''} ${doc.filename || ''} ${doc.doc_type || ''}`).join(' ').toLowerCase()
  return keys.some(key => joined.includes(String(key).toLowerCase())) ? 'Uploaded' : 'Missing'
}

function getCompleteness(form, existingDocuments) {
  const checks = [
    ['Basic identity', Boolean(form.legal_name && form.phone)],
    ['Contact info', Boolean(form.email || form.phone)],
    ['Address', Boolean(form.mailing_address_line1 && form.city && form.state && form.postal_code)],
    ['Credit report access', Boolean(form.credit_report_access_status) || getRequirementStatus(existingDocuments, ['credit report']) !== 'Missing'],
    ['Business basics', Boolean(form.business_name && form.entity_type && form.industry)],
    ['EIN/entity status', Boolean(form.ein_status)],
    ['Funding goals', Boolean(form.funding_goal_range && form.funding_purpose && form.funding_timeline)],
    ['Required documents', ['government', 'address', 'credit report'].every(key => getRequirementStatus(existingDocuments, [key]) !== 'Missing')],
    ['Business banking status', Boolean(form.business_bank_account_status)],
  ]
  const complete = checks.filter(([, ok]) => ok)
  const missing = checks.filter(([, ok]) => !ok).map(([label]) => label)
  return { percent: Math.round((complete.length / checks.length) * 100), missing, nextBestAction: missing[0] || 'Ready for review' }
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

function SetupStateControl({ label, value, onChange, resourceCategory }) {
  const resource = getClientResources({ category: resourceCategory, limit: 1 })[0]
  return <div className="wc-setupState"><b>{label}</b><div>{['I already have this', 'I need help getting this', 'I am not sure'].map(option => <button key={option} className={value === option ? 'active' : ''} onClick={() => onChange(option)}>{option}</button>)}</div>{value === 'I need help getting this' && resource && <p><strong>{resource.title}</strong> · {resource.description}</p>}</div>
}

function CreditMonitoringConnectCard({ navigate, onUpload }) {
  const providerConfigured = false
  return <div className="wc-card wc-monitoringCard"><div className="wc-sectionHead"><h3>Credit Monitoring Connection</h3><span>{providerConfigured ? 'Secure provider' : 'Coming soon'}</span></div><p>Credit monitoring connection is coming soon. For now, upload a recent report or view recommended monitoring resources.</p><div className="wc-resourceActions"><button onClick={onUpload}>Upload credit report instead</button><button onClick={() => navigate('/client/resources?category=credit-monitoring')}>View recommended monitoring resources</button><button disabled title="Secure provider connection is not configured yet.">Connect securely</button></div></div>
}

function Hero() {
  return <div className="wc-heroExact"><img src={HERO_SRC} alt="Your Path to Funding hero" /></div>
}

function SectionHead({ title, action, onAction }) {
  return <div className="wc-sectionHead"><h3>{title}</h3>{action && (onAction ? <button type="button" onClick={onAction}>{action}</button> : <span>{action}</span>)}</div>
}

function ActionCard({ icon, title, text, button, onClick }) {
  return <div className="wc-actionCard"><div className="wc-softIcon">{icon}</div><b>{title}</b><p>{text}</p><button onClick={onClick}>{button}</button></div>
}

function MiniCard({ icon, title, tag, text, button, onClick }) {
  return <div className="wc-miniCard"><div className="wc-miniIcon">{icon}</div><div className="wc-miniBody"><div className="wc-miniTop"><b>{title}</b>{tag && <span className="wc-miniTag">{tag}</span>}</div><p>{text}</p>{button && <button onClick={onClick}>{button}</button>}</div></div>
}

function WcProfileIntakeForm({ onSaved, existingDocuments, navigate }) {
  const [form, setForm] = useState({
    legal_name: '', preferred_name: '', email: '', phone: '',
    mailing_address_line1: '', city: '', state: '', postal_code: '',
    credit_report_access_status: '',
    has_business: '', business_name: '', dba_name: '', entity_type: '', state_formed: '', formation_date: '',
    ein_status: '', ein_last4: '', industry: '', naics_code: '',
    business_address_line1: '', business_city: '', business_state: '', business_postal_code: '',
    business_phone: '', business_email: '', website: '',
    time_in_business: '', monthly_revenue_range: '', funding_goal_range: '', funding_purpose: '', funding_timeline: '', preferred_funding_type: '',
    duns_status: '', business_bank_account_status: '', business_credit_profile_status: '',
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

  const baseCompleteness = checkProfileIntakeComplete(form)
  const guidedCompleteness = getCompleteness(form, existingDocuments)
  const field = (key, label, placeholder = '') => <label><span>{label}</span><input value={form[key] || ''} onChange={e => updateField(key, e.target.value)} placeholder={placeholder} /></label>
  const select = (key, label, options) => <label><span>{label}</span><select value={form[key] || ''} onChange={e => updateField(key, e.target.value)}><option value="">Select</option>{options.map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select></label>

  return <div className="wc-card wc-profileForm"><div className="wc-sectionHead"><h3>Guided Funding Readiness Intake</h3><span>{loading ? 'Loading...' : `${Math.max(baseCompleteness.percent, guidedCompleteness.percent)}% complete`}</span></div>
    <div className="wc-intakeSummary"><b>Next best step: {guidedCompleteness.nextBestAction}</b><p>Missing: {guidedCompleteness.missing.length ? guidedCompleteness.missing.join(', ') : 'None'}</p></div>
    <div className="wc-intakeSection" id="basic-identity"><div className="wc-sectionHead"><h3>Basic Identity</h3><span>{guidedCompleteness.missing.includes('Basic identity') ? 'Missing' : 'Complete'}</span></div><p>Why it matters: GoClear needs accurate identity and address details before any readiness review.</p>
    <div className="wc-formGrid">
      {field('legal_name', 'Legal name', 'First and last name')}
      {field('preferred_name', 'Preferred name', 'Optional')}
      {field('email', 'Email', 'name@example.com')}
      {field('phone', 'Phone', '(555) 123-4567')}
      {field('mailing_address_line1', 'Mailing address', 'Street address')}
      {field('city', 'City')}
      {field('state', 'State')}
      {field('postal_code', 'Postal code')}
    </div><div className="wc-inlineRequirementGrid"><InlineDocumentRequirement title="Government ID" description="Upload a government-issued ID for GoClear identity review." category="identification" requirementKey="government_id" fromPage="profile" impactLabel="Required" existingDocuments={existingDocuments} onUploaded={onSaved} whyItMatters="Identity review protects your file and prevents mismatched records." /><InlineDocumentRequirement title="Proof of Address" description="Upload a utility bill, statement, or lease showing your current address." category="proof_of_address" requirementKey="proof_of_address" fromPage="profile" impactLabel="High Impact" existingDocuments={existingDocuments} onUploaded={onSaved} whyItMatters="Address proof supports identity and funding readiness." /></div></div>

    <div className="wc-intakeSection" id="credit-report-access"><div className="wc-sectionHead"><h3>Credit Report Access</h3><span>{form.credit_report_access_status ? 'Needs Review' : 'Missing'}</span></div><p>Why it matters: a recent report gives GoClear the clearest view of credit health.</p>
      <div className="wc-choiceRow">{['I already have a recent credit report', 'I need help getting my credit report', 'I want to monitor my credit score through a recommended resource', 'I am not sure'].map(option => <button key={option} className={form.credit_report_access_status === option ? 'active' : ''} onClick={() => updateField('credit_report_access_status', option)}>{option}</button>)}</div>
      <InlineDocumentRequirement title="Credit Report" description="Upload a recent report PDF or image." category="credit_report" requirementKey="credit_report" fromPage="profile" impactLabel="Required" existingDocuments={existingDocuments} onUploaded={onSaved} whyItMatters="Credit report review drives credit health and repair recommendations." />
      <CreditMonitoringConnectCard navigate={navigate} onUpload={() => document.querySelector('[data-requirement=\"credit_report\"] button')?.click()} />
    </div>

    <div className="wc-intakeSection" id="business-foundation"><div className="wc-sectionHead"><h3>Business Foundation</h3><span>{form.business_name ? 'Needs Review' : 'Missing'}</span></div><p>Why it matters: consistent business records improve funding readiness and review quality.</p><div className="wc-formGrid">
      {select('has_business', 'Do you already have a business?', [['yes', 'Yes'], ['no', 'No'], ['not_sure', 'Not sure']])}
      {field('business_name', 'Business name')}
      {field('dba_name', 'DBA optional')}
      {select('entity_type', 'Entity type', [['llc', 'LLC'], ['corporation', 'Corporation'], ['sole_proprietorship', 'Sole Proprietorship'], ['partnership', 'Partnership'], ['s_corp', 'S Corporation'], ['nonprofit', 'Nonprofit'], ['other', 'Other']])}
      {field('state_formed', 'State formed')}
      {field('formation_date', 'Formation date optional')}
      {field('industry', 'Industry')}
      {field('naics_code', 'NAICS code optional')}
      {field('business_address_line1', 'Business address')}
      {field('business_city', 'Business city')}
      {field('business_state', 'Business state')}
      {field('business_postal_code', 'Business postal code')}
      {field('business_phone', 'Business phone')}
      {field('business_email', 'Business email')}
      {field('website', 'Website')}
    </div></div>

    <div className="wc-intakeSection" id="ein-entity-details"><div className="wc-sectionHead"><h3>EIN / Entity Details</h3><span>{form.ein_status ? 'Needs Review' : 'Missing'}</span></div><p>Why it matters: entity records and EIN confirmation help validate the business foundation.</p><div className="wc-formGrid">
      {select('ein_status', 'EIN status', [['already_have', 'I already have an EIN'], ['need_help', 'I need help getting one'], ['not_sure', 'I am not sure']])}
      {field('ein_last4', 'EIN last 4 digits optional')}
    </div><SetupStateControl label="DUNS / Business Profile" value={form.duns_status} onChange={value => updateField('duns_status', value)} resourceCategory="DUNS / Business Profile" /><div className="wc-inlineRequirementGrid"><InlineDocumentRequirement title="EIN Confirmation" description="Upload the EIN confirmation letter if available." category="ein_confirmation" requirementKey="ein_confirmation" fromPage="profile" impactLabel="High Impact" existingDocuments={existingDocuments} onUploaded={onSaved} whyItMatters="Confirms tax identity without collecting full EIN." /><InlineDocumentRequirement title="Business Formation Docs" description="Upload Articles of Organization or Incorporation." category="business_formation" requirementKey="business_formation_docs" fromPage="profile" impactLabel="Required" existingDocuments={existingDocuments} onUploaded={onSaved} whyItMatters="Shows the business entity exists." /><InlineDocumentRequirement title="Operating Agreement" description="Upload if available." category="operating_agreement" requirementKey="operating_agreement" fromPage="profile" impactLabel="Optional" required={false} existingDocuments={existingDocuments} onUploaded={onSaved} whyItMatters="Helpful for entity verification when available." /></div></div>

    <div className="wc-intakeSection" id="funding-goals"><div className="wc-sectionHead"><h3>Funding Goals</h3><span>{form.funding_goal_range ? 'Needs Review' : 'Missing'}</span></div><p>Why it matters: goals help Clyde and GoClear prioritize the right readiness steps.</p><div className="wc-formGrid">
      {select('time_in_business', 'Time in business', [['less_than_1_year', 'Less than 1 year'], ['1_to_2_years', '1-2 years'], ['2_to_5_years', '2-5 years'], ['5_plus_years', '5+ years']])}
      {select('monthly_revenue_range', 'Monthly revenue range', [['under_10k', 'Under $10K'], ['10k_to_25k', '$10K-$25K'], ['25k_to_50k', '$25K-$50K'], ['50k_plus', '$50K+']])}
      {select('funding_goal_range', 'Funding goal range', [['under_25k', 'Under $25K'], ['25k_to_100k', '$25K-$100K'], ['100k_to_250k', '$100K-$250K'], ['250k_plus', '$250K+']])}
      {select('funding_purpose', 'Funding purpose', [['working_capital', 'Working capital'], ['equipment', 'Equipment'], ['growth', 'Growth'], ['debt_refi', 'Debt refinance'], ['not_sure', 'Not sure']])}
      {select('funding_timeline', 'How soon funding is needed', [['now', 'Now'], ['30_60_days', '30-60 days'], ['60_90_days', '60-90 days'], ['planning', 'Planning ahead']])}
      {select('preferred_funding_type', 'Preferred funding type', [['business_credit_cards', 'Business credit cards'], ['line_of_credit', 'Line of credit'], ['sba_prep', 'SBA/funding prep'], ['equipment', 'Equipment'], ['grants', 'Grants'], ['not_sure', 'Not sure']])}
    </div></div>

    <div className="wc-intakeSection" id="required-documents"><div className="wc-sectionHead"><h3>Required Documents</h3><span>Document Status</span></div><p>Why it matters: uploaded documents tell GoClear what is ready, missing, and pending review.</p><div className="wc-inlineRequirementGrid">
      {[
        ['Government ID', 'identification', 'government_id'],
        ['Proof of Address', 'proof_of_address', 'proof_of_address'],
        ['Credit Report', 'credit_report', 'credit_report'],
        ['EIN Confirmation', 'ein_confirmation', 'ein_confirmation'],
        ['Business Formation Docs', 'business_formation', 'business_formation_docs'],
        ['Business License', 'business_license', 'business_license'],
        ['Bank Statement', 'bank_statement', 'bank_statement'],
        ['Tax Return', 'tax_return', 'tax_return'],
        ['Profit & Loss Statement', 'profit_loss', 'profit_loss_statement'],
      ].map(([title, category, key]) => <InlineDocumentRequirement key={key} title={title} description={`Upload ${title.toLowerCase()} for readiness review.`} category={category} requirementKey={key} fromPage="profile" impactLabel={['profit_loss_statement'].includes(key) ? 'If required' : 'Required'} required={key !== 'profit_loss_statement'} existingDocuments={existingDocuments} onUploaded={onSaved} whyItMatters="Supports GoClear readiness review." />)}
    </div></div>

    <div className="wc-intakeSection" id="ready-for-review"><div className="wc-sectionHead"><h3>Ready for Review</h3><span>{guidedCompleteness.percent >= 80 ? 'Ready' : 'Needs Work'}</span></div><p>Why it matters: request review after the key identity, business, credit report, and document items are complete.</p><button className="wc-primaryWide" onClick={() => navigate('/client/request-review')}>Go to Request Review</button></div>
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

function ProfilePanel({ navigate, onSaved, existingDocuments }) {
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
    </div></div><WcProfileIntakeForm onSaved={onSaved} existingDocuments={existingDocuments} navigate={navigate} /></section>
}

function CreditPanel({ navigate, existingDocuments, onUploaded }) {
  const [showAttention, setShowAttention] = useState(false)
  const [showPositive, setShowPositive] = useState(false)
  const [tip, setTip] = useState('')
  const openCreditUpload = () => document.querySelector('[data-requirement="credit_report"] button')?.click()
  const scrollToAttention = () => {
    setShowAttention(true)
    requestAnimationFrame(() => document.getElementById('attention')?.scrollIntoView({ behavior: 'smooth', block: 'center' }))
  }
  const showTip = (message) => setTip(message)
  return <section className="wc-panel wc-panel-credit"><Hero /><div className="wc-scoreFactors"><SectionHead title="Score Factors" action="Updated May 20, 2025" /><div className="wc-factorRow">
    {[
      ['✅', 'Payment History', 'Excellent', '100% · Excellent'],
      ['◔', 'Credit Utilization', 'Good', '32% · Good'],
      ['◔', 'Credit Age', 'Good', '4 yrs 8 mos · Good'],
      ['💳', 'Credit Mix', 'Good', '5 Types · Good'],
      ['📄', 'New Credit', 'Needs Work', '2 · Needs Work'],
    ].map(([icon, title, tag, text]) => <MiniCard key={title} icon={icon} title={title} tag={tag} text={text} button={title === 'Credit Utilization' ? 'Compare' : title === 'New Credit' ? 'Review' : 'Learn'} onClick={() => title === 'Credit Utilization' ? showTip('Compare utilization by card below, then focus first on balances above 30%.') : title === 'New Credit' ? scrollToAttention() : navigate('/client/resources?category=funding-education')} />)}
    </div></div><div className="wc-creditMid"><div className="wc-card wc-util"><h3>Utilization Breakdown by Card</h3>{[['Chase Ink Business', 48], ['Capital One Spark', 28], ['Amex Blue Business', 12], ['Discover It', 8]].map(([name, value]) => <div className="wc-barLine" key={name}><b>{name}</b><span>{value}%</span><i><em style={{ width: `${value}%` }} /></i></div>)}<div className="wc-totalBar"><b>Total Utilization</b><span>32%</span></div></div>
    <div className="wc-card wc-listCard" id="attention"><SectionHead title="Factors Needing Attention" action="View all →" onAction={scrollToAttention} /><button className="wc-rowAction" onClick={() => showTip('Start with the highest utilization card. Moving it below 30% usually has the fastest readiness impact.')}><ListItem tone="orange" mark="!" title="High utilization on 1 card" text="Lower balance first" /></button><button className="wc-rowAction" onClick={() => showTip('Upload a current credit report so GoClear can review which inquiries are accurate and whether dispute prep is appropriate.')}><ListItem tone="orange" mark="!" title="Recent hard inquiries" text="Review inquiries" /></button><button className="wc-rowAction" onClick={() => navigate('/client/resources?category=funding-education')}><ListItem tone="orange" mark="!" title="Limited credit age" text="Average age is below 5 years" /></button>{showAttention && <p className="wc-inlineTip">Full attention list is open. Upload a current report before GoClear reviews inquiry or dispute options.</p>}</div>
    <div className="wc-card wc-listCard"><SectionHead title="Positive Factors" action="View all →" onAction={() => setShowPositive(value => !value)} /><ListItem title="Excellent payment history" text="No missed payments reported" /><ListItem title="Low overall utilization" text="Great job keeping balances low" /><ListItem title="Healthy credit mix" text="Strong mix of credit types" />{showPositive && <ListItem title="Low derogatory activity" text="Keep monitoring and upload current reports for review." />}</div>
    <div className="wc-card wc-uploadBig"><div className="wc-cloud">☁</div><h3>Credit Report Access</h3><p>Get the most accurate picture of your credit health.</p><InlineDocumentRequirement compact title="Credit Report" description="Upload a recent report for GoClear review." category="credit_report" requirementKey="credit_report" fromPage="credit-health" impactLabel="Required" existingDocuments={existingDocuments} onUploaded={onUploaded} whyItMatters="Needed for credit health, utilization, and repair review." /></div>
    </div><CreditMonitoringConnectCard navigate={navigate} onUpload={openCreditUpload} />{tip && <div className="wc-card wc-creditTip"><b>Credit Health Guidance</b><p>{tip}</p><button onClick={() => setTip('')}>Dismiss</button></div>}<div className="wc-card wc-moveBar"><b>Top Next Moves</b><button onClick={() => showTip('Pay down balances above 30% first. Prioritize the highest utilization card, then upload an updated report when available.')}>1 Pay down balances below 30%</button><button onClick={scrollToAttention}>2 Review recent inquiries</button><button onClick={() => showTip('Keep every account paid on time. On-time payment history remains one of the strongest readiness signals.')}>3 Continue on-time payments</button><button onClick={() => navigate('/client/funding-readiness')}>Continue to Funding Readiness →</button></div></section>
}

function DocumentsPanel({ live, refreshLiveData, withSuggestedUpload, navigate }) {
  const docs = getLiveDocuments(live)
  const documentRows = getDocumentRows(live)
  const uploadedDocs = docs.uploaded.length ? docs.uploaded : ['Bank Statement - Chase', 'Pay Stub - April 2025', 'ID - Driver License', 'Utility Bill - April 2025']
  const missingDocs = docs.missing.length ? docs.missing : ['Credit Report', 'Bank Statement', 'Proof of Address']
  const underReviewDocs = docs.underReview.length ? docs.underReview : ['Tax Return - 2023', 'Business License', 'Profit & Loss Statement']
  return <section className="wc-panel wc-panel-documents"><Hero /><div className="wc-docHub"><div className="wc-card wc-drop"><div className="wc-uploadIcon">↑</div><h3>Drag & drop files here to upload</h3><p>or choose an option below</p><DocumentUploadZone onUploadComplete={refreshLiveData} /><small>Accepted: PDF, JPG, PNG, HEIC, TXT, DOCX · Max 10MB</small></div><div className="wc-card wc-scanner"><h3>Smart Scanner Flow</h3>{[['↑', 'Uploaded', 'Your document is securely uploaded'], ['✦', 'Scanning', 'We scan and read the contents'], ['✓', 'Categorized', 'We identify the document type'], ['⌂', 'Routed', 'Stored in the right place automatically']].map(([icon, title, text]) => <div className="wc-scanStep" key={title}><span>{icon}</span><div><b>{title}</b><p>{text}</p></div></div>)}</div></div>
    <div className="wc-quickUpload"><b>Quick Upload</b>{['Credit Report', 'ID Document', 'Proof of Address', 'Bank Statement', 'Tax Return', 'Business License', 'Other'].map(x => <button key={x} onClick={() => withSuggestedUpload('quick-upload', x)}>{x}</button>)}</div>
    <div className="wc-docLists"><div className="wc-card wc-listCard"><SectionHead title="Recently Uploaded" action={docs.source === 'supabase' ? 'Live data' : 'View all →'} />{uploadedDocs.slice(0, 4).map((doc, i) => <ListItem key={`${doc}-${i}`} title={doc} text="Categorized" />)}</div><div className="wc-card wc-listCard"><SectionHead title="Needs Review" action="View all →" />{underReviewDocs.slice(0, 3).map(doc => <ListItem key={doc} tone="orange" mark="!" title={doc} text="Pending GoClear review" />)}</div><div className="wc-card wc-listCard"><SectionHead title="Missing Documents" action="View all →" />{missingDocs.slice(0, 3).map(doc => <ListItem key={doc} tone="orange" mark="!" title={doc} text="High Impact" />)}</div><div className="wc-card wc-recommended"><h3>Recommended for You</h3><p>Upload Proof of Income</p><p>Add More Bank Statements</p><p>Submit Business License</p><button onClick={() => navigate('/client/resources')}>See recommendations →</button></div></div>
    <div className="wc-card wc-documentVault"><SectionHead title="Master Document Vault" action={`${documentRows.length} document(s)`} />{documentRows.map((doc, i) => <div className="wc-vaultRow" key={doc.id || `${doc.title}-${i}`}><b>{doc.title || doc.filename || doc.category || 'Uploaded document'}</b><span>{doc.category || doc.doc_type || 'document'}</span><span>{doc.status || 'uploaded'}</span><span>{doc.goclear_review_status || 'pending_review'}</span><span>{doc.created_at ? new Date(doc.created_at).toLocaleDateString() : 'Uploaded'}</span><span>{/credit/i.test(doc.category || doc.title || '') ? 'Credit Health' : /bank|tax|profit|license/i.test(doc.category || doc.title || '') ? 'Funding Readiness' : 'Profile'}</span></div>)}</div>
    <div className="wc-card wc-secure"><b>🛡 Your documents are safe & secure</b><span>Bank-level encryption protects your data.</span><button onClick={() => navigate('/client/resources')}>Learn about security →</button></div></section>
}

function BusinessPanel({ live, navigate }) {
  const checklist = getBusinessChecklist(live)
  const [setupStates, setSetupStates] = useState({})
  const setSetupState = (key, value) => setSetupStates(prev => ({ ...prev, [key]: value }))
  return <section className="wc-panel wc-panel-business"><Hero /><div className="wc-card wc-checklist"><SectionHead title="Your Business Setup Checklist" action={`${checklist.length} steps`} /><div className="wc-checkGrid">{checklist.map(({ icon, title, status }) => <div className="wc-checkTile" key={title}><div className="wc-softIcon">{icon}</div><div><b>{title}</b><p>Business foundation item</p><span>{String(status).replaceAll('_', ' ')}</span></div></div>)}</div><div className="wc-setupGrid">{[
    ['ein', 'EIN', 'EIN / Entity Setup'],
    ['duns', 'DUNS / Business Profile', 'DUNS / Business Profile'],
    ['bank', 'Business bank account', 'Business Banking'],
    ['address', 'Business address', 'Document Prep'],
    ['website', 'Website', 'Business Credit Builder'],
    ['phone_email', 'Business phone/email', 'Business Credit Builder'],
    ['credit_profile', 'Business credit profile', 'Business Credit Builder'],
    ['license', 'Business license', 'Document Prep'],
  ].map(([key, label, category]) => <SetupStateControl key={key} label={label} value={setupStates[key]} onChange={value => setSetupState(key, value)} resourceCategory={category} />)}</div></div><div className="wc-businessBottom"><div className="wc-card wc-why"><h3>Why this matters for Funding Readiness</h3><div className="wc-whyRow"><span>🛡<b>Builds credibility</b></span><span>🎯<b>Unlocks opportunities</b></span><span>📈<b>Improves trust</b></span></div></div><div className="wc-card wc-next"><h3>Ready for the next step?</h3><p>Once your business foundation is solid, move into Funding Readiness.</p><button onClick={() => navigate('/client/funding-readiness')}>Go to Funding Readiness →</button></div></div></section>
}

function FundingPanel({ scores, navigate, existingDocuments, onUploaded }) {
  const fundingResources = getClientResources({ placement: 'funding-readiness', limit: 4 })
  return <section className="wc-panel wc-panel-funding"><Hero /><div className="wc-card wc-flow"><SectionHead title="How Your Data Builds Your Readiness" /><div className="wc-flowLine">{['Profile & Info', 'Credit Health', 'Documents', 'Business Setup', 'Credit Repair Journey', 'Funding Readiness'].map((title, i) => <div key={title}><span>{i === 5 ? '⚑' : '✓'}</span><b>{title}</b><p>{i === 5 ? 'Unlock offers' : 'Build readiness'}</p></div>)}</div></div><div className="wc-fundingGrid"><div className="wc-card wc-summary"><h3>Readiness Summary</h3><Donut value={scores.funding} /><p><b className="wc-orangeText">Moderate</b><br />You're making solid progress. Complete a few key items to reach Strong.</p><button onClick={() => navigate('/client/request-review')}>View full breakdown</button></div><div className="wc-card wc-listCard"><SectionHead title="Factors Helping You" action="View all →" /><ListItem title="Business years in operation" text="Strong history when documented" /><ListItem title="On-time payments" text="Positive credit profile" /><ListItem title="Verified business info" text="Complete verified items improve readiness" /><ListItem title="Documents uploaded" text={`${existingDocuments.length} file(s) available for review`} /></div><div className="wc-card wc-listCard"><SectionHead title="Factors Holding You Back" action="View all →" /><ListItem tone="orange" mark="!" title="Limited business credit history" text="Short" /><ListItem tone="orange" mark="!" title="D-U-N-S number missing" text="Required by many lenders" /><ListItem tone="orange" mark="!" title="Credit inquiries" text="High" /><ListItem tone="orange" mark="!" title="Trade lines reported" text="Low" /></div><div className="wc-card wc-required"><h3>Required Items to Unlock Better Terms</h3>{[
    ['Business Bank Statements', 'bank_statement', 'bank_statement', 'High'],
    ['Tax Return', 'tax_return', 'tax_return', 'High'],
    ['Profit & Loss Statement', 'profit_loss', 'profit_loss_statement', 'Medium'],
    ['Business License', 'business_license', 'business_license', 'Medium'],
    ['EIN Confirmation', 'ein_confirmation', 'ein_confirmation', 'High'],
    ['Business Formation Docs', 'business_formation', 'business_formation_docs', 'High'],
  ].map(([title, category, key, impact]) => <InlineDocumentRequirement compact key={key} title={title} description={`Upload ${title.toLowerCase()} for funding readiness review.`} category={category} requirementKey={key} fromPage="funding-readiness" impactLabel={`${impact} Impact`} existingDocuments={existingDocuments} onUploaded={onUploaded} whyItMatters="GoClear uses this to verify readiness and reduce review delays." />)}</div></div><div className="wc-card wc-opportunityRow"><b>Ready Opportunities for You</b>{fundingResources.map(resource => <span key={resource.title}>{resource.category}</span>)}<button onClick={() => navigate('/client/resources')}>Explore</button></div></section>
}

function RepairPanel({ scores, navigate, existingDocuments, onUploaded }) {
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
  return <section className="wc-panel wc-panel-repair"><Hero /><div className="wc-card wc-repairJourney"><div className="wc-repairLine">{['Profile Complete', 'Upload Credit Report', 'Specialist Review', 'Dispute Items', 'Draft Letters', 'Approve & Send', 'Track Results'].map((title, i) => <div key={title}><span className={`wc-stepDot ${completed.includes(stepKeys[i]) ? 'done' : current === stepKeys[i] ? 'active' : ''}`}>{i + 1}</span><div className="wc-softIcon">{['👤', '☁', '🔍', '⚖', '✎', '✈', '📊'][i]}</div><b>{title}</b><p>{completed.includes(stepKeys[i]) ? 'Complete' : current === stepKeys[i] ? 'In Progress' : 'Upcoming'}</p></div>)}</div></div><div className="wc-repairMid"><div className="wc-card"><SectionHead title="Your Next Actions" action="View all" /><div className="wc-actionRow three"><ActionCard icon="☁" title="Upload your credit report" text="This helps us analyze your file." button="Upload Now" onClick={() => document.querySelector('[data-requirement=\"credit_report\"] button')?.click()} /><ActionCard icon="👥" title="Answer a few questions" text="Help us understand your goals." button="Continue Profile" onClick={() => navigate('/client/profile')} /><ActionCard icon="➕" title="Review dispute letters" text={`${journey?.letters?.length || 0} letter(s) in workflow.`} button="Review" onClick={() => navigate('/client/dispute-review')} /></div><div className="wc-inlineRequirementGrid"><InlineDocumentRequirement title="Credit Report" description="Upload a current report for the repair workflow." category="credit_report" requirementKey="credit_report" fromPage="credit-repair" impactLabel="Required" existingDocuments={existingDocuments} onUploaded={onUploaded} whyItMatters="Starts specialist review." /><InlineDocumentRequirement title="Supporting Dispute Documents" description="Upload evidence or supporting documents for dispute review." category="dispute_support" requirementKey="dispute_support" fromPage="credit-repair" impactLabel="Optional" required={false} existingDocuments={existingDocuments} onUploaded={onUploaded} whyItMatters="Helps specialists draft accurate letters." /></div></div><div className="wc-card wc-progressBox"><h3>Progress Overview</h3><Donut value={percent} small tone="blue" /><p>{completed.length} completed · current step: {current.replaceAll('_', ' ')}</p></div></div><CreditRepairCaseEnginePanel existingDocuments={existingDocuments} onUploaded={onUploaded} navigate={navigate} /><div className="wc-repairBottom"><MiniCard icon="✉" title="Send From Home with DocuPost" tag="Approval gated" text="No letter is sent until specialist review and your explicit approval." button="Review gate" onClick={() => navigate('/client/dispute-review')} /><MiniCard icon="📝" title="Draft Letters" tag={`${journey?.letters?.length || 0} Ready`} text="Clyde and your specialist draft custom dispute letters." button="View drafts" onClick={() => navigate('/client/dispute-review')} /><MiniCard icon="⚑" title="Credit Monitoring Support" tag="Optional" text="Monitoring can support awareness, but upload/review drives this workflow." button="Resources" onClick={() => navigate('/client/resources?category=credit-monitoring')} /></div></section>
}

function CreditRepairCaseEnginePanel({ existingDocuments, onUploaded, navigate }) {
  const reasonEntries = Object.entries(DISPUTE_REASON_LABELS)
  const [ctx, setCtx] = useState(null)
  const [creditCase, setCreditCase] = useState(null)
  const [items, setItems] = useState([])
  const [selectedItemId, setSelectedItemId] = useState('')
  const [selectedReason, setSelectedReason] = useState('not_sure')
  const [options, setOptions] = useState([])
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [form, setForm] = useState({ bureau: 'experian', furnisher_name: '', account_name: '', account_number_masked: '', item_type: 'collection', reported_status: '', raw_notes: '' })

  const loadCase = async () => {
    try {
      const resolved = await resolveClientContextForCurrentUser()
      if (!resolved) throw new Error('Sign in is required to load your credit repair case.')
      setCtx(resolved)
      const active = await getOrCreateCreditRepairCase(resolved)
      setCreditCase(active)
      const rows = await listCreditReportItems(resolved, active.id)
      setItems(rows)
      if (!selectedItemId && rows[0]) setSelectedItemId(rows[0].id)
    } catch (err) {
      setError(err.message || 'Could not load credit repair case.')
    }
  }

  useEffect(() => { loadCase() }, [])

  const selectedItem = items.find(item => item.id === selectedItemId)

  async function addItem() {
    if (!ctx || !creditCase) return
    setError('')
    const result = await createManualReportItem(ctx, creditCase.id, form)
    if (!result.ok) {
      setError(result.error || 'Could not add item.')
      return
    }
    setMessage('Item added. Choose whether you want it challenged and select a reason.')
    setForm({ bureau: 'experian', furnisher_name: '', account_name: '', account_number_masked: '', item_type: 'collection', reported_status: '', raw_notes: '' })
    await loadCase()
  }

  async function toggleChallenge(item) {
    if (!ctx) return
    const next = !item.client_wants_challenged
    const result = await markItemForChallenge(ctx, item.id, next)
    if (!result.ok) setError(result.error || 'Could not update challenge preference.')
    else {
      setMessage(next ? 'Marked for challenge. Choose the dispute reason next.' : 'Challenge preference removed.')
      await loadCase()
    }
  }

  async function chooseReason(reason) {
    setSelectedReason(reason)
    if (!selectedItem || !ctx) return
    const generated = generateDisputeLetterOptions(selectedItem, reason, { caseId: creditCase?.id })
    setOptions(generated)
    await selectDisputeReason(ctx, selectedItem.id, reason)
    setMessage('Dispute options prepared for GoClear review. No letter is sent from this step.')
  }

  async function prepareDraft(option) {
    if (!ctx || !selectedItem) return
    setError('')
    const result = await createLetterDraftFromOption(ctx, { ...option, caseId: creditCase?.id, reportItemId: selectedItem.id, item: selectedItem })
    if (!result.ok) {
      setError(result.error || 'Could not prepare draft.')
      return
    }
    setMessage('Draft prepared for specialist review. Client approval is required before any DocuPost send request.')
  }

  return <div className="wc-card wc-caseEngine"><SectionHead title="Credit Repair Case Engine" action={creditCase ? `Round ${creditCase.current_round} · ${creditCase.status}` : 'Loading'} /><p>Tell me which items you want challenged. Clyde will help organize them, ask the right dispute questions, prepare options for GoClear review, and move approved disputes into the next action step.</p><div className="wc-caseStatusGrid"><MiniCard icon="⚖" title="Credit Repair Case Status" tag={creditCase?.status || 'Intake'} text={creditCase?.case_goal || 'Challenge negative items and pursue removal or correction when supportable.'} /><MiniCard icon="☁" title="Upload Credit Report" tag="Required" text="Upload the latest report before specialist review." button="Open upload" onClick={() => document.querySelector('[data-requirement=\"credit_report\"] button')?.click()} /><MiniCard icon="✉" title="Specialist Review" tag="Required" text="GoClear reviews selected items, evidence, and letter options before client approval." button="Review letters" onClick={() => navigate('/client/dispute-review')} /></div><div className="wc-caseGrid"><div className="wc-caseColumn"><h3>Negative Items / Items to Challenge</h3><div className="wc-formGrid two"><label><span>Bureau</span><select value={form.bureau} onChange={e => setForm(p => ({ ...p, bureau: e.target.value }))}><option value="experian">Experian</option><option value="equifax">Equifax</option><option value="transunion">TransUnion</option><option value="other">Other</option></select></label><label><span>Item type</span><select value={form.item_type} onChange={e => setForm(p => ({ ...p, item_type: e.target.value }))}><option value="collection">Collection</option><option value="charge_off">Charge off</option><option value="late_payment">Late payment</option><option value="inquiry">Inquiry</option><option value="personal_info">Personal info</option><option value="duplicate_account">Duplicate account</option><option value="other">Other</option></select></label><label><span>Furnisher</span><input value={form.furnisher_name} onChange={e => setForm(p => ({ ...p, furnisher_name: e.target.value }))} /></label><label><span>Account / item name</span><input value={form.account_name} onChange={e => setForm(p => ({ ...p, account_name: e.target.value }))} /></label><label><span>Account last 4 only</span><input value={form.account_number_masked} onChange={e => setForm(p => ({ ...p, account_number_masked: e.target.value }))} placeholder="1234" /></label><label><span>Reported status</span><input value={form.reported_status} onChange={e => setForm(p => ({ ...p, reported_status: e.target.value }))} /></label></div><textarea className="wc-textarea" value={form.raw_notes} onChange={e => setForm(p => ({ ...p, raw_notes: e.target.value }))} placeholder="Why do you want this reviewed? Do not enter SSN, full DOB, full account numbers, or bureau credentials." /><button className="wc-primaryWide" onClick={addItem}>Add item to case</button><div className="wc-caseItems">{items.length === 0 && <p>No report items added yet. Add items manually while report parsing is not automated.</p>}{items.map(item => <button key={item.id} className={`wc-caseItem ${selectedItemId === item.id ? 'active' : ''}`} onClick={() => { setSelectedItemId(item.id); setOptions([]) }}><b>{item.furnisher_name || item.account_name || item.item_type}</b><span>{item.bureau} · {item.item_type}</span><small>{item.client_wants_challenged ? 'I want this challenged' : 'Not selected yet'}</small></button>)}</div></div><div className="wc-caseColumn"><h3>Dispute Reason Selector</h3>{selectedItem ? <><button className="wc-primaryWide" onClick={() => toggleChallenge(selectedItem)}>{selectedItem.client_wants_challenged ? 'Selected for challenge' : 'I want this challenged'}</button><div className="wc-reasonGrid">{reasonEntries.map(([key, label]) => <button key={key} className={selectedReason === key ? 'active' : ''} onClick={() => chooseReason(key)}>{label}</button>)}</div><InlineDocumentRequirement title="Evidence Upload" description="Upload proof related to this challenge: payment proof, settlement letter, ID, proof of address, bureau response, collection letter, or other support." category="dispute_support" requirementKey="dispute_support" fromPage="credit-repair-case" impactLabel="Evidence" required={false} existingDocuments={existingDocuments} onUploaded={onUploaded} whyItMatters="Evidence helps GoClear choose the right dispute option." /></> : <p>Select or add an item first.</p>}</div><div className="wc-caseColumn wide"><h3>Letter Options</h3>{options.length === 0 && <p>Choose a dispute reason to see deterministic letter options. Not sure requires specialist review before any recommendation.</p>}{options.map((option, i) => <article key={option.optionType} className="wc-letterOption"><span>{option.recommended ? 'Recommended' : 'Alternate'} · {option.riskLevel} risk</span><h4>{option.title}</h4><p>{option.summary}</p><small><b>When to use:</b> {option.whenToUse}</small><small><b>Why this fits:</b> {option.whyRecommended}</small><small><b>Evidence:</b> {option.evidenceNeeded.join(', ') || 'Client statement'}</small><small><b>Caution:</b> {option.caution}</small><button onClick={() => prepareDraft(option)}>{i === 0 ? 'Prepare recommended draft for GoClear review' : 'Prepare alternate draft for GoClear review'}</button></article>)}</div></div>{message && <p className="wc-successText">{message}</p>}{error && <p className="wc-errorText">{error}</p>}<div className="wc-caseSafety"><b>No guarantees. No auto-send.</b><span>Nexus helps challenge negative items, request investigation/verification, pursue removal or correction when supportable, and track bureau/furnisher responses. Specialist review and client approval are required before mailing.</span></div></div>
}

function DisputeReviewPanel({ navigate, existingDocuments, onUploaded }) {
  const [journey, setJourney] = useState(null)
  const [loading, setLoading] = useState(true)
  const [workingId, setWorkingId] = useState('')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  const loadJourney = () => {
    setLoading(true)
    loadCreditRepairJourney().then(data => {
      setJourney(data)
      setLoading(false)
    }).catch(err => {
      setError(err.message || 'Could not load dispute letters.')
      setLoading(false)
    })
  }

  useEffect(() => { loadJourney() }, [])

  const letters = journey?.letters || []
  const reviewable = letters.filter(letter => ['draft', 'specialist_review', 'client_review', 'client_approved', 'approved_for_docupost'].includes(letter.status || ''))
  const statusText = (status) => String(status || 'draft').replaceAll('_', ' ')

  async function approveLetter(letter) {
    if (!letter?.id || workingId) return
    setWorkingId(letter.id)
    setNotice('')
    setError('')
    const result = await clientApproveLetter(letter.id)
    setWorkingId('')
    if (!result.ok) {
      setError(result.error || 'Approval failed.')
      return
    }
    setNotice('Letter approved. DocuPost mailing still requires the gated send request.')
    loadJourney()
  }

  async function requestSend(letter) {
    if (!letter?.id || workingId || letter.status !== 'client_approved') return
    setWorkingId(letter.id)
    setNotice('')
    setError('')
    const result = await createDocuPostSendRequest(letter.id)
    setWorkingId('')
    if (!result.ok) {
      setError(result.error || 'DocuPost send request failed.')
      return
    }
    setNotice('DocuPost send request created. Mailing remains approval-gated and is not auto-sent.')
    loadJourney()
  }

  async function requestEdits(letter) {
    if (!letter?.id || workingId) return
    setWorkingId(letter.id)
    setNotice('')
    setError('')
    try {
      if (!isSupabaseConfigured || !supabase) throw new Error('Supabase is not configured in this environment.')
      const ctx = await resolveClientContextForCurrentUser()
      if (!ctx) throw new Error('Could not resolve your client profile.')
      const { error: insertError } = await supabase.from('client_tasks').insert({
        id: `${ctx.authUserId}_dispute_letter_edit_${Date.now()}`,
        tenant_id: ctx.tenantId,
        client_id: ctx.clientId,
        category: 'dispute_letter_edit_request',
        title: `Edit request for ${letter.recipient_name || 'dispute letter'}`,
        summary: 'Client requested edits to a dispute letter from the world-class portal dispute review page.',
        status: 'pending_admin_review',
        priority: 'medium',
        risk_level: 'medium',
        automation_level: 'manual',
        client_visible: true,
        approval_required: true,
        goclear_review_status: 'pending_admin_review',
        source: 'client_portal',
        source_concept: `dispute_review:${letter.id}`,
        created_at: new Date().toISOString(),
      })
      if (insertError) throw insertError
      setNotice('Edit request sent to GoClear for review.')
    } catch (err) {
      setError(err.message || 'Could not request edits.')
    } finally {
      setWorkingId('')
    }
  }

  return <section className="wc-panel wc-panel-dispute"><Hero /><div className="wc-card wc-disputeHero"><div><h2>Review & Send Dispute Letters</h2><p>Review your dispute letters, request edits, approve them, and authorize mailing when ready.</p></div><button onClick={() => navigate('/client/credit-repair-journey')}>Back to Credit Repair Journey</button></div><div className="wc-card wc-safetyBanner"><b>DocuPost safety gate</b><p>DocuPost sending is enabled only after specialist review and client approval/e-sign authorization. Nothing is auto-sent from this page.</p></div><div className="wc-disputeGrid"><div className="wc-card wc-disputeList"><SectionHead title="Letter Review Queue" action={loading ? 'Loading...' : `${reviewable.length} letter(s)`} />{error && <p className="wc-errorText">{error}</p>}{notice && <p className="wc-successText">{notice}</p>}{!loading && !reviewable.length && <div className="wc-emptyState"><div className="wc-softIcon">✉</div><h3>No letters ready yet</h3><p>Upload a current credit report and complete specialist review before letters appear here.</p><button onClick={() => navigate('/client/credit-repair-journey')}>Continue Credit Repair Journey</button></div>}{reviewable.map(letter => {
    const approved = letter.status === 'client_approved'
    const sendRequested = letter.status === 'approved_for_docupost'
    const busy = workingId === letter.id
    return <article className="wc-disputeLetter" key={letter.id}><div><span>{statusText(letter.status)}</span><h3>{letter.recipient_name || 'Dispute letter'}</h3><p>{letter.letter_body ? `${String(letter.letter_body).slice(0, 220)}...` : 'Letter preview will appear after specialist drafting.'}</p></div><div className="wc-disputeActions"><button onClick={() => setNotice(letter.letter_body || 'Letter preview is not available yet.')}>View letter</button><button onClick={() => requestEdits(letter)} disabled={busy || sendRequested}>{busy ? 'Sending...' : 'Request edits'}</button><button onClick={() => approveLetter(letter)} disabled={busy || approved || sendRequested}>{approved || sendRequested ? 'Approved' : busy ? 'Approving...' : 'Approve letter'}</button><button onClick={() => requestSend(letter)} disabled={busy || !approved || sendRequested}>{sendRequested ? 'Send request created' : 'Authorize/send request'}</button></div></article>
  })}</div><div className="wc-card wc-disputeStatus"><h3>Mailing/send request status</h3>{[['No letters ready yet', !reviewable.length], ['Letters ready for review', reviewable.some(l => l.status === 'client_review')], ['Approved letters', reviewable.some(l => l.status === 'client_approved')], ['Requested edits', false], ['Mailing/send request status', reviewable.some(l => l.status === 'approved_for_docupost')]].map(([title, active]) => <ListItem key={title} tone={active ? 'green' : 'blue'} mark={active ? '✓' : '·'} title={title} text={active ? 'Active in your workflow' : 'Waiting for the next step'} />)}</div><div className="wc-card wc-disputeUpload"><h3>Supporting Document</h3><InlineDocumentRequirement title="Supporting Dispute Document" description="Upload evidence or support files for GoClear dispute review." category="dispute_support" requirementKey="dispute_support" fromPage="dispute-review" impactLabel="Optional" required={false} existingDocuments={existingDocuments} onUploaded={onUploaded} whyItMatters="Supports letter review and edit requests." /></div></div></section>
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

function ReviewPanel({ live, scores, refreshLiveData, existingDocuments }) {
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

  return <section className="wc-panel wc-panel-review"><Hero /><div className="wc-reviewGrid"><div className="wc-card wc-listCard"><SectionHead title="Review Readiness Checklist" action="View all →" />{checklist.map(([title, ok, text]) => <ListItem key={title} tone={ok ? 'green' : 'orange'} mark={ok ? '✓' : '!'} title={title} text={text} />)}</div><div className="wc-card wc-formCard"><h3>Request Review</h3><p>Tell us what you'd like reviewed.</p><div className="wc-choiceRow">{['Standard Review', 'Final Review', 'Rescore Review', 'Custom Review'].map(x => <button className={reviewType === x ? 'active' : ''} key={x} onClick={() => setReviewType(x)}>{x}</button>)}</div><input className="wc-inputBox" value={topic} onChange={e => setTopic(e.target.value)} /><textarea className="wc-textarea" value={notes} onChange={e => setNotes(e.target.value)} placeholder="Share anything specific you'd like our team to know..." /><InlineDocumentRequirement title="Review Support Attachment" description="Attach support documents for this review request." category="review_support" requirementKey="review_support" fromPage="request-review" impactLabel="Optional" required={false} existingDocuments={existingDocuments} onUploaded={refreshLiveData} whyItMatters="Attachments help GoClear review your request with context." />{error && <p className="wc-errorText">{error}</p>}{isSubmitted && <p className="wc-successText">Review request submitted. Your profile is now in the GoClear admin review queue.</p>}<button className="wc-submitBtn" disabled={state === 'submitting' || isSubmitted} onClick={submitReview}>{state === 'submitting' ? 'Submitting...' : isSubmitted ? 'Review Requested' : 'Submit Review Request'}</button></div><div className="wc-card wc-nextSteps"><h3>What Happens Next</h3>{['Review Submitted', 'Under Review', 'Results Delivered', 'Take Action'].map((title, i) => <ListItem key={title} tone="blue" mark={String(i + 1)} title={title} text={['Confirmation email with next steps.', 'Specialists review your profile.', 'Feedback and recommendations.', 'Improve your profile.'][i]} />)}</div></div></section>
}

function IconSystemPanel() {
  return <section className="wc-panel wc-panel-icons"><div className="wc-iconLayout"><div className="wc-card wc-iconIntro"><div className="wc-brandLine"><div className="wc-brandMark">N</div><div><b>NEXUS</b><span>CLIENT PORTAL</span></div></div><h2>ICON SYSTEM</h2><p>A cohesive modern icon set that reflects clarity, progress, and trust with rounded containers and soft shadows.</p><div className="wc-guidelines"><b>Usage Guidelines</b><p>Use consistently across navigation, feature cards, and actions.</p><p>Maintain clear spacing and proportions.</p><p>Use for navigation, features, and actions.</p></div></div><div className="wc-card wc-iconMain">{[
    ['Navigation & Account', [['⌂', 'Home'], ['♟', 'Profile & Info'], ['〽', 'Credit Health'], ['▤', 'Documents'], ['▥', 'Business Setup']]],
    ['Journey & Progress', [['⚑', 'Funding Readiness'], ['↻', 'Credit Repair Journey'], ['▥', 'Resources'], ['▱', 'Request Review'], ['🔔', 'Notifications']]],
    ['Tools & Actions', [['🎧', 'Support'], ['☁', 'Upload'], ['📄', 'Credit Report'], ['🛡', 'Identity Verification'], ['🏦', 'Bank Statement']]],
    ['Documents & Offers', [['📜', 'Business License'], ['⭐', 'Funding Offer'], ['👤', 'Specialist Review'], ['✉', 'Dispute Letters'], ['✈', 'Approve & Send']]],
  ].map(([group, icons]) => <div className="wc-iconGroup" key={group}><h3>{group}</h3><div className="wc-iconGrid">{icons.map(([icon, label]) => <div className="wc-iconDemo" key={label}><div>{icon}</div><b>{label}</b></div>)}</div></div>)}</div></div></section>
}

function ClydeChatDrawer({ open, onClose, navigate, guidance, pageTitle }) {
  const [answer, setAnswer] = useState('')
  if (!open) return null
  const topActions = guidance.slice(0, 3)
  const respond = (message) => setAnswer(message)
  return <div className="wc-clydeOverlay" role="dialog" aria-modal="true" aria-label="Ask Clyde">
    <div className="wc-clydeDrawer">
      <div className="wc-clydeDrawerHead"><div className="wc-bot">🤖</div><div><h2>Ask Clyde</h2><p>{pageTitle} guidance</p></div><button onClick={onClose} aria-label="Close Clyde chat">×</button></div>
      <div className="wc-clydeContext"><b>Current page context</b><p>Clyde can help you choose items to challenge, organize dispute reasons, prepare options for GoClear review, and track what worked after bureau or furnisher responses.</p></div>
      <div className="wc-clydePromptGrid">
        <button onClick={() => respond('Upload a current credit report and any evidence tied to the item: payment proof, settlement letter, ID, proof of address, bureau response, collection letter, or other support.')}>Which documents do I need?</button>
        <button onClick={() => respond('Tell me which items you want challenged and why. I can prepare dispute options, but GoClear specialist review and client approval are required before mailing.')}>How do I challenge an item?</button>
        <button onClick={() => respond('If a bureau or furnisher verifies an item, the next option may be method of verification, furnisher dispute, stronger evidence upload, or a funding workaround.')}>What happens if verified?</button>
      </div>
      {topActions.length > 0 && <div className="wc-advisorBox"><h4>Recommended actions</h4>{topActions.map((item, i) => <button className="wc-clydeItem" key={item.id || item.title} onClick={() => { onClose(); navigate(routeFromGuidance(item)) }}><ListItem tone={item.priority === 'high' ? 'orange' : item.priority === 'medium' ? 'blue' : 'green'} mark={String(i + 1)} title={item.title} text={item.description} /></button>)}</div>}
      {answer && <div className="wc-clydeAnswer"><b>Clyde</b><p>{answer}</p></div>}
      <label className="wc-clydeInput"><span>Message Clyde</span><input disabled placeholder="Live chat is coming soon. Use the suggested questions or request human review." /></label>
      <div className="wc-clydeDrawerActions"><button onClick={() => navigate('/client/documents')}>Go to Documents</button><button onClick={() => navigate('/client/request-review')}>Request human review</button></div>
    </div>
  </div>
}

function ClydePanel({ navigate, guidance, onOpenChat }) {
  const recommendations = guidance.length ? guidance.slice(0, 3) : [
    { title: 'Complete profile & business info', description: 'Expires in 7 days', priority: 'high', category: 'profile' },
    { title: 'Upload credit report', description: 'Strongly recommended', priority: 'medium', category: 'documents' },
    { title: 'Verify identity', description: 'Completed', priority: 'low', category: 'documents' },
  ]
  return <aside className="wc-advisor"><div className="wc-advisorCard"><div className="wc-botTop"><div className="wc-bot">🤖</div><div><h3>Clyde • Credit Specialist</h3><div className="wc-online">● Online</div></div></div><p>Hi Alex! I'm Clyde, your funding coach. I'm here to help you improve your profile and reach your funding goals.</p><div className="wc-advisorBox"><h4>Top Recommendations</h4>{recommendations.map((item, i) => <button className="wc-clydeItem" key={item.id || item.title} onClick={() => navigate(routeFromGuidance(item))}><ListItem tone={item.priority === 'high' ? 'orange' : item.priority === 'medium' ? 'blue' : 'green'} mark={item.priority === 'low' ? '✓' : String(i + 1)} title={item.title} text={item.description} /></button>)}</div><div className="wc-advisorBox"><h4>Clyde's Tip</h4><p>Keeping utilization below 30% can have one of the biggest positive impacts on your score.</p></div><div className="wc-suggestions"><button onClick={() => navigate('/client/credit-profile')}>What can improve my score fastest?</button><button onClick={() => navigate('/client/documents')}>Which documents do I need?</button></div><button className="wc-chatBtn" onClick={onOpenChat}>💬 Chat with Clyde</button></div></aside>
}

export default function WorldClassClientPortal({ path, onNavigate }) {
  const { live, profileComplete, status, refreshLiveData } = useWorldClassLiveData()
  const [showIcons, setShowIcons] = useState(false)
  const [clydeOpen, setClydeOpen] = useState(false)
  const meta = pageMeta[path] || pageMeta['/client/dashboard']
  const scores = useMemo(() => getScores(live), [live])
  const existingDocuments = useMemo(() => getDocumentRows(live), [live])
  const clientStatuses = useMemo(() => buildClientStatuses(live, profileComplete, scores), [live, profileComplete, scores])
  const clydeGuidance = useMemo(() => generateClientGuidance(clientStatuses), [clientStatuses])
  const profile = clientPortalData.clientProfile
  const liveStatusLabel = status === 'connected' ? 'Live data connected' : status === 'loading' ? 'Live data pending' : 'Demo/fallback data'

  useEffect(() => setShowIcons(false), [path])

  const routeTo = (nextPath) => {
    setShowIcons(false)
    setClydeOpen(false)
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
    profile: <ProfilePanel navigate={routeTo} onSaved={refreshLiveData} existingDocuments={existingDocuments} />,
    credit: <CreditPanel navigate={routeTo} existingDocuments={existingDocuments} onUploaded={refreshLiveData} />,
    documents: <DocumentsPanel live={live} refreshLiveData={refreshLiveData} withSuggestedUpload={withSuggestedUpload} navigate={routeTo} />,
    business: <BusinessPanel live={live} navigate={routeTo} />,
    funding: <FundingPanel scores={scores} navigate={routeTo} existingDocuments={existingDocuments} onUploaded={refreshLiveData} />,
    repair: <RepairPanel scores={scores} navigate={routeTo} existingDocuments={existingDocuments} onUploaded={refreshLiveData} />,
    dispute: <DisputeReviewPanel navigate={routeTo} existingDocuments={existingDocuments} onUploaded={refreshLiveData} />,
    resources: <ResourcesPanel live={live} navigate={routeTo} />,
    review: <ReviewPanel live={live} scores={scores} refreshLiveData={refreshLiveData} existingDocuments={existingDocuments} />,
  }[meta.key]

  return <div className="wc-client-portal">
    <aside className="wc-sidebar"><div className="wc-brandButton"><div className="wc-brandMark">N</div><div className="wc-brandText"><b>NEXUS</b><span>CLIENT PORTAL</span></div></div><nav className="wc-sideNav">{navItems.map(([route, label, icon]) => <button key={route} className={`wc-navLabel ${!showIcons && pageMeta[route]?.key === meta.key ? 'active' : ''}`} onClick={() => routeTo(route)}><span className="wc-navIcon">{icon}</span><span>{label}</span></button>)}</nav><button className={`wc-sideAction ${showIcons ? 'active' : ''}`} onClick={() => setShowIcons(true)}>View icon system →</button><div className="wc-help"><strong>Need help?</strong><p>Our team is here to support you.</p></div>{shouldShowInternalDataBadge && <div className="wc-live"><strong>●</strong> {liveStatusLabel}<p>as of today, 9:41 AM</p></div>}<button className="wc-signOut" onClick={async () => { await supabase?.auth.signOut(); window.location.assign('/client/login') }}>Sign Out</button></aside>
    <main className="wc-main"><header className="wc-topbar"><div className="wc-pill">💎 {profile.membershipTier || 'GoClear Readiness Member'}</div><button className="wc-bell" onClick={() => routeTo('/client/resources')}>🔔<span>2</span></button><div className="wc-userPill"><div className="wc-avatar">👨🏻</div>{profile.name || 'Alex Morgan'}⌄</div></header><div className="wc-pageHost">{panel}</div></main>
    <ClydePanel navigate={routeTo} guidance={clydeGuidance} onOpenChat={() => setClydeOpen(true)} />
    <ClydeChatDrawer open={clydeOpen} onClose={() => setClydeOpen(false)} navigate={routeTo} guidance={clydeGuidance} pageTitle={meta.title} />
  </div>
}
