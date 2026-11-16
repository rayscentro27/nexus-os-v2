export interface SensitivityCell {
  paramX: number; // e.g. Lookback Period (bars)
  paramY: number; // e.g. ATR Multiplier
  profitFactor: number;
  sharpeRatio: number;
  winRatePct: number;
  drawdownPct: number;
  isOverfitted: boolean;
  isOptimal: boolean;
}

export interface StrategySensitivityMatrix {
  strategyId: string;
  strategyName: string;
  symbol: string;
  timeframe: string;
  paramXName: string;
  paramYName: string;
  paramXValues: number[];
  paramYValues: number[];
  grid: SensitivityCell[][];
  islandOfStabilityConfidence: number; // percentage e.g. 94.2%
  curveFitWarning: boolean;
  recommendation: string;
  monteCarlo: {
    medianReturn: number;
    pct5Var: number;
    pct95Var: number;
    maxDrawdownWorstCase: number;
    samples: number[];
  };
}

export interface ExecutionQualityRecord {
  id: string;
  orderId: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  route: string;
  submittedAt: string;
  filledAt: string;
  latencyMs: number;
  expectedPrice: number;
  actualPrice: number;
  slippagePips: number;
  slippageCostDollars: number;
  spreadAtFillPips: number;
  sessionRegime: 'Asian Session' | 'London Open' | 'NY Overlap' | 'NY Afternoon' | 'Roll/Swap';
  flaggedAnomaly?: string;
  executionGrade: 'EXCELLENT' | 'NORMAL' | 'DEGRADED_LATENCY' | 'SLIPPAGE_BREACH';
}

export interface PostTradeScorecard {
  tradeId: string;
  symbol: string;
  strategyName: string;
  side: 'LONG' | 'SHORT';
  entryTime: string;
  exitTime: string;
  entryPrice: number;
  exitPrice: number;
  stopLossPrice: number;
  takeProfitPrice: number;
  realizedPnl: number;
  realizedPips: number;
  disciplineGrade: 'A+' | 'A' | 'B+' | 'B-' | 'C' | 'F';
  maePips: number; // Maximum Adverse Excursion
  maeDollars: number;
  mfePips: number; // Maximum Favorable Excursion
  mfeDollars: number;
  pnlLeftOnTableDollars: number;
  rulesAdhered: {
    rule: string;
    passed: boolean;
    note?: string;
  }[];
  postMortemNotes: string;
}

// ---------------------------------------------------------------------------
// 1. PARAMETER SENSITIVITY MATRICES
// ---------------------------------------------------------------------------
export const SENSITIVITY_MATRICES: Record<string, StrategySensitivityMatrix> = {
  'EUR/USD': {
    strategyId: 'strat-fx-01',
    strategyName: 'EUR/USD Mean Reversion v2.1',
    symbol: 'EUR/USD',
    timeframe: '15m',
    paramXName: 'Lookback Period (Bars)',
    paramYName: 'ATR Band Multiplier',
    paramXValues: [12, 16, 20, 24, 28, 32],
    paramYValues: [1.6, 1.8, 2.0, 2.2, 2.4, 2.6],
    islandOfStabilityConfidence: 94.6,
    curveFitWarning: false,
    recommendation: 'Stable plateau identified around Lookback 20-24 with Multiplier 2.0-2.2. Sharpe decay < 3.8% across neighbors. Validated for live canary allocation.',
    monteCarlo: {
      medianReturn: 28.4,
      pct5Var: 18.2,
      pct95Var: 37.6,
      maxDrawdownWorstCase: 4.1,
      samples: [
        18.4, 21.2, 23.5, 24.8, 26.1, 27.5, 28.4, 29.2, 30.8, 32.1, 33.5, 35.2, 36.8, 38.1
      ]
    },
    grid: [
      // row 0: Y = 1.6
      [
        { paramX: 12, paramY: 1.6, profitFactor: 1.34, sharpeRatio: 1.12, winRatePct: 51.2, drawdownPct: 5.4, isOverfitted: false, isOptimal: false },
        { paramX: 16, paramY: 1.6, profitFactor: 1.42, sharpeRatio: 1.25, winRatePct: 52.8, drawdownPct: 4.8, isOverfitted: false, isOptimal: false },
        { paramX: 20, paramY: 1.6, profitFactor: 1.51, sharpeRatio: 1.38, winRatePct: 54.1, drawdownPct: 4.2, isOverfitted: false, isOptimal: false },
        { paramX: 24, paramY: 1.6, profitFactor: 1.54, sharpeRatio: 1.41, winRatePct: 54.8, drawdownPct: 4.0, isOverfitted: false, isOptimal: false },
        { paramX: 28, paramY: 1.6, profitFactor: 1.48, sharpeRatio: 1.32, winRatePct: 53.6, drawdownPct: 4.5, isOverfitted: false, isOptimal: false },
        { paramX: 32, paramY: 1.6, profitFactor: 1.39, sharpeRatio: 1.21, winRatePct: 52.0, drawdownPct: 4.9, isOverfitted: false, isOptimal: false }
      ],
      // row 1: Y = 1.8
      [
        { paramX: 12, paramY: 1.8, profitFactor: 1.45, sharpeRatio: 1.28, winRatePct: 53.4, drawdownPct: 4.7, isOverfitted: false, isOptimal: false },
        { paramX: 16, paramY: 1.8, profitFactor: 1.58, sharpeRatio: 1.45, winRatePct: 55.2, drawdownPct: 3.9, isOverfitted: false, isOptimal: false },
        { paramX: 20, paramY: 1.8, profitFactor: 1.68, sharpeRatio: 1.59, winRatePct: 56.7, drawdownPct: 3.5, isOverfitted: false, isOptimal: false },
        { paramX: 24, paramY: 1.8, profitFactor: 1.72, sharpeRatio: 1.64, winRatePct: 57.3, drawdownPct: 3.3, isOverfitted: false, isOptimal: false },
        { paramX: 28, paramY: 1.8, profitFactor: 1.65, sharpeRatio: 1.52, winRatePct: 56.1, drawdownPct: 3.6, isOverfitted: false, isOptimal: false },
        { paramX: 32, paramY: 1.8, profitFactor: 1.52, sharpeRatio: 1.37, winRatePct: 54.4, drawdownPct: 4.1, isOverfitted: false, isOptimal: false }
      ],
      // row 2: Y = 2.0 (Plateau Core)
      [
        { paramX: 12, paramY: 2.0, profitFactor: 1.52, sharpeRatio: 1.39, winRatePct: 54.6, drawdownPct: 4.2, isOverfitted: false, isOptimal: false },
        { paramX: 16, paramY: 2.0, profitFactor: 1.69, sharpeRatio: 1.62, winRatePct: 56.9, drawdownPct: 3.4, isOverfitted: false, isOptimal: false },
        { paramX: 20, paramY: 2.0, profitFactor: 1.81, sharpeRatio: 1.78, winRatePct: 58.2, drawdownPct: 3.1, isOverfitted: false, isOptimal: false },
        { paramX: 24, paramY: 2.0, profitFactor: 1.84, sharpeRatio: 1.82, winRatePct: 58.7, drawdownPct: 3.2, isOverfitted: false, isOptimal: true },
        { paramX: 28, paramY: 2.0, profitFactor: 1.79, sharpeRatio: 1.74, winRatePct: 57.8, drawdownPct: 3.3, isOverfitted: false, isOptimal: false },
        { paramX: 32, paramY: 2.0, profitFactor: 1.64, sharpeRatio: 1.55, winRatePct: 55.9, drawdownPct: 3.8, isOverfitted: false, isOptimal: false }
      ],
      // row 3: Y = 2.2 (Plateau Core)
      [
        { paramX: 12, paramY: 2.2, profitFactor: 1.56, sharpeRatio: 1.44, winRatePct: 55.1, drawdownPct: 4.0, isOverfitted: false, isOptimal: false },
        { paramX: 16, paramY: 2.2, profitFactor: 1.72, sharpeRatio: 1.66, winRatePct: 57.4, drawdownPct: 3.3, isOverfitted: false, isOptimal: false },
        { paramX: 20, paramY: 2.2, profitFactor: 1.83, sharpeRatio: 1.80, winRatePct: 58.4, drawdownPct: 3.0, isOverfitted: false, isOptimal: false },
        { paramX: 24, paramY: 2.2, profitFactor: 1.82, sharpeRatio: 1.79, winRatePct: 58.3, drawdownPct: 3.1, isOverfitted: false, isOptimal: false },
        { paramX: 28, paramY: 2.2, profitFactor: 1.76, sharpeRatio: 1.70, winRatePct: 57.2, drawdownPct: 3.4, isOverfitted: false, isOptimal: false },
        { paramX: 32, paramY: 2.2, profitFactor: 1.61, sharpeRatio: 1.50, winRatePct: 55.3, drawdownPct: 3.9, isOverfitted: false, isOptimal: false }
      ],
      // row 4: Y = 2.4
      [
        { paramX: 12, paramY: 2.4, profitFactor: 1.49, sharpeRatio: 1.34, winRatePct: 53.8, drawdownPct: 4.4, isOverfitted: false, isOptimal: false },
        { paramX: 16, paramY: 2.4, profitFactor: 1.64, sharpeRatio: 1.53, winRatePct: 56.1, drawdownPct: 3.6, isOverfitted: false, isOptimal: false },
        { paramX: 20, paramY: 2.4, profitFactor: 1.73, sharpeRatio: 1.67, winRatePct: 57.2, drawdownPct: 3.4, isOverfitted: false, isOptimal: false },
        { paramX: 24, paramY: 2.4, profitFactor: 1.74, sharpeRatio: 1.68, winRatePct: 57.5, drawdownPct: 3.5, isOverfitted: false, isOptimal: false },
        { paramX: 28, paramY: 2.4, profitFactor: 1.68, sharpeRatio: 1.59, winRatePct: 56.4, drawdownPct: 3.7, isOverfitted: false, isOptimal: false },
        { paramX: 32, paramY: 2.4, profitFactor: 1.54, sharpeRatio: 1.41, winRatePct: 54.7, drawdownPct: 4.2, isOverfitted: false, isOptimal: false }
      ],
      // row 5: Y = 2.6
      [
        { paramX: 12, paramY: 2.6, profitFactor: 1.38, sharpeRatio: 1.18, winRatePct: 52.1, drawdownPct: 5.1, isOverfitted: false, isOptimal: false },
        { paramX: 16, paramY: 2.6, profitFactor: 1.51, sharpeRatio: 1.37, winRatePct: 54.2, drawdownPct: 4.2, isOverfitted: false, isOptimal: false },
        { paramX: 20, paramY: 2.6, profitFactor: 1.61, sharpeRatio: 1.50, winRatePct: 55.6, drawdownPct: 3.9, isOverfitted: false, isOptimal: false },
        { paramX: 24, paramY: 2.6, profitFactor: 1.62, sharpeRatio: 1.51, winRatePct: 55.8, drawdownPct: 3.8, isOverfitted: false, isOptimal: false },
        { paramX: 28, paramY: 2.6, profitFactor: 1.56, sharpeRatio: 1.43, winRatePct: 54.9, drawdownPct: 4.1, isOverfitted: false, isOptimal: false },
        { paramX: 32, paramY: 2.6, profitFactor: 1.44, sharpeRatio: 1.27, winRatePct: 53.2, drawdownPct: 4.6, isOverfitted: false, isOptimal: false }
      ]
    ]
  },
  'NVDA': {
    strategyId: 'strat-eq-02',
    strategyName: 'Volatility Expansion Matrix (VEM-4)',
    symbol: 'NVDA',
    timeframe: '15m/1h',
    paramXName: 'Opening Range Mins',
    paramYName: 'Volume Z-Score Cutoff',
    paramXValues: [15, 30, 45, 60],
    paramYValues: [1.0, 1.5, 2.0, 2.5],
    islandOfStabilityConfidence: 89.2,
    curveFitWarning: false,
    recommendation: 'Stable zone detected at 30-45m opening range with Z-Score cutoff 1.5-2.0. Good robustness across regime shifts.',
    monteCarlo: {
      medianReturn: 34.1,
      pct5Var: 22.4,
      pct95Var: 46.2,
      maxDrawdownWorstCase: 5.8,
      samples: [22.4, 26.5, 29.1, 31.8, 34.1, 37.5, 41.2, 46.2]
    },
    grid: [
      [
        { paramX: 15, paramY: 1.0, profitFactor: 1.32, sharpeRatio: 1.15, winRatePct: 49.5, drawdownPct: 6.2, isOverfitted: false, isOptimal: false },
        { paramX: 30, paramY: 1.0, profitFactor: 1.48, sharpeRatio: 1.32, winRatePct: 52.4, drawdownPct: 5.4, isOverfitted: false, isOptimal: false },
        { paramX: 45, paramY: 1.0, profitFactor: 1.52, sharpeRatio: 1.38, winRatePct: 53.1, drawdownPct: 5.1, isOverfitted: false, isOptimal: false },
        { paramX: 60, paramY: 1.0, profitFactor: 1.41, sharpeRatio: 1.24, winRatePct: 51.0, drawdownPct: 5.7, isOverfitted: false, isOptimal: false }
      ],
      [
        { paramX: 15, paramY: 1.5, profitFactor: 1.45, sharpeRatio: 1.31, winRatePct: 51.8, drawdownPct: 5.6, isOverfitted: false, isOptimal: false },
        { paramX: 30, paramY: 1.5, profitFactor: 1.68, sharpeRatio: 1.58, winRatePct: 55.4, drawdownPct: 4.8, isOverfitted: false, isOptimal: false },
        { paramX: 45, paramY: 1.5, profitFactor: 1.76, sharpeRatio: 1.68, winRatePct: 56.8, drawdownPct: 4.4, isOverfitted: false, isOptimal: true },
        { paramX: 60, paramY: 1.5, profitFactor: 1.58, sharpeRatio: 1.44, winRatePct: 53.9, drawdownPct: 5.0, isOverfitted: false, isOptimal: false }
      ],
      [
        { paramX: 15, paramY: 2.0, profitFactor: 1.50, sharpeRatio: 1.37, winRatePct: 52.9, drawdownPct: 5.2, isOverfitted: false, isOptimal: false },
        { paramX: 30, paramY: 2.0, profitFactor: 1.72, sharpeRatio: 1.64, winRatePct: 56.1, drawdownPct: 4.5, isOverfitted: false, isOptimal: false },
        { paramX: 45, paramY: 2.0, profitFactor: 1.74, sharpeRatio: 1.66, winRatePct: 56.4, drawdownPct: 4.6, isOverfitted: false, isOptimal: false },
        { paramX: 60, paramY: 2.0, profitFactor: 1.60, sharpeRatio: 1.47, winRatePct: 54.2, drawdownPct: 4.9, isOverfitted: false, isOptimal: false }
      ],
      [
        { paramX: 15, paramY: 2.5, profitFactor: 1.38, sharpeRatio: 1.21, winRatePct: 50.4, drawdownPct: 5.9, isOverfitted: false, isOptimal: false },
        { paramX: 30, paramY: 2.5, profitFactor: 1.55, sharpeRatio: 1.42, winRatePct: 53.8, drawdownPct: 5.1, isOverfitted: false, isOptimal: false },
        { paramX: 45, paramY: 2.5, profitFactor: 1.59, sharpeRatio: 1.46, winRatePct: 54.2, drawdownPct: 5.0, isOverfitted: false, isOptimal: false },
        { paramX: 60, paramY: 2.5, profitFactor: 1.46, sharpeRatio: 1.30, winRatePct: 52.1, drawdownPct: 5.4, isOverfitted: false, isOptimal: false }
      ]
    ]
  }
};

// ---------------------------------------------------------------------------
// 2. EXECUTION QUALITY & SLIPPAGE AUDIT RECORDS
// ---------------------------------------------------------------------------
export const EXECUTION_QUALITY_RECORDS: ExecutionQualityRecord[] = [
  {
    id: 'exec-8821',
    orderId: 'ord-sim-9142',
    symbol: 'EUR/USD',
    side: 'BUY',
    route: 'EBS ECN (Direct)',
    submittedAt: '10:15:00.120',
    filledAt: '10:15:00.142',
    latencyMs: 22,
    expectedPrice: 1.0848,
    actualPrice: 1.0848,
    slippagePips: 0.0,
    slippageCostDollars: 0.0,
    spreadAtFillPips: 0.4,
    sessionRegime: 'NY Overlap',
    executionGrade: 'EXCELLENT'
  },
  {
    id: 'exec-8822',
    orderId: 'ord-sim-9143',
    symbol: 'NVDA',
    side: 'BUY',
    route: 'Alpaca Smart Router',
    submittedAt: '09:30:12.040',
    filledAt: '09:30:12.074',
    latencyMs: 34,
    expectedPrice: 124.50,
    actualPrice: 124.52,
    slippagePips: 0.2,
    slippageCostDollars: 4.0,
    spreadAtFillPips: 0.02,
    sessionRegime: 'NY Overlap',
    executionGrade: 'NORMAL'
  },
  {
    id: 'exec-8823',
    orderId: 'ord-sim-9144',
    symbol: 'BTC/USDT',
    side: 'BUY',
    route: 'Binance Microstructure L3',
    submittedAt: '08:30:00.010',
    filledAt: '08:30:00.152',
    latencyMs: 142,
    expectedPrice: 63820.0,
    actualPrice: 63824.5,
    slippagePips: 4.5,
    slippageCostDollars: 5.62,
    spreadAtFillPips: 1.5,
    sessionRegime: 'London Open',
    flaggedAnomaly: 'Binance L3 Latency 142ms (>50ms SLA). Microstructure queue delay caused adverse 4.5 pt fill.',
    executionGrade: 'DEGRADED_LATENCY'
  },
  {
    id: 'exec-8824',
    orderId: 'ord-sim-9145',
    symbol: 'EUR/USD',
    side: 'SELL',
    route: 'OANDA Practice Direct',
    submittedAt: '08:30:02.110',
    filledAt: '08:30:02.138',
    latencyMs: 28,
    expectedPrice: 1.0878,
    actualPrice: 1.08775,
    slippagePips: -0.5,
    slippageCostDollars: -5.0,
    spreadAtFillPips: 0.5,
    sessionRegime: 'NY Overlap',
    executionGrade: 'NORMAL'
  },
  {
    id: 'exec-8825',
    orderId: 'ord-sim-9146',
    symbol: 'GBP/USD',
    side: 'BUY',
    route: 'Currenex Hotspot',
    submittedAt: '03:00:01.005',
    filledAt: '03:00:01.026',
    latencyMs: 21,
    expectedPrice: 1.2940,
    actualPrice: 1.2940,
    slippagePips: 0.0,
    slippageCostDollars: 0.0,
    spreadAtFillPips: 0.7,
    sessionRegime: 'London Open',
    executionGrade: 'EXCELLENT'
  }
];

// ---------------------------------------------------------------------------
// 3. POST-TRADE SCORECARD & AUDIT DISCIPLINE GRADES
// ---------------------------------------------------------------------------
export const POST_TRADE_SCORECARDS: PostTradeScorecard[] = [
  {
    tradeId: 'tr-0941',
    symbol: 'EUR/USD',
    strategyName: 'EUR/USD Mean Reversion v2.1',
    side: 'LONG',
    entryTime: '08:30 EST',
    exitTime: '12:15 EST',
    entryPrice: 1.0838,
    exitPrice: 1.0878,
    stopLossPrice: 1.0818,
    takeProfitPrice: 1.0878,
    realizedPnl: 400.0,
    realizedPips: 40.0,
    disciplineGrade: 'A+',
    maePips: 3.0,
    maeDollars: 30.0,
    mfePips: 42.0,
    mfeDollars: 420.0,
    pnlLeftOnTableDollars: 20.0,
    rulesAdhered: [
      { rule: 'Entered within 0.5 pips of model band signal', passed: true },
      { rule: 'Stop loss remained immutable (never widened)', passed: true },
      { rule: 'Full target hit without premature manual intervention', passed: true },
      { rule: 'Position size strictly conformed to 0.85% equity risk cap', passed: true }
    ],
    postMortemNotes: 'Textbook execution. Liquidity dip into 1.0838 absorbed cleanly. MAE was only 3 pips before immediate favorable reversal. Zero emotional slippage.'
  },
  {
    tradeId: 'tr-0942',
    symbol: 'NVDA',
    strategyName: 'Volatility Expansion Matrix (VEM-4)',
    side: 'LONG',
    entryTime: '09:45 EST',
    exitTime: '11:30 EST',
    entryPrice: 124.50,
    exitPrice: 127.80,
    stopLossPrice: 122.90,
    takeProfitPrice: 128.50,
    realizedPnl: 660.0,
    realizedPips: 33.0,
    disciplineGrade: 'A',
    maePips: 8.0,
    maeDollars: 160.0,
    mfePips: 40.0,
    mfeDollars: 800.0,
    pnlLeftOnTableDollars: 140.0,
    rulesAdhered: [
      { rule: 'Opening range breakout confirmation with volume filter', passed: true },
      { rule: 'Stop loss respected and trailed systematically at 1.5R', passed: true },
      { rule: 'Exit executed at predetermined trailing stop boundary', passed: true },
      { rule: 'Risk cap respected', passed: true }
    ],
    postMortemNotes: 'Strong trending impulse. Trailing stop safely locked in $660 profit. Exited slightly below the absolute daily peak ($128.50), leaving $140 on the table as designed by the trend-following exit rule.'
  },
  {
    tradeId: 'tr-0943',
    symbol: 'BTC/USDT',
    strategyName: 'Orderflow Microstructure Reversion',
    side: 'LONG',
    entryTime: '10:15 EST',
    exitTime: '14:15 EST',
    entryPrice: 63820.0,
    exitPrice: 65800.0,
    stopLossPrice: 63200.0,
    takeProfitPrice: 65800.0,
    realizedPnl: 2475.0,
    realizedPips: 198.0,
    disciplineGrade: 'A+',
    maePips: 65.0,
    maeDollars: 81.25,
    mfePips: 201.0,
    mfeDollars: 2512.5,
    pnlLeftOnTableDollars: 37.5,
    rulesAdhered: [
      { rule: 'Liquidation sweep absorption verified in CVD depth', passed: true },
      { rule: 'Post-only limit order executed to eliminate taker fee drag', passed: true },
      { rule: 'Target order filled passively at cluster high', passed: true },
      { rule: 'Zero margin breach under simulated crypto rules', passed: true }
    ],
    postMortemNotes: 'Flawless 3.19 R:R capture on CVD divergence bounce. Passive limit execution saved $28.40 in fees. MAE kept to minimal 65 points.'
  },
  {
    tradeId: 'tr-0944',
    symbol: 'GBP/USD',
    strategyName: 'London Breakout Trend Hunter',
    side: 'LONG',
    entryTime: '03:15 EST',
    exitTime: '05:45 EST',
    entryPrice: 1.2940,
    exitPrice: 1.2915,
    stopLossPrice: 1.2915,
    takeProfitPrice: 1.2995,
    realizedPnl: -250.0,
    realizedPips: -25.0,
    disciplineGrade: 'A',
    maePips: 25.0,
    maeDollars: 250.0,
    mfePips: 8.0,
    mfeDollars: 80.0,
    pnlLeftOnTableDollars: 0.0,
    rulesAdhered: [
      { rule: 'Valid Asian range breakout confirmed at 03:00', passed: true },
      { rule: 'Stop loss accepted cleanly without modification', passed: true },
      { rule: 'Position sized strictly for 0.5% max risk cap ($250)', passed: true },
      { rule: 'No revenge entry initiated post-stopout', passed: true }
    ],
    postMortemNotes: 'Disciplined loss. Breakout failed due to surprise UK inflation commentary. Stop loss took the trade off exactly at -$250 as calibrated. High discipline grade despite negative outcome.'
  }
];
