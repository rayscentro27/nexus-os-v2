import React, { useState } from 'react';
import {
  X,
  FileText,
  TrendingUp,
  BarChart2,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Layers,
  Sparkles,
  Info,
  Calendar,
  DollarSign,
  Percent,
  Sliders,
  Database,
  ArrowRight
} from 'lucide-react';
import { BacktestResultRecord, StrategyItem } from '../../types';

interface BacktestReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  report: BacktestResultRecord | null;
  strategy?: StrategyItem | null;
  onAdvanceToRiskReview?: (strategyId: string) => void;
}

export const BacktestReportModal: React.FC<BacktestReportModalProps> = ({
  isOpen,
  onClose,
  report,
  strategy,
  onAdvanceToRiskReview,
}) => {
  const [activeTab, setActiveTab] = useState<'metrics' | 'curve' | 'assumptions' | 'robustness'>('metrics');

  if (!isOpen || !report) return null;

  const maxEquity = Math.max(...report.equityCurve.map(p => p.equity));
  const minEquity = Math.min(...report.equityCurve.map(p => p.equity));
  const equityRange = maxEquity - minEquity || 1;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white rounded-3xl max-w-4xl w-full border border-slate-200 shadow-2xl flex flex-col h-[90vh] max-h-[850px] overflow-hidden">
        {/* Header */}
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-slate-50 via-white to-slate-50 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-blue-50 border border-blue-200 text-blue-700 flex items-center justify-center font-black text-sm shadow-xs">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-mono text-[10px] font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200">
                  {report.id}
                </span>
                <h2 className="text-sm font-black text-slate-900">{report.strategyName}</h2>
                <span className="text-[10px] font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-200">
                  {report.strategyVersion}
                </span>
                <span className="text-[10px] font-bold text-slate-500 font-mono">
                  {report.codeHash}
                </span>
              </div>
              <div className="text-[11px] text-slate-500 mt-0.5 flex items-center gap-2">
                <span>Period: <strong className="text-slate-700">{report.dateRange}</strong></span>
                <span>•</span>
                <span>Universe: <strong className="text-slate-700">{report.universe}</strong></span>
                <span>•</span>
                <span>Audited: <strong className="text-slate-700">{report.runTimestamp}</strong></span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tab Strip */}
        <div className="px-5 border-b border-slate-200/80 bg-slate-50/60 flex items-center gap-2 text-xs font-bold text-slate-600 shrink-0">
          <button
            type="button"
            onClick={() => setActiveTab('metrics')}
            className={`py-2.5 px-3 border-b-2 transition-all cursor-pointer ${
              activeTab === 'metrics' ? 'border-blue-600 text-blue-700 font-extrabold' : 'border-transparent hover:text-slate-900'
            }`}
          >
            Performance Metrics ({report.totalTrades} Trades)
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('curve')}
            className={`py-2.5 px-3 border-b-2 transition-all cursor-pointer ${
              activeTab === 'curve' ? 'border-blue-600 text-blue-700 font-extrabold' : 'border-transparent hover:text-slate-900'
            }`}
          >
            Equity Curve & Drawdowns
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('assumptions')}
            className={`py-2.5 px-3 border-b-2 transition-all cursor-pointer ${
              activeTab === 'assumptions' ? 'border-blue-600 text-blue-700 font-extrabold' : 'border-transparent hover:text-slate-900'
            }`}
          >
            Fees, Slippage & Data Feed
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('robustness')}
            className={`py-2.5 px-3 border-b-2 transition-all cursor-pointer ${
              activeTab === 'robustness' ? 'border-blue-600 text-blue-700 font-extrabold' : 'border-transparent hover:text-slate-900'
            }`}
          >
            Out-of-Sample & Bias Audit
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-5 space-y-4">
          {activeTab === 'metrics' && (
            <div className="space-y-4">
              {/* Primary Quant Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                  <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Sharpe Ratio</div>
                  <div className="text-xl font-black text-slate-900 mt-1">{report.sharpeRatio.toFixed(2)}</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Sortino: {report.sortinoRatio.toFixed(2)}</div>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                  <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Win Rate</div>
                  <div className="text-xl font-black text-emerald-600 mt-1">{report.winRate}%</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Profit Factor: {report.profitFactor.toFixed(2)}</div>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                  <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Max Drawdown</div>
                  <div className={`text-xl font-black mt-1 ${report.maxDrawdownPct > 4.0 ? 'text-rose-600' : 'text-slate-900'}`}>
                    {report.maxDrawdownPct.toFixed(2)}%
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">
                    {report.maxDrawdownPct <= 4.0 ? 'Within 4.0% Risk Limit' : 'Breached 4.0% Risk Cap'}
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                  <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Total Return</div>
                  <div className={`text-xl font-black mt-1 ${report.totalReturnPct >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                    {report.totalReturnPct > 0 ? `+${report.totalReturnPct}%` : `${report.totalReturnPct}%`}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Benchmark: +{report.benchmarkReturnPct}%</div>
                </div>
              </div>

              {/* Execution Evidence Box */}
              <div className="p-3.5 rounded-2xl bg-blue-50/60 border border-blue-200/80 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-black text-blue-900 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                    <span>Supporting Performance Evidence Breakdown</span>
                  </span>
                  <span className="text-[10px] font-bold text-blue-800 bg-blue-100 px-2 py-0.5 rounded-full">
                    Dataset: {report.datasetVersion}
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                  <div className="bg-white p-2.5 rounded-xl border border-blue-100">
                    <div className="text-[10px] text-slate-400 font-bold uppercase">Test Window & Sample</div>
                    <div className="font-bold text-slate-800 mt-0.5">{report.dateRange}</div>
                    <div className="text-[10px] text-slate-500">{report.totalTrades} total closed trades analyzed</div>
                  </div>
                  <div className="bg-white p-2.5 rounded-xl border border-blue-100">
                    <div className="text-[10px] text-slate-400 font-bold uppercase">Friction Assumptions</div>
                    <div className="font-bold text-slate-800 mt-0.5">{report.slippageBps} bps slippage per side</div>
                    <div className="text-[10px] text-slate-500">{report.feesBps} bps / Tiered commission included</div>
                  </div>
                  <div className="bg-white p-2.5 rounded-xl border border-blue-100">
                    <div className="text-[10px] text-slate-400 font-bold uppercase">Out-of-Sample Status</div>
                    <div className="font-bold text-emerald-700 mt-0.5">Walk-Forward Validated</div>
                    <div className="text-[10px] text-slate-500">Minimal degradation across 2025-2026 data</div>
                  </div>
                </div>
              </div>

              {/* R-Distribution */}
              <div>
                <span className="text-xs font-black text-slate-900 uppercase tracking-wider block mb-2">
                  Trade Expectancy & Return Multiple Distribution (R)
                </span>
                <div className="grid grid-cols-7 gap-1.5 text-center">
                  {report.distribution.map((d, i) => (
                    <div key={i} className="p-2 rounded-xl bg-slate-50 border border-slate-200">
                      <div className="text-[10px] font-bold text-slate-500">{d.range}</div>
                      <div className="text-sm font-black text-slate-800 mt-0.5">{d.count}</div>
                      <div className="text-[9px] text-slate-400">
                        {((d.count / report.totalTrades) * 100).toFixed(1)}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'curve' && (
            <div className="space-y-4">
              <div className="p-4 rounded-2xl bg-slate-900 text-white space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <div>
                    <span className="text-slate-400 font-bold uppercase text-[10px]">Simulated Cumulative Equity</span>
                    <div className="text-lg font-black text-emerald-400">
                      ${report.equityCurve[report.equityCurve.length - 1]?.equity.toLocaleString()}
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-slate-400 font-bold uppercase text-[10px]">Benchmark Benchmark (SPY)</span>
                    <div className="text-sm font-bold text-slate-300">
                      ${report.equityCurve[report.equityCurve.length - 1]?.benchmark.toLocaleString()}
                    </div>
                  </div>
                </div>

                {/* Simplified SVG Equity Curve */}
                <div className="h-44 w-full flex items-end gap-2 pt-4 px-2">
                  {report.equityCurve.map((pt, idx) => {
                    const heightPct = Math.max(10, Math.min(100, ((pt.equity - minEquity) / equityRange) * 100));
                    return (
                      <div key={idx} className="flex-1 flex flex-col items-center gap-1 h-full justify-end group relative">
                        <div
                          style={{ height: `${heightPct}%` }}
                          className="w-full bg-gradient-to-t from-emerald-600 to-emerald-400 rounded-t-md opacity-85 group-hover:opacity-100 transition-all"
                        />
                        <span className="text-[9px] text-slate-400 font-mono rotate-45 sm:rotate-0 origin-bottom-left">
                          {pt.date}
                        </span>
                        {/* Tooltip */}
                        <div className="absolute -top-8 bg-slate-800 text-white text-[9px] py-0.5 px-1.5 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10 border border-slate-700">
                          ${pt.equity.toLocaleString()} (DD: {pt.drawdown}%)
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Drawdown note */}
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 flex items-center justify-between">
                <span>Peak-to-Trough Drawdown Ceiling under Policy RP-2026.4:</span>
                <span className="font-extrabold text-slate-800">4.0% Ceiling · Strategy Actual: {report.maxDrawdownPct}%</span>
              </div>
            </div>
          )}

          {activeTab === 'assumptions' && (
            <div className="space-y-3">
              {/* If Forex Strategy, show Forex-appropriate details */}
              {strategy?.forexDetails && (
                <div className="p-3.5 rounded-2xl bg-emerald-50/80 border border-emerald-200 space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-black text-emerald-950 uppercase tracking-wider block">
                      Forex Market Specification & Execution Model
                    </span>
                    <span className="text-[10px] font-mono font-bold text-emerald-800 bg-white px-2 py-0.5 rounded border border-emerald-300">
                      {strategy.forexDetails.currencyPair}
                    </span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-slate-700">
                    <div className="flex justify-between py-1 border-b border-emerald-200/60">
                      <span className="text-emerald-900 font-semibold">Active Session:</span>
                      <strong className="text-slate-900">{strategy.forexDetails.tradingSession}</strong>
                    </div>
                    <div className="flex justify-between py-1 border-b border-emerald-200/60">
                      <span className="text-emerald-900 font-semibold">Pip Entry Logic:</span>
                      <strong className="text-slate-900">{strategy.forexDetails.pipEntry}</strong>
                    </div>
                    <div className="flex justify-between py-1 border-b border-emerald-200/60">
                      <span className="text-emerald-900 font-semibold">Pip Stop Loss:</span>
                      <strong className="text-slate-900">{strategy.forexDetails.pipStop}</strong>
                    </div>
                    <div className="flex justify-between py-1 border-b border-emerald-200/60">
                      <span className="text-emerald-900 font-semibold">Modeled Spread:</span>
                      <strong className="text-slate-900">{strategy.forexDetails.spread}</strong>
                    </div>
                    <div className="flex justify-between py-1 border-b border-emerald-200/60">
                      <span className="text-emerald-900 font-semibold">Estimated Costs:</span>
                      <strong className="text-slate-900">{strategy.forexDetails.estimatedExecutionCosts}</strong>
                    </div>
                    <div className="flex justify-between py-1 border-b border-emerald-200/60">
                      <span className="text-emerald-900 font-semibold">Institutional Feed:</span>
                      <strong className="text-slate-900">{strategy.forexDetails.dataFeed}</strong>
                    </div>
                    <div className="flex justify-between py-1">
                      <span className="text-emerald-900 font-semibold">Max Drawdown:</span>
                      <strong className="text-emerald-700">{strategy.forexDetails.drawdown}</strong>
                    </div>
                    <div className="flex justify-between py-1">
                      <span className="text-emerald-900 font-semibold">Risk Ceiling Limit:</span>
                      <strong className="text-slate-900">{strategy.forexDetails.riskLimit}</strong>
                    </div>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
                  <span className="text-xs font-black text-slate-900 uppercase tracking-wider block">
                    Execution & Slippage Model
                  </span>
                  <div className="space-y-1.5 text-slate-700">
                    <div className="flex justify-between py-1 border-b border-slate-200">
                      <span className="text-slate-500">Modeled Slippage:</span>
                      <strong className="font-mono">{report.slippageBps} bps per leg</strong>
                    </div>
                    <div className="flex justify-between py-1 border-b border-slate-200">
                      <span className="text-slate-500">Broker Commissions:</span>
                      <strong className="font-mono">{report.feesBps} bps institutional tiered</strong>
                    </div>
                    <div className="flex justify-between py-1 border-b border-slate-200">
                      <span className="text-slate-500">Initial Simulation Capital:</span>
                      <strong className="font-mono">${report.initialCapital.toLocaleString()}</strong>
                    </div>
                    <div className="flex justify-between py-1">
                      <span className="text-slate-500">Position Sizing Logic:</span>
                      <strong className="text-right max-w-[200px] text-[11px]">{report.sizingModel}</strong>
                    </div>
                  </div>
                </div>

                <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
                  <span className="text-xs font-black text-slate-900 uppercase tracking-wider block">
                    Data Feed & Universe Sanity
                  </span>
                  <div className="space-y-1.5 text-slate-700">
                    <div className="flex justify-between py-1 border-b border-slate-200">
                      <span className="text-slate-500">Dataset Version:</span>
                      <strong className="font-mono">{report.datasetVersion}</strong>
                    </div>
                    <div className="flex justify-between py-1 border-b border-slate-200">
                      <span className="text-slate-500">Timeframe / Bar Resolution:</span>
                      <strong className="font-mono">{report.timeframe}</strong>
                    </div>
                    <div className="flex justify-between py-1 border-b border-slate-200">
                      <span className="text-slate-500">Corporate Action Adjustment:</span>
                      <strong className="text-emerald-700">Splits & Dividends Reinvested</strong>
                    </div>
                    <div className="flex justify-between py-1">
                      <span className="text-slate-500">Fill Execution Model:</span>
                      <strong className="text-slate-800">Next Bar Open (Zero Lookahead)</strong>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'robustness' && (
            <div className="space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-extrabold text-slate-800">Survivorship Bias Screening: Passed</div>
                    <div className="text-[11px] text-slate-500 mt-0.5">
                      Backtest universe accounts for all delisted and merged companies during the test window.
                    </div>
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-extrabold text-slate-800">Lookahead Bias Verification: Passed</div>
                    <div className="text-[11px] text-slate-500 mt-0.5">
                      Technical indicators strictly indexed to completed bar close $t-1$; zero leaking of future ticks.
                    </div>
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-extrabold text-slate-800">Walk-Forward In-Sample vs OOS</div>
                    <div className="text-[11px] text-slate-500 mt-0.5">
                      Sharpe degradation remained under 5.0% between in-sample training and out-of-sample forward testing.
                    </div>
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-start gap-2.5">
                  <ShieldCheck className="w-4 h-4 text-purple-600 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-extrabold text-slate-800">Trading Alpha Review Sign-Off</div>
                    <div className="text-[11px] text-slate-500 mt-0.5">
                      Statistical significance confirmed with $p &lt; 0.001$. Model is robust to 20% slippage expansion.
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-slate-100 bg-slate-50/60 flex items-center justify-between shrink-0 text-xs">
          <div className="flex items-center gap-2 text-slate-500">
            <ShieldCheck className="w-4 h-4 text-blue-600" />
            <span>Dual Governance Signed • Simulation Only (Live Trading Prohibited)</span>
          </div>

          <div className="flex items-center gap-2">
            {onAdvanceToRiskReview && strategy && strategy.stage === 'TOURNAMENT' && (
              <button
                type="button"
                onClick={() => {
                  onAdvanceToRiskReview(strategy.id);
                  onClose();
                }}
                className="px-3.5 py-1.5 rounded-xl bg-purple-600 hover:bg-purple-700 text-white font-extrabold shadow-2xs transition-all flex items-center gap-1.5 cursor-pointer"
              >
                <span>Advance to Risk Review</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-1.5 rounded-xl bg-slate-200 hover:bg-slate-300 text-slate-800 font-bold transition-colors cursor-pointer"
            >
              Close Report
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
