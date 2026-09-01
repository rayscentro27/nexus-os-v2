// Bounded WP8.5 evidence rendered by the admin review surface.
// This is presentation metadata only; Nexus governed records remain authoritative.
export const tradingLabData = {
  safety: { liveTrading: false, autoTrading: false, paperOnly: true, authorities: { FOREX: 'NONE', CRYPTO: 'NONE', OPTIONS: 'NONE' } },
  source: 'OANDA Practice',
  range: '2026-08-04 → 2026-09-01',
  bars: 499,
  experiments: [
    { id: 'exp_fe363776dcd226d3648f3c10', family: 'TREND_FOLLOWING', strategy: 'nexus_trend_following_v1', params: 'SMA 10 / 30', decision: 'PAPER_RESEARCH', score: 25, oos: { trades: 0, expectancy: 0, drawdown: 0, profitFactor: 0 }, equity: [10000] },
    { id: 'exp_fd28addac7162caa2ff74749', family: 'BREAKOUT', strategy: 'nexus_breakout_v1', params: 'SMA 20 / 50', decision: 'PAPER_RESEARCH', score: 25, oos: { trades: 0, expectancy: 0, drawdown: 0, profitFactor: 0 }, equity: [10000] },
    { id: 'exp_3ae9ff8da329e4198e76c332', family: 'MEAN_REVERSION', strategy: 'nexus_mean_reversion_v1', params: 'SMA 5 / 20', decision: 'PAPER_RESEARCH', score: 25, oos: { trades: 0, expectancy: 0, drawdown: 0, profitFactor: 0 }, equity: [10000] },
  ],
}
