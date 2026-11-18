export interface CandleData {
  time: string; // e.g. "08:30"
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface ReplayTradeEvent {
  id: string;
  type: 'ENTRY' | 'TRAILING_STOP' | 'TAKE_PROFIT' | 'STOP_LOSS' | 'EXIT';
  side: 'BUY' | 'SELL';
  time: string; // matches candle time
  price: number;
  size: string;
  pnl?: number;
  pnlPct?: number;
  note: string;
  novaInsight: string;
}

export interface InstrumentReplaySession {
  symbol: string;
  name: string;
  assetClass: 'Forex' | 'Equities' | 'Crypto';
  timeframe: string;
  sessionDate: string;
  pipOrPointMultiplier: number;
  decimals: number;
  currentPrice: number;
  candles: CandleData[];
  events: ReplayTradeEvent[];
  activePosition: {
    side: 'LONG' | 'SHORT';
    size: string;
    entryPrice: number;
    stopLossPrice: number;
    takeProfitPrice: number;
    entryTime: string;
    currentPnl: number;
    currentPnlPct: number;
    riskAmount: number;
    rewardAmount: number;
    riskRewardRatio: number;
    trailingStopActive: boolean;
    trailingStopPrice?: number;
    strategyName: string;
    strategyId: string;
    spreadPips: number;
  };
}

// Generate realistic session candles for EUR/USD (15m candles from 04:00 to 17:00 EST)
const generateEURUSDCandles = (): CandleData[] => {
  const times = [
    '04:00', '04:15', '04:30', '04:45',
    '05:00', '05:15', '05:30', '05:45',
    '06:00', '06:15', '06:30', '06:45',
    '07:00', '07:15', '07:30', '07:45',
    '08:00', '08:15', '08:30', '08:45',
    '09:00', '09:15', '09:30', '09:45',
    '10:00', '10:15', '10:30', '10:45',
    '11:00', '11:15', '11:30', '11:45',
    '12:00', '12:15', '12:30', '12:45',
    '13:00', '13:15', '13:30', '13:45',
    '14:00', '14:15', '14:30', '14:45',
    '15:00', '15:15', '15:30', '15:45',
    '16:00', '16:15', '16:30', '16:45', '17:00'
  ];

  const prices = [
    [1.0824, 1.0828, 1.0821, 1.0825, 420],
    [1.0825, 1.0830, 1.0823, 1.0828, 510],
    [1.0828, 1.0832, 1.0826, 1.0830, 390],
    [1.0830, 1.0833, 1.0827, 1.0829, 310],
    [1.0829, 1.0831, 1.0825, 1.0827, 280],
    [1.0827, 1.0830, 1.0824, 1.0826, 330],
    [1.0826, 1.0829, 1.0823, 1.0828, 410],
    [1.0828, 1.0833, 1.0827, 1.0831, 480],
    [1.0831, 1.0835, 1.0829, 1.0832, 620],
    [1.0832, 1.0834, 1.0828, 1.0830, 540],
    [1.0830, 1.0833, 1.0827, 1.0829, 490],
    [1.0829, 1.0836, 1.0828, 1.0835, 780],
    [1.0835, 1.0839, 1.0832, 1.0836, 920],
    [1.0836, 1.0840, 1.0833, 1.0838, 1050],
    [1.0838, 1.0842, 1.0835, 1.0839, 1140],
    [1.0839, 1.0844, 1.0836, 1.0841, 1280],
    // 08:00 - London / NY overlap surge
    [1.0841, 1.0848, 1.0838, 1.0845, 1850],
    [1.0845, 1.0852, 1.0842, 1.0849, 2140],
    // 08:30 - US Economic Release & Breakout
    [1.0849, 1.0858, 1.0836, 1.0838, 3890], // Dip to entry fill at 1.0838
    [1.0838, 1.0850, 1.0835, 1.0846, 2980], // Rebound confirms breakout
    [1.0846, 1.0855, 1.0843, 1.0852, 2410],
    [1.0852, 1.0860, 1.0849, 1.0857, 2100],
    [1.0857, 1.0863, 1.0854, 1.0861, 1950],
    [1.0861, 1.0868, 1.0858, 1.0865, 2240],
    // 10:00 - Steady continuation
    [1.0865, 1.0872, 1.0862, 1.0869, 1820],
    [1.0869, 1.0874, 1.0865, 1.0871, 1680],
    [1.0871, 1.0876, 1.0868, 1.0872, 1540],
    [1.0872, 1.0874, 1.0866, 1.0869, 1320],
    [1.0869, 1.0873, 1.0864, 1.0870, 1210],
    [1.0870, 1.0875, 1.0868, 1.0873, 1430],
    [1.0873, 1.0878, 1.0871, 1.0875, 1620],
    [1.0875, 1.0880, 1.0872, 1.0878, 1890],
    // 12:00 - Midday peak & target test
    [1.0878, 1.0884, 1.0875, 1.0881, 1420],
    [1.0881, 1.0885, 1.0877, 1.0879, 1150],
    [1.0879, 1.0882, 1.0874, 1.0876, 980],
    [1.0876, 1.0878, 1.0871, 1.0873, 890],
    [1.0873, 1.0876, 1.0868, 1.0871, 920],
    [1.0871, 1.0874, 1.0866, 1.0868, 870],
    [1.0868, 1.0871, 1.0863, 1.0867, 810],
    [1.0867, 1.0870, 1.0862, 1.0865, 760],
    // 14:00 - London close & afternoon consolidation
    [1.0865, 1.0868, 1.0859, 1.0862, 940],
    [1.0862, 1.0866, 1.0858, 1.0861, 880],
    [1.0861, 1.0864, 1.0856, 1.0859, 790],
    [1.0859, 1.0862, 1.0854, 1.0857, 720],
    [1.0857, 1.0860, 1.0852, 1.0855, 680],
    [1.0855, 1.0858, 1.0850, 1.0853, 620],
    [1.0853, 1.0855, 1.0847, 1.0850, 580],
    [1.0850, 1.0852, 1.0844, 1.0847, 520],
    [1.0847, 1.0849, 1.0842, 1.0845, 610],
    [1.0845, 1.0847, 1.0841, 1.0845, 690],
    [1.0845, 1.0848, 1.0843, 1.0846, 730],
    [1.0846, 1.0848, 1.0842, 1.0845, 810],
    [1.0845, 1.0847, 1.0843, 1.0845, 890]
  ];

  const baseDate = new Date('2026-10-03T04:00:00Z').getTime();

  return times.map((t, i) => ({
    time: t,
    timestamp: baseDate + i * 15 * 60 * 1000,
    open: prices[i][0],
    high: prices[i][1],
    low: prices[i][2],
    close: prices[i][3],
    volume: prices[i][4]
  }));
};

// Generate NVDA 15m session candles (09:30 to 16:00 EST)
const generateNVDACandles = (): CandleData[] => {
  const times = [
    '09:30', '09:45', '10:00', '10:15', '10:30', '10:45',
    '11:00', '11:15', '11:30', '11:45', '12:00', '12:15',
    '12:30', '12:45', '13:00', '13:15', '13:30', '13:45',
    '14:00', '14:15', '14:30', '14:45', '15:00', '15:15',
    '15:30', '15:45', '16:00'
  ];

  const prices = [
    [123.80, 125.10, 123.40, 124.50, 48200],
    [124.50, 126.20, 124.30, 125.80, 61400],
    [125.80, 127.40, 125.50, 126.90, 54000],
    [126.90, 127.80, 126.40, 127.20, 42100],
    [127.20, 128.50, 127.00, 128.10, 39500],
    [128.10, 128.90, 127.80, 128.40, 36200],
    [128.40, 129.20, 128.10, 128.80, 31400],
    [128.80, 129.60, 128.50, 129.10, 28900],
    [129.10, 129.80, 128.90, 129.50, 26400],
    [129.50, 130.20, 129.20, 129.90, 29800],
    [129.90, 130.60, 129.70, 130.10, 24500],
    [130.10, 130.40, 129.80, 130.00, 21200],
    [130.00, 130.30, 129.60, 129.80, 19800],
    [129.80, 130.10, 129.40, 129.70, 18500],
    [129.70, 130.00, 129.30, 129.50, 17900],
    [129.50, 129.80, 129.20, 129.40, 16800],
    [129.40, 129.70, 129.10, 129.60, 19400],
    [129.60, 130.10, 129.40, 129.90, 22100],
    [129.90, 130.50, 129.70, 130.20, 25800],
    [130.20, 130.70, 130.00, 130.40, 28100],
    [130.40, 130.80, 130.10, 130.50, 31500],
    [130.50, 130.60, 129.90, 130.20, 33400],
    [130.20, 130.40, 129.70, 130.00, 38900],
    [130.00, 130.20, 129.50, 129.80, 42100],
    [129.80, 130.00, 129.40, 129.70, 46500],
    [129.70, 129.90, 129.50, 129.80, 52100],
    [129.80, 130.10, 129.60, 129.80, 68900]
  ];

  const baseDate = new Date('2026-10-03T09:30:00Z').getTime();

  return times.map((t, i) => ({
    time: t,
    timestamp: baseDate + i * 15 * 60 * 1000,
    open: prices[i][0],
    high: prices[i][1],
    low: prices[i][2],
    close: prices[i][3],
    volume: prices[i][4]
  }));
};

// Generate BTC/USDT 15m session candles (24h snapshot)
const generateBTCCandles = (): CandleData[] => {
  const times = [
    '08:00', '08:15', '08:30', '08:45',
    '09:00', '09:15', '09:30', '09:45',
    '10:00', '10:15', '10:30', '10:45',
    '11:00', '11:15', '11:30', '11:45',
    '12:00', '12:15', '12:30', '12:45',
    '13:00', '13:15', '13:30', '13:45',
    '14:00', '14:15', '14:30', '14:45'
  ];

  const prices = [
    [63400, 63650, 63320, 63580, 420],
    [63580, 63720, 63500, 63690, 380],
    [63690, 63840, 63620, 63750, 410],
    [63750, 63900, 63700, 63820, 460],
    [63820, 63980, 63780, 63910, 520],
    [63910, 64100, 63850, 64050, 610],
    [64050, 64250, 63980, 64180, 780],
    [64180, 64320, 64100, 64240, 840],
    [64240, 64150, 63700, 63780, 1120], // Liquidity sweep down
    [63780, 63920, 63650, 63820, 1420], // Order entry fill @ 63820
    [63820, 64150, 63800, 64100, 980],
    [64100, 64350, 64050, 64280, 890],
    [64280, 64500, 64220, 64450, 940],
    [64450, 64620, 64380, 64550, 810],
    [64550, 64750, 64480, 64680, 760],
    [64680, 64850, 64600, 64790, 690],
    [64790, 64920, 64700, 64850, 640],
    [64850, 64980, 64780, 64910, 590],
    [64910, 65120, 64850, 65050, 720],
    [65050, 65240, 64980, 65180, 780],
    [65180, 65350, 65100, 65280, 840],
    [65280, 65420, 65200, 65380, 910],
    [65380, 65550, 65300, 65490, 880],
    [65490, 65680, 65420, 65610, 920],
    [65610, 65780, 65540, 65720, 1050],
    [65720, 65850, 65650, 65800, 1280], // Target reached
    [65800, 65820, 65480, 65520, 1140],
    [65520, 65600, 65380, 65450, 960]
  ];

  const baseDate = new Date('2026-10-03T08:00:00Z').getTime();

  return times.map((t, i) => ({
    time: t,
    timestamp: baseDate + i * 15 * 60 * 1000,
    open: prices[i][0],
    high: prices[i][1],
    low: prices[i][2],
    close: prices[i][3],
    volume: prices[i][4]
  }));
};

export const REPLAY_SESSIONS: Record<string, InstrumentReplaySession> = {
  'EUR/USD': {
    symbol: 'EUR/USD',
    name: 'Euro / US Dollar (London-NY Breakout)',
    assetClass: 'Forex',
    timeframe: '15m',
    sessionDate: 'Today (Session: London / NY Overlap)',
    pipOrPointMultiplier: 10000,
    decimals: 4,
    currentPrice: 1.0845,
    candles: generateEURUSDCandles(),
    activePosition: {
      side: 'LONG',
      size: '100,000 units (1.0 Lot)',
      entryPrice: 1.0838,
      stopLossPrice: 1.0822,
      takeProfitPrice: 1.0870,
      entryTime: '08:35 EST',
      currentPnl: 70.00,
      currentPnlPct: 0.65,
      riskAmount: 160.00,
      rewardAmount: 320.00,
      riskRewardRatio: 2.0,
      trailingStopActive: true,
      trailingStopPrice: 1.0840,
      strategyName: 'London-NY Session Breakout (LNY-FX)',
      strategyId: 'strat-fx-09',
      spreadPips: 0.8
    },
    events: [
      {
        id: 'evt-1',
        type: 'ENTRY',
        side: 'BUY',
        time: '08:35',
        price: 1.0838,
        size: '100,000 units',
        note: 'Breakout candle closed +8.5 pips above Asian session ceiling on 2.4x volume.',
        novaInsight: 'London-NY momentum surge validated. Initial risk strictly bounded to 16.0 pips ($160.00 / 0.85% equity) with target at 1.0870 (2.0R payout).'
      },
      {
        id: 'evt-2',
        type: 'TRAILING_STOP',
        side: 'BUY',
        time: '10:15',
        price: 1.0840,
        size: '100,000 units',
        note: 'Trailing Stop ratcheted up to 1.0840 (+2 pips locked profit).',
        novaInsight: 'Price reached +33 pips excursion (1.0871). Risk engine automatically ratcheted stop into positive territory, guaranteeing zero loss.'
      },
      {
        id: 'evt-3',
        type: 'TAKE_PROFIT',
        side: 'BUY',
        time: '12:00',
        price: 1.0870,
        size: '100,000 units',
        pnl: 320.00,
        pnlPct: 2.95,
        note: 'Take Profit target triggered cleanly at 1.0870 (+$320.00 / 2.0R).',
        novaInsight: 'Institutional target achieved during European midday liquidity pool. Slippage: 0.1 pips. Trade closed with full 2.0R asymmetric expectancy.'
      }
    ]
  },

  'NVDA': {
    symbol: 'NVDA',
    name: 'NVIDIA Corporation (Volatility Expansion)',
    assetClass: 'Equities',
    timeframe: '15m',
    sessionDate: 'Today (Session: Regular US Market)',
    pipOrPointMultiplier: 1,
    decimals: 2,
    currentPrice: 129.80,
    candles: generateNVDACandles(),
    activePosition: {
      side: 'LONG',
      size: '350 Shares',
      entryPrice: 124.50,
      stopLossPrice: 122.10,
      takeProfitPrice: 136.50,
      entryTime: '09:45 EST',
      currentPnl: 1855.00,
      currentPnlPct: 4.26,
      riskAmount: 840.00,
      rewardAmount: 4200.00,
      riskRewardRatio: 5.0,
      trailingStopActive: true,
      trailingStopPrice: 127.50,
      strategyName: 'Volatility Expansion Matrix (VEM-4)',
      strategyId: 'strat-vol-01',
      spreadPips: 0.02
    },
    events: [
      {
        id: 'evt-nvda-1',
        type: 'ENTRY',
        side: 'BUY',
        time: '09:45',
        price: 124.50,
        size: '350 Shares',
        note: 'Opening range breakout past 15m ATR band with 61.4k share volume spike.',
        novaInsight: 'Semiconductor sector momentum leader. Risk cap of $840 (0.84% equity) enforced with stop at 122.10.'
      },
      {
        id: 'evt-nvda-2',
        type: 'TRAILING_STOP',
        side: 'BUY',
        time: '11:30',
        price: 127.50,
        size: '350 Shares',
        note: 'Stop moved up to $127.50 (+3.00 pts profit lock).',
        novaInsight: 'NVDA broke above $129.00 resistance. Trailing stop ratcheted to lock in +$1,050 minimum profit.'
      }
    ]
  },

  'BTC/USDT': {
    symbol: 'BTC/USDT',
    name: 'Bitcoin Perpetual (Orderflow Reversion)',
    assetClass: 'Crypto',
    timeframe: '15m',
    sessionDate: 'Today (24h Continuous)',
    pipOrPointMultiplier: 1,
    decimals: 2,
    currentPrice: 64450.00,
    candles: generateBTCCandles(),
    activePosition: {
      side: 'LONG',
      size: '1.25 BTC',
      entryPrice: 63820.00,
      stopLossPrice: 63200.00,
      takeProfitPrice: 65800.00,
      entryTime: '11:05 EST',
      currentPnl: 787.50,
      currentPnlPct: 0.99,
      riskAmount: 775.00,
      rewardAmount: 2475.00,
      riskRewardRatio: 3.19,
      trailingStopActive: false,
      strategyName: 'Orderflow Microstructure Reversion (OMR-B)',
      strategyId: 'strat-crypto-03',
      spreadPips: 1.50
    },
    events: [
      {
        id: 'evt-btc-1',
        type: 'ENTRY',
        side: 'BUY',
        time: '10:15',
        price: 63820.00,
        size: '1.25 BTC',
        note: 'Limit order fill on liquidity cascade bounce following CVD divergence.',
        novaInsight: 'Cascade liquidation sweep absorbed by passive buy wall. Post-only order saved $28.40 in taker fees.'
      },
      {
        id: 'evt-btc-2',
        type: 'TAKE_PROFIT',
        side: 'BUY',
        time: '14:15',
        price: 65800.00,
        size: '1.25 BTC',
        pnl: 2475.00,
        pnlPct: 3.10,
        note: 'Take Profit hit at $65,800 (+3.19 R:R payout).',
        novaInsight: 'Mean reversion cycle completed. Closed position at top of local orderbook cluster.'
      }
    ]
  },

  'DXY': {
    symbol: 'DXY',
    name: 'US Dollar Currency Index',
    assetClass: 'Forex',
    timeframe: '15m',
    sessionDate: 'Today (04:00 - 17:00 EST)',
    pipOrPointMultiplier: 100,
    decimals: 3,
    currentPrice: 103.420,
    candles: generateEURUSDCandles().map(c => {
      // Inversely correlated to EUR/USD
      const baseDXY = 104.200 - (c.close - 1.0825) * 55;
      return {
        ...c,
        open: +(baseDXY + (c.close - c.open) * -35).toFixed(3),
        high: +(baseDXY + 0.12).toFixed(3),
        low: +(baseDXY - 0.09).toFixed(3),
        close: +baseDXY.toFixed(3),
        volume: Math.round(c.volume * 0.85)
      };
    }),
    activePosition: {
      side: 'SHORT',
      size: '500k USD',
      entryPrice: 103.950,
      stopLossPrice: 104.250,
      takeProfitPrice: 103.200,
      entryTime: '08:30 EST',
      currentPnl: 530.00,
      currentPnlPct: 0.51,
      riskAmount: 300.00,
      rewardAmount: 750.00,
      riskRewardRatio: 2.50,
      trailingStopActive: true,
      trailingStopPrice: 103.650,
      strategyName: 'Dollar Index Anti-Beta Alignment',
      strategyId: 'strat-dxy-01',
      spreadPips: 0.2
    },
    events: [
      {
        id: 'evt-dxy-1',
        type: 'ENTRY',
        side: 'SELL',
        time: '08:30',
        price: 103.950,
        size: '500k USD',
        note: 'Breakdown below Asian range floor confirming EUR/USD long breakout.',
        novaInsight: 'Negative DXY correlation coefficient measured at -0.92. Strong macro confirmation.'
      }
    ]
  },

  'QQQ': {
    symbol: 'QQQ',
    name: 'Invesco QQQ Trust (Nasdaq 100)',
    assetClass: 'Equities',
    timeframe: '15m',
    sessionDate: 'Today (09:30 - 16:00 EST)',
    pipOrPointMultiplier: 100,
    decimals: 2,
    currentPrice: 486.20,
    candles: generateNVDACandles().map(c => {
      // Beta correlated to NVDA
      const baseQQQ = 480.00 + (c.close - 124.50) * 1.1;
      return {
        ...c,
        open: +(baseQQQ + (c.open - c.close) * 0.5).toFixed(2),
        high: +(baseQQQ + 1.20).toFixed(2),
        low: +(baseQQQ - 0.80).toFixed(2),
        close: +baseQQQ.toFixed(2),
        volume: Math.round(c.volume * 1.4)
      };
    }),
    activePosition: {
      side: 'LONG',
      size: '200 Shares',
      entryPrice: 481.50,
      stopLossPrice: 478.20,
      takeProfitPrice: 489.00,
      entryTime: '09:45 EST',
      currentPnl: 940.00,
      currentPnlPct: 0.98,
      riskAmount: 660.00,
      rewardAmount: 1500.00,
      riskRewardRatio: 2.27,
      trailingStopActive: true,
      trailingStopPrice: 484.00,
      strategyName: 'Nasdaq Beta Momentum Continuation',
      strategyId: 'strat-qqq-01',
      spreadPips: 0.05
    },
    events: [
      {
        id: 'evt-qqq-1',
        type: 'ENTRY',
        side: 'BUY',
        time: '09:45',
        price: 481.50,
        size: '200 Shares',
        note: 'High relative volume breakout matching tech breadth expansion.',
        novaInsight: '82% of Nasdaq-100 components trading above VWAP. Clean trend day impulse.'
      }
    ]
  }
};
