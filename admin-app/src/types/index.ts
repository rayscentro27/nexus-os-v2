export type PageId =
  | 'command-center'
  | 'approvals'
  | 'projects'
  | 'research'
  | 'marketing'
  | 'campaigns'
  | 'creative'
  | 'business-hub'
  | 'finance'
  | 'trading-engine'
  | 'systems'
  | 'nova'
  | 'clients'
  | 'documents'
  | 'development-labs'
  | 'upgrade-control'
  | 'settings'
  | 'operations'
  | 'existing-business'
  | 'rea';

export type NovaState = 'idle' | 'listening' | 'thinking' | 'speaking' | 'working';

export interface NovaMessage {
  id: string;
  sender: 'user' | 'nova';
  text: string;
  timestamp: string;
  isAction?: boolean;
}

export interface MetricItem {
  id: string;
  label: string;
  value: string;
  change?: string;
  trend?: 'up' | 'down' | 'neutral';
  color?: 'blue' | 'cyan' | 'emerald' | 'amber' | 'purple' | 'red';
  icon?: string;
  subtitle?: string;
}

export interface ClientItem {
  id: string;
  name: string;
  company: string;
  tenant: string;
  plan: 'Enterprise' | 'Pro' | 'Basic';
  status: 'Active' | 'Needs Attention' | 'At Risk';
  assignedTeam: { name: string; avatar: string }[];
  progress: number;
  segment: 'Technology' | 'Financial Services' | 'Healthcare' | 'Retail & Consumer' | 'Other';
  renewalDate?: string;
  health: 'Healthy' | 'Stable' | 'Needs Attention' | 'At Risk';
}

export interface ResearchItem {
  id: string;
  title: string;
  source: 'YouTube' | 'SEO Search' | 'GitHub' | 'Grants' | 'Competitors' | 'Funding' | 'TradingView' | 'Gov Portals' | 'SEC EDGAR' | 'Primary Research';
  priority: 'High' | 'Medium' | 'Low';
  status: 'In Progress' | 'In Review' | 'Queued' | 'Completed';
  dueDate: string;
  age?: string;
  summary?: string;
}

export interface CampaignItem {
  id: string;
  title: string;
  sub: string;
  status: 'Live' | 'In Review' | 'Draft' | 'Completed';
  channel: string;
  channelIcons: string[];
  impressions: string;
  leads: string;
  convRate: string;
  roas: string;
  growth?: string;
}

export interface ApprovalItem {
  id: string;
  title: string;
  sub: string;
  category: 'Marketing' | 'Finance' | 'Documents' | 'Compliance';
  owner: { name: string; role: string; avatar: string };
  client: string;
  submitted: string;
  priority: 'High' | 'Medium' | 'Low';
  status: 'Pending' | 'In Review' | 'Approved' | 'Changes Requested';
  description?: string;
}

export interface DocumentItem {
  id: string;
  name: string;
  size: string;
  client: string;
  category: 'Marketing' | 'Creative' | 'Legal' | 'Financial' | 'Research' | 'Operations';
  status: 'Needs Review' | 'Verified' | 'Needs Signature' | 'In Review';
  uploadedDate: string;
  reviewer: { name: string; avatar: string };
  format: 'pdf' | 'docx' | 'xlsx' | 'zip' | 'fig';
}

// ==========================================
// TRADING ENGINE TYPES
// ==========================================

export type TradingEngineStatus = 'Healthy' | 'Degraded' | 'Paused' | 'Blocked';

export type TradingMode =
  | 'RESEARCH_ONLY'
  | 'BACKTEST_ONLY'
  | 'PAPER_TRADING'
  | 'LIVE_TRADING_DISABLED'
  | 'LIVE_TRADING_APPROVAL_REQUIRED';

export type KillSwitchScope = 'NONE' | 'PAUSE_SIGNALS' | 'PAUSE_PAPER_ORDERS' | 'PAUSE_ALL_ACTIONS';

export type StrategyStage =
  | 'BACKTEST'
  | 'TOURNAMENT'
  | 'RISK_REVIEW'
  | 'PAPER_TRADING'
  | 'PAUSED'
  | 'RETIRED'
  | 'IDEA'
  | 'RESEARCHING'
  | 'BACKTESTING'
  | 'ALPHA_REVIEW'
  | 'PAPER_TEST'
  | 'REVIEW_REQUIRED'
  | 'APPROVED_FOR_PAPER'
  | 'REJECTED'
  | 'ARCHIVED'
  | 'APPROVED_FOR_LIVE';

export type StrategyType =
  | 'trend following'
  | 'mean reversion'
  | 'breakout'
  | 'momentum'
  | 'volatility'
  | 'pairs/statistical'
  | 'event-driven'
  | 'macro'
  | 'sentiment-assisted'
  | 'options research'
  | 'forex research'
  | 'crypto research'
  | 'equities research';

export type AlphaDecision =
  | 'QUALIFY'
  | 'RESEARCH_MORE'
  | 'REJECT'
  | 'PAPER_TEST'
  | 'PAUSE'
  | 'NO_ACTION';

export interface StrategyVersion {
  version: string;
  date: string;
  summary: string;
  codeHash: string;
  parametersChanged: string[];
  backtestResult: {
    sharpe: number;
    winRate: number;
    profitFactor: number;
    maxDrawdown: number;
  };
  paperResult?: {
    totalPnl: string;
    trades: number;
    winRate: number;
  };
  alphaDecision: AlphaDecision;
  reasoning: string;
}

export interface StrategyProgression {
  currentStage: StrategyStage;
  stageLabel: string;
  nextGate: string;
  status: 'Advanced' | 'Waiting' | 'Rejected' | 'In Progress';
  reason: string;
  requirementForNextGate: string;
}

export interface StrategyPerformanceEvidence {
  testPeriod: string;
  tradeCount: number;
  feesAssumptions: string;
  slippageAssumptions: string;
  outOfSampleStatus: 'Passed' | 'Untested' | 'Marginal' | 'Failed';
  outOfSampleWindow: string;
  backtestReportId: string;
  inSampleSharpe: number;
  outOfSampleSharpe: number;
  sharpeDecayPct: number;
}

export interface StrategyRiskApproval {
  status: 'Approved' | 'Pending Review' | 'Rejected' | 'Not Eligible';
  reviewer?: string;
  timestamp?: string;
  policyRef: string;
  maxDrawdownLimit: string;
  maxPositionLimit: string;
  notes: string;
}

export interface StrategyItem {
  id: string;
  name: string;
  market: 'Equities' | 'Crypto' | 'Forex' | 'Futures' | 'Options' | 'Multi-Asset';
  universe: string;
  timeframe: string;
  type: StrategyType;
  stage: StrategyStage;
  nextGate?: string;
  progression?: StrategyProgression;
  performanceEvidence?: StrategyPerformanceEvidence;
  riskApproval?: StrategyRiskApproval;
  owner: { name: string; avatar: string };
  createdDate: string;
  lastTested: string;
  dataSource: string;
  alphaDecision: AlphaDecision;
  confidence: number; // 0 - 100
  evidenceQuality: 'High' | 'Medium' | 'Low' | 'Insufficient';
  riskLevel: 'Low' | 'Medium' | 'High' | 'Critical';
  currentStatus: 'Active Testing' | 'Queued' | 'Paused' | 'Pending Review' | 'Archived';
  nextAction: string;

  // Workspace details
  overview: {
    thesis: string;
    hypothesis: string;
    marketAssumptions: string[];
    entryLogic: string;
    exitLogic: string;
    stopLogic: string;
    positionSizingLogic: string;
    filters: string[];
    timeHorizon: string;
  };

  forexDetails?: {
    currencyPair: string;
    tradingSession: string;
    pipEntry: string;
    pipStop: string;
    pipTarget: string;
    spread: string;
    estimatedExecutionCosts: string;
    dataFeed: string;
    testPeriod: string;
    drawdown: string;
    riskLimit: string;
  };

  researchEvidence: {
    supportingResearch: string[];
    contradictingEvidence: string[];
    sourceLinks: { title: string; url: string; type: string }[];
    dataQuality: string;
    dateRange: string;
  };

  backtestSummary: {
    totalTrades: number;
    winRate: number;
    lossRate: number;
    profitFactor: number;
    expectancy: number;
    averageWin: number;
    averageLoss: number;
    maxDrawdown: number;
    volatility: number;
    sharpe: number;
    sortino: number;
    bestPeriod: string;
    worstPeriod: string;
    testRange: string;
    outOfSampleStatus: 'Passed' | 'Untested' | 'Marginal' | 'Failed';
  };

  robustness: {
    walkForwardTested: boolean;
    outOfSampleTested: boolean;
    parameterSensitivity: 'Robust' | 'Moderate' | 'Fragile';
    regimeSensitivity: 'Multi-Regime' | 'Bull-Only' | 'Bear-Only' | 'High-Vol Only';
    slippageAssumptions: string;
    feeAssumptions: string;
    survivorshipBiasCheck: 'Passed' | 'Warning' | 'Failed';
    lookaheadBiasCheck: 'Passed' | 'Warning' | 'Failed';
    overfittingRisk: 'Low' | 'Medium' | 'High' | 'Extreme';
  };

  alphaReview: {
    verdict: AlphaDecision;
    confidenceScore: number;
    reasoning: string;
    keyRisks: string[];
    recommendedParameters: string[];
    evaluatedAt: string;
  };

  versions: StrategyVersion[];
}

export interface PaperPosition {
  id: string;
  symbol: string;
  name: string;
  side: 'LONG' | 'SHORT';
  quantity: number;
  entryPrice: number;
  currentPrice: number;
  unrealizedPnl: number;
  unrealizedPnlPct: number;
  stopPrice: number;
  targetPrice: number;
  strategyId: string;
  strategyName: string;
  openedAt: string;
  riskAmount: number;
  isFlashed?: 'up' | 'down';
}

export interface PaperOrder {
  id: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  type: 'MARKET' | 'LIMIT' | 'STOP';
  quantity: number;
  submittedAt: string;
  filledAt?: string;
  fillPrice?: number;
  status: 'FILLED' | 'PENDING' | 'CANCELLED' | 'REJECTED';
  strategyName: string;
  reason: string;
}

export type SignalStatus =
  | 'NEW'
  | 'WATCHING'
  | 'VALIDATED'
  | 'REJECTED'
  | 'EXPIRED'
  | 'PAPER_ORDER_CREATED'
  | 'NO_ACTION';

export interface TradingSignal {
  id: string;
  strategyId: string;
  strategyName: string;
  symbol: string;
  assetClass: string;
  direction: 'LONG' | 'SHORT' | 'NEUTRAL';
  strength: 'Strong' | 'Moderate' | 'Weak';
  confidence: number;
  generatedAt: string;
  expiration: string;
  currentPrice: number;
  proposedEntry: number;
  proposedStop: number;
  proposedTarget: number;
  riskReward: string;
  evidence: string;
  status: SignalStatus;
  rationale?: string;
  riskLimitCheck?: {
    limitId: string;
    limitName: string;
    currentValue: string;
    threshold: string;
    status: 'PASSED' | 'WARNING' | 'BREACHED';
  };
  resultingPaperAction?: {
    actionType: 'ROUTED_PAPER_ORDER' | 'WAITING_VALIDATION' | 'BLOCKED_BY_RISK' | 'BLOCKED_BY_KILL_SWITCH';
    paperOrderId?: string;
    details: string;
    timestamp?: string;
  };
}

export type TournamentDecision = 'ADVANCE' | 'CONTINUE_TESTING' | 'ELIMINATE';

export interface TournamentRound {
  id: string;
  name: string;
  status: 'ACTIVE' | 'CONCLUDED' | 'UPCOMING';
  testWindow: string;
  startingCapital: number;
  marketDataSet: string;
  sharedRiskLimits: {
    maxDrawdownPct: number;
    maxRiskPerTradePct: number;
    modeledSlippageBps: number;
    executionFee: string;
  };
  totalParticipants: number;
  advancedCount: number;
  eliminatedCount: number;
  testingCount: number;
}

export interface TournamentEntry {
  id: string;
  rank: number;
  strategyId: string;
  strategyName: string;
  author: string;
  authorAvatar: string;
  market: string;
  type: string;
  division?: 'Forex' | 'Equities & Multi-Asset' | 'Crypto';
  divisionRank?: number;
  benchmarkName?: string;
  benchmarkReturnPct?: number;
  currencyPair?: string;
  tradingSession?: string;
  pipMetrics?: {
    pipGain?: number;
    maxPipDrawdown?: number;
    avgSpreadPips?: number;
  };
  returnPct: number;
  returnDollar: number;
  maxDrawdownPct: number;
  consistencyScorePct: number;
  tradeCount: number;
  estimatedCosts: number;
  sharpe: number;
  winRate: number;
  profitFactor: number;
  decision: TournamentDecision;
  decisionReason: string;
  nextGate: string;
  backtestReportId: string;
  evidenceNotes: string;
}

export interface EconomicEventItem {
  id: string;
  eventName: string;
  country: string;
  flag: string;
  timeEst: string;
  impact: 'Critical' | 'High' | 'Medium' | 'Low';
  affectedPairs: string[];
  consensus: string;
  previous: string;
  actual?: string;
  volatilityEstimate: string;
  status: 'UPCOMING' | 'ACTIVE' | 'RELEASED';
}

export interface MarketWatchItem {
  symbol: string;
  name: string;
  market: 'Equities' | 'ETFs' | 'Forex' | 'Crypto' | 'Indices' | 'Commodities' | 'Options';
  price: number;
  change24h: number;
  volume: string;
  volatility: 'Low' | 'Medium' | 'High';
  trend: 'Bullish' | 'Bearish' | 'Neutral';
  signalCount: number;
  lastSignal: string;
  dataAge: string;
  sparkline: number[];
  isFlashed?: 'up' | 'down';
}

export interface MarketIntelligenceItem {
  id: string;
  title: string;
  source: 'Nexus Research' | 'Alpha Intel' | 'Bloomberg Feeds' | 'SEC EDGAR' | 'Macro Desk';
  timestamp: string;
  category: 'Macro' | 'Earnings' | 'Regime Shift' | 'Volatility' | 'Sentiment' | 'Event-Driven';
  affectedSymbols: string[];
  confidence: number;
  materiality: 'High' | 'Medium' | 'Low';
  relatedStrategy: string;
  alphaInterpretation: string;
  recommendation: string;
}

export interface RiskLimitItem {
  id: string;
  name: string;
  currentValue: number;
  limitValue: number;
  unit: string;
  status: 'SAFE' | 'WARNING' | 'BREACH' | 'TRADING_PAUSED';
  category: 'Capital' | 'Exposure' | 'Leverage' | 'Drawdown' | 'Execution';
  description: string;
  lastBreach?: string;
}

export interface DataProviderItem {
  id: string;
  name: string;
  category: 'Market Feeds' | 'Execution Gateway' | 'Compute Engine' | 'Alternative Data';
  status: 'Operational' | 'Degraded' | 'Offline';
  latencyMs: number;
  errorRatePct: number;
  rateLimitUsedPct: number;
  lastHeartbeat: string;
  uptimePct: number;
}

export interface TradingAuditRecord {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  scope: string;
  previousState: string;
  newState: string;
  reason: string;
  governanceHash: string;
}

export interface BacktestResultRecord {
  id: string;
  strategyId: string;
  strategyName: string;
  strategyVersion: string;
  codeHash: string;
  datasetVersion: string;
  universe: string;
  dateRange: string;
  timeframe: string;
  initialCapital: number;
  feesBps: number;
  slippageBps: number;
  sizingModel: string;
  maxRiskPerTradePct: number;
  runTimestamp: string;
  runtimeMs: number;
  totalTrades: number;
  winRate: number;
  profitFactor: number;
  sharpeRatio: number;
  sortinoRatio: number;
  maxDrawdownPct: number;
  totalReturnPct: number;
  benchmarkReturnPct: number;
  equityCurve: { date: string; equity: number; benchmark: number; drawdown: number }[];
  distribution: { range: string; count: number }[];
  status: 'SUCCESS' | 'FAILED' | 'TERMINATED';
}

// ============================================================================
// BUSINESS HUB & OPERATING ARCHITECTURE TYPES
// ============================================================================

export type BusinessHubTab =
  | 'overview'
  | 'opportunities'
  | 'creation'
  | 'funding'
  | 'knowledge-banks';

export type OpportunityWorkflowState =
  | 'RESEARCH_INITIALIZATION'
  | 'ATLAS_OWNERSHIP'
  | 'BUSINESS_PLAN_BUILD'
  | 'BUSINESS_HUB_REVIEW'
  | 'FINANCE_REVIEW'
  | 'FUNDING_REVIEW'
  | 'FINAL_SYNTHESIS'
  | 'RAY_REVIEW_REQUIRED';

export interface FormalHandoffItem {
  id: string;
  from: string;
  to: string;
  project: string;
  status: 'READY FOR HANDOFF' | 'HANDED OFF' | 'IN REVIEW' | 'BLOCKED' | 'RESEARCH REQUIRED';
  nextAction: string;
  age: string;
  departmentOwner: string;
}

export interface AtlasRecommendation {
  whyThisCouldWork: string[];
  whatNexusAlreadyHas: string[];
  affiliateWhiteLabelOptions: string;
  lowestCostEntry: string;
  marketingApproach: string;
  capitalRequirement: string;
  risks: string[];
  recommendedAction: string;
}

export interface OpportunityItem {
  id: string;
  opportunity: string;
  source: string;
  researchCompleteness: number; // 0 - 100
  notebook: string;
  currentOwner: string;
  businessModel: string;
  customer: string;
  problem: string;
  revenueModel: string;
  demandEvidence: string;
  entryTier: 'Tier 1 (Fast Low-Cap)' | 'Tier 2 (Growth Medium-Cap)' | 'Tier 3 (Enterprise Scale)';
  costFreeOption: string;
  capitalRequired: string;
  businessHubReview: 'PENDING' | 'PASSED' | 'REVISIONS_REQUESTED';
  financeReview: 'PENDING' | 'CLEARED' | 'HIGH_BURN_RISK';
  fundingReview: 'PENDING' | 'SELF_FUNDABLE' | 'DEBT_SUITABLE' | 'CLYDE_REVIEW';
  currentState: OpportunityWorkflowState;
  nextAction: string;
  atlasRecommendation: AtlasRecommendation;
}

export interface BankabilityChecklistItem {
  key: string;
  label: string;
  category: 'Corporate Identity' | 'Online Presence' | 'Banking & Treasury' | 'Filings & Compliance' | 'Credit File & Tradelines' | 'Personal Credit Factor';
  status: 'VERIFIED' | 'IN_PROGRESS' | 'ACTION_REQUIRED' | 'ATTENTION_NEEDED' | 'NOT_YET_GOVERNED';
  detail: string;
  notes?: string;
  lastChecked: string;
}

export interface NAICSGovernanceProfile {
  id: string;
  entityName: string;
  currentNaics: string;
  actualPrimaryBusinessActivity: string;
  truthfullyDefensibleAlternatives: {
    code: string;
    title: string;
    defensibilityScore: number;
    fundingSuitability: string;
    description: string;
  }[];
  recommendedNaics: string;
  whyItFits: string;
  fundingImplication: string;
  complianceConcerns: string;
  classificationIntegrity: 'ACCURATE_CLASSIFICATION_FIRST' | 'NEEDS_VERIFICATION';
}

export type FundingRecommendationState =
  | 'CURRENT MATCH'
  | 'NEAR MATCH'
  | 'PATH TO ELIGIBILITY'
  | 'ALTERNATIVE PRODUCT MATCH'
  | 'NOT APPROPRIATE';

export type VerificationEvidenceStatus =
  | 'SOURCE CLAIM'
  | 'CROSS-SUPPORTED'
  | 'VERIFIED'
  | 'CONTRADICTED'
  | 'RESEARCH REQUIRED';

export interface FundingCaseItem {
  id: string;
  lane: 'CLIENT / GOCLEAR' | 'NEXUS / RAY';
  lenderProgram: string;
  product: string;
  productCategory: 'Unsecured Line' | 'SBA 7(a)' | 'Equipment Financing' | 'Merchant Advance' | 'Revolving Card' | 'Term Loan';
  potentialAmount: string;
  currentFit: FundingRecommendationState;
  requirementsMet: string[];
  requirementsMissing: string[];
  improvableRequirements: string[];
  exactNextAction: string;
  milestone: string;
  alternativeOptions: string[];
  evidenceStatus: VerificationEvidenceStatus;
  lastVerifiedDate: string;
  decisionAuthority: 'WAITING ON CLIENT' | 'WAITING ON RAY';
  recommendationNote: string;
}

export interface FundingProductBankItem {
  id: string;
  lender: string;
  product: string;
  productType: string;
  limit: string;
  creditRequirements: string;
  bureaus: string;
  timeInBusiness: string;
  revenue: string;
  bankRelationship: string;
  geographicRestrictions: string;
  documentation: string;
  pgCollateral: string;
  rateFees: string;
  verificationStatus: 'ACTIVE' | 'FLAGGED' | 'IN_REVIEW';
  evidenceStatus: VerificationEvidenceStatus;
  lastVerified: string;
  nextRefresh: string;
}

// ============================================================================
// UNIFIED NEXUS CONTROL-PLANE TYPES (AUTHORITATIVE OPERATING MODEL)
// ============================================================================

export type TruthClass =
  | 'VERIFIED'
  | 'ESTIMATED'
  | 'PROPOSED'
  | 'INFERRED'
  | 'UNKNOWN'
  | 'NOT_CONNECTED'
  | 'PAPER'
  | 'DEMO';

export type NexusWorkflowStageName =
  | 'Research'
  | 'Opportunity / Project'
  | 'Marketing'
  | 'Creative'
  | 'Commerce'
  | 'Distribution'
  | 'Metrics'
  | 'Analysis'
  | 'Next Action';

export type NexusDepartmentName =
  | 'Research'
  | 'Marketing'
  | 'Creative'
  | 'Commerce'
  | 'Distribution'
  | 'Finance'
  | 'Trading'
  | 'Systems'
  | 'Development / Labs'
  | 'Upgrade Control';

export interface NexusProjectWorkflowStep {
  stage: NexusWorkflowStageName;
  status: 'COMPLETE' | 'ACTIVE' | 'WAITING_APPROVAL' | 'BLOCKED' | 'PENDING';
  owner: string;
  summary: string;
  timestamp?: string;
}

export interface NexusProjectActivityItem {
  id: string;
  timestamp: string;
  department: NexusDepartmentName | 'Nova';
  event: string;
  truthClass: TruthClass;
}

export interface NexusProjectEvidenceItem {
  id: string;
  label: string;
  value: string;
  truthClass: TruthClass;
  source: string;
}

export interface NexusProject {
  id: string;
  name: string;
  ventureId?: string;
  opportunityId?: string;
  clientOrTrack: 'NEXUS_VENTURE' | 'CLIENT_PILOT' | 'TRADING_R1' | 'INTERNAL_INFRA';
  status: 'ACTIVE' | 'BLOCKED' | 'AWAITING_APPROVAL' | 'PAUSED' | 'COMPLETE';
  currentDepartment: NexusDepartmentName;
  stage: string;
  summary: string;
  nextAction: string;
  blocker: string | null;
  lastActivity: string;
  truthClass: TruthClass;
  workflowSteps: NexusProjectWorkflowStep[];
  linkedApprovalIds: string[];
  linkedCampaignIds: string[];
  linkedAssetIds: string[];
  linkedOfferId?: string;
  evidence: NexusProjectEvidenceItem[];
  activityLog: NexusProjectActivityItem[];
}

export type NexusApprovalType =
  | 'Creative'
  | 'Campaign publication'
  | 'Commerce go-live'
  | 'Spend'
  | 'Provider access'
  | 'Credentials'
  | 'Production changes'
  | 'Trading actions'
  | 'Other';

export type NexusApprovalStatus =
  | 'PENDING'
  | 'APPROVED'
  | 'REJECTED'
  | 'REVISION_REQUESTED';

export interface NexusApprovalPreviewFact {
  label: string;
  value: string;
  truthClass: TruthClass;
}

export interface NexusApproval {
  id: string;
  projectId: string;
  projectName: string;
  department: NexusDepartmentName;
  type: NexusApprovalType;
  status: NexusApprovalStatus;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';
  title: string;
  subtitle: string;
  reason: string;
  whatIsBeingApproved: string;
  plainEnglishExplanation: string;
  costImpact: string;
  blockedAction: string;
  nextAction: string;
  createdAt: string;
  decisionTimestamp?: string;
  decisionNote?: string;
  decisionBy?: string;
  notebookRef?: string;
  linkedEntity?: {
    kind: 'asset' | 'campaign' | 'offer' | 'strategy' | 'system' | 'experiment' | 'upgrade';
    id: string;
  };
  preview: {
    kind: 'creative' | 'campaign' | 'commerce' | 'trading' | 'system' | 'finance';
    headline: string;
    imageUrl?: string;
    body?: string;
    facts: NexusApprovalPreviewFact[];
  };
}

export interface NexusCampaign {
  id: string;
  projectId: string;
  projectName: string;
  name: string;
  stageLabel: string;
  objective: string;
  variant: string;
  hooks: string[];
  primaryCopy: string;
  channels: string[];
  channelConnectionState: 'CONNECTED' | 'NOT_CONNECTED' | 'PARTIAL';
  linkedAssetIds: string[];
  trackedUrls: { label: string; url: string; utmSource: string }[];
  approvalId?: string;
  approvalStatus: 'APPROVED' | 'AWAITING_PUBLICATION_APPROVAL' | 'REVISION_REQUESTED' | 'DRAFT';
  publicationStatus: 'NOT_PUBLISHED' | 'SCHEDULED' | 'PUBLISHED' | 'BLOCKED' | 'PAUSED';
  measurementStatus: 'AWAITING_LAUNCH' | 'NO_DATA_YET' | 'DEMO_TRACKING' | 'CONNECTED';
  resultsSummary: string;
  truthClass: TruthClass;
  estimatedBudget: string;
}

export interface NexusCommerceOffer {
  id: string;
  projectId: string;
  projectName: string;
  title: string;
  provider: string;
  externalProductId: string;
  variantId: string;
  variantSpec: string;
  productTruth: {
    baseCost: number;
    baseCostTruth: TruthClass;
    firstItemShipping: number;
    firstItemShippingTruth: TruthClass;
    additionalItemShipping: number;
    additionalShippingTruth: TruthClass;
    totalVerifiedCost: number;
    stagedPrice: number;
    stagedPriceTruth: TruthClass;
    estimatedGrossMarginDollar: number;
    estimatedGrossMarginPct: number;
    marginTruth: TruthClass;
  };
  interestTest: {
    mode: 'INTEREST CAPTURE ONLY' | 'LIVE SALES' | 'PAUSED';
    landingUrl: string;
    waitlistSignups: number | null;
    waitlistTruth: TruthClass;
    stageAApprovalId: string;
  };
  liveSales: {
    checkoutStatus: 'BLOCKED' | 'READY' | 'LIVE';
    blockerReason: string | null;
    stripeStatus: 'MISSING CREDENTIAL' | 'TEST_MODE' | 'LIVE_VERIFIED';
    stageBApprovalId: string;
  };
  claimsVsTruth: {
    claim: string;
    verification: TruthClass;
    note: string;
  }[];
}

export interface NexusResearchFinding {
  id: string;
  title: string;
  source: string;
  sourceType: 'Market Signal' | 'Fulfillment API' | 'SEO / Demand' | 'Quantitative Research' | 'Gov / Grant' | 'Competitor Audit';
  evidenceQuality: 'HIGH' | 'MEDIUM' | 'LOW';
  confidence: 'VERIFIED' | 'HIGH' | 'MODERATE' | 'EARLY';
  truthClass: TruthClass;
  recommendation: string;
  departmentDestination: NexusDepartmentName;
  whatHappensNext: string;
  linkedProjectId?: string;
  linkedProjectName?: string;
  promotedToProject: boolean;
  discoveredAt: string;
}

export type NexusNotificationType =
  | 'APPROVAL_REQUIRED'
  | 'WORK_COMPLETED'
  | 'WORK_FAILED'
  | 'PROJECT_BLOCKED'
  | 'PROJECT_CONTINUED'
  | 'CREATIVE_CREATED'
  | 'CAMPAIGN_CREATED'
  | 'COMMERCE_OFFER_CREATED';

export interface NexusNotification {
  id: string;
  type: NexusNotificationType;
  title: string;
  detail: string;
  timestamp: string;
  read: boolean;
  targetPage: PageId;
  targetEntityId?: string;
  projectId?: string;
  truthClass?: TruthClass;
}

export interface NexusCredentialState {
  id: string;
  provider: string;
  category: 'AI & Compute' | 'Commerce & Payments' | 'Marketing & Social' | 'Trading & Market Data' | 'Infrastructure & Storage';
  state: 'CONNECTED' | 'SANDBOX / PAPER' | 'MISSING CREDENTIAL' | 'NOT_CONNECTED';
  truthClass: TruthClass;
  usedBy: string[];
  impact: string;
  lastVerified: string;
}

export interface NexusLabExperiment {
  id: string;
  name: string;
  owner: string;
  environment: 'ISOLATED_SANDBOX' | 'ORACLE_EVAL' | 'MAC_MINI_LOCAL';
  hypothesis: string;
  status: 'RUNNING' | 'VALIDATED' | 'BLOCKED' | 'PROMOTED_TO_UPGRADE_CONTROL';
  benchmarkSummary: string;
  truthClass: TruthClass;
  linkedProjectId?: string;
  linkedApprovalId?: string;
  canDeployDirectly: false;
}

export interface NexusUpgradeCandidate {
  id: string;
  name: string;
  fromVersion: string;
  toVersion: string;
  targetNode: string;
  securityReview: 'PASSED' | 'PENDING' | 'FAILED';
  costImpact: string;
  rollbackPlan: string;
  status: 'HUMAN_REVIEW' | 'CERTIFIED' | 'REJECTED';
  linkedApprovalId?: string;
  truthClass: TruthClass;
}

export interface DistributedSystemNode {
  id: string;
  name: string;
  role: string;
  workloadPolicy: string;
  status: 'HEALTHY' | 'DEGRADED' | 'BLOCKED' | 'PAPER_MODE' | 'NOT_CONNECTED';
  truthClass: TruthClass;
  activeServices: string[];
  blocker?: string;
  lastChecked: string;
}


