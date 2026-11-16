import React, { useState } from 'react';
import {
  Layers,
  Sparkles,
  ShieldCheck,
  ShieldAlert,
  TrendingUp,
  BarChart2,
  Sliders,
  CheckCircle2,
  Info,
  ChevronRight,
  ArrowRight,
  RefreshCw,
  Cpu
} from 'lucide-react';
import {
  SENSITIVITY_MATRICES,
  StrategySensitivityMatrix,
  SensitivityCell
} from '../../data/tradeAnalyticsData';

interface ParameterSensitivityHeatmapProps {
  initialSymbol?: string;
  onSelectStrategy?: (symbol: string) => void;
  compactMode?: boolean;
}

export const ParameterSensitivityHeatmap: React.FC<ParameterSensitivityHeatmapProps> = ({
  initialSymbol = 'EUR/USD',
  compactMode = true
}) => {
  const [selectedKey, setSelectedKey] = useState<string>(
    SENSITIVITY_MATRICES[initialSymbol] ? initialSymbol : 'EUR/USD'
  );
  const [metricView, setMetricView] = useState<'profitFactor' | 'sharpeRatio' | 'winRate'>('profitFactor');
  const [hoveredCell, setHoveredCell] = useState<SensitivityCell | null>(null);
  const [appliedParamsToast, setAppliedParamsToast] = useState<string | null>(null);

  const matrix: StrategySensitivityMatrix =
    SENSITIVITY_MATRICES[selectedKey] || SENSITIVITY_MATRICES['EUR/USD'];

  // Helper for cell color based on metric
  const getCellBg = (cell: SensitivityCell) => {
    if (metricView === 'profitFactor') {
      const pf = cell.profitFactor;
      if (pf >= 1.8) return 'bg-emerald-600 text-white font-black';
      if (pf >= 1.65) return 'bg-emerald-500/80 text-white font-bold';
      if (pf >= 1.5) return 'bg-emerald-200 text-emerald-950 font-semibold';
      if (pf >= 1.4) return 'bg-blue-100 text-blue-900';
      return 'bg-slate-100 text-slate-600';
    }
    if (metricView === 'sharpeRatio') {
      const sr = cell.sharpeRatio;
      if (sr >= 1.7) return 'bg-indigo-600 text-white font-black';
      if (sr >= 1.5) return 'bg-indigo-500/80 text-white font-bold';
      if (sr >= 1.3) return 'bg-indigo-200 text-indigo-950 font-semibold';
      return 'bg-slate-100 text-slate-600';
    }
    // Win Rate
    const wr = cell.winRatePct;
    if (wr >= 57) return 'bg-cyan-600 text-white font-black';
    if (wr >= 54) return 'bg-cyan-500/80 text-white font-bold';
    if (wr >= 52) return 'bg-cyan-200 text-cyan-950 font-semibold';
    return 'bg-slate-100 text-slate-600';
  };

  const getMetricDisplay = (cell: SensitivityCell) => {
    if (metricView === 'profitFactor') return cell.profitFactor.toFixed(2);
    if (metricView === 'sharpeRatio') return cell.sharpeRatio.toFixed(2);
    return `${cell.winRatePct.toFixed(1)}%`;
  };

  const handleApplyParameters = (cell: SensitivityCell) => {
    setAppliedParamsToast(
      `Parameters Promoted: ${matrix.paramXName} = ${cell.paramX}, ${matrix.paramYName} = ${cell.paramY} (PF: ${cell.profitFactor.toFixed(2)})`
    );
    setTimeout(() => setAppliedParamsToast(null), 3500);
  };

  return (
    <div className="h-full flex flex-col min-h-0 space-y-1.5 overflow-hidden select-none">
      {/* Toast Notification */}
      {appliedParamsToast && (
        <div className="fixed top-16 right-6 z-50 animate-in slide-in-from-top duration-200">
          <div className="bg-slate-900 text-white px-3.5 py-2 rounded-xl shadow-xl flex items-center gap-2 border border-slate-700 text-xs font-bold">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span>{appliedParamsToast}</span>
          </div>
        </div>
      )}

      {/* 1. TOP HEADER & TELEMETRY STRIP */}
      <div className="bg-white rounded-xl px-3 py-2 border border-slate-200/90 shadow-2xs flex flex-wrap items-center justify-between gap-2 shrink-0">
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1.5 bg-slate-100 p-0.5 rounded-lg border border-slate-200">
            {Object.keys(SENSITIVITY_MATRICES).map(key => (
              <button
                key={key}
                type="button"
                onClick={() => setSelectedKey(key)}
                className={`px-2.5 py-1 rounded-md text-xs font-black transition-all cursor-pointer ${
                  selectedKey === key
                    ? 'bg-white text-blue-900 shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {key} ({SENSITIVITY_MATRICES[key].strategyName.split(' ')[0]})
              </button>
            ))}
          </div>

          {/* Metric Selector Tabs */}
          <div className="flex items-center gap-1 bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-xs font-bold">
            <button
              type="button"
              onClick={() => setMetricView('profitFactor')}
              className={`px-2 py-0.5 rounded transition-all cursor-pointer ${
                metricView === 'profitFactor'
                  ? 'bg-emerald-600 text-white font-black shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Profit Factor
            </button>
            <button
              type="button"
              onClick={() => setMetricView('sharpeRatio')}
              className={`px-2 py-0.5 rounded transition-all cursor-pointer ${
                metricView === 'sharpeRatio'
                  ? 'bg-indigo-600 text-white font-black shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Sharpe Ratio
            </button>
            <button
              type="button"
              onClick={() => setMetricView('winRate')}
              className={`px-2 py-0.5 rounded transition-all cursor-pointer ${
                metricView === 'winRate'
                  ? 'bg-cyan-600 text-white font-black shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Win Rate %
            </button>
          </div>
        </div>

        {/* Robustness Badge */}
        <div className="flex items-center gap-2 text-xs">
          <div className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-900 font-bold">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            <span>Island of Stability:</span>
            <strong className="text-emerald-700 font-mono font-black">
              {matrix.islandOfStabilityConfidence}% Confidence
            </strong>
          </div>
          <span className="text-[10px] text-slate-400 hidden md:inline">
            Zero Curve-Fitting Vulnerabilities
          </span>
        </div>
      </div>

      {/* 2. MAIN WORKSPACE: HEATMAP MATRIX (LEFT) + MONTE CARLO & INSPECTOR (RIGHT) */}
      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-12 gap-2 overflow-hidden">
        {/* HEATMAP GRID (7 Cols) */}
        <div className="lg:col-span-7 bg-white rounded-xl border border-slate-200/90 shadow-2xs p-3 flex flex-col min-h-0 overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2 mb-2">
            <div>
              <h3 className="text-xs font-black text-slate-900 uppercase tracking-wide flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-blue-600" />
                <span>{matrix.strategyName} · 2D Parameter Stability Surface</span>
              </h3>
              <p className="text-[10px] text-slate-500 font-medium">
                Testing parameter degradation across neighboring clusters. Robust models display broad, continuous plateaus.
              </p>
            </div>
            <span className="px-2 py-0.5 rounded text-[9px] font-black bg-blue-50 text-blue-800 border border-blue-200">
              Walk-Forward OOS
            </span>
          </div>

          {/* Grid Container */}
          <div className="flex-1 min-h-0 flex flex-col justify-center overflow-auto p-2">
            {/* Axis Y Label on Left */}
            <div className="text-[10px] font-bold text-slate-400 uppercase text-center mb-1">
              Y-Axis: {matrix.paramYName}
            </div>

            <div className="overflow-x-auto flex justify-center">
              <table className="border-collapse text-xs select-none">
                <thead>
                  <tr>
                    <th className="p-1.5 text-[9px] font-bold text-slate-400 uppercase">
                      Y \ X
                    </th>
                    {matrix.paramXValues.map(xVal => (
                      <th
                        key={xVal}
                        className="p-1.5 text-center font-mono font-bold text-[10px] text-slate-700 bg-slate-50 border border-slate-200 rounded-t"
                      >
                        {xVal}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {matrix.grid.map((row, rIdx) => {
                    const yVal = matrix.paramYValues[rIdx];
                    return (
                      <tr key={rIdx}>
                        {/* Y-Axis Value */}
                        <td className="p-1.5 text-right font-mono font-bold text-[10px] text-slate-700 bg-slate-50 border border-slate-200">
                          {yVal}
                        </td>

                        {/* Cell Values */}
                        {row.map((cell, cIdx) => {
                          const isOptimal = cell.isOptimal;
                          return (
                            <td
                              key={cIdx}
                              onMouseEnter={() => setHoveredCell(cell)}
                              onClick={() => handleApplyParameters(cell)}
                              className={`p-2.5 text-center border border-slate-200 transition-all cursor-pointer relative group ${getCellBg(
                                cell
                              )} hover:ring-2 hover:ring-blue-500 hover:z-10`}
                              title={`X: ${cell.paramX}, Y: ${cell.paramY} | PF: ${cell.profitFactor} | Click to calibrate`}
                            >
                              <div className="font-mono text-xs leading-none">
                                {getMetricDisplay(cell)}
                              </div>
                              {isOptimal && (
                                <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5">
                                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
                                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500" />
                                </span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Axis X Label on Bottom */}
            <div className="text-[10px] font-bold text-slate-400 uppercase text-center mt-2">
              X-Axis: {matrix.paramXName}
            </div>
          </div>

          {/* Color Scale Legend */}
          <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-500">
            <span className="font-semibold">Stability Legend:</span>
            <div className="flex items-center gap-1.5">
              <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 text-[8.5px]">Sub-Optimal</span>
              <span className="px-1.5 py-0.5 rounded bg-emerald-200 text-emerald-900 text-[8.5px]">Viable</span>
              <span className="px-1.5 py-0.5 rounded bg-emerald-600 text-white font-bold text-[8.5px]">
                Island of Stability (Core Plateau)
              </span>
            </div>
            <span className="text-amber-700 font-bold flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-amber-500" />
              <span>Calibrated Setting</span>
            </span>
          </div>
        </div>

        {/* MONTE CARLO & STABILITY AUDITOR (5 Cols) */}
        <div className="lg:col-span-5 bg-white rounded-xl border border-slate-200/90 shadow-2xs p-3 flex flex-col min-h-0 space-y-3 overflow-y-auto custom-scrollbar">
          {/* Overfitting Verdict Banner */}
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-emerald-50 to-teal-50/40 border border-emerald-200 space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[9px] font-black uppercase px-2 py-0.5 rounded bg-emerald-100 text-emerald-900">
                OVERFITTING AUDIT: PASSED
              </span>
              <span className="font-mono text-xs font-black text-emerald-700">
                Confidence: {matrix.islandOfStabilityConfidence}%
              </span>
            </div>
            <p className="text-[10.5px] text-slate-800 font-semibold leading-relaxed mt-1">
              {matrix.recommendation}
            </p>
          </div>

          {/* Selected / Hovered Cell Deep Dive */}
          <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
            <div className="flex items-center justify-between border-b border-slate-200 pb-1">
              <span className="text-[10px] font-black uppercase text-slate-700 flex items-center gap-1">
                <Sliders className="w-3.5 h-3.5 text-blue-600" />
                <span>Parameter Coordinate Dossier</span>
              </span>
              <span className="text-[9px] text-slate-400">
                {hoveredCell ? 'Hovered Node' : 'Optimal Calibration'}
              </span>
            </div>

            {(() => {
              const active =
                hoveredCell ||
                matrix.grid[2][3] ||
                matrix.grid[0][0];

              return (
                <div className="space-y-2 text-xs">
                  <div className="grid grid-cols-2 gap-1.5 font-mono text-[10px]">
                    <div className="p-1.5 rounded bg-white border border-slate-200">
                      <span className="text-[8px] uppercase text-slate-400 block">
                        {matrix.paramXName}:
                      </span>
                      <strong className="text-slate-900 text-xs font-black">
                        {active.paramX}
                      </strong>
                    </div>

                    <div className="p-1.5 rounded bg-white border border-slate-200">
                      <span className="text-[8px] uppercase text-slate-400 block">
                        {matrix.paramYName}:
                      </span>
                      <strong className="text-slate-900 text-xs font-black">
                        {active.paramY}
                      </strong>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-1 text-center font-mono">
                    <div className="p-1.5 rounded bg-emerald-50 border border-emerald-200 text-emerald-950">
                      <span className="text-[7.5px] uppercase block text-emerald-700 font-bold">
                        Profit Factor
                      </span>
                      <strong className="text-xs font-black text-emerald-700">
                        {active.profitFactor.toFixed(2)}
                      </strong>
                    </div>

                    <div className="p-1.5 rounded bg-indigo-50 border border-indigo-200 text-indigo-950">
                      <span className="text-[7.5px] uppercase block text-indigo-700 font-bold">
                        Sharpe
                      </span>
                      <strong className="text-xs font-black text-indigo-700">
                        {active.sharpeRatio.toFixed(2)}
                      </strong>
                    </div>

                    <div className="p-1.5 rounded bg-blue-50 border border-blue-200 text-blue-950">
                      <span className="text-[7.5px] uppercase block text-blue-700 font-bold">
                        Win Rate
                      </span>
                      <strong className="text-xs font-black text-blue-700">
                        {active.winRatePct.toFixed(1)}%
                      </strong>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => handleApplyParameters(active)}
                    className="w-full py-1.5 px-3 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-extrabold text-xs shadow-2xs flex items-center justify-center gap-1.5 transition-all cursor-pointer"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5 text-white" />
                    <span>Deploy Calibrated Setting ({active.paramX} / {active.paramY})</span>
                  </button>
                </div>
              );
            })()}
          </div>

          {/* Monte Carlo 1,000-Iteration Probability Distribution */}
          <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-black uppercase text-slate-700 flex items-center gap-1">
                <BarChart2 className="w-3.5 h-3.5 text-indigo-600" />
                <span>Monte Carlo 1,000-Run Distribution</span>
              </span>
              <span className="text-[9px] font-bold text-slate-500 font-mono">
                95% VaR: {matrix.monteCarlo.pct5Var}%
              </span>
            </div>

            {/* SVG Histogram curve */}
            <div className="h-16 w-full pt-1">
              <svg viewBox="0 0 240 60" className="w-full h-full overflow-visible">
                {/* Bars */}
                {matrix.monteCarlo.samples.map((val, i) => {
                  const x = i * 17 + 4;
                  const barH = (val / 42) * 50;
                  const isMedian = i === 6;
                  return (
                    <g key={i}>
                      <rect
                        x={x}
                        y={55 - barH}
                        width={12}
                        height={barH}
                        fill={isMedian ? '#2563eb' : '#94a3b8'}
                        rx={2}
                        opacity={0.85}
                      />
                    </g>
                  );
                })}
                {/* Reference line for 5% VaR */}
                <line x1={38} y1={5} x2={38} y2={55} stroke="#f43f5e" strokeDasharray="2 2" strokeWidth={1.5} />
                <text x={42} y={15} fill="#e11d48" fontSize={7.5} fontWeight="bold">
                  5% VaR ({matrix.monteCarlo.pct5Var}%)
                </text>
              </svg>
            </div>

            <div className="grid grid-cols-3 gap-1 text-[9px] font-mono text-center pt-1 border-t border-slate-200">
              <div>
                <span className="text-slate-400 block text-[7.5px] uppercase">Worst-Case DD</span>
                <strong className="text-rose-600 font-black">-{matrix.monteCarlo.maxDrawdownWorstCase}%</strong>
              </div>
              <div>
                <span className="text-slate-400 block text-[7.5px] uppercase">Median Return</span>
                <strong className="text-emerald-700 font-black">+{matrix.monteCarlo.medianReturn}%</strong>
              </div>
              <div>
                <span className="text-slate-400 block text-[7.5px] uppercase">Best-Case 95th</span>
                <strong className="text-blue-700 font-black">+{matrix.monteCarlo.pct95Var}%</strong>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
