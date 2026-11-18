import React, { useState } from 'react';
import { 
  X, 
  Sparkles, 
  Play, 
  CheckCircle2, 
  AlertTriangle, 
  ShieldCheck, 
  Clock, 
  FileText, 
  TrendingUp, 
  GitBranch, 
  Sliders, 
  ArrowRight, 
  ExternalLink,
  ChevronRight,
  Layers,
  Activity,
  AlertCircle,
  Info,
  Check
} from 'lucide-react';
import { StrategyItem, StrategyStage, AlphaDecision } from '../../types';
import { getStageGateDetails } from './StrategyPipelineView';

interface StrategyDetailWorkspaceProps {
  strategy: StrategyItem | null;
  onClose: () => void;
  onRunBacktest: (strategy: StrategyItem) => void;
  onPromoteStage: (strategyId: string, nextStage: StrategyStage) => void;
  onOpenBacktestReport?: (reportId: string, strategy?: StrategyItem) => void;
}

export const StrategyDetailWorkspace: React.FC<StrategyDetailWorkspaceProps> = ({
  strategy,
  onClose,
  onRunBacktest,
  onPromoteStage,
  onOpenBacktestReport,
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'evidence' | 'backtest' | 'robustness' | 'alpha' | 'versions'>('overview');

  if (!strategy) return null;

  const getAlphaBadge = (decision: AlphaDecision) => {
    switch (decision) {
      case 'QUALIFY':
      case 'PAPER_TEST':
        return { label: decision, bg: 'bg-emerald-50 text-emerald-800 border-emerald-300' };
      case 'RESEARCH_MORE':
        return { label: decision.replace('_', ' '), bg: 'bg-blue-50 text-blue-800 border-blue-300' };
      case 'PAUSE':
        return { label: decision, bg: 'bg-amber-50 text-amber-800 border-amber-300' };
      case 'REJECT':
        return { label: decision, bg: 'bg-rose-50 text-rose-800 border-rose-300' };
      default:
        return { label: 'NO ACTION', bg: 'bg-slate-50 text-slate-700 border-slate-300' };
    }
  };

  const alpha = getAlphaBadge(strategy.alphaDecision);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white rounded-3xl max-w-5xl w-full border border-slate-200 shadow-2xl flex flex-col h-[92vh] overflow-hidden">
        {/* Top Header */}
        <div className="px-6 py-4.5 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-slate-50 via-white to-slate-50">
          <div className="flex items-center gap-3.5">
            <div className="w-11 h-11 rounded-2xl bg-blue-50 border border-blue-200 text-blue-700 font-black text-sm flex items-center justify-center shadow-xs">
              {strategy.market.substring(0, 2).toUpperCase()}
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-base font-black text-slate-900">{strategy.name}</h2>
                <span className="font-mono text-[10px] font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200">
                  {strategy.id}
                </span>
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-blue-50 text-blue-800 border border-blue-200">
                  {strategy.stage}
                </span>
                <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-extrabold border ${alpha.bg} flex items-center gap-1`}>
                  <Sparkles className="w-2.5 h-2.5" />
                  <span>Alpha: {alpha.label}</span>
                </span>
              </div>
              <div className="text-xs text-slate-500 mt-0.5 flex items-center gap-2">
                <span>{strategy.universe}</span>
                <span>•</span>
                <span className="capitalize">{strategy.type}</span>
                <span>•</span>
                <span>Owner: <strong className="text-slate-700">{strategy.owner.name}</strong></span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {onOpenBacktestReport && (
              <button
                type="button"
                onClick={() => onOpenBacktestReport(strategy.performanceEvidence?.backtestReportId || 'bt-run-7412', strategy)}
                className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-blue-700 text-xs font-bold border border-slate-300 transition-all cursor-pointer"
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Supporting Report</span>
              </button>
            )}
            <button
              type="button"
              onClick={() => onRunBacktest(strategy)}
              className="hidden sm:flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold transition-all shadow-xs cursor-pointer"
            >
              <Play className="w-3.5 h-3.5" />
              <span>Backtest Strategy</span>
            </button>
            <button
              type="button"
              onClick={onClose}
              className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Progression & Risk Gate Status Strip */}
        {(() => {
          const gateInfo = getStageGateDetails(strategy.stage);
          const GateIcon = gateInfo.icon;
          const stateReason = strategy.progression?.reason || strategy.nextAction || strategy.alphaReview.reasoning;
          const nextGateLabel = strategy.nextGate || strategy.progression?.nextGate || 'Governance Sign-Off';

          return (
            <div className="px-6 py-2.5 bg-slate-50 border-b border-slate-200 space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                {/* Left: Stage Gate badge & Stepper */}
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-extrabold text-slate-500 uppercase text-[10px]">Current Stage Gate:</span>
                  <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-black border uppercase tracking-wider ${gateInfo.pillClasses}`}>
                    <GateIcon className="w-3.5 h-3.5" />
                    <span>{gateInfo.gateKey}</span>
                  </span>

                  <div className="h-4 w-px bg-slate-200 hidden sm:block" />

                  {/* Explicit Next Gate label */}
                  <div className="flex items-center gap-1.5 bg-purple-50/90 border border-purple-200 px-2 py-0.5 rounded-lg text-[10px]">
                    <ArrowRight className="w-3 h-3 text-purple-600" />
                    <span className="font-black text-purple-900 uppercase">Next Gate:</span>
                    <strong className="text-purple-950 font-bold">{nextGateLabel}</strong>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-[10px]">
                  <span className="text-slate-500">Risk Sign-off:</span>
                  <span className={`px-2 py-0.5 rounded-full font-black border ${
                    strategy.riskApproval?.status === 'Approved' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                    strategy.riskApproval?.status === 'Rejected' ? 'bg-rose-50 text-rose-700 border-rose-200' :
                    'bg-amber-50 text-amber-700 border-amber-200'
                  }`}>
                    {strategy.riskApproval?.status || 'Pending Review'}
                  </span>
                  <span className="text-slate-400 font-mono text-[9px]">(RP-2026.4)</span>
                </div>
              </div>

              {/* Reason for Current State Banner */}
              <div className="p-2 rounded-lg bg-white border border-slate-200/90 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-1 shadow-2xs">
                <div className="flex items-center gap-1.5 text-slate-700">
                  <Info className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                  <span className="font-extrabold uppercase text-[9px] text-slate-500">Reason for Current State:</span>
                  <span className="font-semibold text-slate-900 text-[11px]">{stateReason}</span>
                </div>
                <span className={`px-1.5 py-0.2 rounded-full font-black text-[9px] uppercase self-start sm:self-center border ${
                  strategy.progression?.status === 'Advanced' ? 'bg-emerald-50 text-emerald-800 border-emerald-300' :
                  strategy.progression?.status === 'Rejected' ? 'bg-rose-50 text-rose-800 border-rose-300' :
                  strategy.progression?.status === 'Waiting' ? 'bg-blue-50 text-blue-800 border-blue-300' :
                  'bg-amber-50 text-amber-800 border-amber-300'
                }`}>
                  {strategy.progression?.status || 'Active'}
                </span>
              </div>
            </div>
          );
        })()}

        {/* Tab Navigation */}
        <div className="px-6 border-b border-slate-200/80 bg-slate-50/50 flex items-center gap-1 sm:gap-2 overflow-x-auto custom-scrollbar text-xs font-bold text-slate-600">
          <button
            type="button"
            onClick={() => setActiveTab('overview')}
            className={`py-3 px-3 border-b-2 transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'overview' ? 'border-blue-600 text-blue-700 font-extrabold' : 'border-transparent hover:text-slate-900'
            }`}
          >
            Strategy Overview
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('evidence')}
            className={`py-3 px-3 border-b-2 transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'evidence' ? 'border-blue-600 text-blue-700 font-extrabold' : 'border-transparent hover:text-slate-900'
            }`}
          >
            Research Evidence
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('backtest')}
            className={`py-3 px-3 border-b-2 transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'backtest' ? 'border-blue-600 text-blue-700 font-extrabold' : 'border-transparent hover:text-slate-900'
            }`}
          >
            Backtest Summary
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('robustness')}
            className={`py-3 px-3 border-b-2 transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'robustness' ? 'border-blue-600 text-blue-700 font-extrabold' : 'border-transparent hover:text-slate-900'
            }`}
          >
            Robustness Matrix
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('alpha')}
            className={`py-3 px-3 border-b-2 transition-all cursor-pointer whitespace-nowrap flex items-center gap-1.5 ${
              activeTab === 'alpha' ? 'border-purple-600 text-purple-700 font-extrabold' : 'border-transparent hover:text-slate-900'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 text-purple-600" />
            <span>Alpha Review</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('versions')}
            className={`py-3 px-3 border-b-2 transition-all cursor-pointer whitespace-nowrap flex items-center gap-1.5 ${
              activeTab === 'versions' ? 'border-blue-600 text-blue-700 font-extrabold' : 'border-transparent hover:text-slate-900'
            }`}
          >
            <GitBranch className="w-3.5 h-3.5 text-slate-500" />
            <span>Version History ({strategy.versions.length})</span>
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-6">
          {/* TAB 1: STRATEGY OVERVIEW */}
          {activeTab === 'overview' && (
            <div className="space-y-6 animate-in fade-in duration-150">
              {/* Thesis & Hypothesis */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-1.5">
                  <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Economic Thesis</div>
                  <p className="text-xs text-slate-800 font-medium leading-relaxed">{strategy.overview.thesis}</p>
                </div>
                <div className="p-4 rounded-2xl bg-blue-50/50 border border-blue-100 space-y-1.5">
                  <div className="text-[11px] font-bold text-blue-700 uppercase tracking-wider">Testable Hypothesis</div>
                  <p className="text-xs text-slate-800 font-medium leading-relaxed">{strategy.overview.hypothesis}</p>
                </div>
              </div>

              {/* Execution & Logic Matrix */}
              <div className="bg-white rounded-2xl border border-slate-200 p-5 space-y-4">
                <h3 className="text-xs font-black text-slate-900 uppercase tracking-wider">Trading Logic & Rules</h3>
                
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 space-y-1">
                    <span className="text-[10px] font-bold text-slate-500 uppercase">Entry Logic</span>
                    <p className="text-slate-800 font-medium leading-normal">{strategy.overview.entryLogic}</p>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 space-y-1">
                    <span className="text-[10px] font-bold text-slate-500 uppercase">Exit Logic</span>
                    <p className="text-slate-800 font-medium leading-normal">{strategy.overview.exitLogic}</p>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 space-y-1">
                    <span className="text-[10px] font-bold text-slate-500 uppercase">Stop-Loss Logic</span>
                    <p className="text-slate-800 font-medium leading-normal">{strategy.overview.stopLogic}</p>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 space-y-1">
                    <span className="text-[10px] font-bold text-slate-500 uppercase">Position Sizing</span>
                    <p className="text-slate-800 font-medium leading-normal">{strategy.overview.positionSizingLogic}</p>
                  </div>
                </div>

                {/* Filters & Horizon */}
                <div className="pt-3 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                  <div>
                    <span className="text-[11px] font-bold text-slate-500 uppercase block mb-1.5">Gating Filters</span>
                    <ul className="space-y-1">
                      {strategy.overview.filters.map((f, i) => (
                        <li key={i} className="flex items-center gap-2 text-slate-700">
                          <CheckCircle2 className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                          <span>{f}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <span className="text-[11px] font-bold text-slate-500 uppercase block mb-1.5">Market Assumptions</span>
                    <ul className="space-y-1">
                      {strategy.overview.marketAssumptions.map((m, i) => (
                        <li key={i} className="flex items-center gap-2 text-slate-700">
                          <span className="w-1.5 h-1.5 rounded-full bg-slate-400 shrink-0" />
                          <span>{m}</span>
                        </li>
                      ))}
                    </ul>
                    <div className="mt-2 text-[11px] text-slate-500">
                      Time Horizon: <strong className="text-slate-800">{strategy.overview.timeHorizon}</strong>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: RESEARCH EVIDENCE */}
          {activeTab === 'evidence' && (
            <div className="space-y-5 animate-in fade-in duration-150">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {/* Supporting evidence */}
                <div className="p-4 rounded-2xl bg-emerald-50/40 border border-emerald-100 space-y-3">
                  <div className="text-xs font-bold text-emerald-900 uppercase tracking-wider flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span>Supporting Research & Findings</span>
                  </div>
                  <ul className="space-y-2 text-xs text-slate-700">
                    {strategy.researchEvidence.supportingResearch.map((item, idx) => (
                      <li key={idx} className="flex items-start gap-2 bg-white/80 p-2.5 rounded-xl border border-emerald-200/50">
                        <span className="text-emerald-600 font-bold">•</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Contradicting evidence & risks */}
                <div className="p-4 rounded-2xl bg-rose-50/40 border border-rose-100 space-y-3">
                  <div className="text-xs font-bold text-rose-900 uppercase tracking-wider flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-rose-600" />
                    <span>Contradicting Evidence & Edge Decay</span>
                  </div>
                  <ul className="space-y-2 text-xs text-slate-700">
                    {strategy.researchEvidence.contradictingEvidence.map((item, idx) => (
                      <li key={idx} className="flex items-start gap-2 bg-white/80 p-2.5 rounded-xl border border-rose-200/50">
                        <span className="text-rose-600 font-bold">•</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Data Quality & Source Links */}
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-3">
                <div className="text-xs font-bold text-slate-800 uppercase tracking-wider">Dataset Integrity & Source Documents</div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                  <div>
                    <span className="text-slate-500 font-medium">Data Quality Verification:</span>
                    <p className="font-semibold text-slate-800 mt-0.5">{strategy.researchEvidence.dataQuality}</p>
                  </div>
                  <div>
                    <span className="text-slate-500 font-medium">Historical Testing Range:</span>
                    <p className="font-semibold text-slate-800 mt-0.5">{strategy.researchEvidence.dateRange}</p>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-200/60 flex flex-wrap gap-2">
                  {strategy.researchEvidence.sourceLinks.map((link, i) => (
                    <a
                      key={i}
                      href={link.url}
                      onClick={e => e.preventDefault()}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white border border-slate-200 text-xs font-bold text-blue-700 hover:bg-blue-50 transition-colors"
                    >
                      <ExternalLink className="w-3 h-3 text-slate-400" />
                      <span>{link.title}</span>
                      <span className="text-[10px] text-slate-400 font-normal">({link.type})</span>
                    </a>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: BACKTEST SUMMARY */}
          {activeTab === 'backtest' && (
            <div className="space-y-5 animate-in fade-in duration-150">
              {/* Quant Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
                <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs">
                  <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Sharpe Ratio</div>
                  <div className="text-2xl font-black text-slate-900 mt-1">{strategy.backtestSummary.sharpe.toFixed(2)}</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Sortino: {strategy.backtestSummary.sortino.toFixed(2)}</div>
                </div>

                <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs">
                  <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Win Rate / Loss Rate</div>
                  <div className="text-2xl font-black text-emerald-600 mt-1">{strategy.backtestSummary.winRate}%</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">{strategy.backtestSummary.lossRate}% losses ({strategy.backtestSummary.totalTrades} trades)</div>
                </div>

                <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs">
                  <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Profit Factor</div>
                  <div className="text-2xl font-black text-slate-900 mt-1">{strategy.backtestSummary.profitFactor}</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Expectancy: {strategy.backtestSummary.expectancy}R</div>
                </div>

                <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs">
                  <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Max Drawdown</div>
                  <div className="text-2xl font-black text-slate-800 mt-1">{strategy.backtestSummary.maxDrawdown}%</div>
                  <div className="text-[10px] text-emerald-600 font-bold mt-0.5">Within 4.0% limit</div>
                </div>
              </div>

              {/* Extended Metrics Table */}
              <div className="bg-slate-50 rounded-2xl p-4 border border-slate-200 text-xs">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <div>
                    <span className="text-slate-500">Average Win:</span>
                    <div className="font-bold text-emerald-700">${strategy.backtestSummary.averageWin}</div>
                  </div>
                  <div>
                    <span className="text-slate-500">Average Loss:</span>
                    <div className="font-bold text-rose-700">-${strategy.backtestSummary.averageLoss}</div>
                  </div>
                  <div>
                    <span className="text-slate-500">Annualized Volatility:</span>
                    <div className="font-bold text-slate-800">{strategy.backtestSummary.volatility}%</div>
                  </div>
                  <div>
                    <span className="text-slate-500">Out-Of-Sample Status:</span>
                    <div className="font-extrabold text-emerald-700">{strategy.backtestSummary.outOfSampleStatus}</div>
                  </div>
                  <div>
                    <span className="text-slate-500">Best Period:</span>
                    <div className="font-bold text-slate-800">{strategy.backtestSummary.bestPeriod}</div>
                  </div>
                  <div>
                    <span className="text-slate-500">Worst Period:</span>
                    <div className="font-bold text-rose-700">{strategy.backtestSummary.worstPeriod}</div>
                  </div>
                  <div className="sm:col-span-2">
                    <span className="text-slate-500">Backtest Universe Range:</span>
                    <div className="font-bold text-slate-800">{strategy.backtestSummary.testRange}</div>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-end">
                <button
                  type="button"
                  onClick={() => onRunBacktest(strategy)}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold transition-all shadow-xs cursor-pointer"
                >
                  <Play className="w-3.5 h-3.5" />
                  <span>Open in Backtest Center</span>
                </button>
              </div>
            </div>
          )}

          {/* TAB 4: ROBUSTNESS */}
          {activeTab === 'robustness' && (
            <div className="space-y-4 animate-in fade-in duration-150">
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200">
                <h3 className="text-xs font-black text-slate-900 uppercase tracking-wider mb-3">
                  Overfitting & Bias Verification Matrix
                </h3>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5 text-xs">
                  <div className="p-3 rounded-xl bg-white border border-slate-200">
                    <span className="text-slate-500">Walk-Forward Tested:</span>
                    <div className="font-extrabold text-emerald-700 mt-1 flex items-center gap-1.5">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      <span>{strategy.robustness.walkForwardTested ? 'Verified (12 Out-Of-Sample Windows)' : 'No'}</span>
                    </div>
                  </div>

                  <div className="p-3 rounded-xl bg-white border border-slate-200">
                    <span className="text-slate-500">Survivorship Bias Check:</span>
                    <div className={`font-extrabold mt-1 flex items-center gap-1.5 ${
                      strategy.robustness.survivorshipBiasCheck === 'Passed' ? 'text-emerald-700' : 'text-amber-700'
                    }`}>
                      <ShieldCheck className="w-4 h-4" />
                      <span>{strategy.robustness.survivorshipBiasCheck} (Includes delisted tickers)</span>
                    </div>
                  </div>

                  <div className="p-3 rounded-xl bg-white border border-slate-200">
                    <span className="text-slate-500">Lookahead Bias Screening:</span>
                    <div className="font-extrabold text-emerald-700 mt-1 flex items-center gap-1.5">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      <span>{strategy.robustness.lookaheadBiasCheck} (Lagged bar indexing)</span>
                    </div>
                  </div>

                  <div className="p-3 rounded-xl bg-white border border-slate-200">
                    <span className="text-slate-500">Parameter Sensitivity:</span>
                    <div className="font-extrabold text-slate-900 mt-1">{strategy.robustness.parameterSensitivity} plateau</div>
                  </div>

                  <div className="p-3 rounded-xl bg-white border border-slate-200">
                    <span className="text-slate-500">Market Regime Sensitivity:</span>
                    <div className="font-extrabold text-slate-900 mt-1">{strategy.robustness.regimeSensitivity}</div>
                  </div>

                  <div className="p-3 rounded-xl bg-white border border-slate-200">
                    <span className="text-slate-500">Overfitting Risk Grade:</span>
                    <div className={`font-extrabold mt-1 ${
                      strategy.robustness.overfittingRisk === 'Low' ? 'text-emerald-700' :
                      strategy.robustness.overfittingRisk === 'Medium' ? 'text-amber-700' : 'text-rose-700'
                    }`}>
                      {strategy.robustness.overfittingRisk} Risk
                    </div>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-200 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <div>
                    <span className="text-slate-500">Slippage Modeling:</span>
                    <div className="font-semibold text-slate-800">{strategy.robustness.slippageAssumptions}</div>
                  </div>
                  <div>
                    <span className="text-slate-500">Fee Structure Assumptions:</span>
                    <div className="font-semibold text-slate-800">{strategy.robustness.feeAssumptions}</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: ALPHA REVIEW */}
          {activeTab === 'alpha' && (
            <div className="space-y-5 animate-in fade-in duration-150">
              <div className="p-5 rounded-2xl bg-gradient-to-br from-purple-50/80 via-white to-indigo-50/50 border border-purple-200/80 shadow-xs space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-xl bg-purple-600 text-white flex items-center justify-center">
                      <Sparkles className="w-4 h-4" />
                    </div>
                    <div>
                      <h3 className="text-sm font-black text-slate-900">Alpha Autonomous Evaluation Verdict</h3>
                      <div className="text-[10px] text-slate-500 font-mono">Evaluated {strategy.alphaReview.evaluatedAt}</div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <div className="text-right">
                      <div className="text-[10px] text-slate-400 font-bold uppercase">Confidence Score</div>
                      <div className="text-sm font-black text-purple-700">{strategy.alphaReview.confidenceScore}%</div>
                    </div>
                    <span className={`px-3 py-1 rounded-xl text-xs font-black uppercase tracking-tight border ${alpha.bg}`}>
                      {strategy.alphaReview.verdict}
                    </span>
                  </div>
                </div>

                {/* Qualitative Critique */}
                <div className="p-4 rounded-xl bg-white border border-purple-100 shadow-2xs space-y-1.5">
                  <div className="text-[11px] font-bold text-purple-900 uppercase">Alpha Mathematical Critique & Conclusion</div>
                  <p className="text-xs text-slate-800 leading-relaxed font-medium">
                    {strategy.alphaReview.reasoning}
                  </p>
                </div>

                {/* Key Risks Flagged by Alpha */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                  <div className="p-3.5 rounded-xl bg-rose-50/60 border border-rose-100 space-y-1.5">
                    <div className="text-[10px] font-bold text-rose-900 uppercase flex items-center gap-1.5">
                      <AlertCircle className="w-3.5 h-3.5 text-rose-600" />
                      <span>Key Vulnerabilities Flagged by Alpha</span>
                    </div>
                    <ul className="space-y-1 text-slate-700">
                      {strategy.alphaReview.keyRisks.map((k, i) => (
                        <li key={i} className="flex items-start gap-1.5">
                          <span className="text-rose-500 font-bold">•</span>
                          <span>{k}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="p-3.5 rounded-xl bg-blue-50/60 border border-blue-100 space-y-1.5">
                    <div className="text-[10px] font-bold text-blue-900 uppercase flex items-center gap-1.5">
                      <Sliders className="w-3.5 h-3.5 text-blue-600" />
                      <span>Recommended Alpha Parameter Adjustments</span>
                    </div>
                    <ul className="space-y-1 text-slate-700">
                      {strategy.alphaReview.recommendedParameters.map((p, i) => (
                        <li key={i} className="flex items-start gap-1.5">
                          <span className="text-blue-500 font-bold">•</span>
                          <span>{p}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 6: VERSION HISTORY */}
          {activeTab === 'versions' && (
            <div className="space-y-4 animate-in fade-in duration-150">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-xs font-black text-slate-900 uppercase tracking-wider">
                    Model Versioning & Reproducibility Ledger
                  </h3>
                  <p className="text-[11px] text-slate-500">
                    Prevents changing a quantitative model without recording which version actually generated results.
                  </p>
                </div>
              </div>

              <div className="space-y-3">
                {strategy.versions.map((ver, idx) => (
                  <div key={idx} className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="px-2.5 py-0.5 rounded-md text-xs font-black bg-blue-600 text-white shadow-2xs">
                          {ver.version}
                        </span>
                        <span className="text-xs font-bold text-slate-800">{ver.date}</span>
                        <span className="font-mono text-[10px] text-slate-500 bg-white px-2 py-0.5 rounded border border-slate-200">
                          {ver.codeHash}
                        </span>
                      </div>
                      <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
                        {ver.alphaDecision}
                      </span>
                    </div>

                    <p className="text-xs text-slate-700 font-medium">{ver.summary}</p>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs bg-white p-2.5 rounded-xl border border-slate-100">
                      <div>
                        <div className="text-[9px] text-slate-400 font-bold uppercase">Sharpe</div>
                        <div className="font-black text-slate-900">{ver.backtestResult.sharpe.toFixed(2)}</div>
                      </div>
                      <div>
                        <div className="text-[9px] text-slate-400 font-bold uppercase">Win Rate</div>
                        <div className="font-black text-emerald-600">{ver.backtestResult.winRate}%</div>
                      </div>
                      <div>
                        <div className="text-[9px] text-slate-400 font-bold uppercase">Max DD</div>
                        <div className="font-black text-slate-800">{ver.backtestResult.maxDrawdown}%</div>
                      </div>
                      <div>
                        <div className="text-[9px] text-slate-400 font-bold uppercase">Paper PnL</div>
                        <div className="font-black text-emerald-600">{ver.paperResult?.totalPnl || 'N/A'}</div>
                      </div>
                    </div>

                    <div className="text-[11px] text-slate-500">
                      <span className="font-semibold text-slate-700">Parameters Modified: </span>
                      {ver.parametersChanged.join(', ')}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions: Stage Promotion Controls */}
        <div className="px-6 py-4 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-3 bg-slate-50/60">
          <div className="text-xs text-slate-600 font-medium">
            Current Stage: <span className="font-bold text-slate-900">{strategy.stage}</span>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {strategy.stage === 'IDEA' && (
              <button
                type="button"
                onClick={() => onPromoteStage(strategy.id, 'RESEARCHING')}
                className="px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold transition-all shadow-xs cursor-pointer"
              >
                Promote to RESEARCHING
              </button>
            )}

            {strategy.stage === 'RESEARCHING' && (
              <button
                type="button"
                onClick={() => onPromoteStage(strategy.id, 'BACKTESTING')}
                className="px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold transition-all shadow-xs cursor-pointer"
              >
                Promote to BACKTESTING
              </button>
            )}

            {strategy.stage === 'BACKTESTING' && (
              <button
                type="button"
                onClick={() => onPromoteStage(strategy.id, 'ALPHA_REVIEW')}
                className="px-3.5 py-2 rounded-xl bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold transition-all shadow-xs cursor-pointer flex items-center gap-1.5"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Submit to ALPHA_REVIEW</span>
              </button>
            )}

            {strategy.stage === 'ALPHA_REVIEW' && (
              <button
                type="button"
                onClick={() => onPromoteStage(strategy.id, 'APPROVED_FOR_PAPER')}
                className="px-3.5 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-700 text-white text-xs font-bold transition-all shadow-xs cursor-pointer"
              >
                Qualify for APPROVED_FOR_PAPER
              </button>
            )}

            {strategy.stage === 'APPROVED_FOR_PAPER' && (
              <button
                type="button"
                onClick={() => onPromoteStage(strategy.id, 'PAPER_TEST')}
                className="px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition-all shadow-xs cursor-pointer"
              >
                Launch Active PAPER_TEST
              </button>
            )}

            {strategy.stage === 'PAPER_TEST' && (
              <button
                type="button"
                onClick={() => onPromoteStage(strategy.id, 'PAUSED')}
                className="px-3.5 py-2 rounded-xl bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold transition-all shadow-xs cursor-pointer"
              >
                Pause Paper Testing
              </button>
            )}

            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-bold text-slate-600 hover:text-slate-800 hover:bg-slate-200/60 transition-colors cursor-pointer"
            >
              Close Workspace
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
