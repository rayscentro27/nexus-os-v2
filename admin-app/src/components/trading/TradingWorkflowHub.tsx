import React, { useState } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  Activity,
  Layers,
  BarChart2,
  TrendingUp,
  Cpu,
  Radio,
  Trophy,
  DollarSign,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ArrowRight,
  GitBranch,
  RefreshCw,
  ExternalLink,
  ChevronRight,
  Sliders,
  Filter,
  Eye,
  Info
} from 'lucide-react';
import { DataTruthClass } from '../../data/executiveCommandData';

interface TradingWorkflowHubProps {
  onOpenChart?: (symbol: string) => void;
}

export const TradingWorkflowHub: React.FC<TradingWorkflowHubProps> = ({ onOpenChart }) => {
  const [selectedCohort, setSelectedCohort] = useState<'all' | 'eurusd-15m' | 'sp500-1h' | 'gbpusd-1h'>('all');
  const [selectedInventoryPair, setSelectedInventoryPair] = useState<string>('ALL');
  const [selectedInventoryStatus, setSelectedInventoryStatus] = useState<string>('ALL');
  const [activeRegime, setActiveRegime] = useState<'LOW VOLATILITY' | 'TRENDING' | 'RANGING' | 'HIGH VOLATILITY' | 'BREAKOUT' | 'SESSION TRANSITION'>('RANGING');

  const renderTruthBadge = (truth: DataTruthClass) => {
    switch (truth) {
      case 'LIVE_VERIFIED':
        return (
          <span className="text-[7.5px] font-black uppercase px-1 py-0.2 rounded bg-emerald-100 text-emerald-800 border border-emerald-300">
            LIVE
          </span>
        );
      case 'TEST_CANARY':
        return (
          <span className="text-[7.5px] font-black uppercase px-1 py-0.2 rounded bg-blue-100 text-blue-800 border border-blue-300">
            TEST CANARY
          </span>
        );
      case 'PROTOTYPE':
      default:
        return (
          <span className="text-[7.5px] font-black uppercase px-1 py-0.2 rounded bg-amber-100 text-amber-900 border border-amber-300">
            SAMPLE / DEMO
          </span>
        );
    }
  };

  // ---------------------------------------------------------------------------
  // STRATEGY INVENTORY DATA
  // ---------------------------------------------------------------------------
  const STRATEGY_INVENTORY = [
    {
      id: 'inv-01',
      name: 'EUR/USD Mean Reversion v2.1',
      pair: 'EUR/USD',
      market: 'Forex',
      timeframe: '15m',
      strategyType: 'Mean Reversion',
      status: 'PROMISING',
      returnMetric: '+28.4%',
      drawdown: '3.2%',
      profitFactor: '1.84',
      truthClass: 'TEST_CANARY' as DataTruthClass
    },
    {
      id: 'inv-02',
      name: 'Volatility Expansion Matrix (VEM-4)',
      pair: 'SPY / QQQ',
      market: 'US Equities',
      timeframe: '15m/1h',
      strategyType: 'Volatility Breakout',
      status: 'PAPER',
      returnMetric: '+34.1%',
      drawdown: '4.8%',
      profitFactor: '1.76',
      truthClass: 'TEST_CANARY' as DataTruthClass
    },
    {
      id: 'inv-03',
      name: 'London Breakout Trend Hunter',
      pair: 'GBP/USD',
      market: 'Forex',
      timeframe: '1h',
      strategyType: 'Trend Following',
      status: 'TOURNAMENT',
      returnMetric: '+22.6%',
      drawdown: '5.1%',
      profitFactor: '1.58',
      truthClass: 'TEST_CANARY' as DataTruthClass
    },
    {
      id: 'inv-04',
      name: 'USD/JPY Asian Range Reversal',
      pair: 'USD/JPY',
      market: 'Forex',
      timeframe: '5m',
      strategyType: 'Mean Reversion',
      status: 'ROBUSTNESS',
      returnMetric: '+19.2%',
      drawdown: '2.8%',
      profitFactor: '1.62',
      truthClass: 'TEST_CANARY' as DataTruthClass
    },
    {
      id: 'inv-05',
      name: 'Tech Momentum Dispersion',
      pair: 'QQQ / AAPL',
      market: 'US Equities',
      timeframe: '1h',
      strategyType: 'Momentum',
      status: 'BACKTESTING',
      returnMetric: '+18.4%',
      drawdown: '6.2%',
      profitFactor: '1.45',
      truthClass: 'TEST_CANARY' as DataTruthClass
    },
    {
      id: 'inv-06',
      name: 'Orderbook Imbalance Skew Alpha',
      pair: 'EUR/USD',
      market: 'Forex',
      timeframe: '1m',
      strategyType: 'Statistical Arbitrage',
      status: 'NORMALIZED',
      returnMetric: 'Queued',
      drawdown: 'N/A',
      profitFactor: 'N/A',
      truthClass: 'TEST_CANARY' as DataTruthClass
    },
    {
      id: 'inv-07',
      name: 'Cross-Currency Carry Factor',
      pair: 'AUD/JPY',
      market: 'Forex',
      timeframe: '4h',
      strategyType: 'Carry',
      status: 'RESEARCHED',
      returnMetric: 'Intake Raw',
      drawdown: 'N/A',
      profitFactor: 'N/A',
      truthClass: 'TEST_CANARY' as DataTruthClass
    },
    {
      id: 'inv-08',
      name: 'Unhedged Crypto Scalper v0.4',
      pair: 'BTC/USD',
      market: 'Crypto',
      timeframe: '1m',
      strategyType: 'High-Frequency',
      status: 'REJECTED',
      returnMetric: '-8.4%',
      drawdown: '14.2%',
      profitFactor: '0.88',
      truthClass: 'TEST_CANARY' as DataTruthClass
    }
  ];

  const filteredInventory = STRATEGY_INVENTORY.filter(s => {
    if (selectedInventoryPair !== 'ALL' && s.pair !== selectedInventoryPair) return false;
    if (selectedInventoryStatus !== 'ALL' && s.status !== selectedInventoryStatus) return false;
    return true;
  });

  return (
    <div className="w-full flex flex-col space-y-3 pb-8 select-none">
      {/* ===================================================================== */}
      {/* MASTER INTENDED TRADING WORKFLOW BANNER */}
      {/* ===================================================================== */}
      <div className="bg-gradient-to-r from-blue-900 via-indigo-900 to-slate-900 text-white rounded-xl p-3 border border-blue-700/80 shadow-xs space-y-2">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-blue-500 text-white flex items-center justify-center font-black text-xs">
              <Activity className="w-3.5 h-3.5" />
            </div>
            <div>
              <h2 className="text-xs font-black uppercase tracking-wider flex items-center gap-1.5">
                <span>Intended Quantitative Trading Lifecycle</span>
                {renderTruthBadge('TEST_CANARY')}
              </h2>
              <p className="text-[10px] text-blue-200">
                Deterministic algorithmic progression: Research intake to high-confidence candidate notification.
              </p>
            </div>
          </div>
          {/* Explicit Live Trading Status */}
          <div className="flex items-center gap-1.5 bg-rose-950/80 border border-rose-500/80 px-2.5 py-1 rounded-lg">
            <ShieldAlert className="w-3.5 h-3.5 text-rose-400 animate-pulse" />
            <span className="text-[10px] font-black uppercase text-rose-200 tracking-wider">
              LIVE TRADING = OFF
            </span>
            <span className="text-[8.5px] font-mono text-rose-300">· Practice &amp; Sandbox Only</span>
          </div>
        </div>

        {/* 11-Stage Workflow Chevron Strip */}
        <div className="bg-slate-950/60 p-2 rounded-lg border border-white/10 flex items-center justify-between gap-1 overflow-x-auto text-[9px] font-bold text-slate-300">
          {[
            { step: '1. Research', desc: 'YouTube & TV' },
            { step: '2. Intake', desc: 'Normalized' },
            { step: '3. Organization', desc: 'Pair & Timeframe' },
            { step: '4. Backtest Lab', desc: 'Multi-regime' },
            { step: '5. Optimization', desc: 'Parameter sweep' },
            { step: '6. Robustness', desc: 'Monte Carlo / Cost' },
            { step: '7. Tournament', desc: 'Cohort rankings' },
            { step: '8. Paper Trading', desc: 'OANDA Sandbox' },
            { step: '9. Regime Eval', desc: 'Live regime filter' },
            { step: '10. Adaptation', desc: 'Controlled tuning' },
            { step: '11. Candidate', desc: 'Nova / Ray Review' }
          ].map((st, idx) => (
            <React.Fragment key={st.step}>
              {idx > 0 && <ArrowRight className="w-2.5 h-2.5 text-slate-600 shrink-0" />}
              <div className="bg-slate-900/90 px-1.5 py-1 rounded border border-slate-700/80 shrink-0 text-center space-y-0.5">
                <span className="font-black text-cyan-300 block">{st.step}</span>
                <span className="text-[7.5px] text-slate-400 font-medium block">{st.desc}</span>
              </div>
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* ===================================================================== */}
      {/* ROW 1: PANEL A (BROKERS) & PANEL G (MARKET REGIMES) & PANEL I (PROMISING CANDIDATE) */}
      {/* ===================================================================== */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
        {/* PANEL A: BROKER / MARKET CONNECTIONS (4 COLS) */}
        <div className="lg:col-span-4 bg-white rounded-xl border border-slate-200/90 shadow-2xs p-3 space-y-2 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-100 pb-1.5">
              <div className="flex items-center gap-1.5">
                <Radio className="w-3.5 h-3.5 text-blue-600" />
                <h3 className="text-xs font-black text-slate-900 uppercase tracking-wide">
                  A. Broker &amp; Market Connections
                </h3>
              </div>
              {renderTruthBadge('TEST_CANARY')}
            </div>
            <p className="text-[9.5px] text-slate-500 font-medium mt-1">
              Isolated API sandbox connections. Live order routing is strictly disabled.
            </p>

            <div className="space-y-1.5 mt-2">
              {/* OANDA Connection */}
              <div className="p-2 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-black text-slate-900 text-[11px]">OANDA (Forex / FX)</span>
                  <span className="px-1.5 py-0.2 rounded text-[8px] font-black uppercase bg-emerald-100 text-emerald-800 border border-emerald-200">
                    PRACTICE ACCOUNT
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-1 text-[9px] text-slate-600 font-mono">
                  <div>Account: <strong className="text-slate-800">OANDA-v20-PRAC-8910</strong></div>
                  <div>Latency: <strong className="text-emerald-700">18ms (Nominal)</strong></div>
                  <div>Market Data: <strong className="text-emerald-700">Tick Streaming Live</strong></div>
                  <div>Order Routing: <strong className="text-amber-700">Sandbox Simulated</strong></div>
                </div>
              </div>

              {/* Webull Connection */}
              <div className="p-2 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-black text-slate-900 text-[11px]">Webull (US Equities)</span>
                  <span className="px-1.5 py-0.2 rounded text-[8px] font-black uppercase bg-blue-100 text-blue-800 border border-blue-200">
                    SANDBOX METADATA
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-1 text-[9px] text-slate-600 font-mono">
                  <div>Account: <strong className="text-slate-800">WEBULL-SANDBOX-4402</strong></div>
                  <div>Quotes: <strong className="text-emerald-700">L1 Real-Time API</strong></div>
                  <div>Execution: <strong className="text-slate-500">Paper Fill Mirror</strong></div>
                  <div>Live Trading: <strong className="text-rose-700">DISABLED</strong></div>
                </div>
              </div>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[9px] text-slate-500">
            <span>Enforced Rule: Zero live financial exposure</span>
            <span className="font-bold text-rose-700">LIVE ORDERS = OFF</span>
          </div>
        </div>

        {/* PANEL G: MARKET REGIME (4 COLS) */}
        <div className="lg:col-span-4 bg-white rounded-xl border border-slate-200/90 shadow-2xs p-3 space-y-2 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-100 pb-1.5">
              <div className="flex items-center gap-1.5">
                <Sliders className="w-3.5 h-3.5 text-indigo-600" />
                <h3 className="text-xs font-black text-slate-900 uppercase tracking-wide">
                  G. Market Regime Panel
                </h3>
              </div>
              {renderTruthBadge('TEST_CANARY')}
            </div>
            <p className="text-[9.5px] text-slate-500 font-medium mt-1">
              Current detected macro volatility &amp; session regime. Unsupported states not claimed as proven.
            </p>

            {/* Regime States Grid */}
            <div className="grid grid-cols-2 gap-1.5 mt-2">
              {(
                [
                  { id: 'TRENDING', label: 'TRENDING', desc: 'Directional momentum > 1.4 ADX' },
                  { id: 'RANGING', label: 'RANGING', desc: 'Mean-reverting band boundaries' },
                  { id: 'HIGH VOLATILITY', label: 'HIGH VOLATILITY', desc: 'ATR > 85th historical percentile' },
                  { id: 'LOW VOLATILITY', label: 'LOW VOLATILITY', desc: 'Compressed spread & tight range' },
                  { id: 'BREAKOUT', label: 'BREAKOUT', desc: 'Volume expansion candle burst' },
                  { id: 'SESSION TRANSITION', label: 'SESSION TRANSITION', desc: 'London / NY Overlap liquidity shift' }
                ] as const
              ).map(reg => {
                const isActive = activeRegime === reg.id;
                return (
                  <button
                    key={reg.id}
                    type="button"
                    onClick={() => setActiveRegime(reg.id)}
                    className={`p-1.5 rounded-lg border text-left cursor-pointer transition-all ${
                      isActive
                        ? 'bg-blue-50 border-blue-300 ring-1 ring-blue-400/40 text-blue-950 font-black'
                        : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[9.5px] font-extrabold uppercase">{reg.label}</span>
                      {isActive && <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse" />}
                    </div>
                    <span className="text-[7.5px] text-slate-500 block leading-tight mt-0.5">{reg.desc}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[9px]">
            <span className="text-slate-500">Active Evaluation:</span>
            <strong className="text-blue-700 font-mono">{activeRegime} (Confidence: 84%)</strong>
          </div>
        </div>

        {/* PANEL I: PROMISING CANDIDATE (RAY / NOVA REVIEW) (4 COLS) */}
        <div className="lg:col-span-4 bg-gradient-to-br from-amber-500/10 via-amber-500/5 to-white rounded-xl border-2 border-amber-300 shadow-2xs p-3 space-y-2 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-amber-200 pb-1.5">
              <div className="flex items-center gap-1.5">
                <Trophy className="w-4 h-4 text-amber-600" />
                <h3 className="text-xs font-black text-amber-950 uppercase tracking-wide">
                  I. Promising Candidate Flagged
                </h3>
              </div>
              <span className="px-1.5 py-0.2 rounded text-[7.5px] font-black uppercase bg-amber-100 text-amber-900 border border-amber-300">
                RAY / NOVA REVIEW
              </span>
            </div>

            <div className="p-1 rounded bg-amber-100/60 border border-amber-200 text-[8px] font-semibold text-amber-900 mt-1">
              "Strong candidate for further validation" · Prohibits guaranteed income claims.
            </div>

            <div className="space-y-1.5 mt-1.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-black text-slate-900 text-xs">EUR/USD Mean Reversion v2.1</span>
                <span className="font-mono font-bold text-blue-700 text-[10px]">15m Timeframe</span>
              </div>

              <div className="grid grid-cols-3 gap-1 text-[9px] bg-white p-1.5 rounded border border-amber-200 text-center">
                <div>
                  <span className="text-slate-400 block text-[7.5px] uppercase">Profit Factor</span>
                  <strong className="text-emerald-700 font-black">1.84</strong>
                </div>
                <div>
                  <span className="text-slate-400 block text-[7.5px] uppercase">Max Drawdown</span>
                  <strong className="text-slate-900 font-black">3.2%</strong>
                </div>
                <div>
                  <span className="text-slate-400 block text-[7.5px] uppercase">Annualized Return</span>
                  <strong className="text-emerald-700 font-black">+28.4%</strong>
                </div>
              </div>

              <div className="text-[9px] text-slate-600 space-y-0.5 bg-white/80 p-1.5 rounded border border-slate-100">
                <div><strong>Test Period:</strong> 2021 - 2026 (5-Year Walk-Forward) · 412 trades</div>
                <div><strong>Paper Validation:</strong> 14 days active · 38 fills (+$1,420.50 simulated)</div>
                <div><strong>Regimes Tested:</strong> Ranging, Low Volatility, Session Transition</div>
                <div className="text-rose-700"><strong>Risk Flags:</strong> Sensitive to NFP / CPI flash spread disloc (&gt;4 bps)</div>
              </div>

              {onOpenChart && (
                <button
                  type="button"
                  onClick={() => onOpenChart('EUR/USD')}
                  className="w-full py-1.5 px-2.5 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-extrabold text-[10.5px] shadow-2xs flex items-center justify-center gap-1.5 transition-all cursor-pointer"
                >
                  <BarChart2 className="w-3.5 h-3.5 text-cyan-300" />
                  <span>Inspect Visual Day Replay &amp; Live SL/TP (EUR/USD)</span>
                  <ArrowRight className="w-3 h-3 text-white" />
                </button>
              )}
            </div>
          </div>

          <div className="pt-1.5 border-t border-amber-200/80 text-[8.5px] text-amber-950 font-medium">
            <strong>Why Promising:</strong> Expectancy $42.10/trade, OOS Sharpe decay &lt; 4%, zero curve-fit parameters.
          </div>
        </div>
      </div>

      {/* ===================================================================== */}
      {/* ROW 2: PANEL B (STRATEGY INVENTORY) */}
      {/* ===================================================================== */}
      <div className="bg-white rounded-xl border border-slate-200/90 shadow-2xs p-3 space-y-2">
        <div className="flex items-center justify-between border-b border-slate-100 pb-1.5 flex-wrap gap-2">
          <div>
            <div className="flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-blue-600" />
              <h3 className="text-xs font-black text-slate-900 uppercase tracking-wide">
                B. Strategy Inventory (Grouped by Pair &amp; Status)
              </h3>
              {renderTruthBadge('TEST_CANARY')}
            </div>
            <p className="text-[9.5px] text-slate-500 font-medium">
              Categorized through the entire deterministic lifecycle: RESEARCHED → NORMALIZED → BACKTESTING → OPTIMIZING → ROBUSTNESS → TOURNAMENT → PAPER → PROMISING → REJECTED.
            </p>
          </div>

          {/* Filters */}
          <div className="flex items-center gap-1.5 text-[9px] font-bold">
            <select
              value={selectedInventoryPair}
              onChange={e => setSelectedInventoryPair(e.target.value)}
              className="px-2 py-0.5 rounded bg-slate-50 border border-slate-200 text-slate-700"
            >
              <option value="ALL">All Pairs / Markets</option>
              <option value="EUR/USD">EUR/USD</option>
              <option value="SPY / QQQ">SPY / QQQ</option>
              <option value="GBP/USD">GBP/USD</option>
              <option value="USD/JPY">USD/JPY</option>
            </select>

            <select
              value={selectedInventoryStatus}
              onChange={e => setSelectedInventoryStatus(e.target.value)}
              className="px-2 py-0.5 rounded bg-slate-50 border border-slate-200 text-slate-700"
            >
              <option value="ALL">All Statuses ({STRATEGY_INVENTORY.length})</option>
              <option value="PROMISING">PROMISING</option>
              <option value="PAPER">PAPER</option>
              <option value="TOURNAMENT">TOURNAMENT</option>
              <option value="ROBUSTNESS">ROBUSTNESS</option>
              <option value="BACKTESTING">BACKTESTING</option>
              <option value="NORMALIZED">NORMALIZED</option>
              <option value="RESEARCHED">RESEARCHED</option>
              <option value="REJECTED">REJECTED</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead className="bg-slate-50 text-[9px] font-bold text-slate-400 uppercase border-b border-slate-100">
              <tr>
                <th className="py-1.5 px-2">Strategy Name</th>
                <th className="py-1.5 px-2">Market &amp; Pair</th>
                <th className="py-1.5 px-2">Timeframe</th>
                <th className="py-1.5 px-2">Strategy Type</th>
                <th className="py-1.5 px-2">Lifecycle Status</th>
                <th className="py-1.5 px-2">Profit Factor</th>
                <th className="py-1.5 px-2">Max Drawdown</th>
                <th className="py-1.5 px-2 text-right">Truth Class</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-[10px]">
              {filteredInventory.map(strat => (
                <tr key={strat.id} className="hover:bg-slate-50/80">
                  <td className="py-1.5 px-2 font-bold text-slate-900">{strat.name}</td>
                  <td className="py-1.5 px-2 font-mono text-slate-700">{strat.pair}</td>
                  <td className="py-1.5 px-2 font-mono text-slate-500">{strat.timeframe}</td>
                  <td className="py-1.5 px-2 text-slate-600">{strat.strategyType}</td>
                  <td className="py-1.5 px-2">
                    <span
                      className={`px-1.5 py-0.2 rounded text-[8px] font-black uppercase border ${
                        strat.status === 'PROMISING'
                          ? 'bg-amber-100 text-amber-900 border-amber-300'
                          : strat.status === 'PAPER'
                          ? 'bg-blue-100 text-blue-800 border-blue-200'
                          : strat.status === 'TOURNAMENT'
                          ? 'bg-indigo-100 text-indigo-800 border-indigo-200'
                          : strat.status === 'REJECTED'
                          ? 'bg-rose-100 text-rose-800 border-rose-200'
                          : 'bg-slate-100 text-slate-700 border-slate-200'
                      }`}
                    >
                      {strat.status}
                    </span>
                  </td>
                  <td className="py-1.5 px-2 font-bold text-emerald-700">{strat.profitFactor}</td>
                  <td className="py-1.5 px-2 font-mono text-slate-700">{strat.drawdown}</td>
                  <td className="py-1.5 px-2 text-right">{renderTruthBadge(strat.truthClass)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ===================================================================== */}
      {/* ROW 3: PANEL C (CURRENCY/PAIR INTELLIGENCE) & PANEL D (BACKTEST LAB) */}
      {/* ===================================================================== */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
        {/* PANEL C: CURRENCY / PAIR INTELLIGENCE (6 COLS) */}
        <div className="lg:col-span-6 bg-white rounded-xl border border-slate-200/90 shadow-2xs p-3 space-y-2">
          <div className="flex items-center justify-between border-b border-slate-100 pb-1.5">
            <div className="flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-blue-600" />
              <h3 className="text-xs font-black text-slate-900 uppercase tracking-wide">
                C. Currency &amp; Pair Intelligence
              </h3>
            </div>
            {renderTruthBadge('TEST_CANARY')}
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs">
            {[
              {
                pair: 'EUR/USD',
                timeframe: '15m / 1h',
                volatility: 'ATR: 42 pips (48th %ile)',
                spread: '0.4 bps avg',
                session: 'London / NY Overlap',
                regime: 'Ranging / Low Volatility',
                effectiveClasses: 'Mean Reversion, Bollinger Dynamic Bands',
                candidates: 'EUR/USD Mean Reversion v2.1 (Promising)'
              },
              {
                pair: 'GBP/USD',
                timeframe: '1h',
                volatility: 'ATR: 68 pips (72nd %ile)',
                spread: '0.8 bps avg',
                session: 'London Open',
                regime: 'Trending / Breakout',
                effectiveClasses: 'London Breakout, Donchian Channel Hunter',
                candidates: 'London Breakout Trend Hunter (Tournament)'
              },
              {
                pair: 'USD/JPY',
                timeframe: '5m',
                volatility: 'ATR: 54 pips (62nd %ile)',
                spread: '0.6 bps avg',
                session: 'Tokyo / Asian',
                regime: 'Range Bound',
                effectiveClasses: 'Asian Range Reversal, RSI Divergence',
                candidates: 'USD/JPY Asian Range Reversal (Robustness)'
              },
              {
                pair: 'SPY / US Equities',
                timeframe: '15m / 1h',
                volatility: 'VIX: 14.8 (Low)',
                spread: '1.0 cent liquid',
                session: 'US Regular Trading Hours',
                regime: 'Momentum Continuation',
                effectiveClasses: 'Volatility Expansion, Sector Skew Pairs',
                candidates: 'VEM-4 (Paper Trading)'
              }
            ].map(pair => (
              <div key={pair.pair} className="p-2 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <strong className="text-slate-900 font-black text-[11px]">{pair.pair}</strong>
                  <span className="font-mono text-[9px] text-blue-700 bg-blue-50 px-1 rounded">{pair.timeframe}</span>
                </div>
                <div className="text-[9px] text-slate-600 space-y-0.5">
                  <div>Spread: <strong className="text-slate-800">{pair.spread}</strong> · {pair.volatility}</div>
                  <div>Session: <strong className="text-slate-800">{pair.session}</strong></div>
                  <div>Regime: <strong className="text-indigo-700">{pair.regime}</strong></div>
                  <div className="text-[8.5px] text-slate-500">Effective: {pair.effectiveClasses}</div>
                  <div className="text-[8.5px] text-emerald-800 font-semibold">Active: {pair.candidates}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* PANEL D: BACKTEST LAB (6 COLS) */}
        <div className="lg:col-span-6 bg-white rounded-xl border border-slate-200/90 shadow-2xs p-3 space-y-2">
          <div className="flex items-center justify-between border-b border-slate-100 pb-1.5">
            <div className="flex items-center gap-1.5">
              <BarChart2 className="w-3.5 h-3.5 text-blue-600" />
              <h3 className="text-xs font-black text-slate-900 uppercase tracking-wide">
                D. Backtest Lab (Multi-Regime Walk-Forward)
              </h3>
            </div>
            {renderTruthBadge('TEST_CANARY')}
          </div>

          <div className="p-2 rounded-lg bg-blue-50/60 border border-blue-200 text-xs space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-bold text-blue-950">Active Test Target: EUR/USD Mean Reversion v2.1</span>
              <span className="text-[8.5px] font-mono text-blue-700">Run #BT-9904</span>
            </div>
            <div className="grid grid-cols-4 gap-1 text-center text-xs mt-1">
              <div className="bg-white p-1 rounded border border-blue-100">
                <span className="text-slate-400 block text-[7.5px] uppercase">Annual Return</span>
                <strong className="text-emerald-700 text-xs">+28.4%</strong>
              </div>
              <div className="bg-white p-1 rounded border border-blue-100">
                <span className="text-slate-400 block text-[7.5px] uppercase">Max Drawdown</span>
                <strong className="text-slate-900 text-xs">-3.2%</strong>
              </div>
              <div className="bg-white p-1 rounded border border-blue-100">
                <span className="text-slate-400 block text-[7.5px] uppercase">Profit Factor</span>
                <strong className="text-emerald-700 text-xs">1.84</strong>
              </div>
              <div className="bg-white p-1 rounded border border-blue-100">
                <span className="text-slate-400 block text-[7.5px] uppercase">Expectancy</span>
                <strong className="text-blue-900 text-xs">$42.10</strong>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-4 gap-1 text-[9px] bg-slate-50 p-2 rounded-lg border border-slate-200 text-center">
            <div>
              <span className="text-slate-400 block text-[7.5px] uppercase">Trade Count</span>
              <strong className="text-slate-800">412 Trades</strong>
            </div>
            <div>
              <span className="text-slate-400 block text-[7.5px] uppercase">Win Rate</span>
              <strong className="text-emerald-700">58.4%</strong>
            </div>
            <div>
              <span className="text-slate-400 block text-[7.5px] uppercase">Out-of-Sample</span>
              <strong className="text-emerald-700">PASSED (OOS 2025)</strong>
            </div>
            <div>
              <span className="text-slate-400 block text-[7.5px] uppercase">Robustness</span>
              <strong className="text-emerald-700">Monte Carlo 95% VaR OK</strong>
            </div>
          </div>

          <div className="text-[9px] text-slate-500 font-mono">
            Transaction cost stress test: Modeled at 1.5 bps slippage + $0.005/share fee schedule.
          </div>
        </div>
      </div>

      {/* ===================================================================== */}
      {/* ROW 4: PANEL E (TOURNAMENT) & PANEL F (PAPER TRADING) & PANEL H (STRATEGY ADAPTATION) */}
      {/* ===================================================================== */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
        {/* PANEL E: TOURNAMENT (COHORT RANKINGS) (4 COLS) */}
        <div className="lg:col-span-4 bg-white rounded-xl border border-slate-200/90 shadow-2xs p-3 space-y-2 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-100 pb-1.5">
              <div className="flex items-center gap-1.5">
                <Trophy className="w-3.5 h-3.5 text-amber-500" />
                <h3 className="text-xs font-black text-slate-900 uppercase tracking-wide">
                  E. Trading Tournament (Cohorts)
                </h3>
              </div>
              <span className="px-1 py-0.2 rounded text-[7.5px] font-black bg-amber-100 text-amber-800">
                ROUND 4
              </span>
            </div>
            <p className="text-[9.5px] text-slate-500 font-medium mt-1">
              Multi-dimensional evaluation: Not ranked only by raw profit. Compares within sensible cohorts.
            </p>

            <div className="flex items-center gap-1 mt-1 text-[8.5px] font-bold">
              <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-700">Entrants: 16</span>
              <span className="px-1.5 py-0.5 rounded bg-blue-100 text-blue-800">Finalists: 3</span>
              <span className="px-1.5 py-0.5 rounded bg-rose-100 text-rose-800">Eliminated: 11</span>
              <span className="px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800">Promoted: 1</span>
            </div>

            <div className="space-y-1.5 mt-2">
              {[
                {
                  rank: '#1',
                  name: 'EUR/USD Mean Reversion v2.1',
                  cohort: 'Forex 15m Mean Reversion',
                  pf: '1.84',
                  dd: '3.2%',
                  stability: '0.92 R²',
                  status: 'Promoted to Paper'
                },
                {
                  rank: '#2',
                  name: 'VEM-4 Expansion',
                  cohort: 'Equities 1h Volatility',
                  pf: '1.76',
                  dd: '4.8%',
                  stability: '0.88 R²',
                  status: 'Finalist'
                },
                {
                  rank: '#3',
                  name: 'London Breakout Trend Hunter',
                  cohort: 'Forex 1h Trend Following',
                  pf: '1.58',
                  dd: '5.1%',
                  stability: '0.84 R²',
                  status: 'Finalist'
                }
              ].map(t => (
                <div key={t.rank} className="p-1.5 rounded bg-slate-50 border border-slate-200 text-xs flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-1">
                      <span className="font-mono font-black text-amber-700 text-[9px]">{t.rank}</span>
                      <strong className="text-slate-900 text-[10px]">{t.name}</strong>
                    </div>
                    <span className="text-[8px] text-slate-500 block">{t.cohort}</span>
                  </div>
                  <div className="text-right text-[9px]">
                    <div className="font-mono font-bold text-emerald-700">PF: {t.pf} · DD: {t.dd}</div>
                    <span className="text-[7.5px] font-bold text-blue-700">{t.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-1.5 border-t border-slate-100 text-[8.5px] text-slate-500">
            Dimensions: Return, Drawdown, Profit Factor, Expectancy, Stability, OOS Robustness, Cost Sensitivity.
          </div>
        </div>

        {/* PANEL F: PAPER TRADING (SIMULATED PORTFOLIO) (4 COLS) */}
        <div className="lg:col-span-4 bg-white rounded-xl border border-slate-200/90 shadow-2xs p-3 space-y-2 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-100 pb-1.5">
              <div className="flex items-center gap-1.5">
                <DollarSign className="w-3.5 h-3.5 text-blue-600" />
                <h3 className="text-xs font-black text-slate-900 uppercase tracking-wide">
                  F. Paper Trading (OANDA Sandbox)
                </h3>
              </div>
              <span className="px-1 py-0.2 rounded text-[7.5px] font-black bg-blue-100 text-blue-700">
                SIMULATED
              </span>
            </div>
            <p className="text-[9.5px] text-slate-500 font-medium mt-1">
              Active paper execution monitoring. Time in validation seasoning and slippage tracking.
            </p>

            <div className="grid grid-cols-3 gap-1 text-[9px] bg-slate-50 p-1.5 rounded-lg border border-slate-200 text-center mt-1">
              <div>
                <span className="text-slate-400 block text-[7.5px] uppercase">Simulated P&amp;L</span>
                <strong className="text-emerald-700">+$1,420.50</strong>
              </div>
              <div>
                <span className="text-slate-400 block text-[7.5px] uppercase">Peak Drawdown</span>
                <strong className="text-slate-900">-0.8%</strong>
              </div>
              <div>
                <span className="text-slate-400 block text-[7.5px] uppercase">Active Signals</span>
                <strong className="text-blue-700">6 Signals</strong>
              </div>
            </div>

            <div className="space-y-1.5 mt-2 text-xs">
              <div className="p-1.5 rounded bg-slate-50 border border-slate-200 space-y-0.5">
                <div className="flex items-center justify-between text-[10px]">
                  <strong className="text-slate-900">EUR/USD Mean Reversion v2.1</strong>
                  <span className="font-mono text-emerald-700 font-bold">+$980.20</span>
                </div>
                <div className="text-[8.5px] text-slate-500 flex items-center justify-between">
                  <span>Validation: 14d / 30d required</span>
                  <span>Behavior: Fills matched within 0.3 bps</span>
                </div>
              </div>

              <div className="p-1.5 rounded bg-slate-50 border border-slate-200 space-y-0.5">
                <div className="flex items-center justify-between text-[10px]">
                  <strong className="text-slate-900">VEM-4 Expansion (SPY)</strong>
                  <span className="font-mono text-emerald-700 font-bold">+$440.30</span>
                </div>
                <div className="text-[8.5px] text-slate-500 flex items-center justify-between">
                  <span>Validation: 21d / 30d required</span>
                  <span>Behavior: Zero missed entry triggers</span>
                </div>
              </div>

              {onOpenChart && (
                <button
                  type="button"
                  onClick={() => onOpenChart('EUR/USD')}
                  className="w-full py-1 px-2 rounded-md bg-blue-50 hover:bg-blue-100 text-blue-700 font-bold text-[9.5px] border border-blue-200 flex items-center justify-center gap-1 cursor-pointer transition-colors"
                >
                  <BarChart2 className="w-3 h-3 text-blue-600" />
                  <span>Launch Live Chart &amp; SL/TP Terminal</span>
                </button>
              )}
            </div>
          </div>

          <div className="pt-1.5 border-t border-slate-100 text-[8.5px] text-slate-500">
            Regime validation: Continuously compared against live spread dislocation benchmarks.
          </div>
        </div>

        {/* PANEL H: STRATEGY ADAPTATION (CONTROLLED TUNING) (4 COLS) */}
        <div className="lg:col-span-4 bg-white rounded-xl border border-slate-200/90 shadow-2xs p-3 space-y-2 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-100 pb-1.5">
              <div className="flex items-center gap-1.5">
                <RefreshCw className="w-3.5 h-3.5 text-indigo-600" />
                <h3 className="text-xs font-black text-slate-900 uppercase tracking-wide">
                  H. Strategy Adaptation Flow
                </h3>
              </div>
              {renderTruthBadge('TEST_CANARY')}
            </div>
            <p className="text-[9.5px] text-slate-500 font-medium mt-1">
              Market change → Proposed adjustment → New version → Backtest → Robustness → Paper comparison. Old versions preserved.
            </p>

            {/* Adaptation Trace */}
            <div className="space-y-1.5 mt-2 text-[9.5px]">
              <div className="p-1.5 rounded bg-slate-50 border border-slate-200 space-y-0.5">
                <span className="text-[8px] text-slate-400 font-bold uppercase block">1. Market Trigger</span>
                <div className="font-medium text-slate-800">
                  Spread widened from 0.4 to 0.9 bps during Asian/London pre-market transition.
                </div>
              </div>

              <div className="p-1.5 rounded bg-blue-50/70 border border-blue-200 space-y-0.5">
                <span className="text-[8px] text-blue-600 font-bold uppercase block">2. Proposed Tuning</span>
                <div className="font-medium text-blue-950">
                  Dynamic Bollinger multiplier adjusted (2.0 → 2.3) + volatility filter.
                </div>
              </div>

              <div className="p-1.5 rounded bg-emerald-50/70 border border-emerald-200 space-y-0.5">
                <span className="text-[8px] text-emerald-700 font-bold uppercase block">3. Version Control</span>
                <div className="flex items-center justify-between text-[9px]">
                  <span>Archived: <strong>v1.0 (Preserved)</strong></span>
                  <span className="text-emerald-800 font-bold">Active: <strong>v2.1 (PF: 1.84)</strong></span>
                </div>
              </div>
            </div>
          </div>

          <div className="pt-1.5 border-t border-slate-100 text-[8.5px] text-slate-500 flex items-center justify-between">
            <span>Historical versions: Preserved in immutable DB</span>
            <span className="text-indigo-700 font-bold">Zero overwrite</span>
          </div>
        </div>
      </div>
    </div>
  );
};
