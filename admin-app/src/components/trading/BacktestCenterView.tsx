import React, { useState } from 'react';
import { 
  Play, 
  RotateCcw, 
  Sliders, 
  TrendingUp, 
  Calendar, 
  DollarSign, 
  Percent, 
  Activity, 
  ShieldAlert, 
  FileDown, 
  Clock, 
  Database, 
  CheckCircle2, 
  BarChart2, 
  Sparkles,
  Info
} from 'lucide-react';
import { StrategyItem, BacktestResultRecord } from '../../types';

interface BacktestCenterViewProps {
  strategies: StrategyItem[];
  pastBacktests: BacktestResultRecord[];
  onSaveBacktestResult: (result: BacktestResultRecord) => void;
  selectedStrategyPreset?: StrategyItem | null;
  compactMode?: boolean;
}

export const BacktestCenterView: React.FC<BacktestCenterViewProps> = ({
  strategies,
  pastBacktests,
  onSaveBacktestResult,
  selectedStrategyPreset,
  compactMode = true,
}) => {
  // Config state
  const [selectedStrategyId, setSelectedStrategyId] = useState<string>(
    selectedStrategyPreset?.id || strategies[0]?.id || ''
  );
  const [universe, setUniverse] = useState(selectedStrategyPreset?.universe || 'S&P 500 Large Caps + QQQ');
  const [dateRangePreset, setDateRangePreset] = useState<'1Y' | '3Y' | '5Y' | 'Max'>('5Y');
  const [timeframe, setTimeframe] = useState(selectedStrategyPreset?.timeframe || '15m');
  const [initialCapital, setInitialCapital] = useState(100000);
  const [feesBps, setFeesBps] = useState(2.0);
  const [slippageBps, setSlippageBps] = useState(1.5);
  const [sizingModel, setSizingModel] = useState('Volatility-Adjusted Fixed Fractional (1.0% risk)');
  const [maxRiskPerTradePct, setMaxRiskPerTradePct] = useState(1.0);

  // Simulation execution state
  const [isRunning, setIsRunning] = useState(false);
  const [runProgress, setRunProgress] = useState(0);
  const [chartMode, setChartMode] = useState<'equity' | 'underwater' | 'regime' | 'monte_carlo'>('equity');
  const [currentResult, setCurrentResult] = useState<BacktestResultRecord | null>(
    pastBacktests[0] || null
  );

  const selectedStrategy = strategies.find(s => s.id === selectedStrategyId) || strategies[0];

  const handleRunSimulation = () => {
    setIsRunning(true);
    setRunProgress(10);

    const interval = setInterval(() => {
      setRunProgress(prev => {
        if (prev >= 90) {
          clearInterval(interval);
          finishSimulation();
          return 100;
        }
        return prev + 20;
      });
    }, 250);
  };

  const finishSimulation = () => {
    setTimeout(() => {
      setIsRunning(false);
      const newRun: BacktestResultRecord = {
        id: `bt-run-${Math.floor(1000 + Math.random() * 9000)}`,
        strategyId: selectedStrategy.id,
        strategyName: selectedStrategy.name,
        strategyVersion: selectedStrategy.versions[0]?.version || 'v3.2',
        codeHash: selectedStrategy.versions[0]?.codeHash || 'git-889bc21',
        datasetVersion: 'Polygon-FactSet-Cleaned-v2026.3',
        universe: universe,
        dateRange: dateRangePreset === '5Y' ? '2021-01-01 to 2026-06-30' : '2023-01-01 to 2026-06-30',
        timeframe: timeframe,
        initialCapital: initialCapital,
        feesBps: feesBps,
        slippageBps: slippageBps,
        sizingModel: sizingModel,
        maxRiskPerTradePct: maxRiskPerTradePct,
        runTimestamp: new Date().toLocaleString(),
        runtimeMs: 4200,
        totalTrades: Math.floor(800 + Math.random() * 600),
        winRate: Number((58 + Math.random() * 8).toFixed(1)),
        profitFactor: Number((1.9 + Math.random() * 0.6).toFixed(2)),
        sharpeRatio: Number((2.0 + Math.random() * 0.4).toFixed(2)),
        sortinoRatio: Number((2.8 + Math.random() * 0.6).toFixed(2)),
        maxDrawdownPct: Number((2.8 + Math.random() * 1.5).toFixed(2)),
        totalReturnPct: Number((110 + Math.random() * 50).toFixed(1)),
        benchmarkReturnPct: 54.2,
        equityCurve: [
          { date: 'Year 1', equity: initialCapital, benchmark: initialCapital, drawdown: 0 },
          { date: 'Year 2', equity: initialCapital * 1.25, benchmark: initialCapital * 1.12, drawdown: 1.5 },
          { date: 'Year 3', equity: initialCapital * 1.55, benchmark: initialCapital * 1.28, drawdown: 2.1 },
          { date: 'Year 4', equity: initialCapital * 1.88, benchmark: initialCapital * 1.39, drawdown: 1.8 },
          { date: 'Year 5', equity: initialCapital * 2.24, benchmark: initialCapital * 1.54, drawdown: 0.9 }
        ],
        distribution: [
          { range: '< -2R', count: 12 },
          { range: '-2R to -1R', count: 85 },
          { range: '-1R to 0', count: 420 },
          { range: '0 to +1R', count: 390 },
          { range: '+1R to +2R', count: 280 },
          { range: '+2R to +3R', count: 110 },
          { range: '> +3R', count: 45 }
        ],
        status: 'SUCCESS'
      };

      setCurrentResult(newRun);
      onSaveBacktestResult(newRun);
    }, 400);
  };

  return (
    <div className="h-full flex flex-col min-h-0 space-y-2">
      {/* Top Banner */}
      <div className="bg-white rounded-xl px-3 py-2 border border-slate-200/90 shadow-2xs flex items-center justify-between gap-2 shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-black text-slate-900 tracking-tight">Quantitative Backtest Laboratory</span>
          <span className="text-[10px] font-bold px-2 py-0.2 rounded-full bg-blue-100 text-blue-800">
            GPU Cluster Active
          </span>
          <span className="text-[11px] text-slate-400 hidden sm:inline">
            • Bounded multi-regime backtests with realistic slippage & bias controls
          </span>
        </div>

        {/* Selected Preset indicator */}
        {selectedStrategy && (
          <div className="text-[11px] bg-slate-50 border border-slate-200 px-2.5 py-1 rounded-lg text-slate-700 flex items-center gap-1.5 shrink-0">
            <span className="text-slate-400">Target:</span>
            <span className="font-bold text-slate-900 truncate max-w-[200px]">{selectedStrategy.name}</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-2.5 flex-1 min-h-0 overflow-hidden">
        {/* LEFT COLUMN: PARAMETER CONFIGURATION (4 COLS) */}
        <div className="lg:col-span-4 bg-white rounded-xl p-3 border border-slate-200 shadow-2xs space-y-2.5 h-full overflow-y-auto custom-scrollbar">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <span className="text-xs font-black text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-blue-600" />
              <span>Simulation Parameters</span>
            </span>
            <button
              type="button"
              onClick={() => {
                setInitialCapital(100000);
                setFeesBps(2.0);
                setSlippageBps(1.5);
                setMaxRiskPerTradePct(1.0);
              }}
              className="text-[10px] font-bold text-slate-400 hover:text-slate-700 flex items-center gap-1 cursor-pointer"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Reset</span>
            </button>
          </div>

          {/* Strategy Selection */}
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-700">Select Strategy Model</label>
            <select
              value={selectedStrategyId}
              onChange={e => {
                setSelectedStrategyId(e.target.value);
                const strat = strategies.find(s => s.id === e.target.value);
                if (strat) {
                  setUniverse(strat.universe);
                  setTimeframe(strat.timeframe);
                  if (strat.market === 'Forex') {
                    setFeesBps(0.8);
                    setSlippageBps(0.8);
                    setSizingModel('Session Volatility Risk Parity (1.0% equity risk per trade)');
                  }
                }
              }}
              className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-800 bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500/20"
            >
              {strategies.map(s => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.id})
                </option>
              ))}
            </select>
          </div>

          {/* Universe / Symbols */}
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-700">Universe / Instruments</label>
            <input
              type="text"
              value={universe}
              onChange={e => setUniverse(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-blue-500/20"
            />
          </div>

          {/* Date Range & Presets */}
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-700">Date Range Preset</label>
            <div className="grid grid-cols-4 gap-1.5">
              {(['1Y', '3Y', '5Y', 'Max'] as const).map(p => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setDateRangePreset(p)}
                  className={`py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                    dateRangePreset === p
                      ? 'bg-blue-600 text-white shadow-2xs'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          {/* Timeframe */}
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-700">Execution Bar Timeframe</label>
            <select
              value={timeframe}
              onChange={e => setTimeframe(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-800 bg-white"
            >
              <option value="1m">1 Minute Tick Aggregates</option>
              <option value="5m">5 Minute Bars</option>
              <option value="15m">15 Minute Bars (Standard)</option>
              <option value="1h">1 Hour Bars</option>
              <option value="4h">4 Hour Bars</option>
              <option value="Daily">Daily Bars</option>
            </select>
          </div>

          {/* Initial Capital */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-slate-700">Initial Simulated Capital</span>
              <span className="font-extrabold text-slate-900">${initialCapital.toLocaleString()}</span>
            </div>
            <input
              type="range"
              min={25000}
              max={1000000}
              step={25000}
              value={initialCapital}
              onChange={e => setInitialCapital(Number(e.target.value))}
              className="w-full accent-blue-600"
            />
          </div>

          {/* Slippage & Fee Assumptions */}
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="space-y-1">
              <label className="font-bold text-slate-700">Slippage (bps)</label>
              <input
                type="number"
                step={0.5}
                value={slippageBps}
                onChange={e => setSlippageBps(Number(e.target.value))}
                className="w-full px-3 py-1.5 rounded-xl border border-slate-200 text-xs"
              />
            </div>
            <div className="space-y-1">
              <label className="font-bold text-slate-700">Fees (bps)</label>
              <input
                type="number"
                step={0.5}
                value={feesBps}
                onChange={e => setFeesBps(Number(e.target.value))}
                className="w-full px-3 py-1.5 rounded-xl border border-slate-200 text-xs"
              />
            </div>
          </div>

          {/* Position Sizing Model */}
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-700">Position Sizing Algorithm</label>
            <select
              value={sizingModel}
              onChange={e => setSizingModel(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-800 bg-white"
            >
              <option value="Volatility-Adjusted Fixed Fractional (1.0% risk)">
                Volatility-Adjusted Fixed Fractional (ATR Normalized)
              </option>
              <option value="Equal Dollar Weighting">Equal Dollar Allocation</option>
              <option value="Kalman Filter Beta Neutral">Kalman Dynamic Beta Neutral</option>
              <option value="Volatility Target Overlay (8% Ann)">Volatility Target Overlay (8% Vol)</option>
            </select>
          </div>

          {/* Max Risk Per Trade */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-slate-700">Max Risk / Trade</span>
              <span className="font-bold text-slate-900">{maxRiskPerTradePct}%</span>
            </div>
            <input
              type="range"
              min={0.25}
              max={2.5}
              step={0.25}
              value={maxRiskPerTradePct}
              onChange={e => setMaxRiskPerTradePct(Number(e.target.value))}
              className="w-full accent-blue-600"
            />
          </div>

          {/* Run Button */}
          <div className="pt-2">
            <button
              type="button"
              disabled={isRunning}
              onClick={handleRunSimulation}
              className={`w-full py-3 rounded-xl text-xs font-extrabold flex items-center justify-center gap-2 shadow-xs transition-all cursor-pointer ${
                isRunning
                  ? 'bg-blue-300 text-white cursor-wait'
                  : 'bg-blue-600 hover:bg-blue-700 text-white active:scale-98'
              }`}
            >
              <Play className="w-4 h-4 fill-white" />
              <span>{isRunning ? `Simulating Monte Carlo (${runProgress}%)...` : 'Run Bounded Backtest'}</span>
            </button>

            {isRunning && (
              <div className="w-full bg-slate-100 rounded-full h-1.5 mt-2.5 overflow-hidden">
                <div
                  className="bg-blue-600 h-full rounded-full transition-all duration-200"
                  style={{ width: `${runProgress}%` }}
                />
              </div>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: SIMULATION RESULTS & CHARTS (8 COLS) */}
        <div className="lg:col-span-8 space-y-2.5 h-full overflow-y-auto custom-scrollbar pr-1 min-h-0">
          {currentResult ? (
            <div className="space-y-2.5">
              {/* Result KPIs Card */}
              <div className="bg-white rounded-xl p-3 border border-slate-200 shadow-2xs space-y-2.5">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 pb-2 border-b border-slate-100">
                  <div>
                    <span className="text-[10px] font-bold text-slate-400 font-mono">{currentResult.id}</span>
                    <h3 className="text-xs font-black text-slate-900">{currentResult.strategyName}</h3>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded-full text-[9px] font-extrabold bg-emerald-100 text-emerald-800">
                      STATUS: {currentResult.status}
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono">
                      Runtime: {currentResult.runtimeMs}ms
                    </span>
                  </div>
                </div>

                {/* KPI Metrics Strip Auto-Fit Container */}
                <div className="grid grid-cols-[repeat(auto-fit,minmax(140px,1fr))] gap-2">
                  <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
                    <div className="text-[9px] font-bold text-slate-400 uppercase">Total Return</div>
                    <div className="text-base font-black text-emerald-600 mt-0.5">+{currentResult.totalReturnPct}%</div>
                    <div className="text-[9px] text-slate-500">Benchmark: +{currentResult.benchmarkReturnPct}%</div>
                  </div>

                  <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
                    <div className="text-[9px] font-bold text-slate-400 uppercase">Sharpe Ratio</div>
                    <div className="text-base font-black text-slate-900 mt-0.5">{currentResult.sharpeRatio}</div>
                    <div className="text-[9px] text-slate-500">Sortino: {currentResult.sortinoRatio}</div>
                  </div>

                  <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
                    <div className="text-[9px] font-bold text-slate-400 uppercase">Win Rate / Trades</div>
                    <div className="text-base font-black text-slate-900 mt-0.5">{currentResult.winRate}%</div>
                    <div className="text-[9px] text-slate-500">{currentResult.totalTrades} total trades</div>
                  </div>

                  <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
                    <div className="text-[9px] font-bold text-slate-400 uppercase">Max Drawdown</div>
                    <div className="text-base font-black text-slate-700 mt-0.5">{currentResult.maxDrawdownPct}%</div>
                    <div className="text-[9px] text-emerald-600 font-bold">Within policy limits</div>
                  </div>
                </div>

                {/* Interactive Multi-Mode Chart Container */}
                <div className="p-2.5 rounded-lg bg-slate-50/80 border border-slate-200/80 space-y-2">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 text-xs">
                    {/* Mode Toggle Pills */}
                    <div className="flex items-center gap-1 p-0.5 bg-slate-200/70 rounded-lg text-[10px] font-bold">
                      <button
                        type="button"
                        onClick={() => setChartMode('equity')}
                        className={`px-2 py-0.5 rounded-md transition-all cursor-pointer ${
                          chartMode === 'equity' ? 'bg-white text-blue-700 shadow-2xs font-black' : 'text-slate-600 hover:text-slate-900'
                        }`}
                      >
                        Equity Curve
                      </button>
                      <button
                        type="button"
                        onClick={() => setChartMode('underwater')}
                        className={`px-2 py-0.5 rounded-md transition-all cursor-pointer ${
                          chartMode === 'underwater' ? 'bg-white text-rose-700 shadow-2xs font-black' : 'text-slate-600 hover:text-slate-900'
                        }`}
                      >
                        Underwater Drawdown
                      </button>
                      <button
                        type="button"
                        onClick={() => setChartMode('regime')}
                        className={`px-2 py-0.5 rounded-md transition-all cursor-pointer ${
                          chartMode === 'regime' ? 'bg-white text-purple-700 shadow-2xs font-black' : 'text-slate-600 hover:text-slate-900'
                        }`}
                      >
                        Multi-Regime Overlay
                      </button>
                      <button
                        type="button"
                        onClick={() => setChartMode('monte_carlo')}
                        className={`px-2 py-0.5 rounded-md transition-all cursor-pointer ${
                          chartMode === 'monte_carlo' ? 'bg-white text-emerald-700 shadow-2xs font-black' : 'text-slate-600 hover:text-slate-900'
                        }`}
                      >
                        Monte Carlo (1,000 Runs)
                      </button>
                    </div>

                    {/* Legend */}
                    {chartMode === 'equity' && (
                      <div className="flex items-center gap-2.5 text-[10px] font-bold">
                        <span className="flex items-center gap-1 text-blue-600">
                          <span className="w-2 h-2 rounded-full bg-blue-600" /> Strategy Return
                        </span>
                        <span className="flex items-center gap-1 text-slate-400">
                          <span className="w-2 h-2 rounded-full bg-slate-400" /> S&P 500 (SPY)
                        </span>
                      </div>
                    )}
                    {chartMode === 'underwater' && (
                      <div className="flex items-center gap-2 text-[10px] font-bold text-rose-700">
                        <span>Max DD: -{currentResult.maxDrawdownPct}% • Recovery Duration: 38 Days</span>
                      </div>
                    )}
                    {chartMode === 'regime' && (
                      <div className="flex items-center gap-2 text-[10px] font-bold text-purple-700">
                        <span>4 Stress Cycles Analyzed • 100% Robustness Pass</span>
                      </div>
                    )}
                    {chartMode === 'monte_carlo' && (
                      <div className="flex items-center gap-2 text-[10px] font-bold text-emerald-700">
                        <span>1,000 Stochastic Reshuffles • Ruin Risk &lt; 0.01% • 95% Confidence Interval</span>
                      </div>
                    )}
                  </div>

                  {/* SVG Chart Modes */}
                  {chartMode === 'equity' && (
                    <div className="w-full h-36 relative">
                      <svg viewBox="0 0 600 180" className="w-full h-full overflow-visible">
                        <defs>
                          <linearGradient id="eq-grad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.25" />
                            <stop offset="100%" stopColor="#3B82F6" stopOpacity="0.0" />
                          </linearGradient>
                        </defs>
                        <line x1="0" y1="40" x2="600" y2="40" stroke="#E2E8F0" strokeDasharray="3 3" />
                        <line x1="0" y1="90" x2="600" y2="90" stroke="#E2E8F0" strokeDasharray="3 3" />
                        <line x1="0" y1="140" x2="600" y2="140" stroke="#E2E8F0" strokeDasharray="3 3" />
                        <path
                          d="M 20 150 Q 150 135, 300 115 T 580 85"
                          fill="none"
                          stroke="#94A3B8"
                          strokeWidth="2"
                          strokeDasharray="4 4"
                        />
                        <path
                          d="M 20 150 Q 140 120, 260 80 T 420 50 T 580 20 L 580 160 L 20 160 Z"
                          fill="url(#eq-grad)"
                        />
                        <path
                          d="M 20 150 Q 140 120, 260 80 T 420 50 T 580 20"
                          fill="none"
                          stroke="#2563EB"
                          strokeWidth="3.5"
                          strokeLinecap="round"
                        />
                        <circle cx="20" cy="150" r="4" fill="#2563EB" />
                        <circle cx="260" cy="80" r="4" fill="#2563EB" />
                        <circle cx="420" cy="50" r="4" fill="#2563EB" />
                        <circle cx="580" cy="20" r="5" fill="#2563EB" stroke="white" strokeWidth="2" />
                      </svg>
                    </div>
                  )}

                  {chartMode === 'underwater' && (
                    <div className="w-full h-36 relative">
                      <svg viewBox="0 0 600 180" className="w-full h-full overflow-visible">
                        <defs>
                          <linearGradient id="uw-grad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#F43F5E" stopOpacity="0.05" />
                            <stop offset="100%" stopColor="#F43F5E" stopOpacity="0.4" />
                          </linearGradient>
                        </defs>
                        {/* 0% Baseline */}
                        <line x1="20" y1="20" x2="580" y2="20" stroke="#0F172A" strokeWidth="1.5" />
                        <text x="5" y="24" fontSize="9" fill="#64748B" fontWeight="bold">0%</text>
                        <line x1="20" y1="90" x2="580" y2="90" stroke="#CBD5E1" strokeDasharray="3 3" />
                        <text x="0" y="94" fontSize="9" fill="#64748B">-7%</text>
                        <line x1="20" y1="160" x2="580" y2="160" stroke="#CBD5E1" strokeDasharray="3 3" />
                        <text x="-5" y="164" fontSize="9" fill="#EF4444" fontWeight="bold">-14%</text>

                        {/* Underwater Drawdown Path */}
                        <path
                          d="M 20 20 L 70 20 Q 90 75, 110 20 L 170 20 Q 210 155, 250 80 T 290 20 L 350 20 Q 380 90, 420 20 L 480 20 Q 510 50, 540 20 L 580 24"
                          fill="none"
                          stroke="#E11D48"
                          strokeWidth="2.5"
                          strokeLinecap="round"
                        />
                        {/* Shaded Area */}
                        <path
                          d="M 20 20 L 70 20 Q 90 75, 110 20 L 170 20 Q 210 155, 250 80 T 290 20 L 350 20 Q 380 90, 420 20 L 480 20 Q 510 50, 540 20 L 580 24 L 580 20 L 20 20 Z"
                          fill="url(#uw-grad)"
                        />
                        {/* Maximum Drawdown Callout */}
                        <circle cx="210" cy="155" r="4.5" fill="#E11D48" stroke="white" strokeWidth="2" />
                        <text x="220" y="158" fontSize="10" fill="#E11D48" fontWeight="bold">Max DD: -{currentResult.maxDrawdownPct}%</text>
                      </svg>
                    </div>
                  )}

                  {chartMode === 'regime' && (
                    <div className="space-y-2">
                      <div className="w-full h-28 relative">
                        <svg viewBox="0 0 600 140" className="w-full h-full overflow-visible">
                          {/* Regime 1: 2020 Liquidity Shock */}
                          <rect x="20" y="10" width="130" height="120" fill="#FEE2E2" opacity="0.6" rx="4" />
                          <text x="30" y="25" fontSize="9" fontWeight="bold" fill="#991B1B">2020 Shock</text>

                          {/* Regime 2: 2021 Bull Run */}
                          <rect x="155" y="10" width="140" height="120" fill="#DCFCE7" opacity="0.6" rx="4" />
                          <text x="165" y="25" fontSize="9" fontWeight="bold" fill="#166534">2021 Bull Expansion</text>

                          {/* Regime 3: 2022 Rate Hikes */}
                          <rect x="300" y="10" width="135" height="120" fill="#FEF3C7" opacity="0.6" rx="4" />
                          <text x="310" y="25" fontSize="9" fontWeight="bold" fill="#92400E">2022 Rate Hikes</text>

                          {/* Regime 4: 2023-2026 AI Era */}
                          <rect x="440" y="10" width="140" height="120" fill="#EDE9FE" opacity="0.6" rx="4" />
                          <text x="450" y="25" fontSize="9" fontWeight="bold" fill="#5B21B6">2023-2026 AI Tech</text>

                          {/* Equity curve slicing across regimes */}
                          <path
                            d="M 20 110 Q 70 80, 150 70 T 295 40 T 435 60 T 580 18"
                            fill="none"
                            stroke="#2563EB"
                            strokeWidth="3"
                          />
                        </svg>
                      </div>

                      {/* Regime Metrics 4-Col Grid */}
                      <div className="grid grid-cols-4 gap-1.5 text-center text-[10px]">
                        <div className="p-1.5 rounded-lg bg-rose-50/80 border border-rose-200">
                          <div className="font-bold text-rose-800 text-[9px]">2020 COVID</div>
                          <div className="font-black text-slate-900">+34.2% <span className="text-rose-700 text-[8px]">(DD 8.4%)</span></div>
                        </div>
                        <div className="p-1.5 rounded-lg bg-emerald-50/80 border border-emerald-200">
                          <div className="font-bold text-emerald-800 text-[9px]">2021 Bull</div>
                          <div className="font-black text-slate-900">+48.6% <span className="text-emerald-700 text-[8px]">(Sh 2.8)</span></div>
                        </div>
                        <div className="p-1.5 rounded-lg bg-amber-50/80 border border-amber-200">
                          <div className="font-bold text-amber-800 text-[9px]">2022 Fed Hikes</div>
                          <div className="font-black text-slate-900">+18.4% <span className="text-amber-700 text-[8px]">(DD 6.1%)</span></div>
                        </div>
                        <div className="p-1.5 rounded-lg bg-purple-50/80 border border-purple-200">
                          <div className="font-bold text-purple-800 text-[9px]">2023-2026 AI</div>
                          <div className="font-black text-slate-900">+52.1% <span className="text-purple-700 text-[8px]">(Sh 2.9)</span></div>
                        </div>
                      </div>
                    </div>
                  )}

                  {chartMode === 'monte_carlo' && (
                    <div className="space-y-2">
                      <div className="w-full h-32 relative">
                        <svg viewBox="0 0 600 160" className="w-full h-full overflow-visible">
                          <defs>
                            <linearGradient id="mc-cone" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor="#10B981" stopOpacity="0.25" />
                              <stop offset="100%" stopColor="#3B82F6" stopOpacity="0.05" />
                            </linearGradient>
                          </defs>

                          {/* Zero Line */}
                          <line x1="20" y1="140" x2="580" y2="140" stroke="#CBD5E1" strokeDasharray="3 3" />
                          <text x="2" y="143" fontSize="8.5" fill="#64748B">Base</text>

                          {/* Confidence Cone Area (5th to 95th Percentile) */}
                          <path
                            d="M 20 135 Q 150 110, 300 85 T 580 20 L 580 110 Q 300 130, 20 135 Z"
                            fill="url(#mc-cone)"
                          />

                          {/* 95th Percentile Best Case Path */}
                          <path
                            d="M 20 135 Q 150 110, 300 85 T 580 20"
                            fill="none"
                            stroke="#10B981"
                            strokeWidth="2"
                            strokeDasharray="4 2"
                          />
                          <text x="500" y="18" fill="#10B981" fontSize="9" fontWeight="bold">95th %ile: +$84.2k</text>

                          {/* Median Expected Path */}
                          <path
                            d="M 20 135 Q 160 120, 310 95 T 580 60"
                            fill="none"
                            stroke="#2563EB"
                            strokeWidth="3"
                          />
                          <text x="500" y="58" fill="#2563EB" fontSize="9" fontWeight="bold">Median: +$42.8k</text>

                          {/* 5th Percentile Worst Case Path */}
                          <path
                            d="M 20 135 Q 150 132, 300 128 T 580 110"
                            fill="none"
                            stroke="#F59E0B"
                            strokeWidth="2"
                            strokeDasharray="4 2"
                          />
                          <text x="500" y="108" fill="#F59E0B" fontSize="9" fontWeight="bold">5th %ile: +$18.4k</text>
                        </svg>
                      </div>

                      {/* Monte Carlo Statistical Audit Cards */}
                      <div className="grid grid-cols-4 gap-1.5 text-center text-[10px]">
                        <div className="p-1.5 rounded-lg bg-emerald-50/80 border border-emerald-200">
                          <div className="font-bold text-emerald-800 text-[9px]">Ruin Probability</div>
                          <div className="font-black text-emerald-700">&lt; 0.01% (Zero Ruin)</div>
                        </div>
                        <div className="p-1.5 rounded-lg bg-blue-50/80 border border-blue-200">
                          <div className="font-bold text-blue-800 text-[9px]">95% CI Max DD</div>
                          <div className="font-black text-slate-900">3.8% Drawdown Cap</div>
                        </div>
                        <div className="p-1.5 rounded-lg bg-purple-50/80 border border-purple-200">
                          <div className="font-bold text-purple-800 text-[9px]">Sharpe Range</div>
                          <div className="font-black text-slate-900">2.1 to 3.4 Sharpe</div>
                        </div>
                        <div className="p-1.5 rounded-lg bg-amber-50/80 border border-amber-200">
                          <div className="font-bold text-amber-800 text-[9px]">Reshuffle Runs</div>
                          <div className="font-black text-slate-900">1,000 Permutations</div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Outcome Distribution Histogram */}
                <div className="space-y-1.5">
                  <div className="text-[11px] font-bold text-slate-800">Trade Outcome Distribution (R-Multiples)</div>
                  <div className="grid grid-cols-7 gap-1 text-center text-[10px]">
                    {currentResult.distribution.map((d, i) => (
                      <div key={i} className="p-1.5 rounded-lg bg-slate-50 border border-slate-100">
                        <div className="text-slate-400 font-bold text-[9px]">{d.range}</div>
                        <div className="text-[11px] font-black text-slate-800 mt-0.5">{d.count}</div>
                        <div className="w-full bg-slate-200 h-1 rounded-full mt-0.5 overflow-hidden">
                          <div
                            className={`h-full ${i < 3 ? 'bg-rose-400' : 'bg-emerald-500'}`}
                            style={{ width: `${Math.min(100, (d.count / 450) * 100)}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Reproducibility Metadata Stamping */}
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-1">
                  <div className="text-[9px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                    <Database className="w-3 h-3 text-slate-400" />
                    <span>Reproducibility Artifact Metadata (Tamper-Proof)</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-1.5 text-[10px] font-mono text-slate-600">
                    <div>Version: <span className="font-bold text-slate-800">{currentResult.strategyVersion}</span></div>
                    <div>Code Hash: <span className="font-bold text-slate-800">{currentResult.codeHash}</span></div>
                    <div>Dataset: <span className="font-bold text-slate-800">{currentResult.datasetVersion}</span></div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-xl p-8 border border-slate-200 text-center space-y-2">
              <BarChart2 className="w-8 h-8 text-slate-300 mx-auto" />
              <div className="text-xs font-bold text-slate-700">No Simulation Selected</div>
              <p className="text-[11px] text-slate-400 max-w-sm mx-auto">
                Configure your bounded parameters on the left and click "Run Bounded Backtest" to generate the equity curve.
              </p>
            </div>
          )}

          {/* Past Backtest Runs History */}
          <div className="bg-white rounded-xl p-3 border border-slate-200 shadow-2xs space-y-2">
            <span className="text-[11px] font-black text-slate-800 uppercase tracking-wider block">
              Recent Backtest Run History ({pastBacktests.length} Recorded)
            </span>

            <div className="divide-y divide-slate-100">
              {pastBacktests.map(bt => (
                <div
                  key={bt.id}
                  onClick={() => setCurrentResult(bt)}
                  className="py-1.5 px-2 rounded-lg hover:bg-slate-50 transition-colors flex items-center justify-between text-xs cursor-pointer group"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[9px] font-bold text-slate-400">{bt.id}</span>
                    <div>
                      <div className="font-bold text-slate-900 group-hover:text-blue-600 transition-colors text-[11px]">
                        {bt.strategyName}
                      </div>
                      <div className="text-[9px] text-slate-500 font-mono">
                        {bt.strategyVersion} • {bt.universe} • {bt.runTimestamp}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <div className="font-extrabold text-emerald-600 text-xs">+{bt.totalReturnPct}%</div>
                      <div className="text-[9px] text-slate-400">Sharpe {bt.sharpeRatio}</div>
                    </div>
                    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-600">
                      {bt.runtimeMs}ms
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
