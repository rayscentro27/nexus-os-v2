export interface NeedsRayDecisionItem {
  id: string;
  department:
    | 'Finance'
    | 'Trading'
    | 'Creative'
    | 'Development / Labs'
    | 'Systems'
    | 'Research'
    | 'Marketing'
    | 'Business Hub';
  title: string;
  subtitle: string;
  whatNexusIsAsking: string;
  plainEnglishExplanation: string;
  financialImpact: string;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'RE_ANALYSIS_REQUESTED';
  timestamp: string;
  decisionTimestamp?: string;
  decisionNote?: string;
  decisionBy?: string;
  nextAutonomousStep: string;
  urgency: 'HIGH' | 'NORMAL';
  notebookRef?: string;
  capitalAmount?: string;
}

export const INITIAL_NEEDS_RAY_DECISIONS: NeedsRayDecisionItem[] = [
  {
    id: 'dec-atlas-govcon',
    department: 'Business Hub',
    title: 'Atlas Commercial Plan Sign-Off: AI GovCon Proposal Suite',
    subtitle: 'Atlas Business Opportunities · Notebook #OPP-2026-001',
    whatNexusIsAsking: 'Authorize commercial plan buildout and downstream handoff to Finance & Clyde Funding.',
    plainEnglishExplanation: 'Atlas synthesized 14 market citations verifying $42M in small business set-asides. Business plan is complete with $0 entry tier and $15,000 required for security clearance attestation.',
    financialImpact: '+$18,500/mo projected SaaS revenue by Month 4. Initial capital requirement: $15,000.',
    riskLevel: 'LOW',
    status: 'PENDING',
    timestamp: 'Today 07:45 AM',
    nextAutonomousStep: 'Atlas transmits structured brief to Finance for unit economics validation.',
    urgency: 'HIGH',
    notebookRef: 'nb://atlas/govcon-v2.ipynb',
    capitalAmount: '$15,000'
  },
  {
    id: 'dec-clyde-revolver',
    department: 'Business Hub',
    title: 'Clyde Strategic Funding Case: First National Tech Line ($150,000)',
    subtitle: 'Clyde Funding Lane: NEXUS / RAY',
    whatNexusIsAsking: 'Authorize formal submission of Nexus commercial credit line application ($150,000 limit).',
    plainEnglishExplanation: 'Clyde completed underwriting pre-check. NAICS 541512 matched. All 4 Tier-1 tradelines verified on Experian Business file. PG required by lender; requires Ray\'s explicit personal authorization.',
    financialImpact: '+$150,000 revolving credit facility at Prime + 1.25%. Expands strategic deployment runway.',
    riskLevel: 'MEDIUM',
    status: 'PENDING',
    timestamp: 'Today 08:10 AM',
    nextAutonomousStep: 'Clyde securely formats application package and alerts Ray for e-signature submission.',
    urgency: 'HIGH',
    notebookRef: 'nb://clyde/revolver-fn-150k.ipynb',
    capitalAmount: '$150,000'
  },
  {
    id: 'dec-trading-titan-promo',
    department: 'Trading',
    title: 'Strategy Promotion Gate: Titan EUR/USD London Breakout v3.1',
    subtitle: 'Mercury Execution Engine · Alpha Research',
    whatNexusIsAsking: 'Authorize promotion from Historical Sandbox to Paper Trading execution with $10,000 risk allocation.',
    plainEnglishExplanation: 'Strategy completed 500-trade Walk-Forward backtest with 2.14 Profit Factor and 3.8% max drawdown. Live trading remains locked OFF; this enables realistic paper-order tracking on FIX harness.',
    financialImpact: 'Simulated $10,000 paper trading envelope. Live capital at risk: $0.00.',
    riskLevel: 'LOW',
    status: 'PENDING',
    timestamp: 'Today 08:25 AM',
    nextAutonomousStep: 'Mercury initiates paper-trading session on London open (03:00 EST).',
    urgency: 'HIGH',
    notebookRef: 'nb://alpha/titan-eurusd-v3.1.ipynb',
    capitalAmount: '$10,000'
  },
  {
    id: 'dec-grant-clyde',
    department: 'Finance',
    title: 'State Innovation Voucher Submission ($85,000)',
    subtitle: 'Clyde / Funding Division',
    whatNexusIsAsking: 'Submit verified $85,000 non-dilutive government technology voucher application.',
    plainEnglishExplanation: 'Clyde has prepared the 14-page state innovation grant application package with zero equity dilution. Nexus needs Ray\'s authorization to transmit the filing to the economic development agency.',
    financialImpact: '+$85,000 non-dilutive grant pipeline if awarded. Zero cash spend.',
    riskLevel: 'LOW',
    status: 'PENDING',
    timestamp: 'Today 08:30 AM',
    nextAutonomousStep: 'Nexus logs filing receipt into Supabase and monitors review status automatically.',
    urgency: 'HIGH',
    notebookRef: 'nb://clyde/state-voucher-2026.ipynb',
    capitalAmount: '$85,000'
  },
  {
    id: 'dec-openrouter-topup',
    department: 'Finance',
    title: 'OpenRouter API Pre-Fund Top-Up ($50.00)',
    subtitle: 'AI Spend Watchdog',
    whatNexusIsAsking: 'Approve $50.00 debit from reserved operating balance to top up OpenRouter balance.',
    plainEnglishExplanation: 'Current balance is $18.50 (~7.7 days remaining). Auto-topup keeps Llama 3.1-8B and Claude Sonnet workers running smoothly without unexpected API rate limit dropouts.',
    financialImpact: '-$50.00 from reserved cash budget. Extends token runway by ~21 days.',
    riskLevel: 'LOW',
    status: 'PENDING',
    timestamp: 'Today 09:15 AM',
    nextAutonomousStep: 'Nexus tops up via provider webhook and records transaction in the audit ledger.',
    urgency: 'HIGH',
    capitalAmount: '$50.00'
  },
  {
    id: 'dec-creative-prompt-deck',
    department: 'Creative',
    title: 'Creative Prompt Sign-Off: Apex Pitch Deck v2.4',
    subtitle: 'Creative Studio Deliverable',
    whatNexusIsAsking: 'Approve creative prompt revision v2.4 for customer discovery presentation.',
    plainEnglishExplanation: 'Revision v2.4 updated slide typography and customer traction graphics. Waiting for Ray\'s prompt approval before transferring the deck to Marketing for publishing.',
    financialImpact: '$0.00 cost. Advances asset status to APPROVED and unlocks Marketing distribution.',
    riskLevel: 'LOW',
    status: 'PENDING',
    timestamp: 'Today 10:40 AM',
    nextAutonomousStep: 'Nexus generates PDF & Figma web package and stages in Marketing queue.',
    urgency: 'NORMAL',
    capitalAmount: '$0.00'
  },
  {
    id: 'dec-fix-gateway',
    department: 'Trading',
    title: 'Direct FIX Gateway Test Budget ($45.00)',
    subtitle: 'Mercury Execution Engine',
    whatNexusIsAsking: 'Authorize $45.00 testing allocation for Currenex / EBS direct FIX connection latency trial.',
    plainEnglishExplanation: 'Alpha research discovered a 14ms latency reduction opportunity for the London-NY breakout model. Nexus requires your approval to provision test gateway credentials.',
    financialImpact: '-$45.00 one-time test expense. Live trading remains locked strictly OFF.',
    riskLevel: 'LOW',
    status: 'PENDING',
    timestamp: 'Today 11:05 AM',
    nextAutonomousStep: 'Nexus spins up sandbox FIX harness and benchmarks execution round-trip.',
    urgency: 'NORMAL',
    capitalAmount: '$45.00'
  },
  {
    id: 'dec-needles-release',
    department: 'Development / Labs',
    title: 'Needles v1.2 Memory Profiler Release Sign-Off',
    subtitle: 'Isolated Sandbox -> Upgrade Control',
    whatNexusIsAsking: 'Approve transfer of Needles v1.2 candidate to Upgrade Control certification gate.',
    plainEnglishExplanation: 'Needles passed 24-hour continuous load test with 38ms latency and zero memory leaks. Architectural rule requires Ray sign-off before leaving isolated sandbox.',
    financialImpact: 'Zero production risk (goes to Upgrade Control for review, does NOT deploy directly).',
    riskLevel: 'LOW',
    status: 'PENDING',
    timestamp: 'Today 12:20 PM',
    nextAutonomousStep: 'Upgrade Control receives package manifest and executes compatibility audits.',
    urgency: 'NORMAL',
    capitalAmount: '$0.00'
  },
  {
    id: 'dec-goclear-portal-prod',
    department: 'Systems',
    title: 'GoClear Client Portal v1.0 Pilot Release Gate',
    subtitle: 'Systems Infrastructure',
    whatNexusIsAsking: 'Authorize GoClear institutional client portal production edge deployment.',
    plainEnglishExplanation: 'All 14 row-level security tests passed. Tenant isolation verified. Nexus requires your final go-ahead to open live invite links for pilot partners.',
    financialImpact: 'Activates client invitation links and tenant onboarding telemetry.',
    riskLevel: 'MEDIUM',
    status: 'PENDING',
    timestamp: 'Today 01:15 PM',
    nextAutonomousStep: 'Systems points production DNS record to verified edge release.',
    urgency: 'HIGH',
    capitalAmount: '$0.00'
  }
];
