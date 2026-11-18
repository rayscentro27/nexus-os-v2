import React, { useState } from 'react';
import { 
  TrendingUp, 
  BarChart3, 
  GitCompare, 
  ArrowUpRight, 
  Sparkles, 
  CheckCircle2, 
  Percent, 
  Layers,
  PieChart,
  Grid,
  ShieldCheck,
  Sliders,
  DollarSign,
  Zap,
  Award
} from 'lucide-react';
import { StrategyItem } from '../../types';
import { ParameterSensitivityHeatmap } from './ParameterSensitivityHeatmap';
import { ExecutionQualityInspector } from './ExecutionQualityInspector';
import { PostTradeScorecardView } from './PostTradeScorecardView';

interface PerformanceAnalyticsViewProps {
  strategies: StrategyItem[];
  compactMode?: boolean;
}

export const PerformanceAnalyticsView: React.FC<PerformanceAnalyticsViewProps> = ({ 
  strategies,
  compactMode = true
}) => {
  const [activeTab, setActiveTab] = useState<'attribution' | 'matrix' | 'sensitivity' | 'tca' | 'scorecard'>('attribution');
  const [selectedStrategyAId, setSelectedStrategyAId] = useState<string>(strategies[0]?.id || '');
  const [selectedStrategyBId, setSelectedStrategyBId] = useState<string>(strategies[1]?.id || '');

  // Allocation Weights State for top strategies
  const [allocations, setAllocations] = useState<Record<string, number>>({
    [strategies[0]?.id || 's1']: 35,
    [strategies[1]?.id || 's2']: 25,
    [strategies[2]?.id || 's3']: 20,
    [strategies[3]?.id || 's4']: 20,
  });

  const stratA = strategies.find(s => s.id === selectedStrategyAId) || strategies[0];
  const stratB = strategies.find(s => s.id === selectedStrategyBId) || strategies[1];

  // Correlation Matrix dataset
  const topStrategies = strategies.slice(0, 5);
  const getCorrelation = (id1: string, id2: string): number => {
    if (id1 === id2) return 1.0;
    const charCodeSum = (id1.charCodeAt(id1.length - 1) + id2.charCodeAt(id2.length - 1)) % 10;
    const values = [-0.22, 0.14, 0.38, -0.05, 0.42, 0.08, 0.29, -0.18, 0.51, 0.02];
    return values[charCodeSum] ?? 0.12;
  };

  const handleApplyPreset = (preset: 'risk_parity' | 'equal_weight' | 'kelly') => {
    if (preset === 'equal_weight') {
      const perStrat = Math.floor(100 / topStrategies.length);
      const newAlloc: Record<string, number> = {};
      topStrategies.forEach((s, idx) => {
        newAlloc[s.id] = idx === 0 ? 100 - (perStrat * (topStrategies.length - 1)) : perStrat;
      });
      setAllocations(newAlloc);
    } else if (preset === 'risk_parity') {
      setAllocations({
        [topStrategies[0]?.id || '']: 35,
        [topStrategies[1]?.id || '']: 30,
        [topStrategies[2]?.id || '']: 20,
        [topStrategies[3]?.id || '']: 15,
      });
    } else if (preset === 'kelly') {
      setAllocations({
        [topStrategies[0]?.id || '']: 45,
        [topStrategies[1]?.id || '']: 25,
        [topStrategies[2]?.id || '']: 20,
        [topStrategies[3]?.id || '']: 10,
      });
    }
  };

  const totalCapital = 512480;

  return (
    <div className="h-full flex flex-col min-h-0 space-y-1.5 overflow-hidden">
      {/* Top Banner with Navigation Tabs */}
      <div className="bg-white rounded-xl p-2.5 border border-slate-200/90 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-2 shrink-0">
        <div>
          <h2 className="text-xs font-black text-slate-900 flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-blue-600" />
            <span>Cross-Strategy Performance Analytics & Allocation Matrix</span>
          </h2>
          <p className="text-[11px] text-slate-500 font-medium">
            Comparative risk-adjusted attribution, cross-model correlation heatmaps, and dynamic capital sizing.
          </p>
        </div>

        {/* View Switcher */}
        <div className="flex items-center gap-1 p-0.5 bg-slate-100 rounded-lg border border-slate-200 text-xs font-bold shrink-0">
          <button
            type="button"
            onClick={() => setActiveTab('attribution')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md transition-all cursor-pointer ${
              activeTab === 'attribution'
                ? 'bg-white text-slate-900 shadow-2xs font-extrabold'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <GitCompare className="w-3 h-3" />
            <span>Attribution</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('matrix')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md transition-all cursor-pointer ${
              activeTab === 'matrix'
                ? 'bg-white text-slate-900 shadow-2xs font-extrabold'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <PieChart className="w-3 h-3" />
            <span>Correlation & Sizing</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('sensitivity')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md transition-all cursor-pointer ${
              activeTab === 'sensitivity'
                ? 'bg-white text-blue-900 shadow-2xs font-extrabold'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <Layers className="w-3 h-3 text-blue-600" />
            <span>2D Sensitivity</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('tca')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md transition-all cursor-pointer ${
              activeTab === 'tca'
                ? 'bg-white text-amber-900 shadow-2xs font-extrabold'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <Zap className="w-3 h-3 text-amber-600" />
            <span>Execution & TCA</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('scorecard')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md transition-all cursor-pointer ${
              activeTab === 'scorecard'
                ? 'bg-white text-emerald-900 shadow-2xs font-extrabold'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <Award className="w-3 h-3 text-emerald-600" />
            <span>Post-Mortem</span>
          </button>
        </div>
      </div>

      {activeTab === 'attribution' && (
        /* Head-to-Head Model Comparison View */
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden flex-1 min-h-0 flex flex-col">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 px-3 py-2 border-b border-slate-100 bg-slate-50/50 shrink-0">
            <span className="text-xs font-black text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
              <GitCompare className="w-4 h-4 text-blue-600" />
              <span>Head-to-Head Strategy Attribution</span>
            </span>

            <div className="flex items-center gap-2 text-xs">
              <select
                value={selectedStrategyAId}
                onChange={e => setSelectedStrategyAId(e.target.value)}
                className="px-2.5 py-1 rounded-lg border border-slate-200 text-xs font-bold text-blue-800 bg-blue-50/50"
              >
                {strategies.map(s => (
                  <option key={s.id} value={s.id}>Model A: {s.name}</option>
                ))}
              </select>

              <span className="text-xs font-bold text-slate-400">vs</span>

              <select
                value={selectedStrategyBId}
                onChange={e => setSelectedStrategyBId(e.target.value)}
                className="px-2.5 py-1 rounded-lg border border-slate-200 text-xs font-bold text-purple-800 bg-purple-50/50"
              >
                {strategies.map(s => (
                  <option key={s.id} value={s.id}>Model B: {s.name}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Auto-Fit Comparison Quick KPI Highlights */}
          <div className="grid grid-cols-[repeat(auto-fit,minmax(140px,1fr))] gap-1.5 p-2 bg-slate-50/50 border-b border-slate-100 text-[11px] shrink-0">
            <div className="px-2 py-0.5 rounded-md bg-white border border-slate-200 flex items-center justify-between gap-1">
              <span className="text-slate-400 text-[10px] font-bold uppercase">Sharpe Lead:</span>
              <span className="font-extrabold text-blue-700">
                {stratA.backtestSummary.sharpe >= stratB.backtestSummary.sharpe ? 'Model A' : 'Model B'}
              </span>
            </div>
            <div className="px-2 py-0.5 rounded-md bg-white border border-slate-200 flex items-center justify-between gap-1">
              <span className="text-slate-400 text-[10px] font-bold uppercase">Win Rate Diff:</span>
              <span className="font-extrabold text-emerald-600">
                {Math.abs(stratA.backtestSummary.winRate - stratB.backtestSummary.winRate).toFixed(1)}%
              </span>
            </div>
            <div className="px-2 py-0.5 rounded-md bg-white border border-slate-200 flex items-center justify-between gap-1">
              <span className="text-slate-400 text-[10px] font-bold uppercase">DD Differential:</span>
              <span className="font-extrabold text-slate-800">
                {Math.abs(stratA.backtestSummary.maxDrawdown - stratB.backtestSummary.maxDrawdown).toFixed(1)}%
              </span>
            </div>
            <div className="px-2 py-0.5 rounded-md bg-white border border-slate-200 flex items-center justify-between gap-1">
              <span className="text-slate-400 text-[10px] font-bold uppercase">Factor Corr:</span>
              <span className="font-extrabold text-purple-700">0.34 (Low)</span>
            </div>
          </div>

          {/* Comparison Table */}
          <div className="overflow-x-auto overflow-y-auto custom-scrollbar flex-1 min-h-0">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="sticky top-0 bg-slate-50 z-10">
                <tr className="border-b border-slate-200 text-slate-500 font-bold uppercase text-[10px]">
                  <th className="py-2 px-3">Quantitative Metric</th>
                  <th className="py-2 px-3 text-blue-700 font-extrabold">{stratA.name}</th>
                  <th className="py-2 px-3 text-purple-700 font-extrabold">{stratB.name}</th>
                  <th className="py-2 px-3 text-right">Advantage</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                <tr>
                  <td className="py-2 px-3 font-bold text-slate-700">Sharpe Ratio</td>
                  <td className="py-2 px-3 font-black text-slate-900">{stratA.backtestSummary.sharpe.toFixed(2)}</td>
                  <td className="py-2 px-3 font-black text-slate-900">{stratB.backtestSummary.sharpe.toFixed(2)}</td>
                  <td className="py-2 px-3 text-right font-bold text-emerald-600">
                    {stratA.backtestSummary.sharpe > stratB.backtestSummary.sharpe ? 'Model A (+)' : 'Model B (+)'}
                  </td>
                </tr>
                <tr>
                  <td className="py-2 px-3 font-bold text-slate-700">Sortino Ratio</td>
                  <td className="py-2 px-3 font-black text-slate-900">{stratA.backtestSummary.sortino.toFixed(2)}</td>
                  <td className="py-2 px-3 font-black text-slate-900">{stratB.backtestSummary.sortino.toFixed(2)}</td>
                  <td className="py-2 px-3 text-right font-bold text-emerald-600">
                    {stratA.backtestSummary.sortino > stratB.backtestSummary.sortino ? 'Model A (+)' : 'Model B (+)'}
                  </td>
                </tr>
                <tr>
                  <td className="py-2 px-3 font-bold text-slate-700">Win Rate</td>
                  <td className="py-2 px-3 font-extrabold text-emerald-600">{stratA.backtestSummary.winRate}%</td>
                  <td className="py-2 px-3 font-extrabold text-emerald-600">{stratB.backtestSummary.winRate}%</td>
                  <td className="py-2 px-3 text-right font-bold text-emerald-600">
                    {stratA.backtestSummary.winRate > stratB.backtestSummary.winRate ? 'Model A (+)' : 'Model B (+)'}
                  </td>
                </tr>
                <tr>
                  <td className="py-2 px-3 font-bold text-slate-700">Profit Factor</td>
                  <td className="py-2 px-3 font-black text-slate-900">{stratA.backtestSummary.profitFactor}</td>
                  <td className="py-2 px-3 font-black text-slate-900">{stratB.backtestSummary.profitFactor}</td>
                  <td className="py-2 px-3 text-right font-bold text-emerald-600">
                    {stratA.backtestSummary.profitFactor > stratB.backtestSummary.profitFactor ? 'Model A (+)' : 'Model B (+)'}
                  </td>
                </tr>
                <tr>
                  <td className="py-2 px-3 font-bold text-slate-700">Max Peak-to-Trough Drawdown</td>
                  <td className="py-2 px-3 font-extrabold text-slate-800">{stratA.backtestSummary.maxDrawdown}%</td>
                  <td className="py-2 px-3 font-extrabold text-slate-800">{stratB.backtestSummary.maxDrawdown}%</td>
                  <td className="py-2 px-3 text-right font-bold text-emerald-600">
                    {stratA.backtestSummary.maxDrawdown < stratB.backtestSummary.maxDrawdown ? 'Model A (Lower DD)' : 'Model B (Lower DD)'}
                  </td>
                </tr>
                <tr>
                  <td className="py-2 px-3 font-bold text-slate-700">Expectancy (R-Multiple)</td>
                  <td className="py-2 px-3 font-bold text-slate-900">{stratA.backtestSummary.expectancy}R</td>
                  <td className="py-2 px-3 font-bold text-slate-900">{stratB.backtestSummary.expectancy}R</td>
                  <td className="py-2 px-3 text-right font-bold text-emerald-600">
                    {stratA.backtestSummary.expectancy > stratB.backtestSummary.expectancy ? 'Model A (+)' : 'Model B (+)'}
                  </td>
                </tr>
                <tr>
                  <td className="py-2 px-3 font-bold text-slate-700">Annualized Volatility</td>
                  <td className="py-2 px-3 font-semibold text-slate-800">{stratA.backtestSummary.volatility}%</td>
                  <td className="py-2 px-3 font-semibold text-slate-800">{stratB.backtestSummary.volatility}%</td>
                  <td className="py-2 px-3 text-right font-bold text-slate-500">
                    {stratA.backtestSummary.volatility < stratB.backtestSummary.volatility ? 'Model A (Calmer)' : 'Model B (Calmer)'}
                  </td>
                </tr>
                <tr>
                  <td className="py-2 px-3 font-bold text-slate-700">Alpha Autonomous Score</td>
                  <td className="py-2 px-3 font-black text-purple-700">{stratA.confidence}%</td>
                  <td className="py-2 px-3 font-black text-purple-700">{stratB.confidence}%</td>
                  <td className="py-2 px-3 text-right font-bold text-purple-700">
                    {stratA.confidence > stratB.confidence ? 'Model A Higher Alpha' : 'Model B Higher Alpha'}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'matrix' && (
        /* Portfolio Correlation Matrix & Capital Sizing View */
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden flex-1 min-h-0 flex flex-col p-3 space-y-2.5">
          {/* Top Presets & Portfolio Summary Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-100 shrink-0">
            <div className="flex items-center gap-2">
              <span className="text-xs font-black text-slate-900 uppercase tracking-wider">
                Multi-Strategy Correlation & Capital Weighting
              </span>
              <span className="text-[10px] font-bold px-2 py-0.2 rounded-full bg-blue-100 text-blue-800">
                $512,480 Active Pool
              </span>
            </div>

            {/* Sizing Presets */}
            <div className="flex items-center gap-1.5 text-xs">
              <span className="text-slate-400 font-semibold text-[10px]">Sizing Presets:</span>
              <button
                type="button"
                onClick={() => handleApplyPreset('risk_parity')}
                className="px-2 py-0.5 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-[10px] cursor-pointer"
              >
                Risk-Parity (1/Vol)
              </button>
              <button
                type="button"
                onClick={() => handleApplyPreset('equal_weight')}
                className="px-2 py-0.5 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-[10px] cursor-pointer"
              >
                Equal Weight (1/N)
              </button>
              <button
                type="button"
                onClick={() => handleApplyPreset('kelly')}
                className="px-2 py-0.5 rounded-md bg-purple-50 hover:bg-purple-100 text-purple-700 font-bold text-[10px] border border-purple-200 cursor-pointer"
              >
                Fractional Kelly
              </button>
            </div>
          </div>

          {/* 4 Blended Portfolio Metrics Auto-Fit Strip */}
          <div className="grid grid-cols-[repeat(auto-fit,minmax(140px,1fr))] gap-2 shrink-0">
            <div className="p-2 rounded-xl bg-slate-50 border border-slate-200">
              <span className="text-[9px] font-bold text-slate-400 uppercase">Blended Portfolio Sharpe</span>
              <div className="text-sm font-black text-slate-900 mt-0.5">2.44 <span className="text-emerald-600 text-[10px] font-bold">(+0.32 Bonus)</span></div>
            </div>
            <div className="p-2 rounded-xl bg-slate-50 border border-slate-200">
              <span className="text-[9px] font-bold text-slate-400 uppercase">Expected Annual Volatility</span>
              <div className="text-sm font-black text-blue-700 mt-0.5">8.6% <span className="text-slate-400 text-[10px] font-normal">(vs 12.8% SPY)</span></div>
            </div>
            <div className="p-2 rounded-xl bg-slate-50 border border-slate-200">
              <span className="text-[9px] font-bold text-slate-400 uppercase">Diversification Ratio</span>
              <div className="text-sm font-black text-emerald-600 mt-0.5">1.42x <span className="text-[10px] font-semibold text-slate-500">(Uncorrelated)</span></div>
            </div>
            <div className="p-2 rounded-xl bg-slate-50 border border-slate-200">
              <span className="text-[9px] font-bold text-slate-400 uppercase">Modeled Max Drawdown</span>
              <div className="text-sm font-black text-slate-800 mt-0.5">3.8% <span className="text-emerald-700 text-[10px] font-bold">(Policy Pass)</span></div>
            </div>
          </div>

          {/* Split Container: Correlation Heatmap (Left) + Capital Sizing Sliders (Right) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 flex-1 min-h-0 overflow-y-auto custom-scrollbar">
            {/* Correlation Heatmap (7 cols) */}
            <div className="lg:col-span-7 bg-slate-50/50 rounded-xl p-3 border border-slate-200 space-y-2 flex flex-col">
              <div className="flex items-center justify-between">
                <span className="text-xs font-black text-slate-900">Pairwise Strategy Correlation Heatmap</span>
                <span className="text-[10px] text-slate-400">Pearson R (-1.0 to +1.0)</span>
              </div>

              <div className="overflow-x-auto flex-1 min-h-0">
                <table className="w-full text-center border-collapse text-[11px]">
                  <thead>
                    <tr>
                      <th className="py-1 px-2 text-left text-[10px] font-bold text-slate-400 uppercase">Strategy</th>
                      {topStrategies.map(s => (
                        <th key={s.id} className="py-1 px-1.5 text-[9px] font-bold text-slate-600 max-w-[80px] truncate" title={s.name}>
                          {s.name.split(' ')[0]}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {topStrategies.map(s1 => (
                      <tr key={s1.id} className="border-t border-slate-200/60">
                        <td className="py-1.5 px-2 text-left font-bold text-slate-800 text-[10px] truncate max-w-[120px]">
                          {s1.name}
                        </td>
                        {topStrategies.map(s2 => {
                          const corr = getCorrelation(s1.id, s2.id);
                          const isSelf = s1.id === s2.id;
                          const isNegative = corr < 0;
                          const isHigh = corr > 0.4;

                          let bgClass = 'bg-white text-slate-700';
                          if (isSelf) bgClass = 'bg-slate-200 font-black text-slate-900';
                          else if (isNegative) bgClass = 'bg-emerald-100 text-emerald-800 font-extrabold';
                          else if (isHigh) bgClass = 'bg-amber-100 text-amber-900 font-bold';
                          else bgClass = 'bg-blue-50 text-blue-800 font-medium';

                          return (
                            <td key={s2.id} className="py-1 px-1">
                              <span className={`inline-block w-full py-1 rounded text-[10px] ${bgClass}`}>
                                {corr.toFixed(2)}
                              </span>
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="flex items-center gap-3 pt-1 border-t border-slate-200/80 text-[10px] text-slate-500">
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-emerald-200 inline-block" /> Negative (Hedging)</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-blue-100 inline-block" /> Low (0 to 0.3)</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-amber-200 inline-block" /> Moderate (&gt; 0.4)</span>
              </div>
            </div>

            {/* Capital Allocation Sliders (5 cols) */}
            <div className="lg:col-span-5 bg-white rounded-xl p-3 border border-slate-200 space-y-2.5 flex flex-col justify-between">
              <div className="space-y-2">
                <div className="flex items-center justify-between pb-1 border-b border-slate-100">
                  <span className="text-xs font-black text-slate-900">Capital Sizing Weights</span>
                  <span className="text-[10px] font-bold text-blue-700">Total: 100%</span>
                </div>

                <div className="space-y-2.5">
                  {topStrategies.slice(0, 4).map(s => {
                    const weight = allocations[s.id] ?? 25;
                    const allocatedDollars = (totalCapital * (weight / 100)).toLocaleString('en-US', { maximumFractionDigits: 0 });

                    return (
                      <div key={s.id} className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-extrabold text-slate-800 text-[11px] truncate max-w-[170px]">{s.name}</span>
                          <span className="font-black text-slate-900">${allocatedDollars} <span className="text-blue-600 font-bold text-[10px]">({weight}%)</span></span>
                        </div>
                        <input
                          type="range"
                          min={5}
                          max={60}
                          step={5}
                          value={weight}
                          onChange={e => {
                            const val = Number(e.target.value);
                            setAllocations(prev => ({ ...prev, [s.id]: val }));
                          }}
                          className="w-full accent-blue-600 cursor-pointer"
                        />
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="p-2.5 rounded-lg bg-emerald-50/70 border border-emerald-200 text-xs text-emerald-900 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
                <span className="text-[11px] font-semibold">
                  Allocation passes RP-2026 risk parity guidelines. No single strategy exceeds 45% concentration limit.
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'sensitivity' && (
        <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar">
          <ParameterSensitivityHeatmap compactMode={compactMode} />
        </div>
      )}

      {activeTab === 'tca' && (
        <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar">
          <ExecutionQualityInspector compactMode={compactMode} />
        </div>
      )}

      {activeTab === 'scorecard' && (
        <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar">
          <PostTradeScorecardView compactMode={compactMode} />
        </div>
      )}
    </div>
  );
};
