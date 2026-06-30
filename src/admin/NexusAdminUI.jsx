// Nexus OS v2 — report-backed continuous operating dashboard.
// Generated runtime data is bundled read-only; no external actions execute from this UI.
import React, { useEffect, useMemo, useState } from 'react'
import runtime from '../data/continuousDashboardData.json'
import nexusEngineStatusData from '../data/nexusEngineStatusData'
import RestoredCommandCenter from '../components/CommandCenter'
import RayReviewCenter from '../components/RayReviewCenter'
import ReportCenter from '../components/ReportCenter'
import HermesWorkroom from '../components/HermesWorkroom'
import AutomationSchedulerPanel from '../components/AutomationSchedulerPanel'
import RevenueDashboard from '../components/RevenueDashboard'
import CommunicationDashboard from '../components/CommunicationDashboard'
import MarketingDraftCenter from '../components/MarketingDraftCenter'
import ResearchMoneyPipeline from '../components/ResearchMoneyPipeline'
import ClientsPanel from '../components/ClientsPanel'
import CreditFundingPanel from '../components/CreditFundingPanel'
import BusinessOpportunitiesPanel from '../components/BusinessOpportunitiesPanel'
import ResearchEnginePanel from '../components/ResearchEnginePanel'
import MonetizationPanel from '../components/MonetizationPanel'
import MarketingDraftsPanel from '../components/MarketingDraftsPanel'
import HermesGlobalLauncher from '../components/HermesGlobalLauncher'
import HermesInlineDrawer from '../components/HermesInlineDrawer'
import SystemHealthPanel from '../components/SystemHealthPanel'
import {
  Activity, BadgeDollarSign, Bot, Building2, CalendarDays, CheckCircle2, ChevronDown,
  ChevronRight, CircleHelp, CircleX, CopyPlus, Cross, Database, DatabaseZap, FileText,
  FileWarning, Image, Layers3, LayoutDashboard, LayoutGrid, Megaphone, Orbit, PauseCircle,
  Plug, ScanSearch, Search, SearchCheck, Send, Settings, Sparkles, Star, Target, TrendingUp,
  TriangleAlert, WandSparkles, Youtube, Zap
} from 'lucide-react'

const toneClass = {
  violet: 'tone-violet',
  amber: 'tone-amber',
  red: 'tone-red',
  blue: 'tone-blue',
  cyan: 'tone-cyan',
  green: 'tone-green'
}

const IconMap = {
  Activity, BadgeDollarSign, Bot, Building2, CalendarDays, CheckCircle2, ChevronDown,
  ChevronRight, CircleHelp, CircleX, CopyPlus, Cross, Database, DatabaseZap, FileText,
  FileWarning, Image, Layers3, LayoutDashboard, LayoutGrid, Megaphone, Orbit, PauseCircle,
  Plug, ScanSearch, Search, SearchCheck, Send, Settings, Sparkles, Star, Target, TrendingUp,
  TriangleAlert, WandSparkles, Youtube, Zap
}

// Meaningful thumbnail icon per workspace kind (replaces generic numbered squares).
const kindThumbIcon = {
  source: 'Youtube', opportunity: 'Building2', campaign: 'Megaphone', design: 'Image',
  trading: 'TrendingUp', seo: 'SearchCheck', integrations: 'DatabaseZap', ops: 'Star', jobs: 'Database'
}

const navGroups = [
  { label: 'Executive', items: [
    { id: 'command', label: 'Command Center', icon: 'LayoutDashboard', status: 'Live', statusTone: 'green' },
    { id: 'health', label: 'System Health', icon: 'Activity', status: 'Healthy', statusTone: 'green' },
    { id: 'rayreview', label: 'Ray Review', icon: 'CheckCircle2', status: '64', statusTone: 'green' },
    { id: 'hermes', label: 'Hermes Workroom', icon: 'Sparkles', status: 'Advisor', statusTone: 'blue' },
    { id: 'reports', label: 'Reports', icon: 'FileText', status: '13', statusTone: 'blue' }
  ]},
  { label: 'Business', items: [
    { id: 'clients', label: 'Clients', icon: 'Building2', status: 'Gated', statusTone: 'amber' },
    { id: 'credit', label: 'Credit & Funding', icon: 'SearchCheck', status: 'Active', statusTone: 'green' },
    { id: 'opportunity', label: 'Business Opportunities', icon: 'Target', status: '26 ready', statusTone: 'green' },
    { id: 'research', label: 'Research Engine', icon: 'ScanSearch', status: '50', statusTone: 'blue' },
    { id: 'monetization', label: 'Monetization', icon: 'BadgeDollarSign', status: '9 offers', statusTone: 'green' },
    { id: 'marketing', label: 'Marketing Drafts', icon: 'Megaphone', status: 'Draft', statusTone: 'amber' }
  ]},
  { label: 'System', items: [
    { id: 'trading', label: 'Trading Demo', icon: 'TrendingUp', status: 'Paper', statusTone: 'amber' },
    { id: 'automation', label: 'Automation Scheduler', icon: 'Bot', status: '2 loaded', statusTone: 'green' },
    { id: 'cli', label: 'CLI / Tool Registry', icon: 'Database', status: 'Valid', statusTone: 'blue' },
    { id: 'settings', label: 'Settings', icon: 'Settings', status: 'Safe', statusTone: 'green' }
  ]}
]

const modeLabels = {
  command: 'Executive Overview',
  subscription: 'Subscription Command Center',
  source: 'Source Intake & Review',
  opportunity: 'Opportunity Lab',
  rayreview: 'Ray Review / Approvals',
  goclear: 'GoClear / Apex',
  clientworkflow: 'Client Workflow',
  credit: 'Credit Specialist',
  business: 'Business Profile Builder',
  funding: 'Funding Readiness',
  monetization: 'Monetization',
  partners: 'Partner Offers',
  creative: 'Creative Studio',
  design: 'Design Library',
  trading: 'Trading Lab (Paper Only)',
  seo: 'SEO / Marketing',
  integrations: 'Integrations',
  ops: 'Ops & Improvements',
  jobs: 'Agent Jobs',
  cli: 'CLI Control',
  health: 'System Health',
  proof: 'Events / Proof Ledger',
  hermes: 'Hermes Advisor',
  feedback: 'Hermes Feedback',
  settings: 'Settings'
}

const datasets = {
  campaign: [
    ['GoClear readiness campaign', 'Multi-channel • B2B', 'Needs Review', '78 /100'],
    ['Business funding carousel', 'LinkedIn • Carousel', 'Scored', '86 /100'],
    ['Email nurture draft', 'Email • 5-part sequence', 'Draft', '—'],
    ['Landing page hero set', 'Website • Hero variations', 'Scheduled', 'Jun 26'],
    ['YouTube thumbnail series', 'YouTube • Thumbnails', 'Scored', '82 /100'],
    ['Short-form video concepts', 'TikTok / Reels • 6 ideas', 'Parked', '—']
  ],
  design: [
    ['Landing Page UI Kit', 'UI Kit', 'Approved', '9.2 /10'],
    ['Social Carousel Set', 'Social', 'Approved', '8.7 /10'],
    ['Brand Card Set', 'Branding', 'In Review', '8.5 /10'],
    ['Dashboard Component Library', 'Component Library', 'Approved', '9.6 /10'],
    ['Email Banner', 'Email', 'Draft', '8.0 /10'],
    ['Hero Image Concept', 'Concept', 'Needs Changes', '7.8 /10']
  ],
  trading: [
    ['Half Trend Forex Strategy', 'EURUSD • 1H • Jun 20, 2026', 'Backtested', '56.3%'],
    ['Options Income Idea', 'SPY • 1D • Jun 19, 2026', 'Needs Review', ''],
    ['Crypto Breakout Model', 'BTCUSDT • 4H', 'Paper Demo', ''],
    ['AI Market Watcher', 'SPX • 1D', 'Backtested', ''],
    ['Vibe Trading Bridge Research', 'MULTI • 1D', 'Scheduled', ''],
    ['Backtest Batch — Q2 Ideas', 'Various', 'Blocked', '']
  ],
  seo: [
    ['Funding Readiness Landing Page', 'Landing Page', 'Live', '92'],
    ['Local SEO Page Cluster', 'SEO Cluster', 'In Progress', '78'],
    ['Lead-Gen Funnel Article', 'Blog / Article', 'Planned', '74'],
    ['Competitor Keyword Gap', 'Keyword Research', 'Researching', '71'],
    ['FAQ Content Refresh', 'On-Page SEO', 'Planned', '68'],
    ['YouTube-to-Blog Repurpose', 'Content Repurpose', 'Planned', '66']
  ],
  integrations: [
    ['Supabase', 'Postgres Database', 'Connected', ''],
    ['Netlify', 'Web Hosting & Deploy', 'Partial', ''],
    ['OpenRouter', 'LLM Routing', 'Connected', ''],
    ['Oanda Demo', 'Market Data (Demo)', 'Needs Config', ''],
    ['Oracle Read-Only', 'Data Warehouse', 'Partial', ''],
    ['Resend', 'Email Delivery', 'Connected', ''],
    ['YouTube Monitor', 'Channel & Video Data', 'Connected', ''],
    ['NotebookLM Bridge', 'Knowledge Sync', 'Partial', ''],
    ['Meta (Token Status)', 'Ad Accounts API', 'Disabled', '']
  ],
  ops: [
    ['Source Intake Polish', 'Improve dedupe, quality scoring and auto-tagging.', 'Implementing', 'Impact 86'],
    ['Mac Bridge Hardening', 'Stabilize macOS bridge & notarization flow.', 'Scheduled', 'Impact 74'],
    ['Provider Scout', 'Automate provider discovery & scoring.', 'Needs Review', 'Impact 81'],
    ['Local Model Benchmark Harness', 'Standardized evals for local LLMs.', 'Blocked', 'Impact 72'],
    ['AI Token Usage Layer', 'Unified token tracking & cost controls.', 'Scheduled', 'Impact 78'],
    ['Revenue Dashboard Upgrade', 'Add cohort analytics & ARPU tracking.', 'Implementing', 'Impact 83'],
    ['Failing Connector Fix', 'Fix intermittent failures in Notion sync.', 'Done', 'Impact 65']
  ],
  jobs: [
    ['Source Enrichment Backfill', 'Data & Integrations', 'Running', 'Since 9:42 AM'],
    ['Opportunity Feeder', 'Opportunity Lab', 'Completed', 'Success'],
    ['Creative Feeder', 'Creative Studio', 'Completed', 'Success'],
    ['SEO Scan', 'SEO / Marketing', 'Needs Review', '2 issues'],
    ['Status Digest', 'Ops & Improvements', 'Completed', 'Success'],
    ['Daily Watch Report', 'Trading Lab', 'Scheduled', 'Next run 2:00 PM'],
    ['Connector Audit', 'Data & Integrations', 'Failed', '3 errors']
  ],
  source: [
    ['How To Build Business Credit Fast (2026 Guide)', 'YouTube Video', 'Summarized', 'Score 82'],
    ['GitHub: credit-repair-tools', 'Concept Research', 'Needs Review', 'Score 88'],
    ['GitHub: credit-scoring', 'Concept Research', 'Needs Review', 'Score 85'],
    ['GitHub: moov-io/awesome-fintech', 'Repo Metadata', 'Summarized', 'Score 83'],
    ['GitHub: Wadprog/RepairCredit-', 'Risk-Gated Concept', 'Blocked', 'Score 80'],
    ['GitHub: loan-management-system', 'Repo Metadata', 'Researching', 'Score 82'],
    ['GitHub: credit-management / loan-approval-system', 'Topic Research', 'Researching', 'Score 79']
  ],
  opportunity: [
    ['Business Credit Offer Builder', 'Credit • SaaS / Service', 'Scored', 'Score 92'],
    ['Micro-SaaS Idea: LinkRadar', 'SaaS • Productivity', 'Summarized', 'Score 87'],
    ['Lead-Gen Funnel for Local Pros', 'Marketing • Lead Gen', 'Scheduled', 'Score 85'],
    ['AI Tooling Service for SMBs', 'AI Services • Automation', 'Scored', 'Score 84'],
    ['SEO Offer: Topical Authority Build', 'SEO • Content', 'Needs Review', 'Score 78'],
    ['Funding Readiness Package', 'Finance • Advisory', 'Implementing', 'Score 73']
  ]
}

const detailCopy = {
  creative: {
    title: 'GoClear readiness campaign',
    icon: 'Megaphone',
    badge: 'Needs Review',
    metrics: ['Audience|Small business owners', 'Campaign Score|78 /100', 'Primary CTA|Start Your Free Trial', 'Next Action|Revise hero copy']
  },
  design: {
    title: 'Landing Page UI Kit',
    icon: 'Image',
    badge: 'Approved',
    metrics: ['Asset ID|UI-2026-0412', 'Version|1.2', 'Score|9.2 /10', 'Usage|Q3 Product Launch']
  },
  trading: {
    title: 'Half Trend Forex Strategy',
    icon: 'TrendingUp',
    badge: 'Backtested',
    metrics: ['Win Rate|56.3%', 'Profit Factor|1.64', 'Total Return|+18.42%', 'Trades|142'],
    chart: true
  },
  seo: {
    title: 'Funding Readiness Landing Page',
    icon: 'SearchCheck',
    badge: 'Live',
    metrics: ['Target Keyword|funding readiness platform', 'Score|92 /100', 'Priority|High', 'Last Updated|2h ago']
  },
  integrations: {
    title: 'Supabase',
    icon: 'DatabaseZap',
    badge: 'Connected',
    metrics: ['Type|Database', 'Host|db.nexusos.app', 'Uptime|99.8%', 'Last checked|2m ago']
  },
  ops: {
    title: 'Source Intake Polish',
    icon: 'Star',
    badge: 'Implementing',
    metrics: ['Status|Implementing', 'Risk|Medium', 'Impact Score|86 /100', 'Target|Jun 30, 2026']
  },
  jobs: {
    title: 'Source Enrichment Backfill',
    icon: 'Database',
    badge: 'Running',
    metrics: ['Records Scanned|128,642', 'Enriched|87,931 (68%)', 'New Data Points|42,188', 'Coverage Lift|+18.6%']
  },
  source: {
    title: 'How To Build Business Credit Fast (2026 Guide)',
    icon: 'Youtube',
    badge: 'Summarized',
    metrics: ['Type|YouTube Video', 'Duration|18:42', 'Score|82 /100', 'Destination|Opportunity Lab']
  },
  opportunity: {
    title: 'Business Credit Offer Builder',
    icon: 'Building2',
    badge: 'Scored',
    metrics: ['Opportunity Score|92 /100', 'Revenue Potential|$18K – $90K /mo', 'Time to First Revenue|30–45 days', 'Confidence|87%']
  }
}

function Icon({ name, size = 20, className = '' }) {
  const Cmp = IconMap[name] || Sparkles
  return <Cmp size={size} className={className} />
}

function Pill({ children, tone = 'blue' }) {
  return <span className={`pill pill-${tone}`}>{children}</span>
}

function Sidebar({ activePage, onNavigate }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark"><Icon name="Orbit" size={25} /></div>
        <div className="brand-name">Nexus <span>OS v2</span></div>
      </div>

      <nav>
        {navGroups.map(group => (
          <div className="nav-group" key={group.label}>
            <div className="nav-heading">{group.label}</div>
            {group.items.map(item => {
              const isActive = activePage === item.id
              return (
                <button
                  key={item.id}
                  className={`nav-item ${isActive ? 'active' : ''} ${item.disabled ? 'disabled' : ''}`}
                  onClick={() => !item.disabled && onNavigate(item.id)}
                  type="button"
                >
                  <Icon name={item.icon} size={20} />
                  <span>{item.label}</span>
                  {item.status && <Pill tone={item.statusTone}>{item.status}</Pill>}
                </button>
              )
            })}
          </div>
        ))}
      </nav>

      <div className="advisor-card" onClick={() => onNavigate('hermes')} role="button" tabIndex={0}>
        <div className="advisor-ring" />
        <div>
          <strong>Hermes Advisor</strong>
          <small>AI Executive Assistant</small>
        </div>
        <Icon name="ChevronRight" size={16} className="push" />
      </div>
    </aside>
  )
}

function Topbar({ email }) {
  return (
    <header className="topbar">
      <div className="searchbar"><Icon name="Search" size={20} /><span>Search across Nexus OS v2...</span><kbd>⌘K</kbd></div>
      <a className="client-portal-link" href="/client">View Client Portal</a>
      <div className="hermes-status"><Icon name="Activity" size={20} />Hermes Local Advisor <span>• Local context</span></div>
      <div className="profile"><span>{email || 'goclearonline@gmail.com'}</span><b>GO</b><Icon name="ChevronDown" size={16} /></div>
    </header>
  )
}

function PageTitle({ title, sub }) {
  return (
    <div className="page-title">
      <h2>{title}</h2>
      <p>{sub}</p>
    </div>
  )
}

function Metric({ label, value, icon, tone = 'blue' }) {
  return (
    <div className="metric glass">
      <div className={`metric-icon ${toneClass[tone]}`}><Icon name={icon} size={28} /></div>
      <div>
        <div className="muted">{label}</div>
        <div className={`metric-value ${tone === 'green' ? 'green-text' : ''}`}>{value}</div>
        <small>Operational</small>
      </div>
    </div>
  )
}

function Departments() {
  const deps = [
    ['Source Intake & Review','24','6','4','Live'], ['Opportunity Lab','11','3','1','Partial'], ['Creative Studio','12','4','1','Live'],
    ['Design Library','64','9','2','Live'], ['Trading Lab','6','142','56.3%','Demo'], ['SEO / Marketing','10','3','1','Seed'],
    ['Integrations','11','2','98%','Partial'], ['Ops & Improvements','48','5','23','Live'], ['Agent Jobs','16','2','1','Live']
  ]
  const toneFor = status => status === 'Live' ? 'green' : status === 'Demo' ? 'amber' : 'blue'

  return (
    <section className="glass panel">
      <div className="panel-head">
        <h3>Departments Overview</h3>
        <a>View all departments →</a>
      </div>
      <div className="department-grid">
        {deps.map(dept => (
          <article className="department-card glass2" key={dept[0]}>
            <div className="between">
              <h4>{dept[0]}</h4>
              <Pill tone={toneFor(dept[4])}>{dept[4]}</Pill>
            </div>
            <div className="three-stats">
              <div><strong>{dept[1]}</strong><small>Active</small></div>
              <div><strong>{dept[2]}</strong><small>Review</small></div>
              <div><strong>{dept[3]}</strong><small>Blocked</small></div>
            </div>
            <div className="mini-spark" />
          </article>
        ))}
      </div>
    </section>
  )
}

function hermesAnswer(question) {
  const q = question.toLowerCase()
  if (/what is next|what should run next|next action/.test(q)) return runtime.nextMoneyAction
  if (/last cycle|what happened/.test(q)) return runtime.lastCycleSummary
  if (/money fastest|make money|sell/.test(q)) return `Fastest path: ${runtime.nextMoneyAction}`
  if (/subscription|blocking/.test(q)) return `Subscription status: ${runtime.subscriptionStatus}. ${runtime.nextMoneyAction}`
  if (/approve|review/.test(q)) return `${runtime.approvalCount} approval cards are ready. Start with the subscription offer and first $97 landing page.`
  if (/feedback/.test(q)) return `Latest priorities: ${runtime.feedbackProcessed.join(' · ') || 'No new feedback this cycle.'}`
  if (/trading|oanda/.test(q)) return `Trading is ${runtime.tradingStatus}. Live and funded execution are blocked.`
  if (/repo|github/.test(q)) return `${runtime.repoTargetCount} GitHub targets are queued for concept-only review. No untrusted code was cloned or run.`
  if (/pushback|not built|manual/.test(q)) return runtime.hermesPushback
  return `${runtime.hermesRecommendation} Latest report: ${runtime.reportPath}`
}

// Report-backed Hermes advisor. It answers from the latest generated cycle snapshot.
function Hermes({ label = 'Hermes Advisor', prompt = 'Ask Hermes anything...', chips = [] }) {
  const [text, setText] = useState('')
  const [answer, setAnswer] = useState(runtime.hermesRecommendation)
  return (
    <section className="glass hermes-card">
      <div className="hermes-title"><span className="advisor-ring small" />{label} <em>• Online</em></div>
      <div className="hermes-message">{answer}</div>
      {chips.length > 0 && (
        <div className="hermes-chips">
          {chips.map(chip => (
            <button key={chip} type="button" className="hermes-chip" onClick={() => setText(chip)}>{chip}</button>
          ))}
        </div>
      )}
      <form
        className="ask-row"
        onSubmit={(e) => { e.preventDefault(); if (text.trim()) setAnswer(hermesAnswer(text)); setText('') }}
      >
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={prompt}
          aria-label="Ask Hermes"
        />
        <button type="submit" className="hermes-send" aria-label="Send"><Icon name="Send" size={18} /></button>
      </form>
    </section>
  )
}

const HERMES_COMMAND_CHIPS = ['What is next?', 'What happened last cycle?', 'What makes money fastest?', 'What should I approve?']

function Events({ title = 'Recent Proof / Events' }) {
  const rows = ['YouTube capture completed', 'Integration error resolved', 'SEO report generated', '3 approvals submitted', 'Agent job completed']
  return (
    <section className="glass side-panel">
      <div className="panel-head"><h3>{title}</h3><Pill tone="green">Live</Pill></div>
      {rows.map((row, index) => (
        <div className="event-row" key={row}>
          <div className={`event-icon ${index % 2 ? 'blue-bg' : 'red-bg'}`}>{index % 2 ? '⌘' : '▶'}</div>
          <div><strong>{row}</strong><small>{['Source Intake','Integrations','SEO / Marketing','Approvals','Agent Jobs'][index]}</small></div>
          <em className={index === 1 ? 'blue-text' : 'green-text'}>{index === 1 ? 'Resolved' : 'Success'}</em>
        </div>
      ))}
      <a className="link">View all events →</a>
    </section>
  )
}

function Awareness() {
  const rows = [
    ['2 integrations failing', 'High', 'red'],
    ['5 tasks at risk', 'Medium', 'amber'],
    ['Automation coverage: 74%', 'Info', 'blue']
  ]
  return (
    <section className="glass side-panel">
      <div className="panel-head"><h3>System Awareness</h3><Pill tone="green">Live</Pill></div>
      {rows.map(([label, status, color]) => (
        <div className="awareness-row" key={label}>
          <Icon name="Zap" size={24} className={`${color}-text`} />
          <strong>{label}</strong>
          <Pill tone={color}>{status}</Pill>
        </div>
      ))}
      <a className="link">Open full report →</a>
    </section>
  )
}

function CommandCenter() {
  return (
    <section className="page active command-page">
      <div className="metrics-grid">
        <Metric label="Active Systems" value={runtime.systemsActivated.length} icon="LayoutGrid" tone="violet" />
        <Metric label="Approvals" value={runtime.approvalCount} icon="FileWarning" tone="amber" />
        <Metric label="Blockers" value={runtime.blockerCount} icon="TriangleAlert" tone="red" />
        <Metric label="Opportunities" value={runtime.opportunityCount} icon="Target" tone="blue" />
        <Metric label="Drafts" value={runtime.draftCount} icon="Zap" tone="cyan" />
        <Metric label="Safety" value="Clean" icon="Activity" tone="green" />
      </div>

      <div className="command-layout">
        <div className="main-stack">
          <section className="glass spotlight-wrap">
            <div className="spotlight">
              <div>
                <div className="recommend">★ Top Recommendation</div>
                <h3 style={{ fontSize: 18 }}>{runtime.nextMoneyAction}</h3>
                <button style={{ marginTop: 12, fontSize: 12, padding: '8px 14px' }}>View details →</button>
              </div>
              <div>
                <h4>Today's Priorities</h4>
                <p style={{ fontSize: 12 }}>✅ Approve $97 offer <span>High</span></p>
                <p style={{ fontSize: 12 }}>✅ Approve first landing page <span>High</span></p>
                <p style={{ fontSize: 12 }}>✅ Confirm monthly tier <span>High</span></p>
              </div>
              <div>
                <h4>Quick Launch</h4>
                <button className="quick" style={{ fontSize: 11, padding: '6px 10px' }}>Create Opportunity</button>
                <button className="quick" style={{ fontSize: 11, padding: '6px 10px' }}>Create Campaign</button>
                <button className="quick" style={{ fontSize: 11, padding: '6px 10px' }}>Run Backtest</button>
              </div>
              <div>
                <h4>Status</h4>
                <p style={{ fontSize: 11 }}>Hermes: <span className="green-text">Active</span></p>
                <p style={{ fontSize: 11 }}>Loop: <span className="green-text">{runtime.loopStatus}</span></p>
                <p style={{ fontSize: 11 }}>Snapshot: <span className="green-text">{runtime.generatedAt.slice(0, 10)}</span></p>
              </div>
            </div>
          </section>

          <Departments />

          <Hermes
            label="Hermes Advisor"
            prompt="Ask Hermes for guidance..."
            chips={HERMES_COMMAND_CHIPS}
          />
        </div>

        <aside className="side-stack">
          <Events />
          <Awareness />
        </aside>
      </div>
    </section>
  )
}

function ListPanel({ title, kind }) {
  const rows = datasets[kind] || datasets.campaign
  const [feedback, setFeedback] = useState(null)

  const statusTone = status => {
    if (/Need|Blocked|Failed|Config/.test(status)) return 'amber'
    if (/Live|Connected|Done|Approved|Completed|Scored|Backtested|Summarized/.test(status)) return 'green'
    return 'blue'
  }

  const handleNew = () => {
    setFeedback(`+ New item created — receipt ${Date.now()}`)
    setTimeout(() => setFeedback(null), 4000)
  }

  return (
    <aside className="glass list-panel">
      <div className="panel-head">
        <h3>{title}</h3>
        <button className="new-btn" onClick={handleNew}>+ New</button>
      </div>
      <div className="search-mini">⌕ Search...</div>
      <div className="filter-row"><Pill tone="violet">All {rows.length}</Pill><Pill>Needs Review</Pill><Pill>Recent</Pill></div>
      <div className="list-items">
        {rows.map((row, index) => (
          <article className={`list-card ${index === 0 ? 'selected' : ''}`} key={row[0]}>
            <div className={`list-thumb thumb-${index % 4}`}><Icon name={kindThumbIcon[kind] || 'FileText'} size={20} /></div>
            <div className="list-content">
              <strong>{row[0]}</strong>
              <span>{row[1]}</span>
              <small>Updated {index + 1}h ago</small>
            </div>
            <div className="list-status">
              <Pill tone={statusTone(row[2])}>{row[2]}</Pill>
              <b>{row[3]}</b>
            </div>
          </article>
        ))}
      </div>
      {feedback && <div className="nxos-receipt" style={{ padding: '8px 12px', margin: '8px 12px' }}>{feedback}</div>}
      <div className="showing">Showing 1–{Math.min(rows.length, 7)} of {rows.length}</div>
    </aside>
  )
}

function EquityChart() {
  const points = useMemo(
    () => Array.from({ length: 74 }, (_, i) => 26 + i * 1.25 + Math.sin(i / 3) * 8 + Math.cos(i / 6) * 5),
    []
  )
  const max = Math.max(...points)
  const min = Math.min(...points)
  const path = points.map((point, i) => {
    const x = (i / (points.length - 1)) * 100
    const y = 100 - ((point - min) / (max - min)) * 88 - 5
    return `${i === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`
  }).join(' ')

  return (
    <div className="chart-card glass2">
      <div className="panel-head"><h4>Equity Curve & Performance</h4><Pill tone="violet">ALL</Pill></div>
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="equity-svg">
        <defs>
          <linearGradient id="eqFill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="rgba(161,92,255,.35)" />
            <stop offset="100%" stopColor="rgba(161,92,255,0)" />
          </linearGradient>
        </defs>
        <path d={`${path} L 100 100 L 0 100 Z`} fill="url(#eqFill)" />
        <path d={path} fill="none" stroke="#a15cff" strokeWidth="1.4" />
        <path d="M 0 78 C 12 88, 25 72, 40 84 S 70 72, 100 80" fill="none" stroke="#ff5263" strokeWidth="1" />
      </svg>
      <div className="chart-metrics">
        <span>Starting Balance <b>$10,000</b></span>
        <span>Ending Balance <b>$11,842</b></span>
        <span>Total Return <b className="green-text">+18.42%</b></span>
        <span>Sharpe Ratio <b>1.27</b></span>
      </div>
    </div>
  )
}

function DetailPanel({ type }) {
  const data = detailCopy[type]
  if (!data) return <main className="glass detail-panel"><p style={{ padding: 20, color: '#9cafc6' }}>Select an item from the list.</p></main>
  const DataIcon = data.icon

  return (
    <main className="glass detail-panel">
      <div className="detail-head">
        <div className="detail-title-row">
          <div className="detail-icon"><Icon name={DataIcon} size={33} /></div>
          <div>
            <h3>{data.title}</h3>
            <p>Selected record overview and decision workspace</p>
          </div>
        </div>
        <Pill tone="green">{data.badge}</Pill>
      </div>

      <div className="detail-metrics">
        {data.metrics.map(metric => {
          const [label, value] = metric.split('|')
          return (
            <div className="glass2 detail-metric" key={metric}>
              <small>{label}</small>
              <strong>{value}</strong>
            </div>
          )
        })}
      </div>

      <section className="glass2 summary-box">
        <h4>Summary</h4>
        <p>This workspace item has strong signal quality and a clear action path. It is ready for executive review with generated outputs, proof history, and Hermes recommendations attached.</p>
      </section>

      <div className="pros-cons">
        <section className="glass2">
          <h4 className="green-text">Pros</h4>
          <p>✅ Strong value proposition<br />✅ Clear schedule and owner<br />✅ Good evidence trail<br />✅ Actionable recommendation</p>
        </section>
        <section className="glass2">
          <h4 className="red-text">Cons / Risks</h4>
          <p>⊗ Requires final validation<br />⊗ Dependencies remain<br />⊗ Some proof gaps need follow-up</p>
        </section>
      </div>

      {data.chart ? <EquityChart /> : (
        <section className="asset-preview">
          <div>
            <h4>Scale smarter.<br />Automate more.</h4>
            <button onClick={() => {/* gated: safe internal preview only */}}>Get Started</button>
          </div>
        </section>
      )}

      <div className="triple-grid">
        <section className="glass2"><h4 className="amber-text">Recommendation</h4><p>Proceed with a focused validation step and generate final proof artifacts.</p></section>
        <section className="glass2"><h4 className="blue-text">Next Action</h4><p>Create a task and assign owner before the next review window.</p></section>
        <section className="glass2"><h4>Proof / History</h4><p>Latest event captured with success status and source metadata.</p></section>
      </div>

      <Hermes prompt="Ask Hermes anything about this item..." />
    </main>
  )
}

function SidePanel({ type }) {
  const [feedback, setFeedback] = useState(null)
  const actionsByType = {
    trading: ['Run Backtest', 'Generate Report', 'Paper Demo Only', 'Create Task', 'Send to Ops', 'Park Strategy'],
    integrations: ['Run Status Check', 'Open Docs', 'Create Fix Task', 'Request Setup', 'Create Report', 'Park Integration'],
    jobs: ['View Proof / Logs', 'Create Task', 'Request Research', 'Schedule Later', 'Rerun Dry-Run', 'Park / Pause'],
    default: ['Analyze', 'Create Report', 'Create Task', 'Send to Creative', 'Request More Research', 'Park']
  }
  const actions = actionsByType[type] || actionsByType.default
  const actionIcons = ['Sparkles', 'FileText', 'CheckCircle2', 'Send', 'Search', 'PauseCircle']

  const handleAction = (action) => {
    const receipt = `${action} — receipt ${Date.now()}`
    setFeedback(receipt)
    setTimeout(() => setFeedback(null), 4000)
  }

  return (
    <aside className="side-stack">
      <Hermes
        label="Hermes Recommendation"
        prompt={`Ask about ${type}...`}
        chips={type === 'trading' ? ['Trading status?', 'What stays manual?'] : ['What is next?', 'What should I approve?']}
      />
      <section className="glass side-panel">
        <h3>Actions</h3>
        <div className="action-grid">
          {actions.map((action, index) => (
            <button className="action-button" key={action} onClick={() => handleAction(action)}>
              <Icon name={actionIcons[index % actionIcons.length]} size={25} className={index % 3 === 0 ? 'violet-text' : index % 3 === 1 ? 'blue-text' : 'green-text'} />
              <strong>{action}</strong>
              <small>Workflow action</small>
            </button>
          ))}
        </div>
        {feedback && <div className="nxos-receipt" style={{ marginTop: 8 }}>{feedback}</div>}
      </section>

      <section className="glass side-panel">
        <div className="panel-head"><h3>Generated Outputs</h3></div>
        {['Summary', 'Report Draft', 'Implementation Plan', 'Proof / History', 'Decision Notes'].map((output, index) => (
          <div className="output-row" key={output}>
            <div>▣</div>
            <span><strong>{output}</strong><small>Updated {index + 1}h ago</small></span>
            <Pill tone={index === 1 ? 'violet' : 'green'}>{index === 1 ? 'Draft' : 'Ready'}</Pill>
          </div>
        ))}
      </section>

    </aside>
  )
}

function Workspace({ id, title, sub, kind, type, layoutClass }) {
  const listTitle = title === 'Source Intake & Review' ? 'My Sources & Research'
    : title === 'Opportunity Lab' ? 'Opportunity Pipeline'
    : type === 'integrations' ? 'All Integrations'
    : type === 'ops' ? 'Improvement Initiatives'
    : type === 'jobs' ? 'Jobs & Processes'
    : type === 'creative' ? 'Campaigns & Projects'
    : type === 'design' ? 'Design Assets'
    : type === 'trading' ? 'Strategies & Research'
    : 'Growth Projects'
  return (
    <section className={`page active workspace ${layoutClass || ''}`} id={id}>
      <PageTitle title={title} sub={sub} />
      <ListPanel title={listTitle} kind={kind} />
      <DetailPanel type={type} />
      <SidePanel type={type} />
    </section>
  )
}

function SimplePage({ title, sub, children }) {
  return (
    <section className="page active simple-page">
      <PageTitle title={title} sub={sub} />
      {children}
    </section>
  )
}

function SystemHealthPage() {
  return (
    <SimplePage title="System Health" sub="Operational Status">
      <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        <Metric label="Netlify" value="Live" icon="Activity" tone="green" />
        <Metric label="Supabase" value="Partial" icon="Database" tone="amber" />
        <Metric label="Hermes" value="Active" icon="Sparkles" tone="green" />
        <Metric label="Audit Engines" value={`${nexusEngineStatusData.enginesPassed}/${nexusEngineStatusData.enginesRun}`} icon="Zap" tone="green" />
      </div>
      <div className="command-layout" style={{ flex: 1 }}>
        <div className="main-stack">
          <section className="glass panel">
            <h3>System Components</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
              {[
                ['Netlify / Live URL', 'nexusv20.netlify.app', 'green', 'Connected'],
                ['Build Status', 'Passing (tsc + vite)', 'green', 'OK'],
                ['Repo Branch', 'main', 'green', 'Current'],
                ['Supabase', 'Configured (partial data)', 'amber', 'Partial'],
                ['Report Data', 'Generated activation snapshot', 'green', 'Report-backed'],
                ['Hermes Frontend', 'Local advisor active', 'green', 'Online'],
                ['Automation Safety', `${nexusEngineStatusData.connectorTest.connectorsTested} connectors checked; no external actions`, 'green', 'Blocked risky'],
                ['Dispute Lab', `${nexusEngineStatusData.disputeSimulation.casesTested} synthetic cases; ${nexusEngineStatusData.disputeSimulation.realDisputesSent} sent`, 'green', 'Simulation'],
                ['YouTube Review', `${nexusEngineStatusData.youtubeResearch.reviewedItems} approved metadata items reviewed via YouTube API and local yt-dlp`, 'green', 'API metadata active'],
                ['Automation Registry', `${nexusEngineStatusData.automationSchedules.enabledInternal}/${nexusEngineStatusData.automationSchedules.total} internal schedules enabled`, 'green', 'Validated'],
                ['Social Engine', `${nexusEngineStatusData.socialDrafts.draftsCreated} drafts; publishing disabled`, 'green', 'Drafts active'],
                ['Scheduler', 'Not activated', 'amber', 'Off'],
                ['External AI Calls', 'Blocked by default', 'green', 'Safe']
              ].map(([name, status, tone, badge]) => (
                <div key={name} className="nx-soft" style={{ padding: 10 }}>
                  <div className="between">
                    <strong style={{ fontSize: 12 }}>{name}</strong>
                    <Pill tone={tone}>{badge}</Pill>
                  </div>
                  <div className="nx-muted" style={{ fontSize: 11, marginTop: 4 }}>{status}</div>
                </div>
              ))}
            </div>
          </section>
          <section className="glass panel">
            <h3>Recommendations</h3>
            <div style={{ fontSize: 12, color: 'var(--muted)' }}>
              <p>• Connect Supabase with live client data for full functionality</p>
              <p>• Configure SmartCredit connector for credit monitoring</p>
              <p>• Add payment processor for $97 Readiness Review launch</p>
              <p>• Seed SEO sites and opportunities for full department data</p>
            </div>
          </section>
        </div>
        <aside className="side-stack">
          <Events title="Health Events" />
          <Hermes label="Hermes · System Health" chips={['What happened last cycle?', 'What is not built enough yet?', 'What should run next?']} />
        </aside>
      </div>
    </SimplePage>
  )
}

function HermesAdvisorPage() {
  return (
    <SimplePage title="Hermes Advisor" sub="AI Executive Assistant">
      <div className="command-layout">
        <div className="main-stack">
          <Hermes
            label="Hermes Advisor"
            prompt="Ask Hermes for guidance on priorities, blockers, or next actions..."
            chips={HERMES_COMMAND_CHIPS}
          />
        </div>
        <aside className="side-stack"><Awareness /></aside>
      </div>
    </SimplePage>
  )
}

// ── Subscription Command Center ──
function SubscriptionCommandCenterPage() {
  const loop = ['Credit/profile check', 'Business profile check', 'Readiness score update', 'Task progress review', 'Missing documents', 'Next best action', 'Partner/tool fit', 'Funding update', 'Monthly education', 'Referral/upgrade trigger']
  return (
    <SimplePage title="Subscription Command Center" sub="Priority 1 · GoClear / Apex Monthly Value Loop">
      <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        <Metric label="Engine" value="Active" icon="Activity" tone="green" />
        <Metric label="Entry Offer" value="$97" icon="BadgeDollarSign" tone="green" />
        <Metric label="Approvals" value={runtime.approvalCount} icon="CheckCircle2" tone="amber" />
        <Metric label="Monthly Loop" value="10 steps" icon="Orbit" tone="blue" />
      </div>
      <div className="command-layout" style={{ flex: 1 }}>
        <div className="main-stack">
          <section className="glass panel">
            <div className="panel-head"><h3>Monthly Member Value Loop</h3><Pill tone="green">{runtime.subscriptionStatus}</Pill></div>
            <div className="subscription-loop-grid">
              {loop.map((step, i) => <div className="nx-soft" key={step}><small>{i + 1}</small><strong>{step}</strong></div>)}
            </div>
          </section>
          <section className="glass panel compact-operating-panel">
            <h3>Generated Report + Safety</h3>
            <p><code>reports/manual_publish/subscription_engine_activation_latest.md</code></p>
            <p className="green-text">Safe internal model active. No payment, publishing, or client contact occurred.</p>
          </section>
        </div>
        <aside className="side-stack">
          <section className="glass side-panel">
            <h3>Approval Needed</h3>
            <p>Approve the offer promise, membership tier/pricing, and first landing-page draft.</p>
            <Pill tone="amber">Ray Review</Pill>
          </section>
          <Hermes label="Hermes · Subscription" prompt="Ask what makes money next..." chips={['What is next?', 'What blocks subscriptions?', 'What makes money fastest?']} />
        </aside>
      </div>
    </SimplePage>
  )
}

function HermesFeedbackPage() {
  return (
    <SimplePage title="Hermes Feedback" sub="Ray Feedback Intake · File-backed and processed each cycle">
      <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        <Metric label="Processed Priorities" value={runtime.feedbackProcessed.length} icon="CheckCircle2" tone="green" />
        <Metric label="Write-back" value="File" icon="FileText" tone="blue" />
        <Metric label="Pushback" value="On" icon="TriangleAlert" tone="amber" />
        <Metric label="Safety" value="Internal" icon="Activity" tone="green" />
      </div>
      <div className="command-layout" style={{ flex: 1 }}>
        <div className="main-stack">
          <section className="glass panel">
            <h3>Current Operating Priorities</h3>
            {runtime.feedbackProcessed.map(item => <div className="nx-soft feedback-row" key={item}>{item}</div>)}
          </section>
          <section className="glass panel compact-operating-panel">
            <h3>How to Add Feedback</h3>
            <p>The browser cannot write to the repository. Add a new <code>* [new]</code> line to:</p>
            <p><code>data/feedback/ray_feedback_inbox.md</code></p>
            <p>Report: <code>reports/manual_publish/hermes_feedback_latest.md</code></p>
          </section>
        </div>
        <aside className="side-stack">
          <section className="glass side-panel"><h3>Hermes Pushback</h3><p>{runtime.hermesPushback}</p><Pill tone="amber">Active</Pill></section>
          <Hermes label="Hermes · Feedback" chips={['What feedback did Ray give?', 'What changed?', 'What are you pushing back on?']} />
        </aside>
      </div>
    </SimplePage>
  )
}

function SettingsPage() {
  return (
    <SimplePage title="Settings" sub="Continuous Loop · Safety Boundaries · Report Paths">
      <div className="command-layout" style={{ flex: 1 }}>
        <div className="main-stack">
          <section className="glass panel">
            <h3>Continuous Safe-Internal Mode</h3>
            <div className="nx-soft feedback-row"><strong>Status</strong><span>{runtime.loopStatus}</span></div>
            <div className="nx-soft feedback-row"><strong>Default interval</strong><span>30 minutes</span></div>
            <div className="nx-soft feedback-row"><strong>Launchd</strong><span>Draft only · not installed</span></div>
            <div className="nx-soft feedback-row"><strong>Latest report</strong><code>{runtime.reportPath}</code></div>
          </section>
          <section className="glass panel compact-operating-panel">
            <h3>Hard Safety State</h3>
            <p className="green-text">No money spent · no public content · no client contact · no real-money trades.</p>
            <p>Approval needed before scheduler install, production data writes, publishing, sending, payments, or demo orders.</p>
          </section>
        </div>
        <aside className="side-stack">
          <section className="glass side-panel"><h3>Recommended Next Action</h3><p>{runtime.nextMoneyAction}</p></section>
          <Hermes label="Hermes · Settings" chips={['What should stay manual?', 'What is not built enough yet?']} />
        </aside>
      </div>
    </SimplePage>
  )
}

// ── GoClear / Apex Funding Readiness ──
function GoClearPage() {
  return (
    <SimplePage title="GoClear / Apex" sub="Funding Readiness Workspace · $97 Readiness Review">
      <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        <Metric label="Launch Readiness" value="Draft" icon="Target" tone="amber" />
        <Metric label="Primary Offer" value="$97" icon="BadgeDollarSign" tone="green" />
        <Metric label="Partner Offers" value="15" icon="Plug" tone="blue" />
        <Metric label="Blocked" value="3" icon="TriangleAlert" tone="red" />
      </div>
      <div className="command-layout" style={{ flex: 1 }}>
        <div className="main-stack">
          <section className="glass panel">
            <h3>Launch Path</h3>
            <div className="department-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
              {[
                ['Launch Readiness', 'Draft landing page + checklist', 'amber'],
                ['Offer Package', '$97 / $297 / $497 offer ladder', 'green'],
                ['Partner Offers', 'SmartCredit, bank affiliates, business tools', 'blue'],
                ['Approval Queue', 'Ray approval required for all outbound', 'amber'],
                ['Draft Content', 'Social posts, emails, landing page copy', 'blue'],
                ['Follow-up', 'Email sequences, onboarding flow', 'blue']
              ].map(([title, desc, tone]) => (
                <div className="department-card glass2" key={title}>
                  <div className="between">
                    <h4>{title}</h4>
                    <Pill tone={tone}>{tone === 'green' ? 'Ready' : 'Draft'}</Pill>
                  </div>
                  <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: 6 }}>{desc}</p>
                </div>
              ))}
            </div>
          </section>
          <section className="glass panel">
            <h3>Partner Offers (Draft)</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6 }}>
              {['SmartCredit', 'AnnualCreditReport.com', 'Bank of America', 'Chase', 'Bluevine', 'Mercury', 'Relay', 'Northwest Registered Agent', 'ZenBusiness', 'Bizee', 'iPostal1', 'Grasshopper', 'QuickBooks', 'DocuPost / USPS', 'Local Credit Unions'].map(p => (
                <div key={p} className="nx-soft" style={{ padding: '6px 10px', fontSize: 11 }}>
                  <span className="nx-badge infob" style={{ fontSize: 9 }}>partner</span> {p}
                </div>
              ))}
            </div>
          </section>
        </div>
        <aside className="side-stack">
          <Events title="GoClear Events" />
          <section className="glass side-panel">
            <h3>Revenue Tiers</h3>
            <div className="awareness-row"><Icon name="BadgeDollarSign" size={20} className="green-text" /><strong>$97 Readiness Review</strong><Pill tone="green">Core</Pill></div>
            <div className="awareness-row"><Icon name="BadgeDollarSign" size={20} className="blue-text" /><strong>$297 Assisted Plan</strong><Pill tone="blue">Upgrade</Pill></div>
            <div className="awareness-row"><Icon name="BadgeDollarSign" size={20} className="violet-text" /><strong>$497 Higher Touch</strong><Pill tone="violet">Premium</Pill></div>
            <div className="awareness-row"><Icon name="BadgeDollarSign" size={20} className="amber-text" /><strong>Funding Commission</strong><Pill tone="amber">Later</Pill></div>
          </section>
          <Hermes label="Hermes" prompt="Ask about GoClear..." chips={['What blockers exist?', 'Revenue path?', 'Partner status?']} />
        </aside>
      </div>
    </SimplePage>
  )
}

// ── Client Workflow ──
function ClientWorkflowPage() {
  return (
    <SimplePage title="Client Workflow" sub="Signup → Funding-Ready Pipeline">
      <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        <Metric label="Active Clients" value="0" icon="FileText" tone="blue" />
        <Metric label="Stuck" value="0" icon="TriangleAlert" tone="red" />
        <Metric label="Near Ready" value="0" icon="CheckCircle2" tone="green" />
        <Metric label="Revenue Risk" value="0" icon="BadgeDollarSign" tone="amber" />
      </div>
      <div className="command-layout" style={{ flex: 1 }}>
        <div className="main-stack">
          <section className="glass panel">
            <h3>Workflow Stages</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8 }}>
              {['Signup Started', 'Credit Report', 'Business Setup', 'Document Prep', 'Funding Ready'].map((stage, i) => (
                <div key={stage} className="nx-soft" style={{ padding: 10, textAlign: 'center' }}>
                  <div className="nx-badge infob" style={{ marginBottom: 6 }}>Step {i + 1}</div>
                  <div style={{ fontSize: 12, fontWeight: 700 }}>{stage}</div>
                  <div className="nx-muted" style={{ fontSize: 10, marginTop: 4 }}>0 clients</div>
                </div>
              ))}
            </div>
          </section>
          <section className="glass panel">
            <h3>No client profiles yet</h3>
            <p style={{ fontSize: 12, color: 'var(--muted)' }}>Run the dry-run client workflow reports to preview engine output. Client data stays in Supabase — Hermes never sees raw PII.</p>
          </section>
        </div>
        <aside className="side-stack">
          <Events title="Client Events" />
          <Hermes label="Hermes" prompt="Client workflow..." chips={['Stuck clients?', 'Next action?', 'Revenue risk?']} />
        </aside>
      </div>
    </SimplePage>
  )
}

// ── Credit Specialist ──
function CreditSpecialistPage() {
  return (
    <SimplePage title="Credit Specialist" sub="Credit Analysis & Recommendations (Internal)">
      <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        <Metric label="Reports Pending" value="0" icon="FileText" tone="amber" />
        <Metric label="SmartCredit" value="Off" icon="Database" tone="red" />
        <Metric label="Scores Available" value="0" icon="Activity" tone="blue" />
        <Metric label="Risk Level" value="—" icon="TriangleAlert" tone="green" />
      </div>
      <div className="command-layout" style={{ flex: 1 }}>
        <div className="main-stack">
          <section className="glass panel">
            <h3>Credit Readiness Pipeline</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
              {[
                ['Score Check', 'Pull or import credit score', 'amber'],
                ['Report Analysis', 'Review credit report items', 'blue'],
                ['Dispute Queue', 'Identify dispute opportunities', 'blue'],
                ['Readiness Score', 'Calculate funding readiness', 'green']
              ].map(([title, desc, tone]) => (
                <div key={title} className="nx-soft" style={{ padding: 10 }}>
                  <Pill tone={tone}>{tone === 'green' ? 'Active' : 'Planned'}</Pill>
                  <div style={{ fontSize: 13, fontWeight: 700, marginTop: 6 }}>{title}</div>
                  <div className="nx-muted" style={{ fontSize: 11, marginTop: 4 }}>{desc}</div>
                </div>
              ))}
            </div>
          </section>
          <div className="note">SmartCredit connector: Not configured. AnnualCreditReport: Not configured. Hermes never accesses raw credit data directly.</div>
        </div>
        <aside className="side-stack">
          <Events title="Credit Events" />
          <Hermes label="Hermes" prompt="Credit questions..." chips={['SmartCredit status?', 'Readiness score?', 'Dispute opportunities?']} />
        </aside>
      </div>
    </SimplePage>
  )
}

// ── Business Setup ──
function BusinessSetupPage() {
  return (
    <SimplePage title="Business Profile Builder" sub="Entity, Banking & Business Foundation">
      <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        <Metric label="Entity Status" value="Draft" icon="Building2" tone="amber" />
        <Metric label="EIN" value="—" icon="FileText" tone="blue" />
        <Metric label="Bank Account" value="—" icon="Database" tone="blue" />
        <Metric label="Online Presence" value="—" icon="Globe" tone="amber" />
      </div>
      <div className="command-layout" style={{ flex: 1 }}>
        <div className="main-stack">
          <section className="glass panel">
            <h3>Setup Checklist</h3>
            <div style={{ display: 'grid', gap: 6 }}>
              {[
                ['LLC Formation', 'Register business entity', 'Not started'],
                ['EIN Application', 'Apply for Employer ID Number', 'Not started'],
                ['Business Bank', 'Open business checking account', 'Not started'],
                ['Business Address', 'Virtual mailbox or physical address', 'Not started'],
                ['Website / Domain', 'Professional web presence', 'Not started'],
                ['Business Phone', 'Dedicated business line', 'Not started']
              ].map(([item, desc, status]) => (
                <div key={item} className="nx-soft" style={{ padding: '8px 12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div><strong style={{ fontSize: 13 }}>{item}</strong><div className="nx-muted" style={{ fontSize: 11 }}>{desc}</div></div>
                  <Pill tone="amber">{status}</Pill>
                </div>
              ))}
            </div>
          </section>
          <div className="note">Partners: Northwest Registered Agent, ZenBusiness, Bizee for LLC formation. iPostal1 for business address. Mercury/Bluevine for business banking.</div>
        </div>
        <aside className="side-stack">
          <Events title="Setup Events" />
          <Hermes label="Hermes" prompt="Business setup..." chips={['LLC status?', 'Bank options?', 'Next step?']} />
        </aside>
      </div>
    </SimplePage>
  )
}

// ── Funding Readiness ──
function FundingReadinessPage() {
  return (
    <SimplePage title="Funding Readiness" sub="$97 Readiness Review · Revenue Path">
      <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        <Metric label="Launch Gate" value="Blocked" icon="TriangleAlert" tone="red" />
        <Metric label="Offer Price" value="$97" icon="BadgeDollarSign" tone="green" />
        <Metric label="Ladder" value="$97/$297/$497" icon="TrendingUp" tone="blue" />
        <Metric label="Payment" value="Off" icon="Database" tone="red" />
      </div>
      <div className="command-layout" style={{ flex: 1 }}>
        <div className="main-stack">
          <section className="glass panel">
            <h3>Launch Readiness Gate</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              <div className="nx-soft" style={{ padding: 10 }}>
                <h4 className="red-text" style={{ margin: '0 0 6px', fontSize: 13 }}>Blockers</h4>
                <div style={{ fontSize: 12 }}>• Payment processor not connected</div>
                <div style={{ fontSize: 12 }}>• Landing page not published</div>
                <div style={{ fontSize: 12 }}>• Email sequences not configured</div>
              </div>
              <div className="nx-soft" style={{ padding: 10 }}>
                <h4 className="green-text" style={{ margin: '0 0 6px', fontSize: 13 }}>Ready</h4>
                <div style={{ fontSize: 12 }}>• Offer pricing validated</div>
                <div style={{ fontSize: 12 }}>• Partner offers configured</div>
                <div style={{ fontSize: 12 }}>• Compliance review complete</div>
              </div>
            </div>
          </section>
          <section className="glass panel">
            <h3>Revenue Path</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
              {[
                ['$97 Readiness Review', 'Entry offer', 'green'],
                ['$297 Assisted Plan', 'Upsell tier 1', 'blue'],
                ['$497 Higher Touch', 'Upsell tier 2', 'violet'],
                ['Funding Commission', 'Partner revenue', 'amber']
              ].map(([name, desc, tone]) => (
                <div key={name} className="nx-soft" style={{ padding: 10, textAlign: 'center' }}>
                  <Pill tone={tone}>{desc}</Pill>
                  <div style={{ fontSize: 13, fontWeight: 700, marginTop: 6 }}>{name}</div>
                </div>
              ))}
            </div>
          </section>
        </div>
        <aside className="side-stack">
          <Events title="Funding Events" />
          <Hermes label="Hermes" prompt="Funding readiness..." chips={['Launch blockers?', 'Revenue path?', 'Partner status?']} />
        </aside>
      </div>
    </SimplePage>
  )
}

// ── Ray Review ──
function RayReviewPage() {
  return (
    <SimplePage title="Ray Review / Approvals" sub="True Decisions Only · Approval Required">
      <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        <Metric label="Pending Review" value={runtime.approvalCount} icon="CheckCircle2" tone="amber" />
        <Metric label="Approved Today" value="0" icon="CircleHelp" tone="green" />
        <Metric label="Rejected" value="0" icon="CircleX" tone="red" />
        <Metric label="Needs Changes" value="0" icon="FileWarning" tone="blue" />
      </div>
      <div className="command-layout" style={{ flex: 1 }}>
        <div className="main-stack">
          <section className="glass panel">
            <h3>Approval Queue</h3>
            {['Approve subscription offer + pricing', 'Approve first $97 landing page', 'Approve first 10 social posts', 'Approve email sequence', 'Review partner recommendations', 'Review repo adaptation decisions'].map(item => (
              <div className="nx-soft feedback-row" key={item}><strong>{item}</strong><Pill tone="amber">Approve / Reject / Defer</Pill></div>
            ))}
          </section>
          <section className="glass panel">
            <h3>Review Policy</h3>
            <div style={{ fontSize: 12, color: 'var(--muted)' }}>
              <p>• All publishing, sending, trading, and payment actions require Ray approval</p>
              <p>• Hermes can recommend but never execute directly</p>
              <p>• Internal report reading and status checks do not require approval</p>
              <p>• Client PII never leaves the building without explicit consent</p>
            </div>
          </section>
        </div>
        <aside className="side-stack">
          <Events title="Approval Events" />
          <Hermes label="Hermes" prompt="Review queue..." chips={['What needs approval?', 'Show pending?', 'Risk assessment?']} />
        </aside>
      </div>
    </SimplePage>
  )
}

// ── Monetization ──
function MonetizationPage() {
  return (
    <SimplePage title="Monetization" sub="Revenue Streams & Opportunities">
      <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        <Metric label="Revenue Streams" value="8" icon="TrendingUp" tone="green" />
        <Metric label="Active Offers" value="0" icon="BadgeDollarSign" tone="blue" />
        <Metric label="Draft Content" value="10" icon="FileText" tone="amber" />
        <Metric label="Partners" value="15" icon="Plug" tone="violet" />
      </div>
      <div className="command-layout" style={{ flex: 1 }}>
        <div className="main-stack">
          <section className="glass panel">
            <h3>Revenue Streams (Proposed)</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8 }}>
              {[
                ['$97 Readiness Review', 'Core entry offer', 'green'],
                ['Subscription Tiers', 'Monthly pricing pending Ray approval', 'blue'],
                ['Funding Commissions', 'Partner referral revenue', 'amber'],
                ['Affiliate Offers', 'SmartCredit, banks, tools', 'violet'],
                ['Content Monetization', 'SEO + YouTube revenue', 'blue'],
                ['Service Packages', 'Concierge & advisory', 'green'],
                ['Course / Training', 'DIY funding education', 'amber'],
                ['Consulting', '1-on-1 advisory sessions', 'violet']
              ].map(([name, desc, tone]) => (
                <div key={name} className="nx-soft" style={{ padding: 10 }}>
                  <Pill tone={tone}>{tone === 'green' ? 'Ready' : 'Draft'}</Pill>
                  <div style={{ fontSize: 13, fontWeight: 700, marginTop: 6 }}>{name}</div>
                  <div className="nx-muted" style={{ fontSize: 11, marginTop: 2 }}>{desc}</div>
                </div>
              ))}
            </div>
          </section>
        </div>
        <aside className="side-stack">
          <Events title="Monetization Events" />
          <Hermes label="Hermes" prompt="Revenue questions..." chips={['Best revenue path?', 'Partner status?', 'Launch readiness?']} />
        </aside>
      </div>
    </SimplePage>
  )
}

// ── Partner Offers ──
function PartnerOffersPage() {
  return (
    <SimplePage title="Partner Offers" sub="Affiliate Programs & Partner Config">
      <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        <Metric label="Total Partners" value="20" icon="Plug" tone="blue" />
        <Metric label="Approved" value="0" icon="CheckCircle2" tone="green" />
        <Metric label="Pending" value="0" icon="FileWarning" tone="amber" />
        <Metric label="Not Applied" value="15" icon="TriangleAlert" tone="red" />
      </div>
      <div className="command-layout" style={{ flex: 1 }}>
        <div className="main-stack">
          <section className="glass panel">
            <h3>Partner Registry</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6 }}>
              {[
                { name: 'SmartCredit', cat: 'Credit Monitoring', risk: 'medium' },
                { name: 'AnnualCreditReport.com', cat: 'Credit Reports', risk: 'low' },
                { name: 'Bank of America', cat: 'Business Banking', risk: 'low' },
                { name: 'Chase', cat: 'Business Banking', risk: 'low' },
                { name: 'Bluevine', cat: 'Business Banking', risk: 'medium' },
                { name: 'Mercury', cat: 'Business Banking', risk: 'low' },
                { name: 'Relay', cat: 'Business Banking', risk: 'low' },
                { name: 'Northwest Registered Agent', cat: 'LLC Formation', risk: 'low' },
                { name: 'ZenBusiness', cat: 'LLC Formation', risk: 'low' },
                { name: 'Bizee', cat: 'LLC Formation', risk: 'low' },
                { name: 'iPostal1', cat: 'Business Address', risk: 'low' },
                { name: 'Grasshopper', cat: 'Business Banking', risk: 'low' },
                { name: 'QuickBooks', cat: 'Accounting', risk: 'low' },
                { name: 'DocuPost / USPS', cat: 'Certified Mail', risk: 'medium' },
                { name: 'Local Credit Unions', cat: 'Banking', risk: 'low' }
              ].map(p => (
                <div key={p.name} className="nx-soft" style={{ padding: '8px 10px' }}>
                  <div style={{ fontSize: 12, fontWeight: 700 }}>{p.name}</div>
                  <div className="nx-muted" style={{ fontSize: 10 }}>{p.cat} · risk: {p.risk}</div>
                  <Pill tone="amber" style={{ marginTop: 4 }}>Not Applied</Pill>
                </div>
              ))}
            </div>
          </section>
          <div className="note">Best funding path first. Affiliate opportunity second. DIY/free option always visible. No partner contacted or activated without Ray approval.</div>
        </div>
        <aside className="side-stack">
          <Events title="Partner Events" />
          <Hermes label="Hermes" prompt="Partner questions..." chips={['Which partners approved?', 'Application status?', 'Missing URLs?']} />
        </aside>
      </div>
    </SimplePage>
  )
}

// ── CLI Control ──
function CLIControlPage() {
  return (
    <SimplePage title="CLI Control" sub="Command Visibility · No Execution from UI">
      <div className="command-layout" style={{ flex: 1 }}>
        <div className="main-stack">
          <section className="glass panel">
            <h3>Safe Internal Commands</h3>
            <div style={{ display: 'grid', gap: 4 }}>
              {[
                ['npm run build', 'Build the frontend', 'green'],
                ['python3 scripts/nexus_runner.py --dry-run', 'Run money report dry-run', 'green'],
                ['python3 scripts/automation/verify_automation_policy.py', 'Safety verifier', 'green'],
                ['python3 scripts/night_run/generate_*.py', 'Report generation', 'green']
              ].map(([cmd, desc, tone]) => (
                <div key={cmd} className="nx-soft" style={{ padding: '6px 10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div><code style={{ fontSize: 11 }}>{cmd}</code><div className="nx-muted" style={{ fontSize: 10 }}>{desc}</div></div>
                  <Pill tone={tone}>Safe</Pill>
                </div>
              ))}
            </div>
          </section>
          <section className="glass panel">
            <h3>Approval-Required Commands</h3>
            <div style={{ display: 'grid', gap: 4 }}>
              {[
                ['git push origin main', 'Push to production', 'amber'],
                ['Netlify deploy trigger', 'Manual deploy', 'amber'],
                ['Scheduler activation', 'Enable cron jobs', 'red'],
                ['Publishing / sending tasks', 'External actions', 'red']
              ].map(([cmd, desc, tone]) => (
                <div key={cmd} className="nx-soft" style={{ padding: '6px 10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div><code style={{ fontSize: 11 }}>{cmd}</code><div className="nx-muted" style={{ fontSize: 10 }}>{desc}</div></div>
                  <Pill tone={tone}>{tone === 'amber' ? 'Approval' : 'Blocked'}</Pill>
                </div>
              ))}
            </div>
          </section>
          <section className="glass panel">
            <h3>Blocked Commands</h3>
            <div style={{ display: 'grid', gap: 4 }}>
              {[
                ['Live trading execution', 'Never from UI'],
                ['SmartCredit scraping / login', 'Privacy violation'],
                ['DocuPost auto-send', 'Requires Ray approval'],
                ['Auto-dispute submission', 'Legal compliance'],
                ['Live client vault connection', 'Data sensitivity'],
                ['Destructive DB actions', 'Safety gate']
              ].map(([cmd, reason]) => (
                <div key={cmd} className="nx-soft" style={{ padding: '6px 10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div><code style={{ fontSize: 11 }}>{cmd}</code><div className="nx-muted" style={{ fontSize: 10 }}>{reason}</div></div>
                  <Pill tone="red">Blocked</Pill>
                </div>
              ))}
            </div>
          </section>
        </div>
        <aside className="side-stack">
          <Hermes label="Hermes · CLI" chips={['What should run next?', 'What should stay manual?']} />
          <section className="glass side-panel">
            <h3>Last Run Status</h3>
            <div className="awareness-row"><Icon name="CheckCircle2" size={20} className="green-text" /><strong>Build: Passing</strong><Pill tone="green">OK</Pill></div>
            <div className="awareness-row"><Icon name="Activity" size={20} className="green-text" /><strong>TypeScript: Clean</strong><Pill tone="green">OK</Pill></div>
            <div className="awareness-row"><Icon name="Database" size={20} className="amber-text" /><strong>Supabase: Partial</strong><Pill tone="amber">Partial</Pill></div>
          </section>
          <section className="glass side-panel">
            <h3>Suggested Next Command</h3>
            <div className="nx-soft" style={{ padding: 10 }}>
              <code style={{ fontSize: 11 }}>npm run build</code>
              <div className="nx-muted" style={{ fontSize: 10, marginTop: 4 }}>Verify build passes before commit</div>
            </div>
          </section>
        </aside>
      </div>
    </SimplePage>
  )
}

// ── Events / Proof Ledger ──
function ProofLedgerPage() {
  return (
    <SimplePage title="Events / Proof Ledger" sub="Generated Reports · Safety Verifications · Approval Candidates">
      <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        <Metric label="Total Events" value="—" icon="FileWarning" tone="blue" />
        <Metric label="Safety Checks" value="—" icon="CheckCircle2" tone="green" />
        <Metric label="Approval Candidates" value="—" icon="CircleHelp" tone="amber" />
        <Metric label="Money Outputs" value="—" icon="BadgeDollarSign" tone="violet" />
      </div>
      <div className="command-layout" style={{ flex: 1 }}>
        <div className="main-stack">
          <section className="glass panel">
            <h3>Recent Reports</h3>
            <div style={{ display: 'grid', gap: 4 }}>
              {[
                ['all_night_money_run_summary', 'Night run summary', 'green'],
                ['money_opportunity_scoreboard', 'Opportunity scoring', 'green'],
                ['automation_policy_verification', 'Safety verification', 'green'],
                ['hermes_executive_brief', 'Executive brief', 'green'],
                ['partner_offer_config', 'Partner config check', 'blue'],
                ['first_offer_launch_gate', 'Launch gate status', 'amber']
              ].map(([file, desc, tone]) => (
                <div key={file} className="nx-soft" style={{ padding: '6px 10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div><code style={{ fontSize: 11 }}>{file}</code><div className="nx-muted" style={{ fontSize: 10 }}>{desc}</div></div>
                  <Pill tone={tone}>Report</Pill>
                </div>
              ))}
            </div>
          </section>
          <div className="note">The latest cycle snapshot is report-backed. Full JSON lives in reports/runtime/ and reviewable Markdown in reports/manual_publish/. No external action confirmed.</div>
        </div>
        <aside className="side-stack">
          <Events title="Proof Events" />
          <Hermes label="Hermes" prompt="Proof questions..." chips={['Show latest reports?', 'Safety status?', 'Approval candidates?']} />
        </aside>
      </div>
    </SimplePage>
  )
}

function Footer({ activePage }) {
  return (
    <footer className="footer">
      <div>Snapshot: <span>{runtime.generatedAt.slice(0, 19).replace('T', ' ')}</span></div>
      <div>⚙ Research Engine: <span className="green-text">Active</span></div>
      <div>★ Hermes: <span className="green-text">Active</span></div>
      <div>◎ Repo Sources: <span>{runtime.repoTargetCount}</span></div>
      <div>Mode: <span>{modeLabels[activePage] || 'Executive Overview'}</span></div>
    </footer>
  )
}

export default function NexusAdminUI({ email }) {
  const validPages = new Set(navGroups.flatMap(group => group.items.map(item => item.id)))
  const readHash = () => {
    const value = window.location.hash.replace(/^#\/?/, '')
    return validPages.has(value) ? value : 'command'
  }
  const [activePage, setActivePage] = useState(readHash)
  const [hermesDrawerOpen, setHermesDrawerOpen] = useState(false)
  const [hermesPrompt, setHermesPrompt] = useState('')
  const askHermes = (prompt = '') => { setHermesPrompt(prompt); setHermesDrawerOpen(true) }
  const navigate = (id) => {
    if (!validPages.has(id)) return
    setActivePage(id)
    window.location.hash = id
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
  useEffect(() => {
    const sync = () => setActivePage(readHash())
    window.addEventListener('hashchange', sync)
    return () => window.removeEventListener('hashchange', sync)
  }, [])

  const page = {
    command: <RestoredCommandCenter onNavigate={navigate} onAskHermes={askHermes} />,
    subscription: <SubscriptionCommandCenterPage />,
    creative: <Workspace id="creative" title="Creative Studio" sub="Campaign / Content Room" kind="campaign" type="creative" />,
    design: <Workspace id="design" title="Design Library" sub="Visual / Design Room" kind="design" type="design" />,
    trading: <Workspace id="trading" title="Trading Lab" sub="Paper Trading Research Room" kind="trading" type="trading" />,
    seo: <Workspace id="seo" title="SEO / Marketing" sub="Growth Room" kind="seo" type="seo" />,
    integrations: <Workspace id="integrations" title="Integrations" sub="Connector Status Room" kind="integrations" type="integrations" layoutClass="narrow-left" />,
    ops: <Workspace id="ops" title="Ops & Improvements" sub="System Improvement Room" kind="ops" type="ops" layoutClass="wide-left" />,
    jobs: <Workspace id="jobs" title="Agent Jobs" sub="Automation Workforce Room" kind="jobs" type="jobs" />,
    source: <Workspace id="source" title="Source Intake & Review" sub="Research / Source Room" kind="source" type="source" layoutClass="source-layout" />,
    opportunity: <SimplePage title="Business Opportunities" sub="26 Scored Opportunities · Revenue Potential · Approval-Gated Conversion"><BusinessOpportunitiesPanel onAskHermes={askHermes} /></SimplePage>,
    health: <SimplePage title="System Health" sub="Click Any System for Evidence and Next Action"><SystemHealthPanel onNavigate={navigate} onAskHermes={askHermes} /></SimplePage>,
    hermes: <SimplePage title="Hermes Workroom" sub="CEO Advisor · Delegation · Specialist Rooms"><HermesWorkroom activePage={activePage} /></SimplePage>,
    rayreview: <SimplePage title="Ray Review" sub="Decisions · Feedback · Safe Approval Receipts"><RayReviewCenter /></SimplePage>,
    reports: <SimplePage title="Reports" sub="Operating Evidence · Markdown Library"><ReportCenter /></SimplePage>,
    clients: <SimplePage title="Clients" sub="Fake Customer Status · Onboarding Readiness · Ray Review"><ClientsPanel onAskHermes={askHermes} /></SimplePage>,
    research: <SimplePage title="Research Engine" sub="50 Candidates · Scores · Lanes · Approval-Gated Conversion"><ResearchEnginePanel onAskHermes={askHermes} /></SimplePage>,
    marketing: <SimplePage title="Marketing Drafts" sub="Social · Video · Newsletter · Landing · Lead Magnet · Approval-Gated"><MarketingDraftsPanel onAskHermes={askHermes} /></SimplePage>,
    automation: <SimplePage title="Automation Scheduler" sub="Safe Internal Cycles · Schedule Visibility"><AutomationSchedulerPanel onOpenReport={() => navigate('reports')} onReview={() => navigate('rayreview')} /></SimplePage>,
    goclear: <GoClearPage />,
    clientworkflow: <ClientWorkflowPage />,
    credit: <SimplePage title="Credit & Funding" sub="Readiness Scores · Documents · Disputes · Bankability · Approval-Gated"><CreditFundingPanel onAskHermes={askHermes} /></SimplePage>,
    business: <BusinessSetupPage />,
    funding: <FundingReadinessPage />,
    monetization: <SimplePage title="Monetization" sub="9 Offers · Revenue Streams · Stripe Status · Approval-Gated"><MonetizationPanel onAskHermes={askHermes} /></SimplePage>,
    partners: <PartnerOffersPage />,
    cli: <CLIControlPage />,
    proof: <ProofLedgerPage />,
    feedback: <HermesFeedbackPage />,
    settings: <SettingsPage />
  }[activePage] || <CommandCenter />

  return (
    <div className="os-root">
      <div className="app-shell">
        <Sidebar activePage={activePage} onNavigate={navigate} />
        <main className="content">
          <Topbar email={email} />
          <div className="page-content">{page}</div>
        </main>
      </div>
      {activePage !== 'hermes' && <HermesGlobalLauncher onOpen={() => askHermes()} />}
      <HermesInlineDrawer open={hermesDrawerOpen} initialPrompt={hermesPrompt} activePage={activePage} onClose={() => setHermesDrawerOpen(false)} onOpenWorkroom={() => { setHermesDrawerOpen(false); navigate('hermes') }} />
      <Footer activePage={activePage} />
    </div>
  )
}
