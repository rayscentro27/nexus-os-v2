import React, { useEffect, useMemo, useState } from 'react'
import { clientPortalData } from '../../data/clientPortalData'
import { clientDataMode, shouldShowInternalDataBadge } from '../../data/clientDataMode'
import { supabase } from '../../lib/supabaseClient'
import { loadClientPortalLiveData, loadClientProfileIntake, checkProfileIntakeComplete } from '../../lib/clientPortalDataAdapter'
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

  useEffect(() => {
    if (!clientDataMode.liveSupabaseTestClientEnabled) return
    let cancelled = false
    loadClientPortalLiveData().then(result => {
      if (cancelled) return
      setLive(result)
      setStatus(result?.profile ? 'connected' : 'fallback')
    }).catch(() => setStatus('error'))
    loadClientProfileIntake().then(result => {
      if (!cancelled && result.source === 'supabase') setProfileComplete(checkProfileIntakeComplete(result.data))
    }).catch(() => {})
    return () => { cancelled = true }
  }, [])

  return { live, profileComplete, status }
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

function ProfilePanel({ navigate }) {
  return <section className="wc-panel wc-panel-profile"><Hero /><div className="wc-profileCards">
    {[
      ['👤', 'Personal Details', 'Complete', 'Personal and identification details.'],
      ['📞', 'Contact Information', 'Complete', 'Phone, email, and contact methods.'],
      ['🏠', 'Home Address', '80%', 'Primary residential address.'],
      ['💼', 'Business Information', 'Complete', 'Legal name, industry, and key details.'],
      ['📍', 'Business Address', '60%', 'Physical address for operations.'],
      ['🪪', 'EIN / Entity Details', '40%', 'Tax ID, entity type, and formation info.'],
    ].map(([icon, title, tag, text]) => <MiniCard key={title} icon={icon} title={title} tag={tag} text={text} button="Edit" />)}
    </div><div className="wc-supportDocs"><SectionHead title="Supporting Documents" action="Upload documents to verify your identity and business." /><div className="wc-docTileRow">
      {[
        ['📄', 'Government ID', 'Complete', 'driver_license.pdf', 'Replace file', 'greenText'],
        ['📄', 'Proof of Address', 'Pending', 'Upload Document', 'Upload Document', 'orangeText'],
        ['📄', 'Business Formation Docs', 'Pending', 'Upload Document', 'Upload Document', 'orangeText'],
      ].map(([icon, title, status, text, button, cls]) => <div className="wc-card wc-docTile" key={title}><div className="wc-softIcon">{icon}</div><b>{title}</b><span className={`wc-${cls}`}>{status}</span><p>{text}</p><button onClick={() => navigate('/client/documents')}>{button}</button></div>)}
    </div></div></section>
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

function DocumentsPanel({ live }) {
  const uploadedDocs = live?.documents?.uploadedDocuments || ['Bank Statement - Chase', 'Pay Stub - April 2025', 'ID - Driver License', 'Utility Bill - April 2025']
  const missingDocs = live?.documents?.missingDocuments || ['Credit Report', 'Bank Statement', 'Proof of Address']
  return <section className="wc-panel wc-panel-documents"><Hero /><div className="wc-docHub"><div className="wc-card wc-drop"><div className="wc-uploadIcon">↑</div><h3>Drag & drop files here to upload</h3><p>or choose an option below</p><div><button>Choose Files</button><button className="secondary">Use Mobile Camera</button></div><small>Accepted: PDF, JPG, PNG · Max 25MB</small></div><div className="wc-card wc-scanner"><h3>Smart Scanner Flow</h3>{[['↑', 'Uploaded', 'Your document is securely uploaded'], ['✦', 'Scanning', 'We scan and read the contents'], ['✓', 'Categorized', 'We identify the document type'], ['⌂', 'Routed', 'Stored in the right place automatically']].map(([icon, title, text]) => <div className="wc-scanStep" key={title}><span>{icon}</span><div><b>{title}</b><p>{text}</p></div></div>)}</div></div>
    <div className="wc-quickUpload"><b>Quick Upload</b>{['Credit Report', 'ID Document', 'Proof of Address', 'Bank Statement', 'Tax Return', 'Business License', 'Other'].map(x => <button key={x}>{x}</button>)}</div>
    <div className="wc-docLists"><div className="wc-card wc-listCard"><SectionHead title="Recently Uploaded" action="View all →" />{uploadedDocs.slice(0, 4).map((doc, i) => <ListItem key={`${doc}-${i}`} title={doc} text="Categorized" />)}</div><div className="wc-card wc-listCard"><SectionHead title="Needs Review" action="View all →" /><ListItem tone="orange" mark="!" title="Tax Return - 2023" text="Uploaded May 16, 2025" /><ListItem tone="orange" mark="!" title="Business License" text="Uploaded May 15, 2025" /><ListItem tone="orange" mark="!" title="Profit & Loss Statement" text="Uploaded May 14, 2025" /></div><div className="wc-card wc-listCard"><SectionHead title="Missing Documents" action="View all →" />{missingDocs.slice(0, 3).map(doc => <ListItem key={doc} tone="orange" mark="!" title={doc} text="High Impact" />)}</div><div className="wc-card wc-recommended"><h3>Recommended for You</h3><p>Upload Proof of Income</p><p>Add More Bank Statements</p><p>Submit Business License</p><button>See recommendations →</button></div></div>
    <div className="wc-card wc-secure"><b>🛡 Your documents are safe & secure</b><span>Bank-level encryption protects your data.</span><button>Learn about security →</button></div></section>
}

function BusinessPanel({ navigate }) {
  return <section className="wc-panel wc-panel-business"><Hero /><div className="wc-card wc-checklist"><SectionHead title="Your Business Setup Checklist" action="9 of 9 steps" /><div className="wc-checkGrid">{[
    ['🏢', 'Business Name', 'Complete'], ['📜', 'Entity Formation', 'In Progress'], ['🧾', 'EIN (Tax ID)', 'In Progress'], ['📍', 'Business Address', 'Complete'], ['☎', 'Phone & Email', 'Complete'], ['🌐', 'Website', 'Recommended'], ['🏙', 'Industry / NAICS', 'Complete'], ['🏦', 'Bank Account Setup', 'Missing'], ['📁', 'Required Documents', 'In Progress'],
  ].map(([icon, title, status]) => <div className="wc-checkTile" key={title}><div className="wc-softIcon">{icon}</div><div><b>{title}</b><p>Business foundation item</p><span>{status}</span></div></div>)}</div></div><div className="wc-businessBottom"><div className="wc-card wc-why"><h3>Why this matters for Funding Readiness</h3><div className="wc-whyRow"><span>🛡<b>Builds credibility</b></span><span>🎯<b>Unlocks opportunities</b></span><span>📈<b>Improves trust</b></span></div></div><div className="wc-card wc-next"><h3>Ready for the next step?</h3><p>Once your business foundation is solid, move into Funding Readiness.</p><button onClick={() => navigate('/client/funding-readiness')}>Go to Funding Readiness →</button></div></div></section>
}

function FundingPanel({ scores, navigate }) {
  return <section className="wc-panel wc-panel-funding"><Hero /><div className="wc-card wc-flow"><SectionHead title="How Your Data Builds Your Readiness" /><div className="wc-flowLine">{['Profile & Info', 'Credit Health', 'Documents', 'Business Setup', 'Credit Repair Journey', 'Funding Readiness'].map((title, i) => <div key={title}><span>{i === 5 ? '⚑' : '✓'}</span><b>{title}</b><p>{i === 5 ? 'Unlock offers' : 'Build readiness'}</p></div>)}</div></div><div className="wc-fundingGrid"><div className="wc-card wc-summary"><h3>Readiness Summary</h3><Donut value={scores.funding} /><p><b className="wc-orangeText">Moderate</b><br />You're making solid progress. Complete a few key items to reach Strong.</p><button>View full breakdown</button></div><div className="wc-card wc-listCard"><SectionHead title="Factors Helping You" action="View all →" /><ListItem title="Business years in operation: 7 yrs" text="Strong history" /><ListItem title="On-time payments: 90%" text="Positive credit profile" /><ListItem title="Verified business info" text="Complete" /><ListItem title="Documents uploaded: 13" text="Good record" /></div><div className="wc-card wc-listCard"><SectionHead title="Factors Holding You Back" action="View all →" /><ListItem tone="orange" mark="!" title="Limited business credit history" text="Short" /><ListItem tone="orange" mark="!" title="D-U-N-S number missing" text="Required by many lenders" /><ListItem tone="orange" mark="!" title="Credit inquiries" text="High" /><ListItem tone="orange" mark="!" title="Trade lines reported" text="Low" /></div><div className="wc-card wc-required"><h3>Required Items to Unlock Better Terms</h3>{['D-U-N-S Number', 'Business Bank Statements', 'Tax Return', 'Profit & Loss Statement', 'Business License'].map((title, i) => <div className="wc-req" key={title}><b>{title}</b><p>Impact: {i < 3 ? 'High' : 'Medium'}</p><button onClick={() => navigate(i === 0 ? '/client/business-setup' : '/client/documents')}>{i === 0 ? 'Add Now' : 'Upload'}</button></div>)}</div></div><div className="wc-card wc-opportunityRow"><b>Ready Opportunities for You</b><span>Business Credit · $1K-$250K</span><span>Startup Funding · $5K-$500K</span><span>Equipment Financing · $2K-$1M+</span><span>Monitoring Tools · Recommended</span><button onClick={() => navigate('/client/resources')}>Explore</button></div></section>
}

function RepairPanel({ scores, navigate }) {
  return <section className="wc-panel wc-panel-repair"><Hero /><div className="wc-card wc-repairJourney"><div className="wc-repairLine">{['Profile Complete', 'Upload Credit Report', 'Specialist Review', 'Dispute Items', 'Draft Letters', 'Approve & Send', 'Track Results'].map((title, i) => <div key={title}><span className={`wc-stepDot ${i === 0 ? 'done' : i < 3 ? 'active' : ''}`}>{i + 1}</span><div className="wc-softIcon">{['👤', '☁', '🔍', '⚖', '✎', '✈', '📊'][i]}</div><b>{title}</b><p>{i === 0 ? 'Complete' : i < 3 ? 'In Progress' : 'Upcoming'}</p></div>)}</div></div><div className="wc-repairMid"><div className="wc-card"><SectionHead title="Your Next Actions" action="View all" /><div className="wc-actionRow three"><ActionCard icon="☁" title="Upload your credit report" text="This helps us analyze your file." button="Upload Now" onClick={() => navigate('/client/documents')} /><ActionCard icon="👥" title="Answer a few questions" text="Help us understand your goals." button="Continue Profile" onClick={() => navigate('/client/profile')} /><ActionCard icon="➕" title="Invite a co-applicant" text="Strengthen your credit profile." button="Invite Now" /></div></div><div className="wc-card wc-progressBox"><h3>Progress Overview</h3><Donut value={scores.repair} small tone="blue" /><p>2 completed · 1 in progress · 4 upcoming</p></div></div><div className="wc-repairBottom"><MiniCard icon="✉" title="Send From Home with DocuPost" tag="New" text="We'll send approved letters securely and trackably." button="Learn more" /><MiniCard icon="📝" title="Draft Letters" tag="Ready" text="Clyde and your specialist draft custom dispute letters." button="View drafts" onClick={() => navigate('/client/dispute-review')} /><MiniCard icon="⚑" title="Nexus Guidance" tag="Active" text="You are not alone. We educate, advocate, and deliver results." button="Open" /></div></section>
}

function ResourcesPanel() {
  return <section className="wc-panel wc-panel-resources"><Hero /><div className="wc-resourceRec">{[
    ['Continue Learning', 'Understanding Your Funding Readiness Score', 'Read →'],
    ['Next Step', 'Build Strong Business Credit', 'Start →'],
    ['In Progress', 'Credit Repair Action Plan', 'Continue →'],
    ['Tool Recommendation', 'Monitor Credit with Confidence', 'Compare →'],
  ].map(([tag, title, button]) => <div className="wc-card wc-resCard" key={title}><span>{tag}</span><h3>{title}</h3><p>Recommended based on your current goals.</p><button>{button}</button></div>)}</div><div className="wc-card wc-resourceBanner"><h3>Resources connect to real progress.</h3><p>Every article, video, guide, and tool helps you take action and move closer to funding.</p><div><span>✓ Learn proven strategies</span><span>✓ Take action with confidence</span><span>✓ Unlock more opportunities</span></div></div><div className="wc-catRow">{[['🎓', 'Learning Center', 18], ['📘', 'Funding Education', 22], ['📈', 'Credit Repair Tips', 15], ['💼', 'Business Setup Guides', 17], ['🧰', 'Recommended Tools', 12]].map(([icon, title, count]) => <MiniCard key={title} icon={icon} title={title} text={`${count} resources available.`} button="Explore" />)}</div><div className="wc-partnerRow">{[['LiveWell', 'Credit Monitoring'], ['Nav', 'Business Credit Builder'], ['Relay', 'Business Banking'], ['D&B', 'Business Credit Profile']].map(([name, text]) => <div className="wc-card wc-partner" key={name}><b>{name}</b><p>{text}</p><button>Learn more →</button></div>)}</div></section>
}

function ReviewPanel() {
  return <section className="wc-panel wc-panel-review"><Hero /><div className="wc-reviewGrid"><div className="wc-card wc-listCard"><SectionHead title="Review Readiness Checklist" action="View all →" />{['Basic Profile & Business Info', 'Credit Health Overview', 'Identity Verification', 'Bank Account Verified', 'Credit Report Uploaded', 'Funding Readiness Score'].map((title, i) => <ListItem key={title} title={title} text={i === 5 ? '72/100 · Recommended 80+' : i === 4 ? 'Required' : 'Complete'} />)}</div><div className="wc-card wc-formCard"><h3>Request Review</h3><p>Tell us what you'd like reviewed.</p><div className="wc-choiceRow">{['Standard Review', 'Final Review', 'Rescore Review', 'Custom Review'].map(x => <button key={x}>{x}</button>)}</div><div className="wc-inputBox">Funding Readiness & Profile Strength</div><div className="wc-textarea">Share anything specific you'd like our team to know...</div><div className="wc-dropMini">☁ Drag & drop files here or Upload Files</div><button className="wc-submitBtn">Submit Review Request</button></div><div className="wc-card wc-nextSteps"><h3>What Happens Next</h3>{['Review Submitted', 'Under Review', 'Results Delivered', 'Take Action'].map((title, i) => <ListItem key={title} tone="blue" mark={String(i + 1)} title={title} text={['Confirmation email with next steps.', 'Specialists review your profile.', 'Feedback and recommendations.', 'Improve your profile.'][i]} />)}</div></div></section>
}

function IconSystemPanel() {
  return <section className="wc-panel wc-panel-icons"><div className="wc-iconLayout"><div className="wc-card wc-iconIntro"><div className="wc-brandLine"><div className="wc-brandMark">N</div><div><b>NEXUS</b><span>CLIENT PORTAL</span></div></div><h2>ICON SYSTEM</h2><p>A cohesive modern icon set that reflects clarity, progress, and trust with rounded containers and soft shadows.</p><div className="wc-guidelines"><b>Usage Guidelines</b><p>Use consistently across navigation, feature cards, and actions.</p><p>Maintain clear spacing and proportions.</p><p>Use for navigation, features, and actions.</p></div></div><div className="wc-card wc-iconMain">{[
    ['Navigation & Account', [['⌂', 'Home'], ['♟', 'Profile & Info'], ['〽', 'Credit Health'], ['▤', 'Documents'], ['▥', 'Business Setup']]],
    ['Journey & Progress', [['⚑', 'Funding Readiness'], ['↻', 'Credit Repair Journey'], ['▥', 'Resources'], ['▱', 'Request Review'], ['🔔', 'Notifications']]],
    ['Tools & Actions', [['🎧', 'Support'], ['☁', 'Upload'], ['📄', 'Credit Report'], ['🛡', 'Identity Verification'], ['🏦', 'Bank Statement']]],
    ['Documents & Offers', [['📜', 'Business License'], ['⭐', 'Funding Offer'], ['👤', 'Specialist Review'], ['✉', 'Dispute Letters'], ['✈', 'Approve & Send']]],
  ].map(([group, icons]) => <div className="wc-iconGroup" key={group}><h3>{group}</h3><div className="wc-iconGrid">{icons.map(([icon, label]) => <div className="wc-iconDemo" key={label}><div>{icon}</div><b>{label}</b></div>)}</div></div>)}</div></div></section>
}

function ClydePanel({ navigate }) {
  return <aside className="wc-advisor"><div className="wc-advisorCard"><div className="wc-botTop"><div className="wc-bot">🤖</div><div><h3>Clyde • Credit Specialist</h3><div className="wc-online">● Online</div></div></div><p>Hi Alex! I'm Clyde, your funding coach. I'm here to help you improve your profile and reach your funding goals.</p><div className="wc-advisorBox"><h4>Top Recommendations</h4><ListItem tone="orange" mark="1" title="Complete profile & business info" text="Expires in 7 days" /><ListItem tone="blue" mark="2" title="Upload credit report" text="Strongly recommended" /><ListItem title="Verify identity" text="Completed" /></div><div className="wc-advisorBox"><h4>Clyde's Tip</h4><p>Keeping utilization below 30% can have one of the biggest positive impacts on your score.</p></div><div className="wc-suggestions"><span>What can improve my score fastest?</span><span>Which documents do I need?</span></div><button className="wc-chatBtn" onClick={() => navigate('/client/resources')}>💬 Chat with Clyde</button></div></aside>
}

export default function WorldClassClientPortal({ path, onNavigate }) {
  const { live, profileComplete, status } = useWorldClassLiveData()
  const [showIcons, setShowIcons] = useState(false)
  const meta = pageMeta[path] || pageMeta['/client/dashboard']
  const scores = useMemo(() => getScores(live), [live])
  const profile = clientPortalData.clientProfile
  const liveStatusLabel = status === 'connected' ? 'Live data connected' : status === 'loading' ? 'Live data pending' : 'Demo/fallback data'

  useEffect(() => setShowIcons(false), [path])

  function navigate(nextPath) {
    setShowIcons(false)
    onNavigate(nextPath)
  }

  const panel = showIcons ? <IconSystemPanel /> : {
    home: <HomePanel scores={scores} live={live} profileComplete={profileComplete} navigate={navigate} />,
    profile: <ProfilePanel navigate={navigate} />,
    credit: <CreditPanel navigate={navigate} />,
    documents: <DocumentsPanel live={live} />,
    business: <BusinessPanel navigate={navigate} />,
    funding: <FundingPanel scores={scores} navigate={navigate} />,
    repair: <RepairPanel scores={scores} navigate={navigate} />,
    resources: <ResourcesPanel />,
    review: <ReviewPanel />,
  }[meta.key]

  return <div className="wc-client-portal">
    <aside className="wc-sidebar"><div className="wc-brandButton"><div className="wc-brandMark">N</div><div className="wc-brandText"><b>NEXUS</b><span>CLIENT PORTAL</span></div></div><nav className="wc-sideNav">{navItems.map(([route, label, icon]) => <button key={route} className={`wc-navLabel ${!showIcons && pageMeta[route]?.key === meta.key ? 'active' : ''}`} onClick={() => navigate(route)}><span className="wc-navIcon">{icon}</span><span>{label}</span></button>)}</nav><button className={`wc-sideAction ${showIcons ? 'active' : ''}`} onClick={() => setShowIcons(true)}>View icon system →</button><div className="wc-help"><strong>Need help?</strong><p>Our team is here to support you.</p></div>{shouldShowInternalDataBadge && <div className="wc-live"><strong>●</strong> {liveStatusLabel}<p>as of today, 9:41 AM</p></div>}<button className="wc-signOut" onClick={async () => { await supabase?.auth.signOut(); window.location.assign('/client/login') }}>Sign Out</button></aside>
    <main className="wc-main"><header className="wc-topbar"><div className="wc-pill">💎 {profile.membershipTier || 'GoClear Readiness Member'}</div><button className="wc-bell" onClick={() => navigate('/client/resources')}>🔔<span>2</span></button><div className="wc-userPill"><div className="wc-avatar">👨🏻</div>{profile.name || 'Alex Morgan'}⌄</div></header><div className="wc-pageHost">{panel}</div></main>
    <ClydePanel navigate={navigate} />
  </div>
}
