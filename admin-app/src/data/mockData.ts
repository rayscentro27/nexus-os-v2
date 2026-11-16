import { ClientItem, ResearchItem, CampaignItem, ApprovalItem, DocumentItem } from '../types';

export const COMMAND_CENTER_DATA = {
  kpis: [
    { id: '1', label: 'System Status', value: 'Nominal (Awaiting Telemetry)', subtitle: 'Core Daemons Active', color: 'emerald' as const, icon: 'Activity' },
    { id: '2', label: 'Active Clients', value: '8 (Demo & Sandbox)', change: 'GoClear / Apex / Sandbox', color: 'blue' as const, icon: 'Users' },
    { id: '3', label: 'Research Queue', value: '5 Jobs', subtitle: 'Universal Deterministic FIFO', color: 'cyan' as const, icon: 'FileSearch' },
    { id: '4', label: 'Pending Approvals', value: '4 Human Gates', subtitle: 'Awaiting Ray in Pillar 4', color: 'emerald' as const, icon: 'CheckCircle2' },
  ],
  pipeline: [
    { stage: 'Discovery', count: 4, color: 'bg-blue-200' },
    { stage: 'Research', count: 6, color: 'bg-cyan-200' },
    { stage: 'In Progress', count: 5, color: 'bg-teal-300' },
    { stage: 'Review', count: 3, color: 'bg-purple-200' },
  ],
  departments: [
    { name: 'Research', pct: 88, color: 'bg-cyan-500' },
    { name: 'Alpha', pct: 92, color: 'bg-blue-500' },
    { name: 'Clyde / Funding', pct: 84, color: 'bg-amber-500' },
    { name: 'Marketing (Mira)', pct: 86, color: 'bg-emerald-400' },
    { name: 'Creative', pct: 80, color: 'bg-purple-500' },
    { name: 'Trading (Mercury)', pct: 95, color: 'bg-rose-400' },
  ],
  campaigns: [
    { name: 'GoClear Institutional Rollout [DEMO]', channel: 'Multi-channel • 3 pilots', status: 'Live', statusColor: 'emerald' },
    { name: 'Apex Capital Quant Research [DEMO]', channel: 'Email + Direct • 2 partners', status: 'Live', statusColor: 'emerald' },
    { name: 'FX Corridor Pilot Initiative [DEMO]', channel: 'Institutional Whitepaper', status: 'In Review', statusColor: 'blue' },
    { name: 'Nexus Platform Architecture [DEMO]', channel: 'Technical Content', status: 'Draft', statusColor: 'slate' },
  ],
  activities: [
    { user: 'Mira', action: 'published market positioning memo', target: 'GoClear Settlement Protocol', time: '2m ago', color: 'bg-blue-100 text-blue-700' },
    { user: 'Nexus Research', action: 'verified canonical package', target: 'G10 Forex Microstructure (Supabase)', time: '18m ago', color: 'bg-emerald-100 text-emerald-700' },
    { user: 'Ray Davis', action: 'authorized tenant onboarding', target: 'GoClear Institutional', time: '1h ago', color: 'bg-indigo-100 text-indigo-700' },
    { user: 'Creative Studio', action: 'rendered interactive prototype', target: 'GoClear Portal Walkthrough', time: '2h ago', color: 'bg-teal-100 text-teal-700' },
    { user: 'Ledger Engine', action: 'generated reconciliation summary', target: 'Q2 Operating Reserve (Demo)', time: '3h ago', color: 'bg-purple-100 text-purple-700' },
  ],
  reviewQueue: [
    { name: 'GoClear Institutional Product Brief', dept: 'Marketing • v2.1', status: 'Needs Review', statusType: 'amber' },
    { name: 'GoClear Pilot Agreement [PROTOTYPE]', dept: 'Legal • v1.0', status: 'In Review', statusType: 'blue' },
    { name: 'FX Microstructure Findings – G10', dept: 'Research • v3.0', status: 'Needs Review', statusType: 'amber' },
    { name: 'Apex Brand Guidelines Update', dept: 'Creative • v1.4', status: 'In Review', statusType: 'blue' },
    { name: 'Hermes Cloud ASR Evaluation Agreement', dept: 'Operations • v1.0', status: 'Pending', statusType: 'slate' },
  ],
  activeClients: [
    { name: 'GoClear Institutional', service: 'Liquidity & Settlement', status: 'On Track', statusType: 'emerald' },
    { name: 'Apex Capital [DEMO]', service: 'Quant Alpha & Funding', status: 'On Track', statusType: 'emerald' },
    { name: 'Nexus Internal Sandbox', service: 'Core Infrastructure', status: 'In Progress', statusType: 'blue' },
    { name: 'Sovereign Treasury [DEMO]', service: 'FX Corridor Pilot', status: 'On Track', statusType: 'emerald' },
    { name: 'Horizon Global [DEMO]', service: 'Clearing Gateway', status: 'At Risk', statusType: 'rose' },
  ]
};

export const CLIENTS_DATA: ClientItem[] = [
  {
    id: 'c1',
    name: 'GoClear Institutional',
    company: 'GoClear Liquidity & Settlement Network',
    tenant: 'goclear',
    plan: 'Enterprise',
    status: 'Active',
    assignedTeam: [{ name: 'Ray Davis', avatar: 'RD' }, { name: 'Sarah Kim', avatar: 'SK' }, { name: 'Michael Chen', avatar: 'MC' }],
    progress: 92,
    segment: 'Financial Services',
    renewalDate: 'Jun 15, 2026',
    health: 'Healthy'
  },
  {
    id: 'c2',
    name: 'Apex Capital Opportunities [DEMO]',
    company: 'Apex Ventures & Quant Research',
    tenant: 'apex-quant',
    plan: 'Enterprise',
    status: 'Active',
    assignedTeam: [{ name: 'Ray Davis', avatar: 'RD' }, { name: 'Emily Rodriguez', avatar: 'ER' }],
    progress: 84,
    segment: 'Financial Services',
    renewalDate: 'Jul 22, 2026',
    health: 'Healthy'
  },
  {
    id: 'c3',
    name: 'Nexus Internal Sandbox',
    company: 'Nexus OS System Operations',
    tenant: 'nexus-sandbox',
    plan: 'Enterprise',
    status: 'Active',
    assignedTeam: [{ name: 'Sarah Kim', avatar: 'SK' }, { name: 'Jordan Lee', avatar: 'JL' }],
    progress: 88,
    segment: 'Technology',
    renewalDate: 'May 30, 2026',
    health: 'Healthy'
  },
  {
    id: 'c4',
    name: 'Sovereign Treasury [DEMO]',
    company: 'Sovereign Reserves & FX Corridor Pilot',
    tenant: 'sovereign',
    plan: 'Pro',
    status: 'Active',
    assignedTeam: [{ name: 'Daniel Park', avatar: 'DP' }, { name: 'Taylor Kim', avatar: 'TK' }],
    progress: 76,
    segment: 'Financial Services',
    renewalDate: 'Aug 14, 2026',
    health: 'Stable'
  },
  {
    id: 'c5',
    name: 'Horizon Global Liquidity [DEMO]',
    company: 'Horizon Clearing & Settlement',
    tenant: 'horizon',
    plan: 'Pro',
    status: 'Needs Attention',
    assignedTeam: [{ name: 'Michael Chen', avatar: 'MC' }, { name: 'Sarah Kim', avatar: 'SK' }],
    progress: 52,
    segment: 'Financial Services',
    renewalDate: 'May 10, 2026',
    health: 'Needs Attention'
  },
  {
    id: 'c6',
    name: 'PixelForge Studios [DEMO]',
    company: 'PixelForge Render Fleet',
    tenant: 'pixelforge',
    plan: 'Basic',
    status: 'Active',
    assignedTeam: [{ name: 'Emily Rodriguez', avatar: 'ER' }, { name: 'Marcus Lee', avatar: 'ML' }],
    progress: 86,
    segment: 'Technology',
    renewalDate: 'Sep 01, 2026',
    health: 'Healthy'
  },
  {
    id: 'c7',
    name: 'ClearPath Tech [PROTOTYPE]',
    company: 'ClearPath API Gateway',
    tenant: 'clearpath',
    plan: 'Pro',
    status: 'At Risk',
    assignedTeam: [{ name: 'Priya Shah', avatar: 'PS' }, { name: 'Jordan Lee', avatar: 'JL' }],
    progress: 34,
    segment: 'Technology',
    renewalDate: 'May 05, 2026',
    health: 'At Risk'
  },
  {
    id: 'c8',
    name: 'Vector Dynamics [DEMO]',
    company: 'Vector Dynamics Group',
    tenant: 'vector',
    plan: 'Enterprise',
    status: 'Active',
    assignedTeam: [{ name: 'Ray Davis', avatar: 'RD' }, { name: 'Sarah Kim', avatar: 'SK' }],
    progress: 90,
    segment: 'Technology',
    renewalDate: 'Oct 19, 2026',
    health: 'Healthy'
  }
];

export const RESEARCH_QUEUE_DATA: ResearchItem[] = [
  { id: 'r1', title: 'G10 Forex Microstructure & Spread Compression', source: 'TradingView', priority: 'High', status: 'In Progress', dueDate: 'Apr 22', summary: 'EBS & Currenex tick liquidity analysis on EUR/USD London/NY overlap.' },
  { id: 'r2', title: 'GoClear B2B Settlement Friction Audit', source: 'Primary Research', priority: 'High', status: 'In Review', dueDate: 'Apr 23', summary: 'Mapping 48-72h settlement lag across commercial bank cross-border rails.' },
  { id: 'r3', title: 'CDFI Intermediary Small Business Lending Matrix', source: 'Gov Portals', priority: 'Medium', status: 'In Progress', dueDate: 'Apr 24', summary: '13 CFR § 120.700 statutory rate caps and qualification standards.' },
  { id: 'r4', title: 'ASR Inference Benchmarking: faster-whisper vs whisper.cpp', source: 'GitHub', priority: 'Medium', status: 'Queued', dueDate: 'Apr 25', summary: 'Comparative real-time factor and VRAM footprint evaluation.' },
  { id: 'r5', title: 'SEC 10-K Supply Chain Risk Disclosures', source: 'SEC EDGAR', priority: 'Low', status: 'In Progress', dueDate: 'Apr 26', summary: '124 of 150 filings parsed; awaiting rate limit backoff for remaining 26.' },
];

export const CAMPAIGNS_DATA: CampaignItem[] = [
  {
    id: 'cp1',
    title: 'GoClear Institutional Pilot Outreach',
    sub: 'PROTOTYPE DATA · Q2 2025',
    status: 'Live',
    channel: 'LinkedIn & Direct',
    channelIcons: ['Linkedin', 'Mail'],
    impressions: 'Demo: 125,420',
    leads: 'Demo: 1,234 MQLs',
    convRate: '3.8% (Demo)',
    roas: 'N/A (Awaiting Live Spend)',
    growth: '+42%'
  },
  {
    id: 'cp2',
    title: 'Apex Capital Research Showcase',
    sub: 'PROTOTYPE DATA · Quant Whitepaper',
    status: 'Live',
    channel: 'LinkedIn & YouTube',
    channelIcons: ['Linkedin', 'Youtube'],
    impressions: 'Demo: 98,760',
    leads: 'Demo: 842 MQLs',
    convRate: '2.9% (Demo)',
    roas: 'N/A (Awaiting Live Spend)',
    growth: '+28%'
  },
  {
    id: 'cp3',
    title: 'B2B Liquidity Infrastructure Briefing',
    sub: 'PROTOTYPE DATA · Thought Leadership',
    status: 'In Review',
    channel: 'Direct & Industry Portals',
    channelIcons: ['Mail', 'Linkedin'],
    impressions: 'Demo: 210,340',
    leads: 'Demo: 1,876 MQLs',
    convRate: '4.1% (Demo)',
    roas: 'N/A (Awaiting Live Spend)',
    growth: '+24%'
  },
  {
    id: 'cp4',
    title: 'Nexus Platform Overview & Architecture',
    sub: 'PROTOTYPE DATA · Technical Series',
    status: 'Live',
    channel: 'YouTube & GitHub',
    channelIcons: ['Youtube', 'Linkedin'],
    impressions: 'Demo: 76,180',
    leads: 'Demo: 623 MQLs',
    convRate: '2.4% (Demo)',
    roas: 'N/A (Awaiting Live Spend)',
    growth: '+18%'
  },
  {
    id: 'cp5',
    title: 'Cross-Border Treasury Architecture Webinar',
    sub: 'PROTOTYPE DATA · Executive Education',
    status: 'Draft',
    channel: 'Email & LinkedIn',
    channelIcons: ['Mail', 'Linkedin'],
    impressions: 'Demo: 45,320',
    leads: 'Demo: 410 MQLs',
    convRate: '1.9% (Demo)',
    roas: 'N/A (Awaiting Live Spend)',
    growth: '+12%'
  }
];

export const APPROVALS_DATA: ApprovalItem[] = [
  {
    id: 'app-1',
    title: 'GoClear Customer Discovery Offer Deck',
    sub: 'Marketing • Creative [PROTOTYPE]',
    category: 'Marketing',
    owner: { name: 'Sarah Kim', role: 'Brand Manager', avatar: 'SK' },
    client: 'GoClear Institutional',
    submitted: '2h ago',
    priority: 'High',
    status: 'Pending',
    description: 'Creative assets for the GoClear pilot including hero images, institutional workflow diagrams, and pitch deck.'
  },
  {
    id: 'app-2',
    title: 'Apex Q2 Infrastructure Allocation',
    sub: 'Finance • Budget [PROTOTYPE]',
    category: 'Finance',
    owner: { name: 'Michael Chen', role: 'Finance Lead', avatar: 'MC' },
    client: 'Apex Capital',
    submitted: '4h ago',
    priority: 'High',
    status: 'In Review',
    description: 'Proposed Q2 compute budget for Hermes Cloud ASR evaluation and Mac mini local execution.'
  },
  {
    id: 'app-3',
    title: 'GoClear Pilot Agreement v2.1',
    sub: 'Legal • Contract [PROTOTYPE]',
    category: 'Documents',
    owner: { name: 'Priya Sharma', role: 'Legal Counsel', avatar: 'PS' },
    client: 'GoClear Institutional',
    submitted: '1d ago',
    priority: 'Medium',
    status: 'Pending',
    description: 'Updated SLA and data processing agreement for annual enterprise platform renewal.'
  },
  {
    id: 'app-4',
    title: 'Apex Brand Guidelines Update',
    sub: 'Creative • Brand [PROTOTYPE]',
    category: 'Marketing',
    owner: { name: 'Alex Rivera', role: 'Creative Director', avatar: 'AR' },
    client: 'Apex Capital',
    submitted: '1d ago',
    priority: 'Medium',
    status: 'Approved',
    description: 'Comprehensive brand typography and updated color palette documentation.'
  },
  {
    id: 'app-5',
    title: 'Oracle / Hermes Cloud ASR Evaluation Agreement',
    sub: 'Operations • Vendor [PROTOTYPE]',
    category: 'Compliance',
    owner: { name: 'Jordan Lee', role: 'Ops Manager', avatar: 'JL' },
    client: 'PixelForge Studios',
    submitted: '2d ago',
    priority: 'Low',
    status: 'Pending',
    description: 'Third-party compute provider evaluation agreement with SOC-2 compliance addendum.'
  }
];

export const DOCUMENTS_DATA: DocumentItem[] = [
  {
    id: 'doc-1',
    name: 'GoClear Customer Discovery Deck v2.pdf',
    size: '2.4 MB',
    client: 'GoClear Institutional',
    category: 'Marketing',
    status: 'Needs Review',
    uploadedDate: 'Apr 22, 2025 2:14 PM',
    reviewer: { name: 'Sarah Kim', avatar: 'SK' },
    format: 'pdf'
  },
  {
    id: 'doc-2',
    name: 'Apex Brand Guidelines v1.4.pdf',
    size: '8.1 MB',
    client: 'Apex Capital',
    category: 'Creative',
    status: 'Verified',
    uploadedDate: 'Apr 21, 2025 11:03 AM',
    reviewer: { name: 'Marcus Lee', avatar: 'ML' },
    format: 'pdf'
  },
  {
    id: 'doc-3',
    name: 'GoClear Master Services Contract.docx',
    size: '1.8 MB',
    client: 'GoClear Institutional',
    category: 'Legal',
    status: 'Needs Signature',
    uploadedDate: 'Apr 21, 2025 9:22 AM',
    reviewer: { name: 'Ray Davis', avatar: 'RD' },
    format: 'docx'
  },
  {
    id: 'doc-4',
    name: 'Q1 Treasury & Cash Runway Report.pdf',
    size: '3.2 MB',
    client: 'Nexus Internal Sandbox',
    category: 'Financial',
    status: 'Verified',
    uploadedDate: 'Apr 20, 2025 4:17 PM',
    reviewer: { name: 'Daniel Park', avatar: 'DP' },
    format: 'pdf'
  },
  {
    id: 'doc-5',
    name: 'Sovereign FX Corridor Pilot Deck.pdf',
    size: '12.6 MB',
    client: 'Sovereign Treasury',
    category: 'Marketing',
    status: 'In Review',
    uploadedDate: 'Apr 20, 2025 1:45 PM',
    reviewer: { name: 'Priya Shah', avatar: 'PS' },
    format: 'pdf'
  }
];

export const CREATIVE_PIPELINE = {
  brief: [
    { id: 'b1', title: 'GoClear Liquidity Deck Social Set', client: 'GoClear Institutional', priority: 'High', color: 'rose' },
    { id: 'b2', title: 'Apex Investor Briefing Email', client: 'Apex Capital', priority: 'Medium', color: 'amber' },
    { id: 'b3', title: 'FX Corridor Pilot Diagrams', client: 'Sovereign Treasury', priority: 'Medium', color: 'amber' }
  ],
  design: [
    { id: 'd1', title: 'Q2 Architecture Graphics', client: 'Nexus Internal', priority: 'High', color: 'rose' },
    { id: 'd2', title: 'GoClear Settlement Spec Dossier', client: 'GoClear Institutional', priority: 'Medium', color: 'amber' },
    { id: 'd3', title: 'Event Showcase Graphics', client: 'Apex Capital', priority: 'Low', color: 'emerald' }
  ],
  review: [
    { id: 'r1', title: 'Interactive Flow Prototype', client: 'GoClear Institutional', priority: 'High', color: 'rose' },
    { id: 'r2', title: 'ASR Pipeline Walkthrough Video', client: 'Nexus Internal', priority: 'Medium', color: 'amber' },
    { id: 'r3', title: 'Website Refresh', client: 'Apex Capital', priority: 'Medium', color: 'amber' }
  ],
  approved: [
    { id: 'a1', title: 'GoClear Institutional One-Pager', client: 'GoClear Institutional', date: 'Apr 21' },
    { id: 'a2', title: 'Apex Feature Launch Video', client: 'Apex Capital', date: 'Apr 19' },
    { id: 'a3', title: 'Social Media Set', client: 'Nexus Internal', date: 'Apr 18' }
  ]
};

export const FINANCE_DATA = {
  kpis: [
    { id: '1', label: 'Revenue (MTD)', value: '$0.00 Verified', change: 'Awaiting ledger sync (Demo: $482k)', color: 'emerald' as const, icon: 'TrendingUp' },
    { id: '2', label: 'Commissions (MTD)', value: '$0.00 Verified', change: 'Awaiting sync (Demo: $86.4k)', color: 'blue' as const, icon: 'Users' },
    { id: '3', label: 'Pending Payouts', value: '4 Requests', subtitle: 'Awaiting Ray sign-off (Demo)', color: 'cyan' as const, icon: 'FileText' },
    { id: '4', label: 'Cash Position', value: 'Not Connected', change: 'Awaiting banking API ($1.25M Demo)', color: 'emerald' as const, icon: 'Wallet' },
  ],
  invoices: [
    { id: 'INV-DEMO-0421', client: 'GoClear Institutional [PROTOTYPE]', initial: 'G', amount: '$24,500', status: 'Paid', issued: 'Apr 21, 2025', due: '—' },
    { id: 'INV-DEMO-0418', client: 'Apex Capital [PROTOTYPE]', initial: 'A', amount: '$18,000', status: 'Paid', issued: 'Apr 18, 2025', due: '—' },
    { id: 'INV-DEMO-0415', client: 'Sovereign Treasury [PROTOTYPE]', initial: 'S', amount: '$32,750', status: 'Sent', issued: 'Apr 15, 2025', due: 'Apr 30' },
    { id: 'INV-DEMO-0412', client: 'Horizon Global [PROTOTYPE]', initial: 'H', amount: '$15,600', status: 'Sent', issued: 'Apr 12, 2025', due: 'Apr 27' },
    { id: 'INV-DEMO-0409', client: 'Vector Dynamics [PROTOTYPE]', initial: 'V', amount: '$12,400', status: 'Overdue', issued: 'Apr 9, 2025', due: 'Apr 19' },
  ],
  expenses: [
    { name: 'Compute & Model Inference (Demo)', pct: 32, amount: '$154,280', color: 'bg-blue-500' },
    { name: 'Engineering & Systems', pct: 24, amount: '$116,450', color: 'bg-emerald-400' },
    { name: 'Cloud Infrastructure & DB', pct: 16, amount: '$77,320', color: 'bg-purple-500' },
    { name: 'Data Feeds & Telemetry APIs', pct: 14, amount: '$68,910', color: 'bg-amber-500' },
    { name: 'Operations & Facilities', pct: 9, amount: '$42,110', color: 'bg-rose-400' },
    { name: 'Other', pct: 5, amount: '$23,600', color: 'bg-slate-400' },
  ],
  payouts: [
    { name: 'Taylor Kim', type: 'Commission', amount: '$4,250', status: 'Pending', submitted: 'Apr 21, 2025' },
    { name: 'Jordan Lee', type: 'Commission', amount: '$3,600', status: 'Pending', submitted: 'Apr 20, 2025' },
    { name: 'Casey Park', type: 'Payout', amount: '$2,800', status: 'In Review', submitted: 'Apr 19, 2025' },
    { name: 'Morgan Chen', type: 'Payout', amount: '$5,400', status: 'Approved', submitted: 'Apr 18, 2025' },
  ]
};

export const OPERATIONS_DATA = {
  kpis: [
    { id: '1', label: 'Open Work Orders', value: '4 Active', change: 'Deterministic FIFO Queue', color: 'blue' as const, icon: 'Cog' },
    { id: '2', label: 'Core Daemons', value: '4 Connected', change: 'Mac mini, Oracle, Supabase, Workers', color: 'cyan' as const, icon: 'Zap' },
    { id: '3', label: 'Queue Integrity', value: 'Verified', subtitle: 'Deterministic skips & cooldowns', color: 'emerald' as const, icon: 'ShieldCheck' },
    { id: '4', label: 'Human Gates', value: '4 Items', subtitle: 'Awaiting Ray in Pillar 4', color: 'rose' as const, icon: 'AlertTriangle' },
  ],
  workflow: [
    { stage: 'Intake', count: 'FIFO Queue', time: '< 1 second', color: 'bg-cyan-500 text-white' },
    { stage: 'Acquire', count: 'Raw Source', time: 'Deterministic', color: 'bg-blue-500 text-white' },
    { stage: 'Normalize', count: 'Schema Standard', time: 'Instant', color: 'bg-indigo-500 text-white' },
    { stage: 'Supabase', count: 'Canonical Pack', time: 'Verified Readback', color: 'bg-purple-500 text-white' },
    { stage: 'Alpha / Route', count: 'Downstream', time: 'Post-Storage', color: 'bg-emerald-500 text-white' },
  ],
  matrix: [
    { dept: 'Research', auto: 12, manual: 1, avgTime: '1.8h' },
    { dept: 'Alpha', auto: 15, manual: 1, avgTime: '2.4h' },
    { dept: 'Clyde / Funding', auto: 8, manual: 2, avgTime: '3.1h' },
    { dept: 'Finance (Ledger)', auto: 6, manual: 1, avgTime: '2.0h' },
    { dept: 'Systems (Forge)', auto: 10, manual: 1, avgTime: '1.5h' },
  ],
  workload: [
    { dept: 'Research (Queue)', current: 5, total: 10, pct: 50, color: 'bg-blue-500' },
    { dept: 'Alpha (Quant)', current: 3, total: 5, pct: 60, color: 'bg-emerald-400' },
    { dept: 'Clyde (Funding)', current: 2, total: 4, pct: 50, color: 'bg-purple-500' },
    { dept: 'Creative (Studio)', current: 4, total: 6, pct: 67, color: 'bg-amber-500' },
    { dept: 'Forge (Systems)', current: 4, total: 4, pct: 100, color: 'bg-rose-400' },
  ]
};
