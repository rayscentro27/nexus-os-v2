import {
  StrategyItem,
  PaperPosition,
  PaperOrder,
  TradingSignal,
  MarketWatchItem,
  MarketIntelligenceItem,
  RiskLimitItem,
  DataProviderItem,
  TradingAuditRecord,
  BacktestResultRecord,
  TradingMode,
  TradingEngineStatus,
  TournamentRound,
  TournamentEntry,
  EconomicEventItem
} from '../types';

export const INITIAL_TRADING_STATUS = {
  status: 'Degraded' as TradingEngineStatus, // Reflects the 1 degraded feed (Binance L3)
  mode: 'PAPER_TRADING' as TradingMode,
  modeChangedBy: 'Alex Chen (Principal Quantitative Architect)',
  modeChangedAt: 'Today, 08:30:14 EST',
  modeChangeReason: 'Scheduled walk-forward paper evaluation cycle #14 for Volatility Breakout & Pairs models',
  approvalStatus: 'Dual Governance Sign-off (Ref #GOV-8821)',
  riskPolicy: 'RP-2026.4: Standard Multi-Asset Quantitative Risk Limits (Max DD 4.0%)',
  allowedProviders: ['OANDA Practice API (v20 Deterministic Paper)', 'Polygon.io Pro', 'TradingView Feed'],
  allowedAccounts: ['OANDA Practice Sandbox Account Only (Live Trading Strictly Disabled)'],
  marketsOpenCount: 4,
  marketsTotalCount: 5,
  activeStrategiesCount: 8,
  strategiesUnderReviewCount: 3,
  activePaperPositionsCount: 5,
  openSignalsCount: 6,
  pendingApprovalsCount: 2,
  
  // System Feeds vs Workers Separation
  dataProviderStatus: '3/4 Operational · 1 Degraded (Binance L3 Latency 142ms)',
  feedHealthStatus: 'Degraded (1 Feed Alert)',
  feedAlerts: ['Binance Microstructure L3 Feed: Latency spike to 142ms (> 50ms SLA) · Packet retransmit 1.8%'],
  workerHealthStatus: '4/4 Workers Operational (Normal)',
  workerFleetSummary: 'Compute-A100 (Active) · Alpaca-Paper-Gateway (Active) · Risk-Guard-Engine (Active) · Tick-Stream-Ingest (Active)',
  
  // Kill Switch state & explanation
  killSwitchState: 'DISENGAGED',
  killSwitchScope: 'NONE',
  killSwitchExplanation: 'Kill Switch is currently DISENGAGED (Normal Operations). When engaged, it selectively pauses inbound signal ingestion, halts simulated paper order routing, or freezes all simulation loops while preserving historical audit trails.',
  
  lastTradingCycle: 'Cycle #284,102 (12 seconds ago)',
  lastMarketRefresh: '1.4s ago',
  estimatedDailyComputeCost: '$16.42 / day (GPU + API Quota)'
};

export const INITIAL_STRATEGIES: StrategyItem[] = [
  {
    id: 'strat-r1-wick',
    name: 'Wick Sequence Breakout v1 (R1 Core)',
    market: 'Forex',
    universe: 'EUR_USD · H1 Deterministic Core',
    timeframe: 'H1',
    type: 'breakout',
    stage: 'PAPER_TRADING',
    nextGate: 'Continuous OANDA Practice Paper Reconciliation (Live Trading Locked OFF)',
    progression: {
      currentStage: 'PAPER_TRADING',
      stageLabel: 'R1 Certified Paper Core (OANDA Practice)',
      nextGate: 'Ongoing R1 Deterministic Parity Checks',
      status: 'Advanced',
      reason: 'Primary R1 certified Forex strategy on EUR_USD H1 executing deterministic wick rejection + breakout confirmation.',
      requirementForNextGate: 'Maintain < 0.8 pip slippage tolerance and 100% receipt reconciliation in OANDA Practice.'
    },
    performanceEvidence: {
      testPeriod: 'Jan 2021 - Nov 2026 (5.8 Years)',
      tradeCount: 914,
      feesAssumptions: 'OANDA core spread + $0 commission equivalent',
      slippageAssumptions: '0.6 pips per leg modeled',
      outOfSampleStatus: 'Passed',
      outOfSampleWindow: 'Jan 2025 - Nov 2026 (Walk-Forward OOS)',
      backtestReportId: 'bt-run-7412',
      inSampleSharpe: 1.98,
      outOfSampleSharpe: 1.91,
      sharpeDecayPct: 3.5
    },
    riskApproval: {
      status: 'Approved',
      reviewer: 'Risk Guardrail Engine (R1 Cert)',
      timestamp: 'Today, 07:00 EST',
      policyRef: 'RP-2026.4 §R1-FX (Max 0.75% Risk / Trade)',
      maxDrawdownLimit: '4.0% Peak Equity',
      maxPositionLimit: '100,000 units EUR_USD (Paper)',
      notes: 'Deterministic OANDA Practice paper execution only. Live broker routing strictly disabled.'
    },
    owner: { name: 'Elena Rostova', avatar: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150&auto=format&fit=crop&q=80' },
    createdDate: '2026-08-01',
    lastTested: '9m ago (Reconciled)',
    dataSource: 'OANDA Practice v20 H1 Candles',
    alphaDecision: 'PAPER_TEST',
    confidence: 92,
    evidenceQuality: 'High',
    riskLevel: 'Low',
    currentStatus: 'Active Testing',
    nextAction: 'Continue deterministic H1 candle reconciliation and monitor FIX optional budget gate.',
    overview: {
      thesis: 'Consecutive opposing H1 rejection wicks inside London/NY overlap reliably precede asymmetric EUR_USD H1 structural breakouts.',
      hypothesis: 'When 2+ consecutive H1 candles show >= 55% wick-to-range exhaustion followed by an impulsive close beyond range high/low, continuation reaches >= 2.1R.',
      marketAssumptions: [
        'EUR_USD bid/ask spread <= 1.2 pips during London/NY session',
        'No FOMC/ECB high-impact announcement within 30m buffer',
        'Deterministic OANDA Practice execution parity'
      ],
      entryLogic: 'Enter Market/Stop on H1 close outside multi-bar wick cluster with ATR(14) regime filter active.',
      exitLogic: 'Scale 50% at 1.5R; trail remaining 50% at 1.4x ATR(14) behind H1 swings.',
      stopLogic: 'Hard bracket stop placed beyond signal wick extreme (max 0.75% paper equity risk).',
      positionSizingLogic: 'Deterministic ATR risk-normalized lot sizing against OANDA Practice NAV.',
      filters: ['Session: 07:00–17:00 UTC', 'Spread Gate <= 1.2 pips', 'Daily DD Circuit Breaker < 1.5%'],
      timeHorizon: 'H1 Intraday Swing (4 to 24 hours)'
    },
    researchEvidence: {
      supportingResearch: [
        'Nexus R1 FX Dossier: "EUR_USD H1 Wick Sequence Exhaustion Study (2021-2026)"',
        'OANDA Practice deterministic execution parity audit (0 orphan fills)'
      ],
      contradictingEvidence: [
        'Reduced win rate during August low-liquidity holiday compression weeks'
      ],
      sourceLinks: [
        { title: 'R1 Deterministic Manifest', url: '#', type: 'Internal Document' }
      ],
      dataQuality: 'High (OANDA v20 H1 reconciled)',
      dateRange: '2021-01-01 to 2026-11-15'
    },
    backtestSummary: {
      totalTrades: 914,
      winRate: 58.6,
      lossRate: 41.4,
      profitFactor: 1.94,
      expectancy: 0.42,
      averageWin: 640,
      averageLoss: 390,
      maxDrawdown: 2.15,
      volatility: 6.8,
      sharpe: 1.91,
      sortino: 2.74,
      bestPeriod: '+11.2% (Q1 2026)',
      worstPeriod: '-1.3% (Aug 2025)',
      testRange: 'Jan 2021 - Nov 2026',
      outOfSampleStatus: 'Passed'
    },
    robustness: {
      walkForwardTested: true,
      outOfSampleTested: true,
      parameterSensitivity: 'Robust',
      regimeSensitivity: 'Multi-Regime',
      slippageAssumptions: '0.6 pips modeled',
      feeAssumptions: 'OANDA Practice core spread',
      survivorshipBiasCheck: 'Passed',
      lookaheadBiasCheck: 'Passed',
      overfittingRisk: 'Low'
    },
    alphaReview: {
      verdict: 'PAPER_TEST',
      confidenceScore: 92,
      reasoning: 'Deterministic EUR_USD H1 wick exhaustion breakout validated across London/NY overlap sessions with 2.15% max drawdown and 0 orphan fills against OANDA Practice.',
      keyRisks: ['Spread widening > 3.0 pips during CPI/NFP news releases', 'August low-liquidity session chop'],
      recommendedParameters: ['Spread gate <= 1.2 pips', '30m FOMC/ECB news buffer'],
      evaluatedAt: '2026-11-15T07:00:00Z'
    },
    versions: [
      {
        version: 'v1.0',
        date: '2026-11-15',
        summary: 'Deterministic R1 Core release with OANDA Practice reconciliation & paper risk guardrails',
        codeHash: 'r1-wick-8e4c2a',
        parametersChanged: ['max_risk_per_trade_pct: 0.75', 'spread_gate_pips: 1.2'],
        backtestResult: { sharpe: 1.91, winRate: 58.6, profitFactor: 1.94, maxDrawdown: 2.15 },
        paperResult: { totalPnl: '+$1,840 (Paper)', trades: 28, winRate: 60.7 },
        alphaDecision: 'PAPER_TEST',
        reasoning: 'Continuous deterministic OANDA Practice paper baseline.'
      }
    ]
  },
  {
    id: 'strat-vol-01',
    name: 'Volatility Expansion Matrix (VEM-4)',
    market: 'Equities',
    universe: 'S&P 500 Large Caps + QQQ Components',
    timeframe: '15m / 1h Hybrid',
    type: 'volatility',
    stage: 'PAPER_TRADING',
    nextGate: 'Performance Review (Accumulate 50 paper fills before live governance review)',
    progression: {
      currentStage: 'PAPER_TRADING',
      stageLabel: 'Paper Trading Sandbox',
      nextGate: 'Governance Review (50 Paper Fills Required)',
      status: 'Advanced',
      reason: 'Won Tournament Round 4 (Rank #1) with 2.14 Sharpe; passed Risk Review approval by Dr. Marcus Vance with 1.0% trade risk cap.',
      requirementForNextGate: 'Execute 50 simulated fills in paper sandbox with real-world slippage tracking within 2.0 bps benchmark.'
    },
    performanceEvidence: {
      testPeriod: 'Jan 2020 - Dec 2025 (5 Years)',
      tradeCount: 1482,
      feesAssumptions: '$0.005 / share IBKR tiered equivalent',
      slippageAssumptions: '1.5 bps per side modeled',
      outOfSampleStatus: 'Passed',
      outOfSampleWindow: 'Jan 2025 - Dec 2025 (Walk-Forward OOS)',
      backtestReportId: 'bt-run-7412',
      inSampleSharpe: 2.22,
      outOfSampleSharpe: 2.14,
      sharpeDecayPct: 3.6
    },
    riskApproval: {
      status: 'Approved',
      reviewer: 'Dr. Marcus Vance (Risk Director)',
      timestamp: '2026-09-24 16:45 EST',
      policyRef: 'RP-2026.4 §4.2 (Volatility Breakout Exposure)',
      maxDrawdownLimit: '4.0% Peak Equity',
      maxPositionLimit: '$100,000 Simulated Capital',
      notes: 'Approved for Paper Trading Sandbox only. Dual governance sign-off recorded. Live trading disabled.'
    },
    owner: { name: 'Elena Rostova', avatar: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150&auto=format&fit=crop&q=80' },
    createdDate: '2026-06-12',
    lastTested: 'Today, 07:15 EST',
    dataSource: 'Polygon.io 15m Aggs + CBOE Volatility Surface',
    alphaDecision: 'PAPER_TEST',
    confidence: 88,
    evidenceQuality: 'High',
    riskLevel: 'Medium',
    currentStatus: 'Active Testing',
    nextAction: 'Accumulate 20 paper fills to measure real slippage vs benchmark',
    overview: {
      thesis: 'Implied volatility squeezes preceded by historical ATR compression reliably expand into asymmetric 2.5R directional legs.',
      hypothesis: 'When Bollinger Band width contracts below the 10th percentile over 60 bars and Keltner channels breach on 2x volume, post-breakout continuation sustains > 68% expectancy.',
      marketAssumptions: [
        'Regime stability: VIX between 14.5 and 28.0',
        'Bid-ask spreads on target universe < 0.03%',
        'No impending Fed rate announcements within 90 minutes of signal trigger'
      ],
      entryLogic: 'Enter Long/Short upon confirmed 15m candle close outside Keltner Channel with volume > 200% 20-period moving average.',
      exitLogic: 'Trailing stop pegged at 2.2x ATR(14) or time-stop at bar 18 if unrealized profit < 0.5R.',
      stopLogic: 'Initial stop at opposite Keltner channel midline or max 1.25% equity risk per trade.',
      positionSizingLogic: 'Volatility-adjusted fixed fractional risk (1.0% portfolio risk per trade, inverted against instrument ATR).',
      filters: ['RSI(14) between 45 and 65 prior to trigger (no exhaustion)', 'Regime Filter: 200 SMA slope > 0 for longs'],
      timeHorizon: 'Intraday to Swing (2 to 28 hours)'
    },
    researchEvidence: {
      supportingResearch: [
        'Academic paper: "Asymmetric Volatility Expansion in US Equities" (Journal of Financial Economics, 2024)',
        'Nexus Research internal report: "Empirical Keltner Bandwidth Compression Dynamics across 10 years of Tick Data"'
      ],
      contradictingEvidence: [
        'Degradation observed during severe zero-day-to-expiry (0DTE) option roll hours (14:30 - 15:30 EST)',
        'Higher slippage on small-cap Russell 2000 components during low-liquidity noon sessions'
      ],
      sourceLinks: [
        { title: 'Nexus Quant Memo #412', url: '#', type: 'Internal Document' },
        { title: 'CBOE Historical Surface Archive', url: '#', type: 'External Dataset' }
      ],
      dataQuality: 'High (Tick-level cleaned, dividend adjusted, corporate action sanitized)',
      dateRange: '2019-01-01 to 2026-08-31 (7+ years)'
    },
    backtestSummary: {
      totalTrades: 1482,
      winRate: 61.4,
      lossRate: 38.6,
      profitFactor: 2.18,
      expectancy: 1.42,
      averageWin: 1240,
      averageLoss: 620,
      maxDrawdown: 3.84,
      volatility: 11.2,
      sharpe: 2.14,
      sortino: 3.05,
      bestPeriod: '+18.4% (Q1 2025)',
      worstPeriod: '-2.1% (August 2024)',
      testRange: 'Jan 2020 - Dec 2025',
      outOfSampleStatus: 'Passed'
    },
    robustness: {
      walkForwardTested: true,
      outOfSampleTested: true,
      parameterSensitivity: 'Robust',
      regimeSensitivity: 'Multi-Regime',
      slippageAssumptions: '1.5 bps per side modeled',
      feeAssumptions: '$0.005 / share IBKR tiered equivalent',
      survivorshipBiasCheck: 'Passed',
      lookaheadBiasCheck: 'Passed',
      overfittingRisk: 'Low'
    },
    alphaReview: {
      verdict: 'PAPER_TEST',
      confidenceScore: 89,
      reasoning: 'Alpha stresses this model across 3 interest-rate regimes. Statistical significance is p < 0.001 over 1,482 trades. Slippage drag is negligible on mega-caps. Recommended for paper testing with 1.0% risk cap.',
      keyRisks: ['0DTE volatility spikes between 14:00-15:30 EST', 'Sudden sector rotation whipsaws'],
      recommendedParameters: ['Tighten Keltner multiplier from 2.0 to 2.15', 'Enforce hard flat position before FOMC statements'],
      evaluatedAt: '2026-09-24T14:32:00Z'
    },
    versions: [
      {
        version: 'v3.2',
        date: '2026-09-22',
        summary: 'Incorporated dynamic ATR trailing stop and filtered 0DTE late afternoon sessions',
        codeHash: 'git-a4f910c',
        parametersChanged: ['atr_multiplier: 2.2 -> 2.15', 'fomc_buffer_mins: 90'],
        backtestResult: { sharpe: 2.14, winRate: 61.4, profitFactor: 2.18, maxDrawdown: 3.84 },
        paperResult: { totalPnl: '+$14,200 (Paper)', trades: 18, winRate: 66.7 },
        alphaDecision: 'PAPER_TEST',
        reasoning: 'Reduced drawdown by 40 bps while preserving positive drift.'
      }
    ]
  },
  {
    id: 'strat-pairs-02',
    name: 'Stat-Arb Cointegration Pairs (SACP-X)',
    market: 'Equities',
    universe: 'Semiconductor ETF (SMH) vs Top 5 Components',
    timeframe: '5m / 30m',
    type: 'pairs/statistical',
    stage: 'RISK_REVIEW',
    nextGate: 'Paper Trading Approval (Dual risk review by Dr. Marcus Vance & Alex Chen)',
    progression: {
      currentStage: 'RISK_REVIEW',
      stageLabel: 'Risk Review Gate',
      nextGate: 'Paper Trading Approval',
      status: 'Waiting',
      reason: 'Advanced from Tournament Round 4 (Rank #2, Sharpe 2.45, DD 2.15%). Currently awaiting risk committee sign-off on borrow fee assumptions and overnight gap hedges.',
      requirementForNextGate: 'Risk Director review of Kalman filter hedge ratio bounds and single-name short borrow cost ceiling.'
    },
    performanceEvidence: {
      testPeriod: '2022-01 to 2026-06 (4.5 Years)',
      tradeCount: 2140,
      feesAssumptions: 'Standard institutional prime rate ($0.0035/sh)',
      slippageAssumptions: '1.0 bps per leg modeled',
      outOfSampleStatus: 'Passed',
      outOfSampleWindow: '2025-07 to 2026-06 (12 Months OOS)',
      backtestReportId: 'bt-run-7411',
      inSampleSharpe: 2.52,
      outOfSampleSharpe: 2.45,
      sharpeDecayPct: 2.8
    },
    riskApproval: {
      status: 'Pending Review',
      reviewer: 'Dr. Marcus Vance (Risk Director)',
      timestamp: 'Awaiting scheduled review (Today 14:00 EST)',
      policyRef: 'RP-2026.4 §3.1 (Statistical Arbitrage Pairs)',
      maxDrawdownLimit: '3.0% Peak Equity',
      maxPositionLimit: '$150,000 Gross Notional',
      notes: 'Under active risk evaluation. Beta-neutral hedge ratio validated via Kalman filter.'
    },
    owner: { name: 'Dr. Marcus Vance', avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80' },
    createdDate: '2026-05-18',
    lastTested: 'Today, 06:40 EST',
    dataSource: 'FactSet L2 Orderbook + Tick Stream',
    alphaDecision: 'QUALIFY',
    confidence: 92,
    evidenceQuality: 'High',
    riskLevel: 'Low',
    currentStatus: 'Pending Review',
    nextAction: 'Authorize initial allocation on paper trading gateway following risk sign-off',
    overview: {
      thesis: 'Johansen cointegrated semiconductor clusters show mean-reverting residual spreads with half-life < 140 minutes.',
      hypothesis: 'When residual spread z-score deviates by > 2.3 standard deviations from rolling 30-day Kalman filter mean, regression to mean occurs with 74% empirical certainty.',
      marketAssumptions: [
        'Borrow rate for short leg < 1.2% annualized',
        'Both legs remain cointegrated with Engle-Granger p-value < 0.01',
        'No earnings announcement scheduled within 48 hours for either leg'
      ],
      entryLogic: 'Simultaneous market order pairs execution when Z-Score > 2.3 or Z-Score < -2.3 with zero autocorrelation of residuals.',
      exitLogic: 'Exit both legs when Z-Score crosses zero or reaches 0.2 sigma.',
      stopLogic: 'Hard stop at Z-Score deviation of 3.8 sigma or adverse spread expansion of 2.5%.',
      positionSizingLogic: 'Dollar-neutral beta-weighted ratio determined by rolling hedge ratio calculation.',
      filters: ['Johansen Trace Statistic > 95% critical value', 'Spread volume > 10,000 shares/min'],
      timeHorizon: 'Intraday (30 minutes to 4 hours)'
    },
    researchEvidence: {
      supportingResearch: [
        'Johansen cointegration matrix validation on 4 years of clean trade-and-quote data',
        'Stationarity confirmed via Augmented Dickey-Fuller (ADF) test (t = -4.82, p < 0.001)'
      ],
      contradictingEvidence: [
        'Spread diverges persistently during major semiconductor export policy announcements or supply chain sanctions'
      ],
      sourceLinks: [{ title: 'Pairs Research Notebook #89', url: '#', type: 'Jupyter Research' }],
      dataQuality: 'High',
      dateRange: '2021-01-01 to 2026-08-01'
    },
    backtestSummary: {
      totalTrades: 2140,
      winRate: 72.8,
      lossRate: 27.2,
      profitFactor: 2.65,
      expectancy: 1.88,
      averageWin: 850,
      averageLoss: 490,
      maxDrawdown: 2.15,
      volatility: 8.4,
      sharpe: 2.45,
      sortino: 3.82,
      bestPeriod: '+24.1% (Q4 2025)',
      worstPeriod: '-1.4% (April 2024)',
      testRange: '2022 - 2026',
      outOfSampleStatus: 'Passed'
    },
    robustness: {
      walkForwardTested: true,
      outOfSampleTested: true,
      parameterSensitivity: 'Robust',
      regimeSensitivity: 'Multi-Regime',
      slippageAssumptions: '1.0 bps per leg',
      feeAssumptions: 'Standard institutional prime rate',
      survivorshipBiasCheck: 'Passed',
      lookaheadBiasCheck: 'Passed',
      overfittingRisk: 'Low'
    },
    alphaReview: {
      verdict: 'QUALIFY',
      confidenceScore: 94,
      reasoning: 'Exemplary mathematical soundness. Stationary residuals with rapid half-life. Alpha approves for paper deployment with up to $200k simulated buying power.',
      keyRisks: ['Structural break in cointegration due to M&A or radical tech divergence'],
      recommendedParameters: ['Retain Kalman dynamic filter instead of static OLS regression'],
      evaluatedAt: '2026-09-23T11:00:00Z'
    },
    versions: [
      {
        version: 'v2.1',
        date: '2026-09-15',
        summary: 'Replaced OLS regression with Kalman filter for dynamic hedge ratio adaptation',
        codeHash: 'git-b8921df',
        parametersChanged: ['model: kalman_filter_v2', 'z_threshold: 2.3'],
        backtestResult: { sharpe: 2.45, winRate: 72.8, profitFactor: 2.65, maxDrawdown: 2.15 },
        paperResult: { totalPnl: '+$9,840 (Paper)', trades: 14, winRate: 78.5 },
        alphaDecision: 'QUALIFY',
        reasoning: 'Smooth tracking of beta drift during market rallies.'
      }
    ]
  },
  {
    id: 'strat-crypto-03',
    name: 'Orderflow Microstructure Reversion (OMR-B)',
    market: 'Crypto',
    universe: 'BTC/USDT, ETH/USDT, SOL/USDT',
    timeframe: '1m / 5m',
    type: 'mean reversion',
    stage: 'TOURNAMENT',
    nextGate: 'Tournament Round 4 Qualification (Needs 115 more OOS trades + latency audit)',
    progression: {
      currentStage: 'TOURNAMENT',
      stageLabel: 'Trading Tournament (Round 4)',
      nextGate: 'Risk Review (Pending Tournament Finish)',
      status: 'In Progress',
      reason: 'Sample size deficit & feed latency: strong Sharpe (2.28) but held back from advancing by insufficient sample size (185/300 required OOS trades) and Binance feed latency sensitivity.',
      requirementForNextGate: 'Accumulate 115 additional verified trades under normalized exchange API latency (< 45ms).'
    },
    performanceEvidence: {
      testPeriod: '2024-01 to 2026-09 (2.7 Years)',
      tradeCount: 3410,
      feesAssumptions: 'Maker 0.02% / Taker 0.04%',
      slippageAssumptions: '4.0 bps conservative fill assumption',
      outOfSampleStatus: 'Marginal',
      outOfSampleWindow: 'June 2026 - Sept 2026 (185 trades recorded)',
      backtestReportId: 'bt-run-7410',
      inSampleSharpe: 2.40,
      outOfSampleSharpe: 2.28,
      sharpeDecayPct: 5.0
    },
    riskApproval: {
      status: 'Pending Review',
      policyRef: 'RP-2026.4 §5.0 (Crypto Microstructure Volatility)',
      maxDrawdownLimit: '4.0% Peak Equity',
      maxPositionLimit: '$50,000 Simulated Capital',
      notes: 'Restricted from Paper Trading until out-of-sample trade quota reaches 300 trades.'
    },
    owner: { name: 'Siddharth Rao', avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80' },
    createdDate: '2026-07-01',
    lastTested: 'Today, 08:28 EST',
    dataSource: 'Binance / Coinbase L3 WebSocket Feeds',
    alphaDecision: 'PAPER_TEST',
    confidence: 84,
    evidenceQuality: 'Medium',
    riskLevel: 'Medium',
    currentStatus: 'Active Testing',
    nextAction: 'Monitor execution latency during US market open volatility; need 115 more trades to qualify',
    overview: {
      thesis: 'Cascading liquidations create momentary orderbook voids that mean-revert as institutional market makers restore depth.',
      hypothesis: 'Cumulative Volume Delta (CVD) divergence exceeding 3.5 standard deviations accompanied by open interest flush yields a sharp 0.8% - 1.6% rebound within 15 minutes.',
      marketAssumptions: [
        'Exchange API latency remains under 45ms',
        'Funding rate within +/- 0.05% per 8h',
        'No major regulatory or stablecoin de-peg headlines active'
      ],
      entryLogic: 'Execute limit order inside orderbook bid/ask when CVD divergence confirms exhaustion following a 50M+ liquidation cascade.',
      exitLogic: 'Scale out 50% at 0.75% profit, trail remainder with VWAP benchmark.',
      stopLogic: 'Hard stop at previous liquidation low minus 0.35%.',
      positionSizingLogic: 'Strict 0.75% portfolio risk per trade.',
      filters: ['Funding rate neutral check', 'Binance + Coinbase depth correlation > 0.85'],
      timeHorizon: 'Micro-Scalp (5 to 45 minutes)'
    },
    researchEvidence: {
      supportingResearch: ['Historical tick liquidation archives across 2024-2026 show 81% bounce rate post-exhaustion'],
      contradictingEvidence: ['Extreme systemic selloffs can cascade through multiple depth levels, causing slippage'],
      sourceLinks: [{ title: 'Crypto Liquidation Mechanics Memo', url: '#', type: 'Internal Research' }],
      dataQuality: 'High',
      dateRange: '2024-01-01 to 2026-09-01'
    },
    backtestSummary: {
      totalTrades: 3410,
      winRate: 67.2,
      lossRate: 32.8,
      profitFactor: 2.28,
      expectancy: 1.55,
      averageWin: 640,
      averageLoss: 380,
      maxDrawdown: 4.12,
      volatility: 14.8,
      sharpe: 2.28,
      sortino: 3.40,
      bestPeriod: '+31.2% (Nov 2025)',
      worstPeriod: '-3.8% (March 2025)',
      testRange: '2024 - 2026',
      outOfSampleStatus: 'Passed'
    },
    robustness: {
      walkForwardTested: true,
      outOfSampleTested: true,
      parameterSensitivity: 'Moderate',
      regimeSensitivity: 'High-Vol Only',
      slippageAssumptions: '4 bps conservative fill assumption',
      feeAssumptions: 'Maker 0.02% / Taker 0.04%',
      survivorshipBiasCheck: 'Passed',
      lookaheadBiasCheck: 'Passed',
      overfittingRisk: 'Medium'
    },
    alphaReview: {
      verdict: 'PAPER_TEST',
      confidenceScore: 85,
      reasoning: 'Strong short-term edge supported by microstructure reality. Alpha requires passive limit orders to avoid adverse taker fee drag. Approved for paper test.',
      keyRisks: ['Slippage in rapid liquidation spirals', 'Exchange API rate limit throttle'],
      recommendedParameters: ['Enforce max 2 concurrent crypto positions'],
      evaluatedAt: '2026-09-25T18:10:00Z'
    },
    versions: [
      {
        version: 'v1.4',
        date: '2026-09-18',
        summary: 'Added passive post-only execution engine to eliminate taker fee penalties',
        codeHash: 'git-c901e4a',
        parametersChanged: ['order_type: post_only_limit', 'max_slippage: 3_bps'],
        backtestResult: { sharpe: 2.28, winRate: 67.2, profitFactor: 2.28, maxDrawdown: 4.12 },
        paperResult: { totalPnl: '+$6,450 (Paper)', trades: 22, winRate: 68.2 },
        alphaDecision: 'PAPER_TEST',
        reasoning: 'Taker fees were previously eroding 18% of net profit; post-only fixes this.'
      }
    ]
  },
  {
    id: 'strat-mom-04',
    name: 'Cross-Asset Momentum Alpha (CAMA-8)',
    market: 'Multi-Asset',
    universe: 'Global Equity ETFs, Commodities (Gold/Oil), BTC, 10Y Treasuries',
    timeframe: 'Daily / 4h',
    type: 'momentum',
    stage: 'PAUSED',
    nextGate: 'Backtest Re-engineering (Implement 8% volatility target overlay to fix 7.2% drawdown breach)',
    progression: {
      currentStage: 'PAUSED',
      stageLabel: 'Paused / Eliminated from Tournament',
      nextGate: 'Backtest Overhaul (Vol Target Overlay)',
      status: 'Rejected',
      reason: 'Insufficient drawdown protection: eliminated from Tournament Round 4 due to 7.20% maximum drawdown breaching the strict 4.0% tournament risk ceiling.',
      requirementForNextGate: 'Re-engineer backtest with an 8% volatility target overlay and re-run survivorship bias screening.'
    },
    performanceEvidence: {
      testPeriod: '2016 - 2026 (10 Years)',
      tradeCount: 580,
      feesAssumptions: '$0.005 / share & futures roll charges',
      slippageAssumptions: '5.0 bps modeled',
      outOfSampleStatus: 'Failed',
      outOfSampleWindow: '2024 - 2026 (Drawdown exceeded limit)',
      backtestReportId: 'bt-run-7409',
      inSampleSharpe: 1.95,
      outOfSampleSharpe: 1.78,
      sharpeDecayPct: 8.7
    },
    riskApproval: {
      status: 'Rejected',
      reviewer: 'Nexus Risk Engine (Autonomous Breaker)',
      timestamp: '2026-09-24 09:15 EST',
      policyRef: 'RP-2026.4 §2.0 (Drawdown Ceiling Breach)',
      maxDrawdownLimit: '4.0% Ceiling (Actual: 7.20%)',
      maxPositionLimit: '$75,000 Simulated Capital',
      notes: 'REJECTED: Strategy breached max portfolio drawdown ceiling during rate shock stress testing.'
    },
    owner: { name: 'Elena Rostova', avatar: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150&auto=format&fit=crop&q=80' },
    createdDate: '2026-08-04',
    lastTested: 'Yesterday, 18:00 EST',
    dataSource: 'FactSet Multi-Asset Daily Series',
    alphaDecision: 'RESEARCH_MORE',
    confidence: 76,
    evidenceQuality: 'Medium',
    riskLevel: 'High',
    currentStatus: 'Paused',
    nextAction: 'Re-run backtest with corrected bond roll fee model and volatility targeting overlay',
    overview: {
      thesis: 'Cross-asset relative strength ranking systematically captures capital rotations across economic regimes.',
      hypothesis: 'Holding the top decile of 3-month risk-adjusted momentum assets while shorting or hedging the bottom decile generates positive alpha uncorrelated with equity markets.',
      marketAssumptions: ['Asset liquidity allows seamless rebalancing without market impact', 'Borrow fees on inverse ETF hedges remain modest'],
      entryLogic: 'Rebalance weekly: rank universe by 63-day Sharpe, hold top 3 assets with equal risk contribution.',
      exitLogic: 'Drop asset when it falls below 40th percentile rank.',
      stopLogic: '2.5x weekly ATR trailing stop.',
      positionSizingLogic: 'Equal risk contribution (inverse volatility weighting).',
      filters: ['Macro trend filter: Cash allocation if all assets below 200-day SMA'],
      timeHorizon: 'Weeks to Months'
    },
    researchEvidence: {
      supportingResearch: ['Classic Asness & Frazzini momentum literature across global asset classes'],
      contradictingEvidence: ['Whipsaw drawdowns during abrupt central bank pivot periods (e.g. 2022)'],
      sourceLinks: [{ title: 'Cross-Asset Momentum Whitepaper', url: '#', type: 'Literature' }],
      dataQuality: 'Medium',
      dateRange: '2015 - 2026'
    },
    backtestSummary: {
      totalTrades: 580,
      winRate: 54.8,
      lossRate: 45.2,
      profitFactor: 1.78,
      expectancy: 1.20,
      averageWin: 2400,
      averageLoss: 1450,
      maxDrawdown: 7.20,
      volatility: 12.1,
      sharpe: 1.78,
      sortino: 2.30,
      bestPeriod: '+34.5% (2025)',
      worstPeriod: '-6.8% (2022)',
      testRange: '2016 - 2026',
      outOfSampleStatus: 'Marginal'
    },
    robustness: {
      walkForwardTested: true,
      outOfSampleTested: true,
      parameterSensitivity: 'Moderate',
      regimeSensitivity: 'Multi-Regime',
      slippageAssumptions: '5 bps',
      feeAssumptions: '$0.005 / share',
      survivorshipBiasCheck: 'Warning',
      lookaheadBiasCheck: 'Passed',
      overfittingRisk: 'Medium'
    },
    alphaReview: {
      verdict: 'RESEARCH_MORE',
      confidenceScore: 74,
      reasoning: 'Drawdown of 7.2% exceeds Nexus 4.0% limit for paper trading. Alpha flags survivorship bias warning in commodity ETF history. Recommend testing with volatility target overlay.',
      keyRisks: ['Regime transition whipsaw', 'Drawdown exceeding risk ceiling'],
      recommendedParameters: ['Implement 8% volatility target overlay to dampen drawdowns'],
      evaluatedAt: '2026-09-24T09:15:00Z'
    },
    versions: [
      {
        version: 'v1.1',
        date: '2026-08-25',
        summary: 'Refined ranking window from 126 days to 63 days to increase responsiveness',
        codeHash: 'git-ff41a98',
        parametersChanged: ['lookback_days: 63'],
        backtestResult: { sharpe: 1.78, winRate: 54.8, profitFactor: 1.78, maxDrawdown: 7.20 },
        alphaDecision: 'RESEARCH_MORE',
        reasoning: 'Sharpe improved but tail risk remains elevated.'
      }
    ]
  },
  {
    id: 'strat-opt-05',
    name: 'Index Volatility Skew Harvesting (IVSH-1)',
    market: 'Options',
    universe: 'SPX / NDX Index Options (30-45 DTE)',
    timeframe: 'Daily',
    type: 'options research',
    stage: 'RISK_REVIEW',
    nextGate: 'Paper Trading Approval (Margin verification on 21 DTE gamma ramp exit)',
    progression: {
      currentStage: 'RISK_REVIEW',
      stageLabel: 'Risk Review Gate',
      nextGate: 'Paper Trading Sandbox Sign-Off',
      status: 'Waiting',
      reason: 'Advanced from Tournament Round 3. Currently in risk review to verify exchange portfolio margin multiplier and tail-risk put hedge buffer.',
      requirementForNextGate: 'Governance sign-off on 21 DTE mandatory gamma exit rule before initiating paper options trading.'
    },
    performanceEvidence: {
      testPeriod: '2018 - 2026 (8 Years)',
      tradeCount: 420,
      feesAssumptions: '$0.65 per contract exchange fee',
      slippageAssumptions: '$0.05 per contract leg',
      outOfSampleStatus: 'Passed',
      outOfSampleWindow: '2024 - 2026 (Walk-Forward Validated)',
      backtestReportId: 'bt-run-7408',
      inSampleSharpe: 1.98,
      outOfSampleSharpe: 1.92,
      sharpeDecayPct: 3.0
    },
    riskApproval: {
      status: 'Pending Review',
      policyRef: 'RP-2026.4 §6.0 (Options Volatility Harvesting)',
      maxDrawdownLimit: '3.4% Peak Equity',
      maxPositionLimit: '$80,000 Portfolio Margin',
      notes: 'Pending sign-off from Alex Chen and Dr. Marcus Vance.'
    },
    owner: { name: 'Dr. Marcus Vance', avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80' },
    createdDate: '2026-06-20',
    lastTested: 'Today, 06:10 EST',
    dataSource: 'CBOE LiveVol Surface & Greek History',
    alphaDecision: 'QUALIFY',
    confidence: 86,
    evidenceQuality: 'High',
    riskLevel: 'Medium',
    currentStatus: 'Pending Review',
    nextAction: 'Governance signoff required to initiate paper options trading',
    overview: {
      thesis: 'Index options persistently price excessive downside crash risk, creating an institutional structural volatility risk premium.',
      hypothesis: 'Selling 16-delta out-of-the-money puts hedged with far-out-of-the-money long puts (credit spreads) captures positive theta decay while limiting catastrophic tail risk.',
      marketAssumptions: ['Options margin requirements remain stable', 'Implied volatility premium over realized > 2.5 vol points'],
      entryLogic: 'Open 40 DTE 16-delta Put Credit Spread when VIX / realized vol ratio > 1.25.',
      exitLogic: 'Close at 50% max profit or 21 DTE (whichever occurs first).',
      stopLogic: 'Close spread if loss reaches 200% of initial premium collected.',
      positionSizingLogic: 'Max 2% portfolio margin utilization per index contract.',
      filters: ['No earnings or FOMC within 5 days of trade entry', 'VIX must be > 13.0'],
      timeHorizon: '14 to 28 days'
    },
    researchEvidence: {
      supportingResearch: ['Extensive academic consensus on the equity volatility risk premium (VRP)'],
      contradictingEvidence: ['Extreme downside shocks (e.g. March 2020) inflict max loss on spreads without fast hedging'],
      sourceLinks: [{ title: 'Options Alpha Review 2026', url: '#', type: 'Institutional Paper' }],
      dataQuality: 'High',
      dateRange: '2012 - 2026'
    },
    backtestSummary: {
      totalTrades: 420,
      winRate: 82.4,
      lossRate: 17.6,
      profitFactor: 2.05,
      expectancy: 1.35,
      averageWin: 480,
      averageLoss: 980,
      maxDrawdown: 3.40,
      volatility: 9.6,
      sharpe: 1.92,
      sortino: 2.88,
      bestPeriod: '+19.2% (2024)',
      worstPeriod: '-2.8% (Aug 2024)',
      testRange: '2018 - 2026',
      outOfSampleStatus: 'Passed'
    },
    robustness: {
      walkForwardTested: true,
      outOfSampleTested: true,
      parameterSensitivity: 'Robust',
      regimeSensitivity: 'Multi-Regime',
      slippageAssumptions: '$0.05 per contract leg',
      feeAssumptions: '$0.65 per contract fee',
      survivorshipBiasCheck: 'Passed',
      lookaheadBiasCheck: 'Passed',
      overfittingRisk: 'Low'
    },
    alphaReview: {
      verdict: 'QUALIFY',
      confidenceScore: 88,
      reasoning: 'Hedging with defined long wings eliminates unlimited tail risk. Historical win rate 82.4% is consistent with delta mechanics. Alpha approves for paper qualification.',
      keyRisks: ['Black swan gap down past both wings', 'Sudden margin requirement spike'],
      recommendedParameters: ['Mandate hard stop at 21 DTE to bypass gamma risk ramp'],
      evaluatedAt: '2026-09-24T16:00:00Z'
    },
    versions: [
      {
        version: 'v2.0',
        date: '2026-09-02',
        summary: 'Added mandatory 21 DTE gamma exit and defined wing width',
        codeHash: 'git-39da421',
        parametersChanged: ['exit_dte: 21', 'wing_width: 50_pts'],
        backtestResult: { sharpe: 1.92, winRate: 82.4, profitFactor: 2.05, maxDrawdown: 3.40 },
        alphaDecision: 'QUALIFY',
        reasoning: 'Cut tail gamma risk dramatically without sacrificing yield.'
      }
    ]
  },
  {
    id: 'strat-macro-06',
    name: 'Macro Yield Curve Dislocation (MYCD-2)',
    market: 'Futures',
    universe: 'US 2Y, 5Y, 10Y, 30Y Treasury Futures (ZT, ZF, ZN, ZB)',
    timeframe: '1h / 4h',
    type: 'macro',
    stage: 'TOURNAMENT',
    nextGate: 'Tournament Round 4 Qualification (Awaiting rate easing regime stress test)',
    progression: {
      currentStage: 'TOURNAMENT',
      stageLabel: 'Trading Tournament (Round 4)',
      nextGate: 'Risk Review (Pending Tournament Finish)',
      status: 'In Progress',
      reason: 'Currently competing in Tournament Round 4 (+18.2% return, 2.05 Sharpe, 2.85% max DD). Waiting for multi-regime stress test on rapid rate easing cycles.',
      requirementForNextGate: 'Complete out-of-sample stress test on high inflation and rapid rate easing regimes.'
    },
    performanceEvidence: {
      testPeriod: '2018 - 2026 (8 Years)',
      tradeCount: 310,
      feesAssumptions: '$1.45 per contract exchange fee',
      slippageAssumptions: '0.5 tick per leg',
      outOfSampleStatus: 'Passed',
      outOfSampleWindow: '2024 - 2026 (Walk-Forward OOS)',
      backtestReportId: 'bt-run-7407',
      inSampleSharpe: 2.10,
      outOfSampleSharpe: 2.05,
      sharpeDecayPct: 2.4
    },
    riskApproval: {
      status: 'Pending Review',
      policyRef: 'RP-2026.4 §4.8 (Treasury Duration Neutrality)',
      maxDrawdownLimit: '3.0% Peak Equity',
      maxPositionLimit: '$200,000 Duration-Weighted Exposure',
      notes: 'DV01 duration hedge ratio requires daily CME settlement price sync.'
    },
    owner: { name: 'Elena Rostova', avatar: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150&auto=format&fit=crop&q=80' },
    createdDate: '2026-08-15',
    lastTested: 'Today, 05:30 EST',
    dataSource: 'CME Market Depth & Federal Reserve H.15 Data',
    alphaDecision: 'QUALIFY',
    confidence: 82,
    evidenceQuality: 'High',
    riskLevel: 'Medium',
    currentStatus: 'Pending Review',
    nextAction: 'Complete out-of-sample stress test on high inflation regimes',
    overview: {
      thesis: 'Yield curve slope dislocates predictably following Federal Reserve dot plot releases and auction tail events.',
      hypothesis: 'Steepener and flattener box spreads capture term premium normalization with high statistical confidence.',
      marketAssumptions: ['Treasury futures basis and delivery basket remain liquid', 'Sufficient liquidity to roll front month contracts'],
      entryLogic: 'Execute 2s10s curve spread when basis spread deviates by > 2.0 standard deviations from 60-day moving average.',
      exitLogic: 'Mean reversion target at 0.1 sigma of spread.',
      stopLogic: 'Stop at 3.5 sigma divergence.',
      positionSizingLogic: 'DV01 duration-neutral matching.',
      filters: ['Auction calendar buffer: No entry within 30 mins of 10Y/30Y auctions'],
      timeHorizon: '2 to 10 days'
    },
    researchEvidence: {
      supportingResearch: ['Historical treasury basis data from 2010 to 2026'],
      contradictingEvidence: ['Persistent inversion periods during aggressive rate hiking cycles'],
      sourceLinks: [{ title: 'Treasury Term Structure Memo', url: '#', type: 'Research' }],
      dataQuality: 'High',
      dateRange: '2015 - 2026'
    },
    backtestSummary: {
      totalTrades: 310,
      winRate: 68.4,
      lossRate: 31.6,
      profitFactor: 2.12,
      expectancy: 1.62,
      averageWin: 1850,
      averageLoss: 940,
      maxDrawdown: 2.85,
      volatility: 7.9,
      sharpe: 2.05,
      sortino: 3.10,
      bestPeriod: '+16.5% (2025)',
      worstPeriod: '-1.8% (2023)',
      testRange: '2018 - 2026',
      outOfSampleStatus: 'Passed'
    },
    robustness: {
      walkForwardTested: true,
      outOfSampleTested: true,
      parameterSensitivity: 'Robust',
      regimeSensitivity: 'Multi-Regime',
      slippageAssumptions: '0.5 tick per leg',
      feeAssumptions: '$1.45 per contract exchange fee',
      survivorshipBiasCheck: 'Passed',
      lookaheadBiasCheck: 'Passed',
      overfittingRisk: 'Low'
    },
    alphaReview: {
      verdict: 'QUALIFY',
      confidenceScore: 84,
      reasoning: 'DV01 duration hedging eliminates interest rate beta, isolating curve slope. Alpha approves qualification with positive recommendation for Paper stage.',
      keyRisks: ['Surprise emergency central bank rate adjustments'],
      recommendedParameters: ['Update DV01 daily from CME settlement price files'],
      evaluatedAt: '2026-09-25T10:00:00Z'
    },
    versions: [
      {
        version: 'v1.0',
        date: '2026-08-15',
        summary: 'Initial model release with DV01 weighting',
        codeHash: 'git-a1288c4',
        parametersChanged: ['initial build'],
        backtestResult: { sharpe: 2.05, winRate: 68.4, profitFactor: 2.12, maxDrawdown: 2.85 },
        alphaDecision: 'QUALIFY',
        reasoning: 'Sound institutional design.'
      }
    ]
  },
  {
    id: 'strat-event-07',
    name: 'High Beta Earnings Post-Announcement Drift (PEAD)',
    market: 'Equities',
    universe: 'Russell 1000 High Beta Subset',
    timeframe: 'Daily / 30m',
    type: 'event-driven',
    stage: 'RETIRED',
    nextGate: 'Permanently Retired (Negative expectancy and structural adverse selection)',
    progression: {
      currentStage: 'RETIRED',
      stageLabel: 'Permanently Retired / Archived',
      nextGate: 'None (Archived)',
      status: 'Rejected',
      reason: 'Eliminated from Tournament Round 4 and permanently retired. Edge has been completely arbitrated by HFT market makers; suffering -0.15R negative expectancy and 14.8% max drawdown.',
      requirementForNextGate: 'Archived permanently. No further testing permitted under policy RP-2026.4.'
    },
    performanceEvidence: {
      testPeriod: '2020 - 2026 (6 Years)',
      tradeCount: 320,
      feesAssumptions: 'Standard tiered fees',
      slippageAssumptions: '15.0 bps opening cross slippage',
      outOfSampleStatus: 'Failed',
      outOfSampleWindow: '2024 - 2026 (Catastrophic tail losses)',
      backtestReportId: 'bt-run-7406',
      inSampleSharpe: 0.65,
      outOfSampleSharpe: 0.42,
      sharpeDecayPct: 35.4
    },
    riskApproval: {
      status: 'Rejected',
      reviewer: 'Nexus Risk Engine',
      policyRef: 'RP-2026.4 §1.0 (Expectancy & Gap Risk)',
      maxDrawdownLimit: '4.0% Ceiling (Actual: 14.80%)',
      maxPositionLimit: '$0 (Prohibited)',
      notes: 'Permanently rejected. Severe gap-down vulnerability and negative edge.'
    },
    owner: { name: 'Dr. Marcus Vance', avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80' },
    createdDate: '2026-05-10',
    lastTested: '2026-09-10',
    dataSource: 'SEC EDGAR Real-time 8-K feeds + Estimize Consensus',
    alphaDecision: 'REJECT',
    confidence: 42,
    evidenceQuality: 'Low',
    riskLevel: 'Critical',
    currentStatus: 'Archived',
    nextAction: 'Strategy archived by Governance due to excessive gap risk and high drawdown',
    overview: {
      thesis: 'Companies beating consensus earnings and raising guidance experience persistent upward drift over 30 days.',
      hypothesis: 'Entering at next-day open following positive earnings surprise captures 3.2% excess drift.',
      marketAssumptions: ['Liquidity at market open is adequate without huge spreads'],
      entryLogic: 'Market order at 09:30:15 EST on earnings beat > 10%.',
      exitLogic: 'Hold for 20 trading days.',
      stopLogic: 'Hard stop at 4.0% loss.',
      positionSizingLogic: 'Equal dollar allocation.',
      filters: ['Guidance positive check'],
      timeHorizon: '20 days'
    },
    researchEvidence: {
      supportingResearch: ['Historical PEAD academic papers from 1968-2015'],
      contradictingEvidence: ['Modern algorithms front-run PEAD within 45 seconds of release, leaving only negative drift for retail/slow participants'],
      sourceLinks: [{ title: 'PEAD Modern Arbitrage Report', url: '#', type: 'Paper' }],
      dataQuality: 'Low',
      dateRange: '2020 - 2026'
    },
    backtestSummary: {
      totalTrades: 320,
      winRate: 46.2,
      lossRate: 53.8,
      profitFactor: 0.94,
      expectancy: -0.15,
      averageWin: 1100,
      averageLoss: 1350,
      maxDrawdown: 14.8,
      volatility: 22.4,
      sharpe: 0.42,
      sortino: 0.51,
      bestPeriod: '+8.4% (2021)',
      worstPeriod: '-12.2% (2024)',
      testRange: '2020 - 2026',
      outOfSampleStatus: 'Failed'
    },
    robustness: {
      walkForwardTested: true,
      outOfSampleTested: true,
      parameterSensitivity: 'Fragile',
      regimeSensitivity: 'Bull-Only',
      slippageAssumptions: '15 bps due to opening cross imbalance',
      feeAssumptions: 'Standard',
      survivorshipBiasCheck: 'Warning',
      lookaheadBiasCheck: 'Warning',
      overfittingRisk: 'Extreme'
    },
    alphaReview: {
      verdict: 'REJECT',
      confidenceScore: 35,
      reasoning: 'REJECTED: The post-announcement drift edge has been fully arbitrated by high-frequency market participants. Modern gap open fills suffer from severe adverse selection. Max drawdown 14.8% violates Nexus risk rules.',
      keyRisks: ['Adverse selection at open', 'Negative guidance surprises resulting in 20% gap losses'],
      recommendedParameters: ['Abandon strategy or pivot to pre-earnings options straddles'],
      evaluatedAt: '2026-09-12T11:00:00Z'
    },
    versions: [
      {
        version: 'v1.0',
        date: '2026-05-10',
        summary: 'Baseline PEAD test',
        codeHash: 'git-009f123',
        parametersChanged: ['initial test'],
        backtestResult: { sharpe: 0.42, winRate: 46.2, profitFactor: 0.94, maxDrawdown: 14.8 },
        alphaDecision: 'REJECT',
        reasoning: 'Negative expectancy with severe tail risk.'
      }
    ]
  },
  {
    id: 'strat-trend-08',
    name: 'Multi-Timeframe Trend Following (MTTF-X)',
    market: 'Crypto',
    universe: 'Top 10 L1/L2 Assets',
    timeframe: '4h / Daily',
    type: 'trend following',
    stage: 'BACKTEST',
    nextGate: 'Tournament Eligibility Gate (Complete multi-year walk-forward test)',
    progression: {
      currentStage: 'BACKTEST',
      stageLabel: 'Backtesting Laboratory',
      nextGate: 'Tournament Eligibility (Round 5)',
      status: 'In Progress',
      reason: 'In active backtest refinement. Parameter grid testing Donchian channel lookbacks (20 to 60 days) to prevent whipsaw in rangebound chop.',
      requirementForNextGate: 'Demonstrate maximum drawdown < 5.0% and out-of-sample Sharpe > 1.8 across 2024-2026 data.'
    },
    performanceEvidence: {
      testPeriod: '2020 - 2026 (6 Years)',
      tradeCount: 280,
      feesAssumptions: '0.04% taker',
      slippageAssumptions: '5.0 bps modeled',
      outOfSampleStatus: 'Untested',
      outOfSampleWindow: 'OOS Walk-Forward in progress',
      backtestReportId: 'bt-run-7405',
      inSampleSharpe: 1.74,
      outOfSampleSharpe: 1.62,
      sharpeDecayPct: 6.8
    },
    riskApproval: {
      status: 'Not Eligible',
      policyRef: 'RP-2026.4 §4.0 (Trend Gating)',
      maxDrawdownLimit: '4.0% Ceiling',
      maxPositionLimit: '$50,000 Simulated Capital',
      notes: 'Must qualify through Trading Tournament before risk review.'
    },
    owner: { name: 'Siddharth Rao', avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80' },
    createdDate: '2026-04-01',
    lastTested: 'Yesterday',
    dataSource: 'Coinbase Pro Aggregate Stream',
    alphaDecision: 'PAUSE',
    confidence: 68,
    evidenceQuality: 'Medium',
    riskLevel: 'High',
    currentStatus: 'Paused',
    nextAction: 'Awaiting market regime transition out of prolonged low-volatility chop',
    overview: {
      thesis: 'Crypto assets exhibit explosive multi-week trends when breaking out from 50-day Donchian channels with rising volume.',
      hypothesis: 'Long-only trend following captures 4x+ reward-to-risk during directional phases.',
      marketAssumptions: ['Asset volatility stays above 40% annualized'],
      entryLogic: 'Breakout of 20-day high with MACD histogram positive.',
      exitLogic: 'Trailing stop at 20-day low or ATR(14) x 3.0.',
      stopLogic: 'Initial stop at 8.0% loss.',
      positionSizingLogic: 'Fixed fractional 1.0% equity risk.',
      filters: ['200-day SMA slope positive'],
      timeHorizon: '2 to 8 weeks'
    },
    researchEvidence: {
      supportingResearch: ['Historical Donchian breakout models across crypto bull markets (2017, 2020, 2024)'],
      contradictingEvidence: ['Chop and whipsaw losses during rangebound sideways consolidation'],
      sourceLinks: [{ title: 'Crypto Trend Dynamics', url: '#', type: 'Memo' }],
      dataQuality: 'Medium',
      dateRange: '2019 - 2026'
    },
    backtestSummary: {
      totalTrades: 280,
      winRate: 41.5,
      lossRate: 58.5,
      profitFactor: 1.85,
      expectancy: 1.40,
      averageWin: 3800,
      averageLoss: 1200,
      maxDrawdown: 6.80,
      volatility: 19.4,
      sharpe: 1.62,
      sortino: 2.15,
      bestPeriod: '+64.2% (Q4 2024)',
      worstPeriod: '-5.9% (Summer 2025)',
      testRange: '2020 - 2026',
      outOfSampleStatus: 'Passed'
    },
    robustness: {
      walkForwardTested: true,
      outOfSampleTested: true,
      parameterSensitivity: 'Robust',
      regimeSensitivity: 'Bull-Only',
      slippageAssumptions: '5 bps',
      feeAssumptions: '0.04% taker',
      survivorshipBiasCheck: 'Passed',
      lookaheadBiasCheck: 'Passed',
      overfittingRisk: 'Low'
    },
    alphaReview: {
      verdict: 'PAUSE',
      confidenceScore: 72,
      reasoning: 'Market regime is currently low-volatility sideways consolidation. Donchian trend following suffers consecutive false breakout whipsaws in this regime. PAUSED until 30-day realized volatility exceeds 45%.',
      keyRisks: ['Extended sideways consolidation', 'False breakout chop'],
      recommendedParameters: ['Add ADX filter > 25 before entering breakouts'],
      evaluatedAt: '2026-09-20T15:00:00Z'
    },
    versions: [
      {
        version: 'v2.1',
        date: '2026-07-14',
        summary: 'Incorporated ADX regime gating',
        codeHash: 'git-29bb901',
        parametersChanged: ['adx_min: 25'],
        backtestResult: { sharpe: 1.62, winRate: 41.5, profitFactor: 1.85, maxDrawdown: 6.80 },
        alphaDecision: 'PAUSE',
        reasoning: 'Temporarily paused due to macro sideways conditions.'
      }
    ]
  },
  {
    id: 'strat-fx-09',
    name: 'London-NY Session Breakout Matrix (LNY-FX)',
    market: 'Forex',
    universe: 'EUR/USD, GBP/USD, USD/JPY (G10 Majors)',
    timeframe: '15m / 1h Hybrid',
    type: 'breakout',
    stage: 'RISK_REVIEW',
    nextGate: 'Paper Trading Approval (Dual risk review by Dr. Marcus Vance & Alex Chen)',
    progression: {
      currentStage: 'RISK_REVIEW',
      stageLabel: 'Risk Review Committee',
      nextGate: 'Paper Trading Approval (Dual committee sign-off)',
      status: 'Waiting',
      reason: 'Advanced from Tournament Round 4 (Forex Division, Rank #1 with 2.18 Sharpe, 1.85% max DD). Currently undergoing institutional dual-risk review for rollover financing swap model.',
      requirementForNextGate: 'Finalize institutional swap rate curve integration and stress-test 100-pip flash crash buffer before paper trading authorization.'
    },
    forexDetails: {
      currencyPair: 'EUR/USD (Primary) + USD/JPY',
      tradingSession: 'London / NY Overlap (08:00 – 11:30 EST)',
      pipEntry: '+8.5 pips breakout over Asian range high with volume spike > 1.8x SMA',
      pipStop: '16.0 pips stop-loss',
      pipTarget: '32.0 pips take-profit (2.0R payout ratio)',
      spread: '0.8 pips modeled institutional spread (EBS L2 Top-of-Book)',
      estimatedExecutionCosts: '$824 ($4.50/lot commission + spread friction)',
      dataFeed: 'EBS / Currenex Institutional FX L2 Feed',
      testPeriod: '2023 - 2026 (36 Months Walk-Forward)',
      drawdown: '1.85% max drawdown (Strictly within 3.5% Forex group risk ceiling)',
      riskLimit: '1.0% equity risk per trade ($1,000 max risk per trade on $100k account)'
    },
    performanceEvidence: {
      testPeriod: '2023 - 2026 (36 Months Walk-Forward)',
      tradeCount: 412,
      feesAssumptions: '$4.50 / round turn lot',
      slippageAssumptions: '0.8 pips institutional spread',
      outOfSampleStatus: 'Passed',
      outOfSampleWindow: '2025-07-01 to 2026-06-30 (12 Mo OOS)',
      backtestReportId: 'bt-run-7414',
      inSampleSharpe: 2.26,
      outOfSampleSharpe: 2.18,
      sharpeDecayPct: 3.5
    },
    riskApproval: {
      status: 'Pending Review',
      reviewer: 'Dr. Marcus Vance (Chief Risk Officer)',
      timestamp: '2026-09-27 16:40 EST',
      policyRef: 'RP-2026.4 §4.5 (Forex Major Pairs Risk Standard)',
      maxDrawdownLimit: '3.5% Forex Ceiling',
      maxPositionLimit: '$100,000 Notional ($10,000 Margin)',
      notes: 'Passed initial Sharpe and drawdown tests. Under review for weekend rollover gap hedge buffer.'
    },
    owner: { name: 'Alex Chen', avatar: 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&auto=format&fit=crop&q=80' },
    createdDate: '2026-02-15',
    lastTested: 'Today, 08:45 EST',
    dataSource: 'EBS / Currenex Institutional FX L2 Feed',
    alphaDecision: 'QUALIFY',
    confidence: 88,
    evidenceQuality: 'High',
    riskLevel: 'Medium',
    currentStatus: 'Pending Review',
    nextAction: 'Complete dual risk committee sign-off to authorize simulated paper trading gateway',
    overview: {
      thesis: 'Cross-border foreign exchange liquidity surges during the London/NY session overlap (08:00–11:30 EST), resolving Asian range consolidations into directional expansions with minimal adverse excursion.',
      hypothesis: 'Entering on confirmed 15m breakout candles exceeding the Asian range high/low by 8.5 pips with tick volume > 1.8x 20-period SMA generates 2.0R payout with 64%+ win rate after 0.8 pip friction.',
      marketAssumptions: [
        'EBS / Currenex institutional spread remains <= 1.2 pips during overlap',
        'Central bank intervention risk mitigated by pausing 30 mins around scheduled rate announcements'
      ],
      entryLogic: 'Long when 15m bar closes > Asian session high + 8.5 pips with volume filter. Short inverted.',
      exitLogic: 'Trailing stop activated at +20 pips; hard target at +32 pips (2.0R).',
      stopLogic: 'Initial stop placed at 16.0 pips from fill price.',
      positionSizingLogic: 'Fixed risk 1.0% ($1,000 on $100k account) = 1.0 standard lot with $10/pip value.',
      filters: ['Active trading session: 08:00 - 11:30 EST only', 'Spread check < 1.2 pips'],
      timeHorizon: 'Intraday (2 to 5 hours average holding duration)'
    },
    researchEvidence: {
      supportingResearch: [
        'BIS Triennial Central Bank Survey 2025: Liquidity clustering in London/NY crossover',
        'Academic paper on Intraday FX Breakout Autocorrelation under Institutional ECN Feeds (2024)'
      ],
      contradictingEvidence: [
        'Whipsaws during unexpected ECB/Fed unscheduled headline releases'
      ],
      sourceLinks: [
        { title: 'BIS FX Microstructure Report', url: '#', type: 'Academic' },
        { title: 'ECN Tick Spread Dynamics Memo', url: '#', type: 'Memo' }
      ],
      dataQuality: 'High',
      dateRange: '2020 - 2026'
    },
    backtestSummary: {
      totalTrades: 412,
      winRate: 64.2,
      lossRate: 35.8,
      profitFactor: 2.24,
      expectancy: 1.82,
      averageWin: 320,
      averageLoss: 160,
      maxDrawdown: 1.85,
      volatility: 9.4,
      sharpe: 2.18,
      sortino: 3.12,
      bestPeriod: '+8.4% (Q1 2025)',
      worstPeriod: '-1.2% (Q3 2024)',
      testRange: '2023 - 2026 (36 Months)',
      outOfSampleStatus: 'Passed'
    },
    robustness: {
      walkForwardTested: true,
      outOfSampleTested: true,
      parameterSensitivity: 'Robust',
      regimeSensitivity: 'Multi-Regime',
      slippageAssumptions: '0.8 pips modeled institutional spread',
      feeAssumptions: '$4.50 / round turn standard lot',
      survivorshipBiasCheck: 'Passed',
      lookaheadBiasCheck: 'Passed',
      overfittingRisk: 'Low'
    },
    alphaReview: {
      verdict: 'QUALIFY',
      confidenceScore: 89,
      reasoning: 'Exceptional consistency in London/NY overlap. Sharpe 2.18 with 1.85% max drawdown comfortably inside the 3.5% FX risk ceiling. High-conviction candidate for paper sandbox.',
      keyRisks: [
        'Susceptible to surprise central bank emergency comments',
        'Requires continuous sub-30ms EBS feed health'
      ],
      recommendedParameters: ['Session: 08:00 - 11:30 EST', 'Stop: 16 pips', 'Target: 32 pips'],
      evaluatedAt: '2026-09-25 14:10 EST'
    },
    versions: [
      {
        version: 'v2.4',
        date: '2026-09-20',
        summary: 'Added tick volume acceleration filter to prevent false breakouts during low-liquidity banking holidays',
        codeHash: 'git-fx-77c102',
        parametersChanged: ['min_tick_volume_ratio: 1.8', 'pip_buffer: 8.5'],
        backtestResult: { sharpe: 2.18, winRate: 64.2, profitFactor: 2.24, maxDrawdown: 1.85 },
        alphaDecision: 'QUALIFY',
        reasoning: 'Reduced false triggers by 24% while preserving full upside capture.'
      }
    ]
  }
];

// ========================================================
// TRADING TOURNAMENT DATA (Fair Comparison Under Identical Conditions)
// ========================================================

export const CURRENT_TOURNAMENT_ROUND: TournamentRound = {
  id: 'tourn-round-04',
  name: 'Tournament Round 4: Q3 Multi-Asset & G10 Forex Walk-Forward Showcase',
  status: 'ACTIVE',
  testWindow: '2024-01-01 to 2026-06-30 (30 Months Fixed)',
  startingCapital: 100000,
  marketDataSet: 'Standardized S&P 500, G10 Forex L2, & Crypto L3 Benchmark Set v2026.4',
  sharedRiskLimits: {
    maxDrawdownPct: 4.0,
    maxRiskPerTradePct: 1.0,
    modeledSlippageBps: 2.0,
    executionFee: '$0.005/share (Equities) · 0.8-1.2 pips (Forex) · 0.04% taker (Crypto)'
  },
  totalParticipants: 9,
  advancedCount: 3,
  testingCount: 3,
  eliminatedCount: 3
};

export const INITIAL_TOURNAMENT_ENTRIES: TournamentEntry[] = [
  {
    id: 'entry-01',
    rank: 1,
    divisionRank: 1,
    division: 'Equities & Multi-Asset',
    benchmarkName: 'S&P 500 (+24.2%)',
    benchmarkReturnPct: 24.2,
    strategyId: 'strat-vol-01',
    strategyName: 'Volatility Expansion Matrix (VEM-4)',
    author: 'Elena Rostova',
    authorAvatar: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150&auto=format&fit=crop&q=80',
    market: 'Equities',
    type: 'volatility',
    returnPct: 42.6,
    returnDollar: 42600,
    maxDrawdownPct: 3.84,
    consistencyScorePct: 78.4,
    tradeCount: 1482,
    estimatedCosts: 1240,
    sharpe: 2.14,
    winRate: 61.4,
    profitFactor: 2.18,
    decision: 'ADVANCE',
    decisionReason: 'Exceeded Sharpe target (2.14 > 2.0) and stayed strictly under 4.0% max drawdown ceiling (3.84%). Asymmetric payout model confirmed across 3 market regimes.',
    nextGate: 'Risk Review (Dr. Marcus Vance sign-off before simulated paper trading)',
    backtestReportId: 'bt-run-7412',
    evidenceNotes: 'Walk-forward verified. Out-of-sample Sharpe decay was only 3.6%. Fees & slippage drag accounted for 2.9% of gross return.'
  },
  {
    id: 'entry-02',
    rank: 2,
    divisionRank: 2,
    division: 'Equities & Multi-Asset',
    benchmarkName: 'S&P 500 (+24.2%)',
    benchmarkReturnPct: 24.2,
    strategyId: 'strat-pairs-02',
    strategyName: 'Stat-Arb Cointegration Pairs (SACP-X)',
    author: 'Dr. Marcus Vance',
    authorAvatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
    market: 'Equities',
    type: 'pairs/statistical',
    returnPct: 34.8,
    returnDollar: 34800,
    maxDrawdownPct: 2.15,
    consistencyScorePct: 84.2,
    tradeCount: 2140,
    estimatedCosts: 890,
    sharpe: 2.45,
    winRate: 72.8,
    profitFactor: 2.65,
    decision: 'ADVANCE',
    decisionReason: 'Highest consistency (84.2%) and lowest drawdown in tournament field (2.15%). Dynamic Kalman filter preserved beta neutrality throughout 2025 tech rally.',
    nextGate: 'Risk Review (Dual governance sign-off before simulated paper trading)',
    backtestReportId: 'bt-run-7411',
    evidenceNotes: 'Dickey-Fuller stationarity p < 0.001. Beta-neutral dollar balancing kept market correlation under 0.08.'
  },
  {
    id: 'entry-fx-01',
    rank: 3,
    divisionRank: 1,
    division: 'Forex',
    currencyPair: 'EUR/USD (Primary) + USD/JPY',
    tradingSession: 'London / NY Overlap (08:00 - 11:30 EST)',
    benchmarkName: 'USD DXY Currency Index (+3.4%)',
    benchmarkReturnPct: 3.4,
    pipMetrics: {
      pipGain: 485,
      maxPipDrawdown: 37,
      avgSpreadPips: 0.8
    },
    strategyId: 'strat-fx-09',
    strategyName: 'London-NY Session Breakout Matrix (LNY-FX)',
    author: 'Alex Chen',
    authorAvatar: 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&auto=format&fit=crop&q=80',
    market: 'Forex',
    type: 'breakout',
    returnPct: 19.4,
    returnDollar: 19400,
    maxDrawdownPct: 1.85,
    consistencyScorePct: 81.2,
    tradeCount: 412,
    estimatedCosts: 824,
    sharpe: 2.18,
    winRate: 64.2,
    profitFactor: 2.24,
    decision: 'ADVANCE',
    decisionReason: 'Rank #1 in Forex Group: Outperformed DXY currency benchmark by +16.0% alpha under institutional 0.8-pip spread friction. Maintained 1.85% max drawdown (well below 3.5% Forex ceiling) and 81.2% consistency across 412 verified trades.',
    nextGate: 'Risk Review (Dual governance sign-off on rollover financing swap model)',
    backtestReportId: 'bt-run-7414',
    evidenceNotes: 'London/NY overlap momentum pulse verified across 36-month walk-forward. Pip-based entry and 16-pip stop strictly enforced. Slippage under 0.2 pips in simulated EBS L2 feed.'
  },
  {
    id: 'entry-03',
    rank: 4,
    divisionRank: 1,
    division: 'Crypto',
    benchmarkName: 'BTC / ETH Equal Weight (+22.1%)',
    benchmarkReturnPct: 22.1,
    strategyId: 'strat-crypto-03',
    strategyName: 'Orderflow Microstructure Reversion (OMR-B)',
    author: 'Siddharth Rao',
    authorAvatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80',
    market: 'Crypto',
    type: 'mean reversion',
    returnPct: 28.4,
    returnDollar: 28400,
    maxDrawdownPct: 3.92,
    consistencyScorePct: 69.1,
    tradeCount: 185,
    estimatedCosts: 2180,
    sharpe: 2.28,
    winRate: 67.2,
    profitFactor: 2.28,
    decision: 'CONTINUE_TESTING',
    decisionReason: 'Strong Sharpe and win rate, but held back by insufficient sample size: only 185 out-of-sample trades recorded against tournament requirement of 300+ trades. Also sensitive to current Binance feed latency degradation.',
    nextGate: 'Tournament Extension (Accumulate 115 additional OOS fills under stabilized feed)',
    backtestReportId: 'bt-run-7410',
    evidenceNotes: 'Taker fee drag reduced by post-only limit engine. Must verify execution stability under volatile news hours.'
  },
  {
    id: 'entry-04',
    rank: 5,
    divisionRank: 3,
    division: 'Equities & Multi-Asset',
    benchmarkName: 'US 10Y Treasury Index (+6.4%)',
    benchmarkReturnPct: 6.4,
    strategyId: 'strat-macro-06',
    strategyName: 'Macro Yield Curve Dislocation (MYCD-2)',
    author: 'Elena Rostova',
    authorAvatar: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150&auto=format&fit=crop&q=80',
    market: 'Futures',
    type: 'macro',
    returnPct: 18.2,
    returnDollar: 18200,
    maxDrawdownPct: 2.85,
    consistencyScorePct: 72.0,
    tradeCount: 310,
    estimatedCosts: 450,
    sharpe: 2.05,
    winRate: 68.4,
    profitFactor: 2.12,
    decision: 'CONTINUE_TESTING',
    decisionReason: 'Sound term-structure mathematics and low drawdown (2.85%), but awaiting out-of-sample stress test on rapid interest-rate easing regimes before risk review eligibility.',
    nextGate: 'Multi-Regime Stress Test (Complete FOMC easing cycle simulation)',
    backtestReportId: 'bt-run-7407',
    evidenceNotes: 'DV01 duration hedge ratio proved robust across 2024-2025 auctions. Zero roll slippage issues on front month.'
  },
  {
    id: 'entry-fx-02',
    rank: 6,
    divisionRank: 2,
    division: 'Forex',
    currencyPair: 'USD/JPY',
    tradingSession: 'Tokyo Asian Session (20:00 - 02:00 EST)',
    benchmarkName: 'USD DXY Currency Index (+3.4%)',
    benchmarkReturnPct: 3.4,
    pipMetrics: {
      pipGain: 295,
      maxPipDrawdown: 44,
      avgSpreadPips: 1.1
    },
    strategyId: 'strat-fx-10',
    strategyName: 'Asian Session Range Mean Reversion (TYO-MR)',
    author: 'Siddharth Rao',
    authorAvatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80',
    market: 'Forex',
    type: 'mean reversion',
    returnPct: 11.8,
    returnDollar: 11800,
    maxDrawdownPct: 2.20,
    consistencyScorePct: 74.0,
    tradeCount: 195,
    estimatedCosts: 580,
    sharpe: 1.92,
    winRate: 68.5,
    profitFactor: 1.98,
    decision: 'CONTINUE_TESTING',
    decisionReason: 'Solid risk-adjusted returns in low-volatility Tokyo session (2.20% DD), but held back from advancing by insufficient sample size (195/300 required OOS trades) and awaiting stress test across BOJ surprise rate windows.',
    nextGate: 'Tournament Extension (Accumulate 105 additional verified OOS trades under active Tokyo feed)',
    backtestReportId: 'bt-run-7415',
    evidenceNotes: 'Mean reversion bounds respected during calm Asian hours. Modeled spread 1.1 pips. Requires verification during sudden cross-session dollar liquidity shifts.'
  },
  {
    id: 'entry-05',
    rank: 7,
    divisionRank: 4,
    division: 'Equities & Multi-Asset',
    benchmarkName: 'Multi-Asset 60/40 (+14.8%)',
    benchmarkReturnPct: 14.8,
    strategyId: 'strat-mom-04',
    strategyName: 'Cross-Asset Momentum Alpha (CAMA-8)',
    author: 'Elena Rostova',
    authorAvatar: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150&auto=format&fit=crop&q=80',
    market: 'Multi-Asset',
    type: 'momentum',
    returnPct: 26.4,
    returnDollar: 26400,
    maxDrawdownPct: 7.20,
    consistencyScorePct: 58.2,
    tradeCount: 580,
    estimatedCosts: 1120,
    sharpe: 1.78,
    winRate: 54.8,
    profitFactor: 1.78,
    decision: 'ELIMINATE',
    decisionReason: 'ELIMINATED BY RISK BREACH: Strategy maximum drawdown reached 7.20%, exceeding the strict 4.0% tournament drawdown ceiling. Whipsaws during regime pivots inflicted unacceptable portfolio drag.',
    nextGate: 'Paused / Backtest Re-engineering (Implement 8% volatility target overlay)',
    backtestReportId: 'bt-run-7409',
    evidenceNotes: 'Survivorship bias warning detected in commodity ETF component history. Overfitting risk flagged.'
  },
  {
    id: 'entry-fx-03',
    rank: 8,
    divisionRank: 3,
    division: 'Forex',
    currencyPair: 'USD/JPY & EUR/USD',
    tradingSession: '24-Hour Continuous',
    benchmarkName: 'USD DXY Currency Index (+3.4%)',
    benchmarkReturnPct: 3.4,
    pipMetrics: {
      pipGain: 310,
      maxPipDrawdown: 112,
      avgSpreadPips: 1.0
    },
    strategyId: 'strat-fx-11',
    strategyName: 'G10 Momentum Carry Bias (G10-CY)',
    author: 'Dr. Marcus Vance',
    authorAvatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
    market: 'Forex',
    type: 'momentum',
    returnPct: 14.2,
    returnDollar: 14200,
    maxDrawdownPct: 5.60,
    consistencyScorePct: 52.4,
    tradeCount: 340,
    estimatedCosts: 1420,
    sharpe: 1.45,
    winRate: 51.2,
    profitFactor: 1.38,
    decision: 'ELIMINATE',
    decisionReason: 'ELIMINATED BY RISK BREACH: Strategy maximum drawdown reached 5.60%, breaching the strict 3.5% Forex group risk ceiling. Unhedged carry exposure suffered severe adverse excursions during unexpected central bank currency interventions.',
    nextGate: 'Paused / Backtest Overhaul (Integrate volatility carry filter & tail put options)',
    backtestReportId: 'bt-run-7416',
    evidenceNotes: 'Negative skewness detected in carry unwinds. Disqualified from Forex group ranking progression.'
  },
  {
    id: 'entry-06',
    rank: 9,
    divisionRank: 5,
    division: 'Equities & Multi-Asset',
    benchmarkName: 'S&P 500 (+24.2%)',
    benchmarkReturnPct: 24.2,
    strategyId: 'strat-event-07',
    strategyName: 'High Beta Earnings Post-Announcement Drift (PEAD)',
    author: 'Dr. Marcus Vance',
    authorAvatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
    market: 'Equities',
    type: 'event-driven',
    returnPct: -4.8,
    returnDollar: -4800,
    maxDrawdownPct: 14.80,
    consistencyScorePct: 32.1,
    tradeCount: 320,
    estimatedCosts: 3840,
    sharpe: 0.42,
    winRate: 46.2,
    profitFactor: 0.94,
    decision: 'ELIMINATE',
    decisionReason: 'ELIMINATED & RETIRED: Negative expectancy (-0.15R) and 14.80% maximum drawdown. Modern HFT market makers arbitrate opening cross imbalances within 45s, creating severe adverse execution drag for this model.',
    nextGate: 'Permanently Retired / Archived',
    backtestReportId: 'bt-run-7406',
    evidenceNotes: 'Severe 15 bps slippage on market open orders eroded all theoretical alpha. Gap down tails inflicted outsized losses.'
  }
];

// ========================================================
// PAPER TRADING POSITIONS (Clearly Labeled as Simulated Paper Results)
// ========================================================

export const INITIAL_PAPER_POSITIONS: PaperPosition[] = [
  {
    id: 'pos-fx-01',
    symbol: 'EUR/USD',
    name: 'Euro / US Dollar (Simulated Paper)',
    side: 'LONG',
    quantity: 100000,
    entryPrice: 1.0838,
    currentPrice: 1.0845,
    unrealizedPnl: 70.00,
    unrealizedPnlPct: 0.65,
    stopPrice: 1.0822,
    targetPrice: 1.0870,
    strategyId: 'strat-fx-09',
    strategyName: 'London-NY Session Breakout (LNY-FX)',
    openedAt: 'Today, 08:35 EST',
    riskAmount: 160.00
  },
  {
    id: 'pos-01',
    symbol: 'NVDA',
    name: 'NVIDIA Corporation (Paper Sim)',
    side: 'LONG',
    quantity: 350,
    entryPrice: 124.50,
    currentPrice: 129.80,
    unrealizedPnl: 1855.00,
    unrealizedPnlPct: 4.26,
    stopPrice: 122.10,
    targetPrice: 136.50,
    strategyId: 'strat-vol-01',
    strategyName: 'Volatility Expansion Matrix (VEM-4)',
    openedAt: 'Today, 09:45 EST',
    riskAmount: 840.00
  },
  {
    id: 'pos-02',
    symbol: 'AMD',
    name: 'Advanced Micro Devices (Paper Sim)',
    side: 'SHORT',
    quantity: 400,
    entryPrice: 158.20,
    currentPrice: 154.60,
    unrealizedPnl: 1440.00,
    unrealizedPnlPct: 2.28,
    stopPrice: 161.40,
    targetPrice: 148.00,
    strategyId: 'strat-pairs-02',
    strategyName: 'Stat-Arb Cointegration Pairs (SACP-X)',
    openedAt: 'Today, 10:12 EST',
    riskAmount: 1280.00
  },
  {
    id: 'pos-03',
    symbol: 'BTC/USDT',
    name: 'Bitcoin Perpetual (Paper Sim)',
    side: 'LONG',
    quantity: 1.25,
    entryPrice: 63820.00,
    currentPrice: 64450.00,
    unrealizedPnl: 787.50,
    unrealizedPnlPct: 0.99,
    stopPrice: 63200.00,
    targetPrice: 65800.00,
    strategyId: 'strat-crypto-03',
    strategyName: 'Orderflow Microstructure Reversion (OMR-B)',
    openedAt: 'Today, 11:05 EST',
    riskAmount: 775.00
  },
  {
    id: 'pos-04',
    symbol: 'QQQ',
    name: 'Invesco QQQ Trust (Paper Sim)',
    side: 'LONG',
    quantity: 250,
    entryPrice: 482.10,
    currentPrice: 484.20,
    unrealizedPnl: 525.00,
    unrealizedPnlPct: 0.44,
    stopPrice: 479.50,
    targetPrice: 489.00,
    strategyId: 'strat-vol-01',
    strategyName: 'Volatility Expansion Matrix (VEM-4)',
    openedAt: 'Today, 10:30 EST',
    riskAmount: 650.00
  },
  {
    id: 'pos-05',
    symbol: 'ETH/USDT',
    name: 'Ethereum Perpetual (Paper Sim)',
    side: 'SHORT',
    quantity: 12.0,
    entryPrice: 2680.00,
    currentPrice: 2707.25,
    unrealizedPnl: -327.00,
    unrealizedPnlPct: -1.02,
    stopPrice: 2725.00,
    targetPrice: 2610.00,
    strategyId: 'strat-crypto-03',
    strategyName: 'Orderflow Microstructure Reversion (OMR-B)',
    openedAt: 'Today, 11:40 EST',
    riskAmount: 540.00
  }
];

export const INITIAL_PAPER_ORDERS: PaperOrder[] = [
  {
    id: 'ord-sim-992',
    symbol: 'EUR/USD',
    side: 'BUY',
    type: 'LIMIT',
    quantity: 100000,
    submittedAt: 'Today, 08:35:10 EST',
    filledAt: 'Today, 08:35:12 EST',
    fillPrice: 1.0838,
    status: 'FILLED',
    strategyName: 'London-NY Session Breakout Matrix (LNY-FX)',
    reason: '[SIMULATED PAPER RESULT] Signal #sig-8842 London/NY breakout fill @ 1.0838; passed Risk Limit RK-FX-01 (1.0% FX risk cap); simulated spread 0.8 pips; routed to Simulated EBS/ECN Gateway.'
  },
  {
    id: 'ord-sim-991',
    symbol: 'ETH/USDT',
    side: 'SELL',
    type: 'MARKET',
    quantity: 12.0,
    submittedAt: 'Today, 11:40:02 EST',
    filledAt: 'Today, 11:40:03 EST',
    fillPrice: 2680.00,
    status: 'FILLED',
    strategyName: 'Orderflow Microstructure Reversion (OMR-B)',
    reason: 'Signal #sig-8839 CVD divergence confirmed; passed Risk Limit RK-01 ($18.5k committed); simulated fill routed to Alpaca Sandbox'
  },
  {
    id: 'ord-sim-990',
    symbol: 'BTC/USDT',
    side: 'BUY',
    type: 'LIMIT',
    quantity: 1.25,
    submittedAt: 'Today, 11:04:45 EST',
    filledAt: 'Today, 11:05:12 EST',
    fillPrice: 63820.00,
    status: 'FILLED',
    strategyName: 'Orderflow Microstructure Reversion (OMR-B)',
    reason: 'Signal #sig-8838 limit fill on liquidity cascade bounce; passed Risk Limit RK-02 (0.75% equity risk)'
  },
  {
    id: 'ord-sim-989',
    symbol: 'QQQ',
    side: 'BUY',
    type: 'MARKET',
    quantity: 250,
    submittedAt: 'Today, 10:30:00 EST',
    filledAt: 'Today, 10:30:01 EST',
    fillPrice: 482.10,
    status: 'FILLED',
    strategyName: 'Volatility Expansion Matrix (VEM-4)',
    reason: 'Keltner channel 15m breakout on 2.4x volume; checked against RK-06 (Sector Limit: 18.2% vs 25% cap); simulated paper fill confirmed'
  },
  {
    id: 'ord-sim-988',
    symbol: 'AMD',
    side: 'SELL',
    type: 'MARKET',
    quantity: 400,
    submittedAt: 'Today, 10:12:05 EST',
    filledAt: 'Today, 10:12:06 EST',
    fillPrice: 158.20,
    status: 'FILLED',
    strategyName: 'Stat-Arb Cointegration Pairs (SACP-X)',
    reason: 'Signal #sig-8840 leg B short fill for SMH vs AMD pair; passed RK-07 leverage check (1.14x gross); simulated fill executed'
  },
  {
    id: 'ord-sim-987',
    symbol: 'NVDA',
    side: 'BUY',
    type: 'MARKET',
    quantity: 350,
    submittedAt: 'Today, 09:45:10 EST',
    filledAt: 'Today, 09:45:11 EST',
    fillPrice: 124.50,
    status: 'FILLED',
    strategyName: 'Volatility Expansion Matrix (VEM-4)',
    reason: 'Morning expansion sweep beyond 15m ATR range; passed RK-02 risk limit (1.0% equity risk); paper fill confirmed'
  },
  {
    id: 'ord-sim-986',
    symbol: 'SPY',
    side: 'BUY',
    type: 'LIMIT',
    quantity: 300,
    submittedAt: 'Today, 09:32:00 EST',
    status: 'CANCELLED',
    strategyName: 'Volatility Expansion Matrix (VEM-4)',
    reason: 'Price moved past limit threshold before fill (Time-in-Force 15m expired)'
  },
  {
    id: 'ord-sim-985',
    symbol: 'TSLA',
    side: 'BUY',
    type: 'MARKET',
    quantity: 200,
    submittedAt: 'Yesterday, 15:40:00 EST',
    status: 'REJECTED',
    strategyName: 'High Beta PEAD (Retired)',
    reason: 'Rejected by Nexus Risk Engine: Strategy PEAD is RETIRED and breached single-asset risk ceiling'
  }
];

// ========================================================
// TRADING SIGNALS (Connected to Strategy, Rationale, Risk Limit & Paper Action)
// ========================================================

export const INITIAL_SIGNALS: TradingSignal[] = [
  {
    id: 'sig-8842',
    strategyId: 'strat-fx-09',
    strategyName: 'London-NY Session Breakout Matrix (LNY-FX)',
    symbol: 'EUR/USD',
    assetClass: 'Forex',
    direction: 'LONG',
    strength: 'Strong',
    confidence: 88,
    generatedAt: '18 mins ago',
    expiration: 'in 42 mins',
    currentPrice: 1.0845,
    proposedEntry: 1.0850,
    proposedStop: 1.0834,
    proposedTarget: 1.0882,
    riskReward: '1 : 2.00 (16 pips / 32 pips)',
    evidence: 'London/NY overlap momentum pulse. EUR/USD broken 1.0842 Asian high by +8 pips with tick volume 2.4x 20-period SMA; institutional EBS spread tight at 0.7 pips.',
    status: 'NEW',
    rationale: 'Active session London/NY overlap (08:00 - 11:30 EST). Breakout confirmed on 15m candle close above Asian session upper band. Modeled spread 0.8 pips.',
    riskLimitCheck: {
      limitId: 'RK-FX-01',
      limitName: 'Forex Major Exposure Cap (1.0% Risk Limit)',
      currentValue: '0.85% equity at risk (16 pips stop on 1.0 standard lot)',
      threshold: '1.0% Forex Equity Limit',
      status: 'PASSED'
    },
    resultingPaperAction: {
      actionType: 'WAITING_VALIDATION',
      details: '[SIMULATED PAPER RESULT] Awaiting Quant Architect validation to route simulated paper order: Buy 1.0 Standard Lot EUR/USD @ 1.0850 (Alpaca Sandbox / EBS mock gateway). Live trading disabled.'
    }
  },
  {
    id: 'sig-8841',
    strategyId: 'strat-vol-01',
    strategyName: 'Volatility Expansion Matrix (VEM-4)',
    symbol: 'MSFT',
    assetClass: 'Equities',
    direction: 'LONG',
    strength: 'Strong',
    confidence: 89,
    generatedAt: '12 mins ago',
    expiration: 'in 48 mins',
    currentPrice: 428.40,
    proposedEntry: 428.50,
    proposedStop: 424.10,
    proposedTarget: 438.00,
    riskReward: '1 : 2.18',
    evidence: 'Bollinger Bandwidth contracted to 8th percentile; Keltner upper breach with 2.8x volume surge.',
    status: 'NEW',
    rationale: 'Volatility squeeze expansion confirmed on 15m chart. Squeeze index < 10th percentile over 60 bars with volume continuation.',
    riskLimitCheck: {
      limitId: 'RK-02',
      limitName: 'Max Risk Per Trade (1.5% Cap)',
      currentValue: '1.0% modeled risk',
      threshold: '1.5% Equity Limit',
      status: 'PASSED'
    },
    resultingPaperAction: {
      actionType: 'WAITING_VALIDATION',
      details: 'Awaiting Quant Architect one-click validation to route simulated paper limit order for 100 shares @ $428.50.'
    }
  },
  {
    id: 'sig-8840',
    strategyId: 'strat-pairs-02',
    strategyName: 'Stat-Arb Cointegration Pairs (SACP-X)',
    symbol: 'SMH / INTC',
    assetClass: 'Equities Pairs',
    direction: 'LONG',
    strength: 'Strong',
    confidence: 91,
    generatedAt: '24 mins ago',
    expiration: 'in 36 mins',
    currentPrice: 24.80,
    proposedEntry: 24.85,
    proposedStop: 23.90,
    proposedTarget: 26.90,
    riskReward: '1 : 2.15',
    evidence: 'Johansen residual spread expanded to Z = +2.64. Stationarity confirmed with zero autocorrelation.',
    status: 'VALIDATED',
    rationale: 'Cointegration spread diverged by > 2.3 standard deviations from rolling Kalman filter mean. Residual half-life is 112 mins.',
    riskLimitCheck: {
      limitId: 'RK-06',
      limitName: 'Sector Concentration (25% Cap)',
      currentValue: '18.2% Tech Allocation',
      threshold: '25.0% Sector Ceiling',
      status: 'PASSED'
    },
    resultingPaperAction: {
      actionType: 'WAITING_VALIDATION',
      details: 'Validated by Dr. Marcus Vance. Ready to route simultaneous market pairs execution to Alpaca Sandbox.'
    }
  },
  {
    id: 'sig-8839',
    strategyId: 'strat-crypto-03',
    strategyName: 'Orderflow Microstructure Reversion (OMR-B)',
    symbol: 'SOL/USDT',
    assetClass: 'Crypto',
    direction: 'LONG',
    strength: 'Moderate',
    confidence: 81,
    generatedAt: '38 mins ago',
    expiration: 'in 22 mins',
    currentPrice: 154.20,
    proposedEntry: 153.80,
    proposedStop: 151.40,
    proposedTarget: 160.00,
    riskReward: '1 : 2.58',
    evidence: '$14.2M short liquidation cascade swept low of day with sharp CVD divergence on 1m chart.',
    status: 'WATCHING',
    rationale: 'Open interest flush accompanied by positive CVD delta absorption. Exhaustion volume pattern detected.',
    riskLimitCheck: {
      limitId: 'RK-01',
      limitName: 'Max Single-Position Size ($100k Cap)',
      currentValue: '$18,500 commitment',
      threshold: '$100,000 Position Ceiling',
      status: 'PASSED'
    },
    resultingPaperAction: {
      actionType: 'WAITING_VALIDATION',
      details: 'Watching orderbook depth. Feed latency is elevated (Binance L3 142ms) so limit execution is buffered.'
    }
  },
  {
    id: 'sig-8838',
    strategyId: 'strat-vol-01',
    strategyName: 'Volatility Expansion Matrix (VEM-4)',
    symbol: 'NVDA',
    assetClass: 'Equities',
    direction: 'LONG',
    strength: 'Strong',
    confidence: 92,
    generatedAt: '2 hours ago',
    expiration: 'Expired',
    currentPrice: 129.80,
    proposedEntry: 124.50,
    proposedStop: 122.10,
    proposedTarget: 136.50,
    riskReward: '1 : 5.00',
    evidence: 'Morning expansion sweep confirmed; order executed.',
    status: 'PAPER_ORDER_CREATED',
    rationale: 'Breakout above 15m Keltner channel with 2.8x volume surge.',
    riskLimitCheck: {
      limitId: 'RK-02',
      limitName: 'Max Risk Per Trade (1.5% Cap)',
      currentValue: '0.92% risk',
      threshold: '1.5% Equity Limit',
      status: 'PASSED'
    },
    resultingPaperAction: {
      actionType: 'ROUTED_PAPER_ORDER',
      paperOrderId: 'ord-sim-987',
      details: 'Filled simulated market order #ord-sim-987 for 350 shares @ $124.50 (Unrealized Paper PnL: +$1,855.00).',
      timestamp: 'Today, 09:45 EST'
    }
  },
  {
    id: 'sig-8837',
    strategyId: 'strat-mom-04',
    strategyName: 'Cross-Asset Momentum Alpha (CAMA-8)',
    symbol: 'GLD',
    assetClass: 'Commodities ETF',
    direction: 'LONG',
    strength: 'Moderate',
    confidence: 77,
    generatedAt: '3 hours ago',
    expiration: 'in 5 hours',
    currentPrice: 242.10,
    proposedEntry: 242.30,
    proposedStop: 238.50,
    proposedTarget: 251.00,
    riskReward: '1 : 2.29',
    evidence: 'Top decile 63-day Sharpe ratio ranking across multi-asset universe.',
    status: 'REJECTED',
    rationale: 'Top decile ranking in multi-asset momentum universe.',
    riskLimitCheck: {
      limitId: 'RK-04',
      limitName: 'Tournament Risk Ceiling (4.0% Max DD)',
      currentValue: '7.20% Max DD (Breach)',
      threshold: '4.0% Max DD Ceiling',
      status: 'BREACHED'
    },
    resultingPaperAction: {
      actionType: 'BLOCKED_BY_RISK',
      details: 'Order blocked by Nexus Risk Engine. Strategy CAMA-8 was eliminated from Tournament Round 4 due to 7.2% drawdown breach.'
    }
  },
  {
    id: 'sig-8836',
    strategyId: 'strat-event-07',
    strategyName: 'High Beta PEAD (Retired)',
    symbol: 'TSLA',
    assetClass: 'Equities',
    direction: 'SHORT',
    strength: 'Weak',
    confidence: 42,
    generatedAt: '4 hours ago',
    expiration: 'Expired',
    currentPrice: 245.80,
    proposedEntry: 246.00,
    proposedStop: 252.00,
    proposedTarget: 234.00,
    riskReward: '1 : 2.00',
    evidence: 'Earnings post-drift signal triggered, but strategy is archived.',
    status: 'REJECTED',
    rationale: 'Post-announcement negative revision drift candidate.',
    riskLimitCheck: {
      limitId: 'RK-09',
      limitName: 'Governance Status',
      currentValue: 'Strategy RETIRED',
      threshold: 'Active Authorization Required',
      status: 'BREACHED'
    },
    resultingPaperAction: {
      actionType: 'BLOCKED_BY_RISK',
      details: 'Blocked: PEAD is permanently retired due to structural HFT front-running and negative expectancy.'
    }
  }
];

export const INITIAL_WATCHLIST: MarketWatchItem[] = [
  {
    symbol: 'NVDA',
    name: 'NVIDIA Corp',
    market: 'Equities',
    price: 129.80,
    change24h: 3.42,
    volume: '$6.8B',
    volatility: 'High',
    trend: 'Bullish',
    signalCount: 4,
    lastSignal: '2h ago',
    dataAge: '0.4s',
    sparkline: [122, 123.5, 123.1, 125, 126.8, 127.4, 129.8]
  },
  {
    symbol: 'SPY',
    name: 'SPDR S&P 500 ETF',
    market: 'ETFs',
    price: 574.60,
    change24h: 0.65,
    volume: '$24.1B',
    volatility: 'Low',
    trend: 'Bullish',
    signalCount: 2,
    lastSignal: '45m ago',
    dataAge: '0.2s',
    sparkline: [571, 572, 571.8, 573.2, 574.0, 573.8, 574.6]
  },
  {
    symbol: 'QQQ',
    name: 'Invesco QQQ Trust',
    market: 'ETFs',
    price: 484.20,
    change24h: 0.94,
    volume: '$16.4B',
    volatility: 'Medium',
    trend: 'Bullish',
    signalCount: 3,
    lastSignal: '1h ago',
    dataAge: '0.3s',
    sparkline: [478, 480, 479.5, 481.8, 483.2, 482.9, 484.2]
  },
  {
    symbol: 'BTC/USDT',
    name: 'Bitcoin Perpetual (Paper)',
    market: 'Crypto',
    price: 64450.00,
    change24h: 2.18,
    volume: '$31.8B',
    volatility: 'High',
    trend: 'Bullish',
    signalCount: 5,
    lastSignal: '38m ago',
    dataAge: '0.1s',
    sparkline: [62800, 63100, 62950, 63500, 64100, 63900, 64450]
  },
  {
    symbol: 'ETH/USDT',
    name: 'Ethereum Perpetual (Paper)',
    market: 'Crypto',
    price: 2707.25,
    change24h: -0.85,
    volume: '$14.2B',
    volatility: 'High',
    trend: 'Neutral',
    signalCount: 3,
    lastSignal: '1h ago',
    dataAge: '0.1s',
    sparkline: [2740, 2735, 2720, 2690, 2710, 2695, 2707]
  },
  {
    symbol: 'EUR/USD',
    name: 'Euro / US Dollar',
    market: 'Forex',
    price: 1.0845,
    change24h: 0.12,
    volume: '$84.5B',
    volatility: 'Low',
    trend: 'Neutral',
    signalCount: 1,
    lastSignal: '4h ago',
    dataAge: '0.6s',
    sparkline: [1.083, 1.0835, 1.084, 1.0838, 1.0842, 1.0844, 1.0845]
  },
  {
    symbol: 'USD/JPY',
    name: 'US Dollar / Japanese Yen',
    market: 'Forex',
    price: 144.20,
    change24h: -0.48,
    volume: '$62.1B',
    volatility: 'Medium',
    trend: 'Bearish',
    signalCount: 2,
    lastSignal: '2h ago',
    dataAge: '0.5s',
    sparkline: [145.4, 145.1, 144.9, 144.6, 144.4, 144.3, 144.2]
  },
  {
    symbol: 'GLD',
    name: 'SPDR Gold Shares',
    market: 'Commodities',
    price: 242.10,
    change24h: 1.15,
    volume: '$2.8B',
    volatility: 'Low',
    trend: 'Bullish',
    signalCount: 2,
    lastSignal: '3h ago',
    dataAge: '0.8s',
    sparkline: [238, 239, 239.8, 240.5, 241.2, 241.6, 242.1]
  }
];

export const INITIAL_MARKET_INTELLIGENCE: MarketIntelligenceItem[] = [
  {
    id: 'intel-01',
    title: 'FOMC Member Speech: Neutral Rate Projections Hint at Faster Easing',
    source: 'Macro Desk',
    timestamp: '25 mins ago',
    category: 'Macro',
    affectedSymbols: ['SPY', 'QQQ', '2Y Treasury', '10Y Treasury', 'USD/JPY'],
    confidence: 88,
    materiality: 'High',
    relatedStrategy: 'Macro Yield Curve Dislocation (MYCD-2)',
    alphaInterpretation: 'Yield curve flattening pressure observed. High probability of front-end yield compressions. Trading Alpha recommends maintaining 2s10s duration neutrality limits.',
    recommendation: 'Maintain duration-neutral hedge; do not widen spread risk'
  },
  {
    id: 'intel-02',
    title: 'Semiconductor Foundry Equipment Export Restrictions Expanded',
    source: 'Bloomberg Feeds',
    timestamp: '1 hour ago',
    category: 'Event-Driven',
    affectedSymbols: ['SMH', 'NVDA', 'AMD', 'ASML', 'INTC'],
    confidence: 94,
    materiality: 'High',
    relatedStrategy: 'Stat-Arb Cointegration Pairs (SACP-X)',
    alphaInterpretation: 'Structural divergence risk between equipment manufacturers and fabless designers. Cointegration residuals likely to expand beyond 3.0 sigma.',
    recommendation: 'Pause automatic execution on SMH pairs with ASML leg until price dispersion stabilizes'
  },
  {
    id: 'intel-03',
    title: 'Cryptocurrency Open Interest Surges to 90-Day High on Deribit & CME',
    source: 'Nexus Research',
    timestamp: '2 hours ago',
    category: 'Regime Shift',
    affectedSymbols: ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'],
    confidence: 85,
    materiality: 'Medium',
    relatedStrategy: 'Orderflow Microstructure Reversion (OMR-B)',
    alphaInterpretation: 'Elevated open interest with compressed funding rates signals high vulnerability to cascading liquidation squeezes. Prime conditions for mean-reverting scalp fills.',
    recommendation: 'Active paper monitoring enabled; retain 0.75% max risk cap'
  },
  {
    id: 'intel-04',
    title: 'CBOE S&P 500 VIX Term Structure Inversion Detected in 1M vs 3M Futures',
    source: 'Alpha Intel',
    timestamp: '3 hours ago',
    category: 'Volatility',
    affectedSymbols: ['SPX', 'VIX', 'UVXY'],
    confidence: 91,
    materiality: 'High',
    relatedStrategy: 'Volatility Expansion Matrix (VEM-4)',
    alphaInterpretation: 'Short-term backwardation in volatility curve indicates acute institutional demand for immediate gamma protection. Asymmetric breakout frequency increases 3.4x.',
    recommendation: 'Favor long breakout entries over short reversion trades'
  },
  {
    id: 'intel-05',
    title: 'ECB Monetary Policy & Eurozone Core CPI Flash Estimate: Rate Cut Probability at 88%',
    source: 'Macro Desk',
    timestamp: '45 mins ago',
    category: 'Macro',
    affectedSymbols: ['EUR/USD', 'EUR/GBP', 'EUR/JPY'],
    confidence: 92,
    materiality: 'High',
    relatedStrategy: 'London-NY Session Breakout Matrix (LNY-FX)',
    alphaInterpretation: 'ECB forward guidance confirms impending 25bps rate trim. EUR/USD implied volatility skew shifts to put dominance. London session momentum breakout triggers favor downside continuation below 1.0820 with tight 0.8 pip spreads.',
    recommendation: 'Observe strict 30-minute pre-announcement trading blackout on EUR pairs; resume London/NY overlap breakout rules post-press conference.'
  }
];

export const INITIAL_ECONOMIC_EVENTS: EconomicEventItem[] = [
  {
    id: 'eco-01',
    eventName: 'ECB Monetary Policy Decision & Rate Statement',
    country: 'EUR',
    flag: '🇪🇺',
    timeEst: 'Today, 08:15 EST',
    impact: 'Critical',
    affectedPairs: ['EUR/USD', 'EUR/GBP', 'EUR/JPY'],
    consensus: '3.25%',
    previous: '3.50%',
    actual: '3.25%',
    volatilityEstimate: 'High (+/- 45 pips)',
    status: 'ACTIVE'
  },
  {
    id: 'eco-02',
    eventName: 'US Non-Farm Payrolls (NFP) & Unemployment Rate',
    country: 'USD',
    flag: '🇺🇸',
    timeEst: 'Tomorrow, 08:30 EST',
    impact: 'Critical',
    affectedPairs: ['EUR/USD', 'USD/JPY', 'GBP/USD'],
    consensus: '165K',
    previous: '142K',
    volatilityEstimate: 'Extreme (+/- 75 pips)',
    status: 'UPCOMING'
  },
  {
    id: 'eco-03',
    eventName: 'Bank of Japan (BOJ) Policy Rate Statement & Outlook',
    country: 'JPY',
    flag: '🇯🇵',
    timeEst: 'Thu, 23:30 EST',
    impact: 'High',
    affectedPairs: ['USD/JPY', 'EUR/JPY'],
    consensus: '0.25%',
    previous: '0.25%',
    volatilityEstimate: 'High (+/- 60 pips)',
    status: 'UPCOMING'
  },
  {
    id: 'eco-04',
    eventName: 'UK Consumer Price Index (CPI YoY)',
    country: 'GBP',
    flag: '🇬🇧',
    timeEst: 'Wed, 02:00 EST',
    impact: 'High',
    affectedPairs: ['GBP/USD', 'EUR/GBP'],
    consensus: '2.2%',
    previous: '2.2%',
    volatilityEstimate: 'Moderate (+/- 35 pips)',
    status: 'UPCOMING'
  },
  {
    id: 'eco-05',
    eventName: 'US Initial Jobless Claims (Weekly)',
    country: 'USD',
    flag: '🇺🇸',
    timeEst: 'Thu, 08:30 EST',
    impact: 'Medium',
    affectedPairs: ['EUR/USD', 'USD/JPY'],
    consensus: '218K',
    previous: '219K',
    volatilityEstimate: 'Low (+/- 15 pips)',
    status: 'UPCOMING'
  }
];

export const INITIAL_RISK_LIMITS: RiskLimitItem[] = [
  {
    id: 'rk-01',
    name: 'Max Single-Position Size',
    currentValue: 48500,
    limitValue: 100000,
    unit: '$ USD',
    status: 'SAFE',
    category: 'Exposure',
    description: 'Maximum simulated dollar capital committed to any individual position.'
  },
  {
    id: 'rk-02',
    name: 'Max Risk Per Trade',
    currentValue: 1.15,
    limitValue: 1.50,
    unit: '% Equity',
    status: 'SAFE',
    category: 'Exposure',
    description: 'Max calculated dollar loss at stop-loss point relative to total equity.'
  },
  {
    id: 'rk-03',
    name: 'Max Daily Portfolio Loss',
    currentValue: 2840,
    limitValue: 15000,
    unit: '$ USD',
    status: 'SAFE',
    category: 'Drawdown',
    description: 'Intraday circuit breaker. Reaching this halts all new order generation.'
  },
  {
    id: 'rk-04',
    name: 'Max Total Portfolio Drawdown',
    currentValue: 1.42,
    limitValue: 4.00,
    unit: '% Peak Equity',
    status: 'SAFE',
    category: 'Drawdown',
    description: 'Cumulative peak-to-trough paper drawdown ceiling under policy RP-2026.4.'
  },
  {
    id: 'rk-05',
    name: 'Max Concurrent Open Positions',
    currentValue: 5,
    limitValue: 10,
    unit: 'Positions',
    status: 'SAFE',
    category: 'Capital',
    description: 'Total simultaneous paper open trades permitted across all active strategies.'
  },
  {
    id: 'rk-06',
    name: 'Max Sector Concentration',
    currentValue: 18.2,
    limitValue: 25.0,
    unit: '% Equity',
    status: 'SAFE',
    category: 'Exposure',
    description: 'Technology / Semiconductor sector allocation ceiling.'
  },
  {
    id: 'rk-07',
    name: 'Simulated Portfolio Leverage',
    currentValue: 1.14,
    limitValue: 1.50,
    unit: 'x Gross',
    status: 'SAFE',
    category: 'Leverage',
    description: 'Gross open notional exposure divided by total equity.'
  },
  {
    id: 'rk-08',
    name: 'Max Strategy Allocation',
    currentValue: 22.5,
    limitValue: 30.0,
    unit: '% Capital',
    status: 'SAFE',
    category: 'Capital',
    description: 'Cap on buying power allocated to a single quantitative strategy.'
  },
  {
    id: 'rk-09',
    name: 'Emergency Kill-Switch State',
    currentValue: 0,
    limitValue: 0,
    unit: 'Disengaged',
    status: 'SAFE',
    category: 'Execution',
    description: 'Global master halt switch for all trading engine activities.'
  },
  {
    id: 'rk-fx-01',
    name: 'Forex Single Pair Max Exposure',
    currentValue: 0.85,
    limitValue: 1.00,
    unit: '% Capital',
    status: 'SAFE',
    category: 'Exposure',
    description: 'Maximum risk exposure permitted across any single G10 currency pair.'
  },
  {
    id: 'rk-fx-02',
    name: 'Forex Group Max Drawdown Ceiling',
    currentValue: 1.85,
    limitValue: 3.50,
    unit: '% Ceiling',
    status: 'SAFE',
    category: 'Drawdown',
    description: 'Strict 3.5% maximum drawdown limit for active Forex quantitative models.'
  }
];

export const INITIAL_DATA_PROVIDERS: DataProviderItem[] = [
  {
    id: 'prov-01',
    name: 'Polygon.io Enterprise Feed',
    category: 'Market Feeds',
    status: 'Operational',
    latencyMs: 24,
    errorRatePct: 0.01,
    rateLimitUsedPct: 34,
    lastHeartbeat: '0.8s ago',
    uptimePct: 99.99
  },
  {
    id: 'prov-06',
    name: 'EBS / Currenex Institutional FX L2 Feed',
    category: 'Market Feeds',
    status: 'Operational',
    latencyMs: 16,
    errorRatePct: 0.01,
    rateLimitUsedPct: 24,
    lastHeartbeat: '0.4s ago',
    uptimePct: 99.99
  },
  {
    id: 'prov-02',
    name: 'FactSet Institutional Orderbook',
    category: 'Market Feeds',
    status: 'Operational',
    latencyMs: 38,
    errorRatePct: 0.02,
    rateLimitUsedPct: 52,
    lastHeartbeat: '1.2s ago',
    uptimePct: 99.98
  },
  {
    id: 'prov-03',
    name: 'Binance Microstructure L3 Stream',
    category: 'Market Feeds',
    status: 'Degraded', // Feed alert causing engine status Degraded
    latencyMs: 142,
    errorRatePct: 1.80,
    rateLimitUsedPct: 82,
    lastHeartbeat: '0.2s ago',
    uptimePct: 98.20
  },
  {
    id: 'prov-04',
    name: 'Alpaca Sandbox Execution Gateway',
    category: 'Execution Gateway',
    status: 'Operational',
    latencyMs: 65,
    errorRatePct: 0.00,
    rateLimitUsedPct: 18,
    lastHeartbeat: '1.4s ago',
    uptimePct: 99.99
  },
  {
    id: 'prov-05',
    name: 'CME Group Direct Market Gateway',
    category: 'Market Feeds',
    status: 'Operational',
    latencyMs: 19,
    errorRatePct: 0.01,
    rateLimitUsedPct: 44,
    lastHeartbeat: '0.5s ago',
    uptimePct: 99.99
  },
  {
    id: 'prov-07',
    name: 'Nexus Quant Compute Cluster (GPU-A100)',
    category: 'Compute Engine',
    status: 'Operational',
    latencyMs: 8,
    errorRatePct: 0.00,
    rateLimitUsedPct: 72,
    lastHeartbeat: '0.1s ago',
    uptimePct: 100.00
  }
];

export const INITIAL_AUDIT_LOG: TradingAuditRecord[] = [
  {
    id: 'aud-2026-910',
    timestamp: 'Today, 08:35:10 EST',
    actor: 'Nexus System Sentinel',
    action: 'DATA_FEED_DEGRADATION_ALERT',
    scope: 'Binance Microstructure L3 Stream (prov-03)',
    previousState: 'Operational (42ms)',
    newState: 'Degraded (142ms · 1.8% packet drops)',
    reason: 'Feed latency crossed 50ms SLA threshold; triggered engine status to Degraded',
    governanceHash: 'sha256:4c90e8a712b1...'
  },
  {
    id: 'aud-2026-909',
    timestamp: 'Today, 08:30:14 EST',
    actor: 'Alex Chen (Principal Quant)',
    action: 'TOURNAMENT_STAGE_PROMOTION',
    scope: 'Strategy VEM-4 (strat-vol-01)',
    previousState: 'TOURNAMENT',
    newState: 'PAPER_TRADING',
    reason: 'Advanced from Tournament Round 4 (Rank #1) and cleared Risk Review approval for simulated paper sandbox testing',
    governanceHash: 'sha256:8f4c2e88a01b...'
  },
  {
    id: 'aud-2026-908',
    timestamp: 'Today, 07:15:22 EST',
    actor: 'Dr. Marcus Vance (Risk Director)',
    action: 'RISK_GATE_REVIEW',
    scope: 'Strategy SACP-X (strat-pairs-02)',
    previousState: 'TOURNAMENT',
    newState: 'RISK_REVIEW',
    reason: 'Tournament qualification confirmed (Rank #2); initiated formal dual-risk evaluation before paper gateway authorization',
    governanceHash: 'sha256:1a77e382bc40...'
  },
  {
    id: 'aud-2026-907',
    timestamp: 'Yesterday, 17:45:00 EST',
    actor: 'Nexus Risk Engine (Autonomous Breaker)',
    action: 'TOURNAMENT_ELIMINATION',
    scope: 'Strategy CAMA-8 (strat-mom-04)',
    previousState: 'TOURNAMENT',
    newState: 'PAUSED',
    reason: 'Drawdown reached 7.20%, violating the strict 4.0% tournament drawdown ceiling. Strategy paused for re-engineering',
    governanceHash: 'sha256:7b901aef4421...'
  },
  {
    id: 'aud-2026-906',
    timestamp: '2026-09-24, 14:32:00 EST',
    actor: 'Nexus Trading Alpha Engine (Autonomous)',
    action: 'TRADING_ALPHA_EVALUATION',
    scope: 'Strategy VEM-4 (strat-vol-01)',
    previousState: 'Evaluation Pending',
    newState: 'QUALIFIED FOR TOURNAMENT',
    reason: 'Trading Alpha completed Monte Carlo stress testing across 3 regimes with p < 0.001 and minimal OOS Sharpe decay',
    governanceHash: 'sha256:99014ccbe712...'
  }
];

export const INITIAL_PAST_BACKTESTS: BacktestResultRecord[] = [
  {
    id: 'bt-run-7414',
    strategyId: 'strat-fx-09',
    strategyName: 'London-NY Session Breakout Matrix (LNY-FX)',
    strategyVersion: 'v2.4',
    codeHash: 'git-fx-77c102',
    datasetVersion: 'EBS-Currenex-L2-Tick-G10-2026.2',
    universe: 'EUR/USD, GBP/USD, USD/JPY (G10 Majors)',
    dateRange: '2023-01-01 to 2026-06-30',
    timeframe: '15m',
    initialCapital: 100000,
    feesBps: 0.8,
    slippageBps: 0.8,
    sizingModel: 'Session Volatility Risk Parity (1.0% equity risk per trade)',
    maxRiskPerTradePct: 1.0,
    runTimestamp: '2026-09-24 11:20 EST',
    runtimeMs: 4210,
    totalTrades: 412,
    winRate: 64.2,
    profitFactor: 2.24,
    sharpeRatio: 2.18,
    sortinoRatio: 3.12,
    maxDrawdownPct: 1.85,
    totalReturnPct: 58.4,
    benchmarkReturnPct: 4.2,
    equityCurve: [
      { date: '2023-01', equity: 100000, benchmark: 100000, drawdown: 0 },
      { date: '2023-07', equity: 108400, benchmark: 101200, drawdown: 0.6 },
      { date: '2024-01', equity: 118200, benchmark: 102400, drawdown: 1.2 },
      { date: '2024-07', equity: 129600, benchmark: 101800, drawdown: 0.8 },
      { date: '2025-01', equity: 142100, benchmark: 103200, drawdown: 1.85 },
      { date: '2025-07', equity: 149800, benchmark: 103800, drawdown: 0.9 },
      { date: '2026-01', equity: 154200, benchmark: 104000, drawdown: 0.4 },
      { date: '2026-06', equity: 158400, benchmark: 104200, drawdown: 0.5 }
    ],
    distribution: [
      { range: '< -2R', count: 4 },
      { range: '-2R to -1R', count: 32 },
      { range: '-1R to 0', count: 111 },
      { range: '0 to +1R', count: 88 },
      { range: '+1R to +2R', count: 122 },
      { range: '+2R to +3R', count: 45 },
      { range: '> +3R', count: 10 }
    ],
    status: 'SUCCESS'
  },
  {
    id: 'bt-run-7412',
    strategyId: 'strat-vol-01',
    strategyName: 'Volatility Expansion Matrix (VEM-4)',
    strategyVersion: 'v3.2',
    codeHash: 'git-a4f910c',
    datasetVersion: 'Polygon-US-EQ-15m-v2026.2',
    universe: 'S&P 500 Large Caps + QQQ',
    dateRange: '2020-01-01 to 2025-12-31',
    timeframe: '15m',
    initialCapital: 100000,
    feesBps: 2.0,
    slippageBps: 1.5,
    sizingModel: 'Volatility Adjusted Fixed Fractional (1.0% risk)',
    maxRiskPerTradePct: 1.0,
    runTimestamp: '2026-09-22 14:15 EST',
    runtimeMs: 3840,
    totalTrades: 1482,
    winRate: 61.4,
    profitFactor: 2.18,
    sharpeRatio: 2.14,
    sortinoRatio: 3.05,
    maxDrawdownPct: 3.84,
    totalReturnPct: 142.6,
    benchmarkReturnPct: 68.4,
    equityCurve: [
      { date: '2020-01', equity: 100000, benchmark: 100000, drawdown: 0 },
      { date: '2020-07', equity: 112000, benchmark: 94000, drawdown: 1.8 },
      { date: '2021-01', equity: 128000, benchmark: 114000, drawdown: 0.9 },
      { date: '2021-07', equity: 144000, benchmark: 126000, drawdown: 2.1 },
      { date: '2022-01', equity: 156000, benchmark: 132000, drawdown: 1.4 },
      { date: '2022-07', equity: 168000, benchmark: 112000, drawdown: 3.2 },
      { date: '2023-01', equity: 182000, benchmark: 118000, drawdown: 1.1 },
      { date: '2023-07', equity: 198000, benchmark: 134000, drawdown: 2.4 },
      { date: '2024-01', equity: 212000, benchmark: 148000, drawdown: 1.2 },
      { date: '2024-07', equity: 226000, benchmark: 158000, drawdown: 3.8 },
      { date: '2025-01', equity: 238000, benchmark: 164000, drawdown: 1.5 },
      { date: '2025-12', equity: 242600, benchmark: 168400, drawdown: 0.8 }
    ],
    distribution: [
      { range: '< -2R', count: 18 },
      { range: '-2R to -1R', count: 94 },
      { range: '-1R to 0', count: 460 },
      { range: '0 to +1R', count: 380 },
      { range: '+1R to +2R', count: 320 },
      { range: '+2R to +3R', count: 150 },
      { range: '> +3R', count: 60 }
    ],
    status: 'SUCCESS'
  },
  {
    id: 'bt-run-7411',
    strategyId: 'strat-pairs-02',
    strategyName: 'Stat-Arb Cointegration Pairs (SACP-X)',
    strategyVersion: 'v2.1',
    codeHash: 'git-b8921df',
    datasetVersion: 'FactSet-SMH-L2-Tick-2026.1',
    universe: 'SMH vs Components (NVDA, AMD, INTC, ASML)',
    dateRange: '2022-01-01 to 2026-06-30',
    timeframe: '5m',
    initialCapital: 100000,
    feesBps: 1.5,
    slippageBps: 1.0,
    sizingModel: 'Kalman Filter Beta Neutral',
    maxRiskPerTradePct: 0.75,
    runTimestamp: '2026-09-15 09:30 EST',
    runtimeMs: 5120,
    totalTrades: 2140,
    winRate: 72.8,
    profitFactor: 2.65,
    sharpeRatio: 2.45,
    sortinoRatio: 3.82,
    maxDrawdownPct: 2.15,
    totalReturnPct: 98.4,
    benchmarkReturnPct: 42.1,
    equityCurve: [
      { date: '2022-01', equity: 100000, benchmark: 100000, drawdown: 0 },
      { date: '2022-07', equity: 114000, benchmark: 88000, drawdown: 1.2 },
      { date: '2023-01', equity: 129000, benchmark: 94000, drawdown: 0.8 },
      { date: '2023-07', equity: 146000, benchmark: 116000, drawdown: 1.5 },
      { date: '2024-01', equity: 162000, benchmark: 128000, drawdown: 1.1 },
      { date: '2024-07', equity: 178000, benchmark: 136000, drawdown: 2.1 },
      { date: '2025-01', equity: 189000, benchmark: 140000, drawdown: 0.9 },
      { date: '2026-06', equity: 198400, benchmark: 142100, drawdown: 0.6 }
    ],
    distribution: [
      { range: '< -2R', count: 6 },
      { range: '-2R to -1R', count: 42 },
      { range: '-1R to 0', count: 534 },
      { range: '0 to +1R', count: 820 },
      { range: '+1R to +2R', count: 580 },
      { range: '+2R to +3R', count: 128 },
      { range: '> +3R', count: 30 }
    ],
    status: 'SUCCESS'
  },
  {
    id: 'bt-run-7410',
    strategyId: 'strat-crypto-03',
    strategyName: 'Orderflow Microstructure Reversion (OMR-B)',
    strategyVersion: 'v1.4',
    codeHash: 'git-c901e4a',
    datasetVersion: 'Binance-Coinbase-L3-Cleaned-2026.2',
    universe: 'BTC/USDT, ETH/USDT, SOL/USDT',
    dateRange: '2024-01-01 to 2026-06-30',
    timeframe: '1m / 5m',
    initialCapital: 100000,
    feesBps: 3.0,
    slippageBps: 4.0,
    sizingModel: 'Micro-Scalp Fixed Risk (0.75%)',
    maxRiskPerTradePct: 0.75,
    runTimestamp: '2026-09-18 11:20 EST',
    runtimeMs: 6420,
    totalTrades: 3410,
    winRate: 67.2,
    profitFactor: 2.28,
    sharpeRatio: 2.28,
    sortinoRatio: 3.40,
    maxDrawdownPct: 4.12,
    totalReturnPct: 114.2,
    benchmarkReturnPct: 48.5,
    equityCurve: [
      { date: '2024-01', equity: 100000, benchmark: 100000, drawdown: 0 },
      { date: '2024-07', equity: 128000, benchmark: 118000, drawdown: 1.8 },
      { date: '2025-01', equity: 154000, benchmark: 132000, drawdown: 2.4 },
      { date: '2025-07', equity: 182000, benchmark: 140000, drawdown: 3.2 },
      { date: '2026-06', equity: 214200, benchmark: 148500, drawdown: 2.1 }
    ],
    distribution: [
      { range: '< -2R', count: 24 },
      { range: '-2R to -1R', count: 180 },
      { range: '-1R to 0', count: 910 },
      { range: '0 to +1R', count: 1140 },
      { range: '+1R to +2R', count: 820 },
      { range: '+2R to +3R', count: 260 },
      { range: '> +3R', count: 76 }
    ],
    status: 'SUCCESS'
  },
  {
    id: 'bt-run-7409',
    strategyId: 'strat-mom-04',
    strategyName: 'Cross-Asset Momentum Alpha (CAMA-8)',
    strategyVersion: 'v1.1',
    codeHash: 'git-ff41a98',
    datasetVersion: 'FactSet-MultiAsset-Daily-2026',
    universe: 'Global Equity ETFs, Commodities, BTC, 10Y Treasuries',
    dateRange: '2016-01-01 to 2026-06-30',
    timeframe: 'Daily / 4h',
    initialCapital: 100000,
    feesBps: 2.5,
    slippageBps: 5.0,
    sizingModel: 'Inverse Volatility Weighting',
    maxRiskPerTradePct: 1.5,
    runTimestamp: '2026-08-25 15:45 EST',
    runtimeMs: 2980,
    totalTrades: 580,
    winRate: 54.8,
    profitFactor: 1.78,
    sharpeRatio: 1.78,
    sortinoRatio: 2.30,
    maxDrawdownPct: 7.20,
    totalReturnPct: 184.5,
    benchmarkReturnPct: 92.1,
    equityCurve: [
      { date: '2016-01', equity: 100000, benchmark: 100000, drawdown: 0 },
      { date: '2018-01', equity: 132000, benchmark: 118000, drawdown: 2.4 },
      { date: '2020-01', equity: 168000, benchmark: 138000, drawdown: 3.1 },
      { date: '2022-01', equity: 210000, benchmark: 162000, drawdown: 6.8 },
      { date: '2024-01', equity: 242000, benchmark: 174000, drawdown: 7.2 },
      { date: '2026-06', equity: 284500, benchmark: 192100, drawdown: 4.8 }
    ],
    distribution: [
      { range: '< -2R', count: 18 },
      { range: '-2R to -1R', count: 48 },
      { range: '-1R to 0', count: 196 },
      { range: '0 to +1R', count: 182 },
      { range: '+1R to +2R', count: 94 },
      { range: '+2R to +3R', count: 32 },
      { range: '> +3R', count: 10 }
    ],
    status: 'SUCCESS'
  },
  {
    id: 'bt-run-7406',
    strategyId: 'strat-event-07',
    strategyName: 'High Beta Earnings PEAD (Retired)',
    strategyVersion: 'v1.0',
    codeHash: 'git-009f123',
    datasetVersion: 'SEC-EDGAR-8K-Russell1000-2026',
    universe: 'Russell 1000 High Beta Subset',
    dateRange: '2020-01-01 to 2026-06-30',
    timeframe: 'Daily / 30m',
    initialCapital: 100000,
    feesBps: 2.0,
    slippageBps: 15.0,
    sizingModel: 'Equal Dollar Allocation',
    maxRiskPerTradePct: 2.0,
    runTimestamp: '2026-09-10 16:30 EST',
    runtimeMs: 3120,
    totalTrades: 320,
    winRate: 46.2,
    profitFactor: 0.94,
    sharpeRatio: 0.42,
    sortinoRatio: 0.51,
    maxDrawdownPct: 14.80,
    totalReturnPct: -4.8,
    benchmarkReturnPct: 58.4,
    equityCurve: [
      { date: '2020-01', equity: 100000, benchmark: 100000, drawdown: 0 },
      { date: '2021-01', equity: 108400, benchmark: 114000, drawdown: 3.2 },
      { date: '2022-01', equity: 102000, benchmark: 118000, drawdown: 8.4 },
      { date: '2023-01', equity: 98000, benchmark: 124000, drawdown: 11.2 },
      { date: '2024-01', equity: 94200, benchmark: 138000, drawdown: 14.8 },
      { date: '2026-06', equity: 95200, benchmark: 158400, drawdown: 14.8 }
    ],
    distribution: [
      { range: '< -2R', count: 32 },
      { range: '-2R to -1R', count: 48 },
      { range: '-1R to 0', count: 92 },
      { range: '0 to +1R', count: 88 },
      { range: '+1R to +2R', count: 42 },
      { range: '+2R to +3R', count: 14 },
      { range: '> +3R', count: 4 }
    ],
    status: 'SUCCESS'
  }
];

export interface ExecutionReceiptRecord {
  id: string;
  orderId: string;
  broker: string;
  strategy: string;
  symbol: string;
  timeframe: string;
  side: 'BUY' | 'SELL';
  units: string;
  fillPrice: string;
  slippagePips: string;
  timestamp: string;
  receiptHash: string;
  truthClass: 'PAPER' | 'VERIFIED';
}

export const EXECUTION_RECEIPTS_R1: ExecutionReceiptRecord[] = [
  {
    id: 'rcpt-r1-904',
    orderId: 'OANDA-PRAC-88241',
    broker: 'OANDA Practice (v20)',
    strategy: 'Wick Sequence Breakout v1',
    symbol: 'EUR_USD',
    timeframe: 'H1',
    side: 'BUY',
    units: '50,000',
    fillPrice: '1.0842',
    slippagePips: '+0.2 pips',
    timestamp: '9m ago',
    receiptHash: 'sha256:9c4a...e18b',
    truthClass: 'PAPER'
  },
  {
    id: 'rcpt-r1-903',
    orderId: 'OANDA-PRAC-88196',
    broker: 'OANDA Practice (v20)',
    strategy: 'Wick Sequence Breakout v1',
    symbol: 'EUR_USD',
    timeframe: 'H1',
    side: 'SELL',
    units: '50,000',
    fillPrice: '1.0869',
    slippagePips: '+0.3 pips',
    timestamp: '3h ago',
    receiptHash: 'sha256:4f11...a702',
    truthClass: 'PAPER'
  },
  {
    id: 'rcpt-r1-902',
    orderId: 'OANDA-PRAC-88112',
    broker: 'OANDA Practice (v20)',
    strategy: 'Wick Sequence Breakout v1',
    symbol: 'EUR_USD',
    timeframe: 'H1',
    side: 'BUY',
    units: '50,000',
    fillPrice: '1.0815',
    slippagePips: '+0.1 pips',
    timestamp: 'Yesterday 14:00',
    receiptHash: 'sha256:7d8e...33c9',
    truthClass: 'PAPER'
  }
];

export interface ReconciliationEventRecord {
  id: string;
  timestamp: string;
  engine: string;
  check: string;
  localPositions: number;
  brokerPositions: number;
  variance: string;
  status: 'MATCHED' | 'DRIFT_RESOLVED';
  truthClass: 'VERIFIED' | 'PAPER';
}

export const RECONCILIATION_EVENTS_R1: ReconciliationEventRecord[] = [
  {
    id: 'rec-991',
    timestamp: '9m ago',
    engine: 'OANDA Practice H1 Reconciler',
    check: 'Open Position & Bracket SL/TP Parity',
    localPositions: 5,
    brokerPositions: 5,
    variance: '$0.00 (0.0 pips)',
    status: 'MATCHED',
    truthClass: 'VERIFIED'
  },
  {
    id: 'rec-990',
    timestamp: '1h ago',
    engine: 'OANDA Practice H1 Reconciler',
    check: 'Hourly Candle & Order Receipt Hash Verification',
    localPositions: 5,
    brokerPositions: 5,
    variance: '$0.00',
    status: 'MATCHED',
    truthClass: 'VERIFIED'
  },
  {
    id: 'rec-989',
    timestamp: '4h ago',
    engine: 'Risk Guardrail Policy Check',
    check: 'Max Drawdown & Live-Trading Lock Verification',
    localPositions: 4,
    brokerPositions: 4,
    variance: 'LIVE_TRADING = DISABLED',
    status: 'MATCHED',
    truthClass: 'PAPER'
  }
];

