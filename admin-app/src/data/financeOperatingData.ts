import { DataTruthClass } from './executiveCommandData';

export interface MoneyPositionMetric {
  id: string;
  label: string;
  value: string;
  numericValue: number;
  truthClass: DataTruthClass;
  source: string;
  sourceStatus: 'CONNECTED' | 'NOT CONNECTED' | 'SANDBOX' | 'PAPER' | 'MANUAL';
  description: string;
  isPaper?: boolean;
}

export interface AIProviderCost {
  provider: string;
  role: string;
  today: number;
  sevenDays: number;
  thirtyDays: number;
  currentBalance: string;
  trend: 'Up' | 'Down' | 'Flat';
  trendPct: string;
  truthClass: DataTruthClass;
  status: 'ACTIVE' | 'FREE TIER' | 'LOW BALANCE' | 'TESTING';
}

export interface ModelTokenUsage {
  model: string;
  provider: string;
  department: string;
  inputTokens: string;
  outputTokens: string;
  totalTokens: string;
  costToday: number;
  costMonth: number;
  truthClass: DataTruthClass;
  pricingNote: string;
}

export interface AutonomousUnitEconomicsItem {
  department: string;
  metricLabel: string;
  periodCost: number;
  outcomeCount: number;
  costPerOutcome: number;
  formattedCostPerOutcome: string;
  truthClass: DataTruthClass;
  notes: string;
}

export interface DepartmentOperatingCostItem {
  department: string;
  todayCost: number;
  sevenDaysCost: number;
  monthCost: number;
  mainCostDriver: string;
  trend: 'Up' | 'Down' | 'Flat';
  trendPct: string;
  truthClass: DataTruthClass;
  status: 'OPTIMAL' | 'EVALUATING' | 'MONITORED';
}

export interface InfrastructureServiceCost {
  service: string;
  category: 'Compute' | 'Database' | 'Hosting' | 'DNS' | 'DevOps' | 'Monitoring';
  monthlyCost: number;
  formattedCost: string;
  currentUsage: string;
  nextBillDate: string;
  renewalDate: string;
  truthClass: DataTruthClass;
  status: 'ACTIVE' | 'FREE TIER' | 'RENEWING SOON';
}

export interface BillCommitmentItem {
  id: string;
  vendor: string;
  amount: number;
  formattedAmount: string;
  dueDate: string;
  daysUntilDue: number;
  isRecurring: boolean;
  frequency?: 'Monthly' | 'Annual' | 'Usage-based';
  departmentOwner: string;
  paymentStatus: 'PAID' | 'DUE SOON' | 'APPROVAL REQUIRED' | 'OVERDUE';
  approvalRequired: boolean;
  approvalId?: string;
}

export interface ProviderBurnItem {
  provider: string;
  currentBalance: number;
  formattedBalance: string;
  avgDailyBurn: number;
  formattedBurn: string;
  estimatedDaysRemaining: number | null;
  status: 'HEALTHY' | 'LOW' | 'CRITICAL' | 'UNLIMITED';
  truthClass: DataTruthClass;
}

export interface CampaignEconomicsItem {
  id: string;
  campaign: string;
  owner: string;
  offer: string;
  targetAudience: string;
  channel: string;
  status: 'PLANNING' | 'WAITING_RAY' | 'TEST' | 'LIVE' | 'PAUSED' | 'COMPLETE';
  truthClass: DataTruthClass;
  spend: number;
  creativeCost: number;
  aiCost: number;
  toolingCost: number;
  leads: number;
  qualifiedLeads: number;
  customers: number;
  verifiedRevenue: number;
  commissionRevenue: number;
  cac: number | null;
  cpl: number | null;
  grossProfit: number;
  netProfit: number;
  roiPct: number | null;
  currentDecision: 'CONTINUE' | 'OPTIMIZE' | 'PAUSE' | 'WAITING_RAY';
}

export interface CreativeCostItem {
  asset: string;
  campaign: string;
  provider: string;
  runtime: string;
  cost: number;
  usable: boolean;
  costPerUsable: number;
  truthClass: DataTruthClass;
}

export interface UpgradeInvestmentItem {
  id: string;
  upgrade: string;
  sourceDepartment: string;
  currentStage: 'PROPOSAL' | 'TEST SANDBOX' | 'AUDIT BY UPGRADE CONTROL' | 'CERTIFIED' | 'READY FOR SYSTEMS';
  testCost: number;
  expectedRecurringCost: number;
  expectedSavings: string;
  paybackRationale: string;
  financeStatus: 'APPROVED' | 'PENDING RAY' | 'EVALUATING' | 'REJECTED';
  approvalRequired: boolean;
  truthClass: DataTruthClass;
}

export interface FinancialAlertItem {
  id: string;
  severity: 'CRITICAL' | 'WARNING' | 'INFO';
  title: string;
  reason: string;
  owner: string;
  currentAction: string;
  needsRay: boolean;
  timestamp: string;
}

export interface GrantPipelineItem {
  id: string;
  program: string;
  amount: number;
  formattedAmount: string;
  status: 'Dossier Prepared' | 'Under Review' | 'Drafting' | 'Submitted';
  deadline: string;
  probability: string;
  nextAction: string;
  rayApprovalState: 'Awaiting Signature' | 'Signed' | 'Pending Review';
  truthClass: DataTruthClass;
}

export interface InvoiceItem {
  id: string;
  client: string;
  amount: number;
  formattedAmount: string;
  status: 'Paid' | 'Sent' | 'Overdue' | 'Draft';
  issuedDate: string;
  dueDate: string;
  isRealProduction: boolean;
  truthClass: DataTruthClass;
}

// -----------------------------------------------------------------------------
// MONEY POSITION DATA (Zero Fake Cash Policy)
// -----------------------------------------------------------------------------
export const MONEY_POSITION_DATA: MoneyPositionMetric[] = [
  {
    id: 'mp-cash',
    label: 'Verified Cash',
    value: '$0.00',
    numericValue: 0,
    truthClass: 'NOT CONNECTED',
    source: 'Commercial Banking (Plaid / Mercury)',
    sourceStatus: 'NOT CONNECTED',
    description: 'Awaiting live bank API credential synchronization. Real ledger balance is not connected.'
  },
  {
    id: 'mp-revenue',
    label: 'Verified Revenue',
    value: '$0.00',
    numericValue: 0,
    truthClass: 'NOT CONNECTED',
    source: 'Stripe Live Webhook',
    sourceStatus: 'NOT CONNECTED',
    description: 'Live merchant gateway disconnected. Zero dollars in real revenue recognized.'
  },
  {
    id: 'mp-ar',
    label: 'Accounts Receivable',
    value: '$0.00 Live / $85,000 Demo',
    numericValue: 0,
    truthClass: 'DEMO',
    source: 'Enterprise Billing Ledger',
    sourceStatus: 'SANDBOX',
    description: 'Demo client invoices staged for GoClear & Apex Capital pilot review.'
  },
  {
    id: 'mp-ap',
    label: 'Accounts Payable',
    value: '$1,420.00',
    numericValue: 1420,
    truthClass: 'LIVE',
    source: 'Vendor Invoice & SaaS Ledger',
    sourceStatus: 'CONNECTED',
    description: 'Upcoming monthly cloud subscriptions, compute billing, and domain commitments.'
  },
  {
    id: 'mp-grant',
    label: 'Grant Pipeline',
    value: '$85,000.00',
    numericValue: 85000,
    truthClass: 'ESTIMATED',
    source: 'Clyde Grant Engine (State AI Voucher)',
    sourceStatus: 'MANUAL',
    description: 'Non-dilutive innovation voucher application dossier pre-compiled for executive signature.'
  },
  {
    id: 'mp-committed',
    label: 'Committed Spend',
    value: '$2,850.00 / mo',
    numericValue: 2850,
    truthClass: 'LIVE_VERIFIED',
    source: 'SaaS & Compute Subscriptions',
    sourceStatus: 'CONNECTED',
    description: 'Authoritative fixed baseline for platform hosting, database pools, and foundational APIs.'
  },
  {
    id: 'mp-budget',
    label: 'Available Budget',
    value: 'NOT PROVEN',
    numericValue: 0,
    truthClass: 'NOT CONNECTED',
    source: 'Treasury Reserve Account',
    sourceStatus: 'NOT CONNECTED',
    description: 'Cannot compute available liquidity until commercial bank account is authenticated.'
  },
  {
    id: 'mp-paper',
    label: 'Paper Trading Value',
    value: '+$18,420.00',
    numericValue: 18420,
    truthClass: 'PAPER',
    source: 'OANDA Practice Sandbox / Tournament R4',
    sourceStatus: 'PAPER',
    isPaper: true,
    description: 'Simulated quantitative algorithmic performance. NOT real cash reserves.'
  },
  {
    id: 'mp-savings',
    label: 'Autonomous Cost Savings',
    value: '~$3,200.00 / mo',
    numericValue: 3200,
    truthClass: 'ESTIMATED',
    source: 'Ollama & Hermes Self-Hosted Compute',
    sourceStatus: 'CONNECTED',
    description: 'Validated savings from routing 1.68M daily tokens to local Metal and Oracle VMs over OpenAI APIs.'
  }
];

// -----------------------------------------------------------------------------
// AI & MODEL SPEND DATA
// -----------------------------------------------------------------------------
export const AI_PROVIDER_COSTS: AIProviderCost[] = [
  {
    provider: 'OpenAI',
    role: 'GPT-4o fallback & reasoning',
    today: 4.12,
    sevenDays: 28.40,
    thirtyDays: 114.20,
    currentBalance: '$42.80',
    trend: 'Down',
    trendPct: '-12%',
    truthClass: 'LIVE',
    status: 'ACTIVE'
  },
  {
    provider: 'OpenRouter',
    role: 'Multi-model router (Claude 3.5 & DeepSeek)',
    today: 2.40,
    sevenDays: 16.50,
    thirtyDays: 68.00,
    currentBalance: '$18.50',
    trend: 'Flat',
    trendPct: '0%',
    truthClass: 'LIVE',
    status: 'LOW BALANCE'
  },
  {
    provider: 'Modal',
    role: 'A10G GPU workers (MuseTalk avatar test sandbox)',
    today: 6.80,
    sevenDays: 44.20,
    thirtyDays: 182.00,
    currentBalance: '$120.00 Credits',
    trend: 'Up',
    trendPct: '+15%',
    truthClass: 'LIVE',
    status: 'ACTIVE'
  },
  {
    provider: 'Oracle Cloud (Hermes)',
    role: 'Hermes-3-70B & faster-whisper CPU benchmark',
    today: 0.00,
    sevenDays: 0.00,
    thirtyDays: 0.00,
    currentBalance: 'Free Tier (4 OCPU)',
    trend: 'Flat',
    trendPct: '0%',
    truthClass: 'LIVE_VERIFIED',
    status: 'FREE TIER'
  },
  {
    provider: 'ElevenLabs',
    role: 'Nova voice synthesis (TTS)',
    today: 1.85,
    sevenDays: 12.40,
    thirtyDays: 48.50,
    currentBalance: '$38.20',
    trend: 'Up',
    trendPct: '+8%',
    truthClass: 'LIVE',
    status: 'ACTIVE'
  },
  {
    provider: 'Deepgram',
    role: 'Voice input transcription (STT)',
    today: 0.45,
    sevenDays: 3.20,
    thirtyDays: 14.10,
    currentBalance: '$24.00',
    trend: 'Flat',
    trendPct: '0%',
    truthClass: 'LIVE',
    status: 'ACTIVE'
  },
  {
    provider: 'Needles Vector Engine',
    role: 'Embedded vector memory indexing',
    today: 0.00,
    sevenDays: 0.00,
    thirtyDays: 0.00,
    currentBalance: 'Self-Hosted ($0.00)',
    trend: 'Flat',
    trendPct: '0%',
    truthClass: 'LIVE_VERIFIED',
    status: 'ACTIVE'
  }
];

export const TOTAL_AI_SPEND = {
  today: 15.62,
  sevenDays: 104.70,
  thirtyDays: 426.80
};

// -----------------------------------------------------------------------------
// TOKEN & MODEL USAGE
// -----------------------------------------------------------------------------
export const TOKEN_MODEL_USAGE: ModelTokenUsage[] = [
  {
    model: 'gpt-4o',
    provider: 'OpenAI',
    department: 'Marketing / Clyde',
    inputTokens: '420,000',
    outputTokens: '84,000',
    totalTokens: '504,000',
    costToday: 3.15,
    costMonth: 88.20,
    truthClass: 'LIVE',
    pricingNote: '$2.50 / $10.00 per 1M tokens'
  },
  {
    model: 'claude-3-5-sonnet',
    provider: 'OpenRouter',
    department: 'Development / Labs',
    inputTokens: '280,000',
    outputTokens: '62,000',
    totalTokens: '342,000',
    costToday: 2.82,
    costMonth: 74.50,
    truthClass: 'LIVE',
    pricingNote: '$3.00 / $15.00 per 1M tokens'
  },
  {
    model: 'hermes-3-70b',
    provider: 'Oracle Cloud VM',
    department: 'Nova / Systems',
    inputTokens: '840,000',
    outputTokens: '210,000',
    totalTokens: '1,050,000',
    costToday: 0.00,
    costMonth: 0.00,
    truthClass: 'LIVE_VERIFIED',
    pricingNote: '$0.00 (Self-hosted on Oracle Always Free 24GB ARM)'
  },
  {
    model: 'llama-3.1-8b',
    provider: 'Ollama (Mac mini)',
    department: 'Research / Systems',
    inputTokens: '1,200,000',
    outputTokens: '480,000',
    totalTokens: '1,680,000',
    costToday: 0.00,
    costMonth: 0.00,
    truthClass: 'LIVE_VERIFIED',
    pricingNote: '$0.00 (Local Metal compute on M-series unified memory)'
  },
  {
    model: 'musetalk-avatar',
    provider: 'Modal (A10G GPU)',
    department: 'Nova Avatar Test',
    inputTokens: 'N/A (Video Frames)',
    outputTokens: '840s rendered',
    totalTokens: '840s GPU',
    costToday: 6.80,
    costMonth: 44.20,
    truthClass: 'TEST',
    pricingNote: '$0.000806 / GPU sec'
  },
  {
    model: 'faster-whisper',
    provider: 'Oracle Cloud VM',
    department: 'Research Ingestion',
    inputTokens: '142m audio',
    outputTokens: 'Clean text',
    totalTokens: '142m parsed',
    costToday: 0.00,
    costMonth: 0.00,
    truthClass: 'LIVE_VERIFIED',
    pricingNote: '$0.00 (CPU benchmark active)'
  }
];

export const TOKEN_HIGHLIGHTS = {
  mostExpensiveModel: 'gpt-4o ($3.15 / day)',
  mostUsedModel: 'llama-3.1-8b (1.68M tokens / day · $0.00)',
  fastestGrowingModelCost: 'Modal GPU (+15% w/w for MuseTalk avatar test)',
  topCostDepartment: 'Creative & Marketing ($8.20 / day combined)'
};

// -----------------------------------------------------------------------------
// AUTONOMOUS UNIT ECONOMICS (Cost per Output)
// -----------------------------------------------------------------------------
export const AUTONOMOUS_UNIT_ECONOMICS: AutonomousUnitEconomicsItem[] = [
  {
    department: 'Research',
    metricLabel: 'Useful findings verified in Supabase',
    periodCost: 1.80,
    outcomeCount: 26,
    costPerOutcome: 0.069,
    formattedCostPerOutcome: '$0.069 / finding',
    truthClass: 'LIVE_VERIFIED',
    notes: '26 structured question findings verified in Supabase at $1.80 daily API cost'
  },
  {
    department: 'Creative',
    metricLabel: 'Usable visual assets & presentation decks',
    periodCost: 4.00,
    outcomeCount: 8,
    costPerOutcome: 0.50,
    formattedCostPerOutcome: '$0.50 / asset',
    truthClass: 'ESTIMATED',
    notes: 'Includes discarded test generations; 8 client-ready components delivered'
  },
  {
    department: 'Trading',
    metricLabel: 'Out-of-sample backtests & tournament fills',
    periodCost: 0.85,
    outcomeCount: 142,
    costPerOutcome: 0.006,
    formattedCostPerOutcome: '$0.006 / backtest',
    truthClass: 'LIVE_VERIFIED',
    notes: 'OANDA practice sandbox compute running historical multi-regime sweeps'
  },
  {
    department: 'Development / Labs',
    metricLabel: 'Validated capabilities & memory benchmarks',
    periodCost: 3.20,
    outcomeCount: 2,
    costPerOutcome: 1.60,
    formattedCostPerOutcome: '$1.60 / capability',
    truthClass: 'LIVE_VERIFIED',
    notes: 'Needles 10k vector profiling completed with zero memory leaks'
  },
  {
    department: 'Nova',
    metricLabel: 'Executive conversation & audio sessions',
    periodCost: 8.65,
    outcomeCount: 42,
    costPerOutcome: 0.206,
    formattedCostPerOutcome: '$0.206 / session',
    truthClass: 'TEST / NOT_PROVEN',
    notes: 'Includes Modal GPU test worker runtime for MuseTalk avatar pipeline'
  }
];

// -----------------------------------------------------------------------------
// DEPARTMENT OPERATING COSTS
// -----------------------------------------------------------------------------
export const DEPARTMENT_OPERATING_COSTS: DepartmentOperatingCostItem[] = [
  {
    department: 'Research',
    todayCost: 1.80,
    sevenDaysCost: 12.60,
    monthCost: 54.00,
    mainCostDriver: 'Search APIs & LLM verification',
    trend: 'Flat',
    trendPct: '0%',
    truthClass: 'LIVE',
    status: 'OPTIMAL'
  },
  {
    department: 'Trading',
    todayCost: 0.85,
    sevenDaysCost: 5.95,
    monthCost: 25.50,
    mainCostDriver: 'Tick data ingestion & sandbox compute',
    trend: 'Flat',
    trendPct: '0%',
    truthClass: 'LIVE',
    status: 'OPTIMAL'
  },
  {
    department: 'Marketing',
    todayCost: 4.20,
    sevenDaysCost: 29.40,
    monthCost: 126.00,
    mainCostDriver: 'LLM copy generation ($0 Ad Spend)',
    trend: 'Down',
    trendPct: '-8%',
    truthClass: 'LIVE',
    status: 'OPTIMAL'
  },
  {
    department: 'Creative',
    todayCost: 4.00,
    sevenDaysCost: 28.00,
    monthCost: 120.00,
    mainCostDriver: 'Figma tokens & vector asset gen',
    trend: 'Up',
    trendPct: '+6%',
    truthClass: 'LIVE',
    status: 'MONITORED'
  },
  {
    department: 'Finance',
    todayCost: 0.20,
    sevenDaysCost: 1.40,
    monthCost: 6.00,
    mainCostDriver: 'Audit ledger compute & tax modeling',
    trend: 'Flat',
    trendPct: '0%',
    truthClass: 'LIVE',
    status: 'OPTIMAL'
  },
  {
    department: 'Development / Labs',
    todayCost: 3.20,
    sevenDaysCost: 22.40,
    monthCost: 96.00,
    mainCostDriver: 'Kaggle GPU & isolated testing',
    trend: 'Up',
    trendPct: '+12%',
    truthClass: 'LIVE',
    status: 'EVALUATING'
  },
  {
    department: 'Upgrade Control',
    todayCost: 0.30,
    sevenDaysCost: 2.10,
    monthCost: 9.00,
    mainCostDriver: 'Canary verification & security audits',
    trend: 'Flat',
    trendPct: '0%',
    truthClass: 'LIVE',
    status: 'OPTIMAL'
  },
  {
    department: 'Systems',
    todayCost: 0.45,
    sevenDaysCost: 3.15,
    monthCost: 13.50,
    mainCostDriver: 'Launchd daemons & lease sockets',
    trend: 'Flat',
    trendPct: '0%',
    truthClass: 'LIVE',
    status: 'OPTIMAL'
  },
  {
    department: 'Nova',
    todayCost: 8.65,
    sevenDaysCost: 60.55,
    monthCost: 259.50,
    mainCostDriver: 'Modal MuseTalk GPU + ElevenLabs TTS',
    trend: 'Up',
    trendPct: '+18%',
    truthClass: 'TEST / NOT_PROVEN',
    status: 'MONITORED'
  }
];

// -----------------------------------------------------------------------------
// INFRASTRUCTURE & PLATFORM COSTS
// -----------------------------------------------------------------------------
export const INFRASTRUCTURE_COSTS: InfrastructureServiceCost[] = [
  {
    service: 'Oracle Cloud Always Free',
    category: 'Compute',
    monthlyCost: 0.00,
    formattedCost: '$0.00 / FREE TIER',
    currentUsage: '4 OCPU / 24GB RAM (Hermes VM)',
    nextBillDate: 'May 1, 2026',
    renewalDate: 'Continuous Free',
    truthClass: 'LIVE_VERIFIED',
    status: 'FREE TIER'
  },
  {
    service: 'Supabase Pro Database',
    category: 'Database',
    monthlyCost: 25.00,
    formattedCost: '$25.00 / mo',
    currentUsage: 'Universal FIFO, Canonical Store, Auth',
    nextBillDate: 'Apr 28, 2026',
    renewalDate: 'Apr 28, 2026',
    truthClass: 'LIVE',
    status: 'RENEWING SOON'
  },
  {
    service: 'Modal Serverless GPU',
    category: 'Compute',
    monthlyCost: 44.20,
    formattedCost: '$44.20 MTD',
    currentUsage: 'A10G On-Demand GPU workers',
    nextBillDate: 'May 1, 2026',
    renewalDate: 'Monthly Invoiced',
    truthClass: 'LIVE',
    status: 'ACTIVE'
  },
  {
    service: 'Netlify Edge Hosting',
    category: 'Hosting',
    monthlyCost: 20.00,
    formattedCost: '$20.00 / mo',
    currentUsage: 'Admin Center & Client Portal Preview',
    nextBillDate: 'May 5, 2026',
    renewalDate: 'May 5, 2026',
    truthClass: 'LIVE',
    status: 'ACTIVE'
  },
  {
    service: 'Cloudflare / DNS & Domains',
    category: 'DNS',
    monthlyCost: 12.50,
    formattedCost: '$12.50 / mo',
    currentUsage: 'Edge SSL, DNSSEC, goclear.io',
    nextBillDate: 'Jun 12, 2026',
    renewalDate: 'Jun 12, 2026',
    truthClass: 'LIVE',
    status: 'ACTIVE'
  },
  {
    service: 'GitHub Team & Actions',
    category: 'DevOps',
    monthlyCost: 4.00,
    formattedCost: '$4.00 / mo',
    currentUsage: 'Private repo storage & CI runners',
    nextBillDate: 'May 2, 2026',
    renewalDate: 'May 2, 2026',
    truthClass: 'LIVE',
    status: 'ACTIVE'
  }
];

// -----------------------------------------------------------------------------
// BILLS & UPCOMING COMMITMENTS
// -----------------------------------------------------------------------------
export const BILLS_COMMITMENTS: BillCommitmentItem[] = [
  {
    id: 'bill-1',
    vendor: 'Supabase Inc.',
    amount: 25.00,
    formattedAmount: '$25.00',
    dueDate: 'Apr 28, 2026',
    daysUntilDue: 6,
    isRecurring: true,
    frequency: 'Monthly',
    departmentOwner: 'Systems',
    paymentStatus: 'DUE SOON',
    approvalRequired: false
  },
  {
    id: 'bill-2',
    vendor: 'Modal Labs Inc.',
    amount: 44.20,
    formattedAmount: '$44.20',
    dueDate: 'May 1, 2026',
    daysUntilDue: 9,
    isRecurring: true,
    frequency: 'Monthly',
    departmentOwner: 'Nova',
    paymentStatus: 'DUE SOON',
    approvalRequired: false
  },
  {
    id: 'bill-3',
    vendor: 'Netlify Edge',
    amount: 20.00,
    formattedAmount: '$20.00',
    dueDate: 'May 5, 2026',
    daysUntilDue: 13,
    isRecurring: true,
    frequency: 'Monthly',
    departmentOwner: 'Systems',
    paymentStatus: 'DUE SOON',
    approvalRequired: false
  },
  {
    id: 'bill-4',
    vendor: 'OpenRouter API Pre-pay',
    amount: 50.00,
    formattedAmount: '$50.00',
    dueDate: 'May 2, 2026',
    daysUntilDue: 10,
    isRecurring: false,
    departmentOwner: 'Labs / Finance',
    paymentStatus: 'APPROVAL REQUIRED',
    approvalRequired: true,
    approvalId: 'gate-openrouter-topup'
  },
  {
    id: 'bill-5',
    vendor: 'TradingView Pro Feeds',
    amount: 59.95,
    formattedAmount: '$59.95',
    dueDate: 'May 15, 2026',
    daysUntilDue: 23,
    isRecurring: true,
    frequency: 'Monthly',
    departmentOwner: 'Trading',
    paymentStatus: 'DUE SOON',
    approvalRequired: false
  }
];

export const BILLS_SUMMARY = {
  dueNext7Days: 25.00,
  dueNext30Days: 199.15,
  overdue: 0.00,
  autoRenewingCount: 4
};

// -----------------------------------------------------------------------------
// PROVIDER BALANCES & BURN RATE
// -----------------------------------------------------------------------------
export const PROVIDER_BURNS: ProviderBurnItem[] = [
  {
    provider: 'OpenRouter',
    currentBalance: 18.50,
    formattedBalance: '$18.50',
    avgDailyBurn: 2.40,
    formattedBurn: '$2.40 / day',
    estimatedDaysRemaining: 7.7,
    status: 'LOW',
    truthClass: 'LIVE'
  },
  {
    provider: 'Modal GPU',
    currentBalance: 120.00,
    formattedBalance: '$120.00 (Credits)',
    avgDailyBurn: 6.80,
    formattedBurn: '$6.80 / day',
    estimatedDaysRemaining: 17.6,
    status: 'HEALTHY',
    truthClass: 'LIVE'
  },
  {
    provider: 'ElevenLabs',
    currentBalance: 38.20,
    formattedBalance: '$38.20',
    avgDailyBurn: 1.85,
    formattedBurn: '$1.85 / day',
    estimatedDaysRemaining: 20.6,
    status: 'HEALTHY',
    truthClass: 'LIVE'
  },
  {
    provider: 'Deepgram',
    currentBalance: 24.00,
    formattedBalance: '$24.00',
    avgDailyBurn: 0.45,
    formattedBurn: '$0.45 / day',
    estimatedDaysRemaining: 53.3,
    status: 'HEALTHY',
    truthClass: 'LIVE'
  }
];

// -----------------------------------------------------------------------------
// CAMPAIGN ECONOMICS (Ad spend strictly guarded at $0.00)
// -----------------------------------------------------------------------------
export const CAMPAIGN_ECONOMICS_DATA: CampaignEconomicsItem[] = [
  {
    id: 'camp-1',
    campaign: 'GoClear Institutional Developer Funnel',
    owner: 'Worker-Marketing-Bot',
    offer: 'Zero-Latency Settlement Sandbox API Key',
    targetAudience: 'DeFi Protocols & Fintech Treasuries',
    channel: 'Organic Technical Content & GitHub SEO',
    status: 'TEST',
    truthClass: 'PROTOTYPE',
    spend: 0.00,
    creativeCost: 48.00,
    aiCost: 24.50,
    toolingCost: 12.00,
    leads: 38,
    qualifiedLeads: 8,
    customers: 0,
    verifiedRevenue: 0.00,
    commissionRevenue: 0.00,
    cac: null,
    cpl: 2.22,
    grossProfit: -84.50,
    netProfit: -84.50,
    roiPct: null,
    currentDecision: 'CONTINUE'
  },
  {
    id: 'camp-2',
    campaign: 'Apex Capital Quant Research Outreach',
    owner: 'Worker-Marketing-Bot',
    offer: 'Forex Macro Liquidity Dislocation Alpha Whitepaper',
    targetAudience: 'Family Offices & Systematic Macro Funds',
    channel: 'Institutional Email & Substack Direct',
    status: 'PLANNING',
    truthClass: 'PROTOTYPE',
    spend: 0.00,
    creativeCost: 32.00,
    aiCost: 18.20,
    toolingCost: 0.00,
    leads: 14,
    qualifiedLeads: 4,
    customers: 0,
    verifiedRevenue: 0.00,
    commissionRevenue: 0.00,
    cac: null,
    cpl: 3.58,
    grossProfit: -50.20,
    netProfit: -50.20,
    roiPct: null,
    currentDecision: 'WAITING_RAY'
  },
  {
    id: 'camp-3',
    campaign: 'Needles Vector Memory Developer Beta',
    owner: 'Worker-Labs-01',
    offer: 'Zero-Dependency Embedded Memory CLI Package',
    targetAudience: 'AI Agent Engineers & TypeScript Devs',
    channel: 'GitHub Readme, X, Developer Discourse',
    status: 'LIVE',
    truthClass: 'LIVE_VERIFIED',
    spend: 0.00,
    creativeCost: 15.00,
    aiCost: 8.40,
    toolingCost: 0.00,
    leads: 84,
    qualifiedLeads: 22,
    customers: 0,
    verifiedRevenue: 0.00,
    commissionRevenue: 0.00,
    cac: null,
    cpl: 0.28,
    grossProfit: -23.40,
    netProfit: -23.40,
    roiPct: null,
    currentDecision: 'CONTINUE'
  }
];

// -----------------------------------------------------------------------------
// CREATIVE PRODUCTION COSTS
// -----------------------------------------------------------------------------
export const CREATIVE_PRODUCTION_COSTS: CreativeCostItem[] = [
  {
    asset: 'GoClear Customer Discovery Deck (24 slides)',
    campaign: 'GoClear Institutional',
    provider: 'Figma Tokens & Vector Synth',
    runtime: '14 mins',
    cost: 32.00,
    usable: true,
    costPerUsable: 32.00,
    truthClass: 'PROTOTYPE'
  },
  {
    asset: 'Hero Workflow Diagram Pack (6 SVGs)',
    campaign: 'GoClear Institutional',
    provider: 'SVG Renderer',
    runtime: '8 mins',
    cost: 16.00,
    usable: true,
    costPerUsable: 16.00,
    truthClass: 'PROTOTYPE'
  },
  {
    asset: 'Video Hook Script Variants (4 concepts)',
    campaign: 'Apex Capital Outreach',
    provider: 'Claude 3.5 Sonnet',
    runtime: '2 mins',
    cost: 1.80,
    usable: true,
    costPerUsable: 1.80,
    truthClass: 'LIVE'
  },
  {
    asset: 'Modal MuseTalk Video Avatar Test (15s canary)',
    campaign: 'Nova Avatar Test',
    provider: 'Modal A10G GPU',
    runtime: '45s GPU',
    cost: 4.20,
    usable: false,
    costPerUsable: 4.20,
    truthClass: 'TEST'
  }
];

// -----------------------------------------------------------------------------
// UPGRADE / INVESTMENT ECONOMICS
// -----------------------------------------------------------------------------
export const UPGRADE_INVESTMENTS: UpgradeInvestmentItem[] = [
  {
    id: 'upg-ollama',
    upgrade: 'Ollama 0.3.1 Local Quant Model Upgrade',
    sourceDepartment: 'Development / Labs',
    currentStage: 'AUDIT BY UPGRADE CONTROL',
    testCost: 0.00,
    expectedRecurringCost: 0.00,
    expectedSavings: '~$3,200.00 / mo vs Cloud LLM APIs',
    paybackRationale: 'Immediate (runs entirely on existing Mac mini Metal compute)',
    financeStatus: 'PENDING RAY',
    approvalRequired: true,
    truthClass: 'LIVE_VERIFIED'
  },
  {
    id: 'upg-needles',
    upgrade: 'Needles Embedded Vector Memory v1.2',
    sourceDepartment: 'Development / Labs',
    currentStage: 'CERTIFIED',
    testCost: 12.00,
    expectedRecurringCost: 0.00,
    expectedSavings: '$75.00 / mo vs Pinecone vector host',
    paybackRationale: 'Under 1 week payback; zero external dependency risk',
    financeStatus: 'APPROVED',
    approvalRequired: false,
    truthClass: 'LIVE_VERIFIED'
  },
  {
    id: 'upg-musetalk',
    upgrade: 'Nova Live Talking Avatar (Modal MuseTalk)',
    sourceDepartment: 'Nova Communication',
    currentStage: 'TEST SANDBOX',
    testCost: 44.20,
    expectedRecurringCost: 180.00,
    expectedSavings: '$0.00 (Pure visual presence upgrade)',
    paybackRationale: 'Executive presentation asset; voice fallback remains $0 cost',
    financeStatus: 'EVALUATING',
    approvalRequired: true,
    truthClass: 'TEST / NOT_PROVEN'
  },
  {
    id: 'upg-fix',
    upgrade: 'Trading Direct FIX Protocol Gateway Bridge',
    sourceDepartment: 'Trading Engine',
    currentStage: 'PROPOSAL',
    testCost: 45.00,
    expectedRecurringCost: 120.00,
    expectedSavings: 'Slippage reduction from 240ms to 15ms latency',
    paybackRationale: 'Reduces slippage on paper & future live trading validation',
    financeStatus: 'PENDING RAY',
    approvalRequired: true,
    truthClass: 'PROTOTYPE'
  }
];

// -----------------------------------------------------------------------------
// FINANCIAL ALERTS
// -----------------------------------------------------------------------------
export const FINANCIAL_ALERTS: FinancialAlertItem[] = [
  {
    id: 'alt-1',
    severity: 'WARNING',
    title: 'OpenRouter Balance Below Threshold',
    reason: 'Prepaid balance at $18.50 with ~$2.40/day burn (~7.7 days remaining).',
    owner: 'Finance / Labs',
    currentAction: 'Staged $50.00 top-up approval request in Approvals queue.',
    needsRay: true,
    timestamp: 'Today 08:45 AM'
  },
  {
    id: 'alt-2',
    severity: 'WARNING',
    title: 'Modal GPU Avatar Test Spend Rising',
    reason: 'Modal GPU charges up +15% w/w ($44.20 MTD) due to iterative MuseTalk avatar benchmarks.',
    owner: 'Nova / Labs',
    currentAction: 'Avatar test locked to test sandbox; production fallback remains voice-only.',
    needsRay: false,
    timestamp: 'Today 07:15 AM'
  },
  {
    id: 'alt-3',
    severity: 'CRITICAL',
    title: 'Commercial Banking Ledger Disconnected',
    reason: 'Plaid & Stripe production webhooks are not connected. Live cash position is $0.00.',
    owner: 'Finance (Clyde)',
    currentAction: 'Operating in pre-audit shadow mode; all verified figures labeled NOT CONNECTED.',
    needsRay: true,
    timestamp: 'Yesterday 04:30 PM'
  },
  {
    id: 'alt-4',
    severity: 'INFO',
    title: 'Supabase Pro Subscription Renews in 6 Days',
    reason: 'Routine monthly charge of $25.00 scheduled for April 28.',
    owner: 'Systems',
    currentAction: 'Card on file authorized; zero manual intervention required.',
    needsRay: false,
    timestamp: 'Yesterday 09:00 AM'
  }
];

// -----------------------------------------------------------------------------
// GRANTS & NON-DILUTIVE CAPITAL
// -----------------------------------------------------------------------------
export const GRANT_PIPELINE: GrantPipelineItem[] = [
  {
    id: 'grant-state-ai',
    program: 'State Non-Dilutive AI Innovation Voucher',
    amount: 85000,
    formattedAmount: '$85,000.00',
    status: 'Dossier Prepared',
    deadline: 'May 15, 2026',
    probability: '68% (Pre-scored model)',
    nextAction: 'Ray executive signature on Section 4 corporate officer declaration',
    rayApprovalState: 'Awaiting Signature',
    truthClass: 'ESTIMATED'
  },
  {
    id: 'grant-sbir-phase1',
    program: 'NSF SBIR Phase I (Autonomous AI Systems)',
    amount: 275000,
    formattedAmount: '$275,000.00',
    status: 'Drafting',
    deadline: 'Jul 2, 2026',
    probability: '34% (Historic baseline)',
    nextAction: 'Clyde compiling research bibliography & Supabase architecture evidence',
    rayApprovalState: 'Pending Review',
    truthClass: 'PROTOTYPE'
  },
  {
    id: 'grant-rd-tax',
    program: 'Federal Section 41 R&D Payroll Tax Offset',
    amount: 32000,
    formattedAmount: '$32,000.00',
    status: 'Under Review',
    deadline: 'Q3 Tax Filing',
    probability: '92% (Statutory qualification)',
    nextAction: 'Reconcile developer engineering git commits against qualified research activities',
    rayApprovalState: 'Pending Review',
    truthClass: 'ESTIMATED'
  }
];

// -----------------------------------------------------------------------------
// INVOICE LEDGER (Strict Separation of Real vs Demo)
// -----------------------------------------------------------------------------
export const INVOICE_LEDGER: InvoiceItem[] = [
  {
    id: 'INV-DEMO-0421',
    client: 'GoClear Institutional [DEMO]',
    amount: 24500,
    formattedAmount: '$24,500.00',
    status: 'Paid',
    issuedDate: 'Apr 21, 2026',
    dueDate: 'Apr 21, 2026',
    isRealProduction: false,
    truthClass: 'DEMO'
  },
  {
    id: 'INV-DEMO-0418',
    client: 'Apex Capital Opportunities [DEMO]',
    amount: 18000,
    formattedAmount: '$18,000.00',
    status: 'Paid',
    issuedDate: 'Apr 18, 2026',
    dueDate: 'Apr 18, 2026',
    isRealProduction: false,
    truthClass: 'DEMO'
  },
  {
    id: 'INV-DEMO-0415',
    client: 'Sovereign Treasury Pilot [DEMO]',
    amount: 32750,
    formattedAmount: '$32,750.00',
    status: 'Sent',
    issuedDate: 'Apr 15, 2026',
    dueDate: 'Apr 30, 2026',
    isRealProduction: false,
    truthClass: 'DEMO'
  },
  {
    id: 'INV-DEMO-0412',
    client: 'Horizon Global Clearing [DEMO]',
    amount: 15600,
    formattedAmount: '$15,600.00',
    status: 'Sent',
    issuedDate: 'Apr 12, 2026',
    dueDate: 'Apr 27, 2026',
    isRealProduction: false,
    truthClass: 'DEMO'
  },
  {
    id: 'INV-DEMO-0409',
    client: 'Vector Dynamics Tech [DEMO]',
    amount: 12400,
    formattedAmount: '$12,400.00',
    status: 'Overdue',
    issuedDate: 'Apr 9, 2026',
    dueDate: 'Apr 19, 2026',
    isRealProduction: false,
    truthClass: 'DEMO'
  }
];

export const RUNWAY_FORECAST = {
  monthlyOperatingCost: 532.50,
  monthlyVerifiedRevenue: 0.00,
  monthlyBurn: 532.50,
  runway: 'NOT PROVEN',
  truthClass: 'NOT CONNECTED' as DataTruthClass,
  note: 'Runway calculation strictly locked until live commercial banking API (Plaid) is connected.'
};

// -----------------------------------------------------------------------------
// 10. WHAT WILL FINANCE DO NEXT? (AUTONOMOUS ROADMAP & PLANNED CYCLES)
// -----------------------------------------------------------------------------
export interface FinanceNextActionItem {
  id: string;
  action: string;
  schedule: string;
  category: 'RECONCILIATION' | 'GRANT_FILING' | 'BUDGET_WATCH' | 'OPTIMIZATION' | 'AUDIT';
  target: string;
  expectedOutcome: string;
  truthClass: DataTruthClass;
  status: 'SCHEDULED' | 'IN_PROGRESS' | 'AWAITING_TRIGGER' | 'PENDING_RAY';
}

export const FINANCE_AUTONOMOUS_NEXT_ACTIONS: FinanceNextActionItem[] = [
  {
    id: 'fna-1',
    action: 'Overnight Multi-Provider Token Metering & Cost Reconciliation',
    schedule: 'Tonight @ 00:00 UTC (Autonomous Cron)',
    category: 'RECONCILIATION',
    target: 'OpenRouter, Anthropic, ElevenLabs & Modal APIs',
    expectedOutcome: 'Detect any per-call drift, flag overages, and update cost per research finding table',
    truthClass: 'LIVE_VERIFIED',
    status: 'SCHEDULED'
  },
  {
    id: 'fna-2',
    action: 'Deliver State AI Innovation Voucher Signature Packet to Ray',
    schedule: 'Awaiting Ray Approval Gate',
    category: 'GRANT_FILING',
    target: 'State Economic Development Office ($85,000 non-dilutive grant)',
    expectedOutcome: 'Formal submission within 24 hours of executive electronic signature',
    truthClass: 'ESTIMATED',
    status: 'PENDING_RAY'
  },
  {
    id: 'fna-3',
    action: 'OpenRouter Balance Watchdog & Automated Refill Trigger',
    schedule: 'Continuous Heartbeat (Every 15 mins)',
    category: 'BUDGET_WATCH',
    target: 'OpenRouter API Account (Current balance: $18.50 · Burn ~$2.40/day)',
    expectedOutcome: 'Trigger high-priority Ray notification if balance dips below $10.00 buffer',
    truthClass: 'LIVE_VERIFIED',
    status: 'IN_PROGRESS'
  },
  {
    id: 'fna-4',
    action: 'Local Ollama Metal Offload Benchmark for Creative Embeddings',
    schedule: 'Tomorrow Morning @ 09:00 AM',
    category: 'OPTIMIZATION',
    target: 'Creative Department Vector Asset Pipeline',
    expectedOutcome: 'Redirect text-embedding-3-small calls to local nomic-embed-text to cut $12.00/mo',
    truthClass: 'TEST',
    status: 'SCHEDULED'
  },
  {
    id: 'fna-5',
    action: 'Pre-Audit Supabase Pro Subscription Renewal',
    schedule: 'In 6 Days (April 28)',
    category: 'AUDIT',
    target: 'Supabase Database & Auth Service ($25.00/mo)',
    expectedOutcome: 'Verify compute & storage usage quotas remain within Pro tier limits prior to debit',
    truthClass: 'LIVE_VERIFIED',
    status: 'SCHEDULED'
  },
  {
    id: 'fna-6',
    action: 'Trading Engine Paper Portfolio Expansion Unit Economics Model',
    schedule: 'Thursday @ 14:00 UTC',
    category: 'OPTIMIZATION',
    target: 'Trading Alpha Simulation Pool (50 assets -> 200 assets)',
    expectedOutcome: 'Calculate memory & Hermes token overhead before authorizing paper expansion',
    truthClass: 'PAPER',
    status: 'AWAITING_TRIGGER'
  }
];
