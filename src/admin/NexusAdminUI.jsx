// Nexus OS v2 — redesigned admin dashboard UI.
// Source: imported React package (nexus-os-react). Design reference: preview HTML.
// Mock/demo data only — no backend calls, no external actions. Rendered after auth by app/App.tsx.
import React, { useMemo, useState } from 'react'
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
  {
    label: 'Executive',
    items: [
      { id: 'command', label: 'Command Center', icon: 'LayoutDashboard' },
      { id: 'source', label: 'Source Intake & Review', icon: 'ScanSearch', status: 'Live', statusTone: 'green' },
      { id: 'opportunity', label: 'Opportunity Lab', icon: 'Target', status: 'Active', statusTone: 'blue' }
    ]
  },
  {
    label: 'Workflows',
    items: [
      { id: 'creative', label: 'Creative Studio', icon: 'WandSparkles', status: 'Live', statusTone: 'green' },
      { id: 'design', label: 'Design Library', icon: 'Layers3', status: 'Live', statusTone: 'green' },
      { id: 'trading', label: 'Trading Lab', icon: 'TrendingUp', status: 'Demo', statusTone: 'amber' },
      { id: 'seo', label: 'SEO / Marketing', icon: 'Search', status: 'Seed', statusTone: 'blue' }
    ]
  },
  {
    label: 'Growth',
    items: [
      { id: 'integrations', label: 'Integrations', icon: 'Plug', status: 'Partial', statusTone: 'blue' },
      { id: 'ops', label: 'Ops & Improvements', icon: 'BadgeDollarSign', status: 'Live', statusTone: 'green' },
      { id: 'jobs', label: 'Agent Jobs', icon: 'Bot', status: 'Live', statusTone: 'green' }
    ]
  },
  {
    label: 'System',
    items: [
      { id: 'health', label: 'System Health', icon: 'Activity', status: 'Live', statusTone: 'green' },
      { id: 'hermes', label: 'Hermes Advisor', icon: 'Sparkles', status: 'Online', statusTone: 'green' },
      { id: 'settings', label: 'Settings', icon: 'Settings', disabled: true },
      { id: 'help', label: 'Help & Docs', icon: 'CircleHelp', disabled: true }
    ]
  }
]

const modeLabels = {
  command: 'Executive Overview',
  source: 'Source Intake & Review',
  opportunity: 'Opportunity Lab',
  creative: 'Creative Studio',
  design: 'Design Library',
  trading: 'Trading Lab (Paper Only)',
  seo: 'Growth Room',
  integrations: 'Connector Status Room',
  ops: 'System Improvement Room',
  jobs: 'Automation Workforce Room',
  health: 'System Health',
  hermes: 'Hermes Advisor'
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
    ['Business Credit for LLCs: The Ultimate 2026 Guide', 'Web Article', 'Needs Review', 'Score 74'],
    ['Navy Federal CLI Program Notes', 'Pasted Note', 'Needs Review', 'Score 68'],
    ['Nav Interview — Building Business Credit Transcript', 'Transcript File', 'Summarized', 'Score 76'],
    ['NotebookLM Export — Business Credit Research', 'NotebookLM Export', 'Summarized', 'Score 79'],
    ['Hermes SEO Strategy Update June 2026', 'YouTube Video', 'Researching', 'Score 71'],
    ['Google March 2026 Core Update', 'Web Article', 'Parked', 'Score 60']
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
      <div className="hermes-status"><Icon name="Activity" size={20} />Hermes v1.2 <span>• Active</span></div>
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

// Hermes Advisor chat bar. Mock-only: input is local state, send is a no-op (no backend, no external action).
function Hermes({ label = 'Hermes Advisor', prompt = 'Ask Hermes anything...', chips = [] }) {
  const [text, setText] = useState('')
  return (
    <section className="glass hermes-card">
      <div className="hermes-title"><span className="advisor-ring small" />{label} <em>• Online</em></div>
      <div className="hermes-message">I recommend moving forward with focused validation, resolving critical blockers first, and generating proof artifacts for review.</div>
      {chips.length > 0 && (
        <div className="hermes-chips">
          {chips.map(chip => (
            <button key={chip} type="button" className="hermes-chip" onClick={() => setText(chip)}>{chip}</button>
          ))}
        </div>
      )}
      <form
        className="ask-row"
        onSubmit={(e) => { e.preventDefault(); setText('') }}
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

const HERMES_COMMAND_CHIPS = ['What needs my attention?', 'Summarize blockers', 'Recommend next actions', 'Show urgent approvals']

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
      <PageTitle title="Command Center" sub="Executive Overview" />

      <div className="metrics-grid">
        <Metric label="Active Departments" value="9 / 12" icon="LayoutGrid" tone="violet" />
        <Metric label="Needs Review" value="23" icon="FileWarning" tone="amber" />
        <Metric label="Blocked Items" value="7" icon="TriangleAlert" tone="red" />
        <Metric label="Scheduled Work" value="18" icon="CalendarDays" tone="blue" />
        <Metric label="Automation Feeders" value="64" icon="Zap" tone="cyan" />
        <Metric label="System Health" value="98%" icon="Activity" tone="green" />
      </div>

      <div className="command-layout">
        <div className="main-stack">
          <section className="glass spotlight-wrap">
            <div className="spotlight">
              <div>
                <div className="recommend">★ Top Recommendation</div>
                <h3>Launch 3 high-intent content assets this week to capture demand ahead of competitor updates.</h3>
                <button>View details →</button>
              </div>
              <div className="hero-art" />
              <div>
                <h4>Today’s Priorities</h4>
                <p>✅ Approve Q2 content calendar <span>High</span></p>
                <p>✅ Unblock integrations (2) <span>Medium</span></p>
                <p>✅ Review SEO strategy update <span>Medium</span></p>
              </div>
              <div>
                <h4>Quick Launch</h4>
                <button className="quick">Create Opportunity</button>
                <button className="quick">Create Campaign Kit</button>
                <button className="quick">Run Backtest</button>
              </div>
            </div>
          </section>

          <Departments />
          <Hermes
            label="Hermes Advisor"
            prompt="Ask Hermes for guidance on priorities, blockers, or next actions..."
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

  const statusTone = status => {
    if (/Need|Blocked|Failed|Config/.test(status)) return 'amber'
    if (/Live|Connected|Done|Approved|Completed|Scored|Backtested|Summarized/.test(status)) return 'green'
    return 'blue'
  }

  return (
    <aside className="glass list-panel">
      <div className="panel-head">
        <h3>{title}</h3>
        <button className="new-btn">+ New</button>
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
            <button>Get Started</button>
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
  const actionsByType = {
    trading: ['Run Backtest', 'Generate Report', 'Paper Demo Only', 'Create Task', 'Send to Ops', 'Park Strategy'],
    integrations: ['Run Status Check', 'Open Docs', 'Create Fix Task', 'Request Setup', 'Create Report', 'Park Integration'],
    jobs: ['View Proof / Logs', 'Create Task', 'Request Research', 'Schedule Later', 'Rerun Dry-Run', 'Park / Pause'],
    default: ['Analyze', 'Create Report', 'Create Task', 'Send to Creative', 'Request More Research', 'Park']
  }
  const actions = actionsByType[type] || actionsByType.default
  const actionIcons = ['Sparkles', 'FileText', 'CheckCircle2', 'Send', 'Search', 'PauseCircle']

  return (
    <aside className="side-stack">
      <section className="glass side-panel">
        <h3>Actions</h3>
        <div className="action-grid">
          {actions.map((action, index) => (
            <button className="action-button" key={action}>
              <Icon name={actionIcons[index % actionIcons.length]} size={25} className={index % 3 === 0 ? 'violet-text' : index % 3 === 1 ? 'blue-text' : 'green-text'} />
              <strong>{action}</strong>
              <small>Workflow action</small>
            </button>
          ))}
        </div>
      </section>

      <section className="glass side-panel">
        <div className="panel-head"><h3>Generated Outputs</h3><a>View all →</a></div>
        {['Summary', 'Report Draft', 'Implementation Plan', 'Proof / History', 'Decision Notes'].map((output, index) => (
          <div className="output-row" key={output}>
            <div>▣</div>
            <span><strong>{output}</strong><small>Updated {index + 1}h ago</small></span>
            <Pill tone={index === 1 ? 'violet' : 'green'}>{index === 1 ? 'Draft' : 'Ready'}</Pill>
          </div>
        ))}
      </section>

      <Events title="System Proof / History" />
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
    <section className="page active command-page">
      <PageTitle title={title} sub={sub} />
      {children}
    </section>
  )
}

function SystemHealthPage() {
  return (
    <SimplePage title="System Health" sub="Operational Status">
      <div className="metrics-grid">
        <Metric label="System Health" value="98%" icon="Activity" tone="green" />
        <Metric label="Active Integrations" value="6 / 9" icon="CopyPlus" tone="blue" />
        <Metric label="Failing Connectors" value="2" icon="TriangleAlert" tone="red" />
        <Metric label="Automation Feeders" value="64" icon="Zap" tone="cyan" />
        <Metric label="Agent Jobs Running" value="1" icon="Bot" tone="violet" />
        <Metric label="Scheduled Work" value="18" icon="CalendarDays" tone="amber" />
      </div>
      <div className="command-layout">
        <div className="main-stack"><Departments /></div>
        <aside className="side-stack"><Events /><Awareness /></aside>
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

function Footer({ activePage }) {
  return (
    <footer className="footer">
      <div>System Time: <span>Jun 27, 2026&nbsp;&nbsp;10:12 AM</span></div>
      <div>⚙ Research Engine: <span className="green-text">Partial</span></div>
      <div>★ Hermes: <span className="green-text">Active</span></div>
      <div>◎ Data Sources: <span>64</span></div>
      <div>Mode: <span>{modeLabels[activePage] || 'Executive Overview'}</span></div>
    </footer>
  )
}

export default function NexusAdminUI({ email }) {
  const [activePage, setActivePage] = useState('command')

  const page = {
    command: <CommandCenter />,
    creative: <Workspace id="creative" title="Creative Studio" sub="Campaign / Content Room" kind="campaign" type="creative" />,
    design: <Workspace id="design" title="Design Library" sub="Visual / Design Room" kind="design" type="design" />,
    trading: <Workspace id="trading" title="Trading Lab" sub="Paper Trading Research Room" kind="trading" type="trading" />,
    seo: <Workspace id="seo" title="SEO / Marketing" sub="Growth Room" kind="seo" type="seo" />,
    integrations: <Workspace id="integrations" title="Integrations" sub="Connector Status Room" kind="integrations" type="integrations" layoutClass="narrow-left" />,
    ops: <Workspace id="ops" title="Ops & Improvements" sub="System Improvement Room" kind="ops" type="ops" layoutClass="wide-left" />,
    jobs: <Workspace id="jobs" title="Agent Jobs" sub="Automation Workforce Room" kind="jobs" type="jobs" />,
    source: <Workspace id="source" title="Source Intake & Review" sub="Research / Source Room" kind="source" type="source" layoutClass="source-layout" />,
    opportunity: <Workspace id="opportunity" title="Opportunity Lab" sub="Revenue / Opportunity Room" kind="opportunity" type="opportunity" layoutClass="opportunity-layout" />,
    health: <SystemHealthPage />,
    hermes: <HermesAdvisorPage />
  }[activePage] || <CommandCenter />

  return (
    <div className="os-root">
      <div className="app-shell">
        <Sidebar activePage={activePage} onNavigate={setActivePage} />
        <main className="content">
          <Topbar email={email} />
          <div className="page-content">{page}</div>
        </main>
      </div>
      <Footer activePage={activePage} />
    </div>
  )
}
