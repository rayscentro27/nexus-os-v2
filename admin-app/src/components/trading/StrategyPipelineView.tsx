import React, { useState } from 'react';
import { 
  Search, 
  Layers, 
  Table as TableIcon, 
  Grid,
  ChevronRight, 
  Sparkles, 
  ArrowRight, 
  Play, 
  TrendingUp, 
  Eye, 
  ShieldCheck, 
  ShieldAlert, 
  Plus, 
  FileText, 
  Info, 
  Trophy,
  Activity,
  PauseCircle,
  Archive,
  FlaskConical,
  Check,
  AlertTriangle
} from 'lucide-react';
import { StrategyItem, StrategyStage, StrategyType, AlphaDecision } from '../../types';

interface StrategyPipelineViewProps {
  strategies: StrategyItem[];
  onSelectStrategy: (strategy: StrategyItem) => void;
  onRunBacktestForStrategy: (strategy: StrategyItem) => void;
  onPromoteStage: (strategyId: string, nextStage: StrategyStage) => void;
  onOpenBacktestReport?: (reportId: string, strategy?: StrategyItem) => void;
  compactMode?: boolean;
  onOpenNewStrategyModal?: () => void;
  onRequestLiveApproval?: (strategy: StrategyItem) => void;
}

// 5 CANONICAL STAGE GATES AS SPECIFIED: Backtest, Tournament, Risk Review, Paper Trading, Paused/Retired
export type StageGateKey = 'Backtest' | 'Tournament' | 'Risk Review' | 'Paper Trading' | 'Paused/Retired';

export interface StageGateDetails {
  gateKey: StageGateKey;
  stepNumber: number; // 1 to 4, or 0 for Paused/Retired
  displayTitle: string;
  badgeLabel: string;
  subLabel: string;
  pillClasses: string;
  bannerBg: string;
  bannerBorder: string;
  bannerText: string;
  accentColor: string;
  icon: React.ComponentType<{ className?: string }>;
  isPaused: boolean;
  isRetired: boolean;
  isPausedOrRetired: boolean;
}

export const getStageGateDetails = (stage: StrategyStage): StageGateDetails => {
  switch (stage) {
    case 'BACKTEST':
    case 'BACKTESTING':
    case 'IDEA':
    case 'RESEARCHING':
      return {
        gateKey: 'Backtest',
        stepNumber: 1,
        displayTitle: 'Backtest Gate',
        badgeLabel: 'Gate 1: Backtest',
        subLabel: 'Hypothesis & Param Grid',
        pillClasses: 'bg-blue-100 text-blue-900 border-blue-300 ring-1 ring-blue-200/50',
        bannerBg: 'bg-blue-50/90',
        bannerBorder: 'border-blue-200',
        bannerText: 'text-blue-900',
        accentColor: 'text-blue-600',
        icon: FlaskConical,
        isPaused: false,
        isRetired: false,
        isPausedOrRetired: false
      };
    case 'TOURNAMENT':
      return {
        gateKey: 'Tournament',
        stepNumber: 2,
        displayTitle: 'Tournament Gate',
        badgeLabel: 'Gate 2: Tournament',
        subLabel: 'Standardized Walk-Forward',
        pillClasses: 'bg-amber-100 text-amber-950 border-amber-300 ring-1 ring-amber-200/50',
        bannerBg: 'bg-amber-50/90',
        bannerBorder: 'border-amber-200',
        bannerText: 'text-amber-950',
        accentColor: 'text-amber-600',
        icon: Trophy,
        isPaused: false,
        isRetired: false,
        isPausedOrRetired: false
      };
    case 'RISK_REVIEW':
    case 'REVIEW_REQUIRED':
    case 'APPROVED_FOR_PAPER':
      return {
        gateKey: 'Risk Review',
        stepNumber: 3,
        displayTitle: 'Risk Review Gate',
        badgeLabel: 'Gate 3: Risk Review',
        subLabel: 'Dual Committee Sign-Off',
        pillClasses: 'bg-purple-100 text-purple-950 border-purple-300 ring-1 ring-purple-200/50',
        bannerBg: 'bg-purple-50/90',
        bannerBorder: 'border-purple-200',
        bannerText: 'text-purple-950',
        accentColor: 'text-purple-600',
        icon: ShieldCheck,
        isPaused: false,
        isRetired: false,
        isPausedOrRetired: false
      };
    case 'PAPER_TRADING':
    case 'PAPER_TEST':
    case 'APPROVED_FOR_LIVE':
      return {
        gateKey: 'Paper Trading',
        stepNumber: 4,
        displayTitle: 'Paper Trading Gate',
        badgeLabel: 'Gate 4: Paper Trading',
        subLabel: 'Simulated Execution Sandbox',
        pillClasses: 'bg-emerald-100 text-emerald-950 border-emerald-300 ring-1 ring-emerald-200/50',
        bannerBg: 'bg-emerald-50/90',
        bannerBorder: 'border-emerald-200',
        bannerText: 'text-emerald-950',
        accentColor: 'text-emerald-600',
        icon: Activity,
        isPaused: false,
        isRetired: false,
        isPausedOrRetired: false
      };
    case 'PAUSED':
      return {
        gateKey: 'Paused/Retired',
        stepNumber: 0,
        displayTitle: 'Paused Gate',
        badgeLabel: 'Gate: Paused/Retired',
        subLabel: 'Temporarily Halted · Risk Cap or Param Fix',
        pillClasses: 'bg-amber-100 text-amber-950 border-amber-300 ring-1 ring-amber-200/50',
        bannerBg: 'bg-amber-50/90',
        bannerBorder: 'border-amber-300',
        bannerText: 'text-amber-950',
        accentColor: 'text-amber-700',
        icon: PauseCircle,
        isPaused: true,
        isRetired: false,
        isPausedOrRetired: true
      };
    case 'RETIRED':
    case 'REJECTED':
    case 'ARCHIVED':
    default:
      return {
        gateKey: 'Paused/Retired',
        stepNumber: 0,
        displayTitle: 'Retired Gate',
        badgeLabel: 'Gate: Paused/Retired',
        subLabel: 'Permanently Archived · Negative Expectancy',
        pillClasses: 'bg-rose-100 text-rose-950 border-rose-300 ring-1 ring-rose-200/50',
        bannerBg: 'bg-rose-50/90',
        bannerBorder: 'border-rose-300',
        bannerText: 'text-rose-950',
        accentColor: 'text-rose-700',
        icon: Archive,
        isPaused: false,
        isRetired: true,
        isPausedOrRetired: true
      };
  }
};

const PIPELINE_GATE_COLUMNS: { id: StageGateKey; label: string; countColor: string; description: string }[] = [
  { id: 'Backtest', label: '1. Backtest', countColor: 'bg-blue-100 text-blue-800', description: 'In-sample hypothesis & parameter grid' },
  { id: 'Tournament', label: '2. Tournament', countColor: 'bg-amber-100 text-amber-900', description: 'Standardized walk-forward competition' },
  { id: 'Risk Review', label: '3. Risk Review', countColor: 'bg-purple-100 text-purple-800', description: 'Governance audit before paper trading' },
  { id: 'Paper Trading', label: '4. Paper Trading', countColor: 'bg-emerald-100 text-emerald-800', description: 'Simulated sandbox execution (Zero real risk)' },
  { id: 'Paused/Retired', label: 'Paused / Retired', countColor: 'bg-rose-100 text-rose-800', description: 'Halted for risk cap breach or archived' }
];

export const StrategyPipelineView: React.FC<StrategyPipelineViewProps> = ({
  strategies,
  onSelectStrategy,
  onRunBacktestForStrategy,
  onPromoteStage,
  onOpenBacktestReport,
  compactMode = true,
  onOpenNewStrategyModal,
  onRequestLiveApproval,
}) => {
  const [viewMode, setViewMode] = useState<'grid' | 'kanban' | 'table'>('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedGateFilter, setSelectedGateFilter] = useState<string>('ALL');
  const [selectedMarketFilter, setSelectedMarketFilter] = useState<string>('ALL');
  const [selectedTypeFilter, setSelectedTypeFilter] = useState<string>('ALL');

  // Filtered strategies
  const filteredStrategies = strategies.filter(item => {
    const gateInfo = getStageGateDetails(item.stage);
    const matchesSearch = 
      item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.universe.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.progression?.reason && item.progression.reason.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesGate = selectedGateFilter === 'ALL' || gateInfo.gateKey === selectedGateFilter;
    const matchesMarket = selectedMarketFilter === 'ALL' || item.market === selectedMarketFilter;
    const matchesType = selectedTypeFilter === 'ALL' || item.type === selectedTypeFilter;

    return matchesSearch && matchesGate && matchesMarket && matchesType;
  });

  const getAlphaBadge = (decision: AlphaDecision) => {
    switch (decision) {
      case 'QUALIFY':
      case 'PAPER_TEST':
        return { label: decision, bg: 'bg-emerald-50 text-emerald-700 border-emerald-200/80' };
      case 'RESEARCH_MORE':
        return { label: decision.replace('_', ' '), bg: 'bg-blue-50 text-blue-700 border-blue-200/80' };
      case 'PAUSE':
        return { label: decision, bg: 'bg-amber-50 text-amber-700 border-amber-200/80' };
      case 'REJECT':
        return { label: decision, bg: 'bg-rose-50 text-rose-700 border-rose-200/80' };
      default:
        return { label: 'NO ACTION', bg: 'bg-slate-50 text-slate-700 border-slate-200' };
    }
  };

  return (
    <div className="h-full flex flex-col min-h-0 space-y-2">
      {/* Header & Progression Pipeline Bar */}
      <div className="bg-white rounded-xl p-2.5 border border-slate-200/90 shadow-2xs space-y-2 shrink-0">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-black text-slate-900 tracking-tight">Strategy Progression Pipeline</span>
            <span className="text-[10px] font-bold px-2 py-0.2 rounded-full bg-blue-100 text-blue-800">
              {filteredStrategies.length} Models
            </span>
            <span className="text-[11px] text-slate-400 hidden lg:inline">
              • Strict Gate Progression: Backtest → Tournament → Risk Review → Paper Trading → Paused/Retired
            </span>
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center gap-1.5 shrink-0">
            {onOpenNewStrategyModal && (
              <button
                type="button"
                onClick={onOpenNewStrategyModal}
                className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-[11px] font-extrabold shadow-2xs transition-all cursor-pointer"
                title="Open Quantitative Strategy Rule Builder"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>+ New Model</span>
              </button>
            )}

            <div className="flex items-center gap-1 p-0.5 bg-slate-100 rounded-lg border border-slate-200 text-xs font-bold">
              <button
                type="button"
                onClick={() => setViewMode('grid')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition-all cursor-pointer ${
                  viewMode === 'grid' ? 'bg-white text-slate-900 shadow-2xs font-extrabold' : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                <Grid className="w-3 h-3" />
                <span>Grid</span>
              </button>
              <button
                type="button"
                onClick={() => setViewMode('kanban')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition-all cursor-pointer ${
                  viewMode === 'kanban' ? 'bg-white text-slate-900 shadow-2xs font-extrabold' : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                <Layers className="w-3 h-3" />
                <span>Kanban</span>
              </button>
              <button
                type="button"
                onClick={() => setViewMode('table')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition-all cursor-pointer ${
                  viewMode === 'table' ? 'bg-white text-slate-900 shadow-2xs font-extrabold' : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                <TableIcon className="w-3 h-3" />
                <span>Table</span>
              </button>
            </div>
          </div>
        </div>

        {/* 5 Progression Stage Gate Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-1.5 pt-1.5 border-t border-slate-100 text-[10px]">
          {PIPELINE_GATE_COLUMNS.map(gate => {
            const count = strategies.filter(s => getStageGateDetails(s.stage).gateKey === gate.id).length;

            return (
              <div
                key={gate.id}
                onClick={() => setSelectedGateFilter(selectedGateFilter === gate.id ? 'ALL' : gate.id)}
                className={`p-1.5 rounded-lg border transition-all cursor-pointer flex flex-col justify-between ${
                  selectedGateFilter === gate.id
                    ? 'bg-blue-50/80 border-blue-400 ring-2 ring-blue-100'
                    : 'bg-slate-50 hover:bg-slate-100/80 border-slate-200'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-extrabold text-slate-800">{gate.label}</span>
                  <span className={`px-1.5 py-0.2 rounded-full font-black text-[9px] ${gate.countColor}`}>
                    {count}
                  </span>
                </div>
                <div className="text-[9px] text-slate-500 mt-0.5 truncate">{gate.description}</div>
              </div>
            );
          })}
        </div>

        {/* Filter Controls Row */}
        <div className="grid grid-cols-[repeat(auto-fit,minmax(140px,1fr))] gap-1.5 pt-1.5 border-t border-slate-100 text-[11px]">
          <div className="relative col-span-2 sm:col-span-1">
            <Search className="w-3 h-3 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search strategy or reason..."
              className="w-full pl-7 pr-2.5 py-1 rounded-lg border border-slate-200 text-[11px] focus:outline-hidden"
            />
          </div>

          <select
            value={selectedGateFilter}
            onChange={e => setSelectedGateFilter(e.target.value)}
            className="w-full px-2 py-1 rounded-lg border border-slate-200 text-[11px] font-semibold text-slate-700 bg-white"
          >
            <option value="ALL">All Stage Gates</option>
            {PIPELINE_GATE_COLUMNS.map(s => (
              <option key={s.id} value={s.id}>{s.label}</option>
            ))}
          </select>

          <select
            value={selectedMarketFilter}
            onChange={e => setSelectedMarketFilter(e.target.value)}
            className="w-full px-2 py-1 rounded-lg border border-slate-200 text-[11px] font-semibold text-slate-700 bg-white"
          >
            <option value="ALL">All Markets</option>
            <option value="Equities">Equities</option>
            <option value="Forex">Forex (Currencies)</option>
            <option value="Crypto">Crypto</option>
            <option value="Futures">Futures</option>
            <option value="Options">Options</option>
            <option value="Multi-Asset">Multi-Asset</option>
          </select>

          <select
            value={selectedTypeFilter}
            onChange={e => setSelectedTypeFilter(e.target.value)}
            className="w-full px-2 py-1 rounded-lg border border-slate-200 text-[11px] font-semibold text-slate-700 bg-white"
          >
            <option value="ALL">All Strategy Types</option>
            <option value="volatility">Volatility</option>
            <option value="pairs/statistical">Pairs / Statistical</option>
            <option value="mean reversion">Mean Reversion</option>
            <option value="momentum">Momentum</option>
            <option value="options research">Options Research</option>
            <option value="macro">Macro</option>
            <option value="trend following">Trend Following</option>
            <option value="event-driven">Event-Driven</option>
          </select>
        </div>
      </div>

      {/* Grid View */}
      {viewMode === 'grid' && (
        <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar pr-0.5">
          <div className="grid grid-cols-[repeat(auto-fit,minmax(310px,1fr))] gap-2.5">
            {filteredStrategies.map(item => {
              const alpha = getAlphaBadge(item.alphaDecision);
              const gateInfo = getStageGateDetails(item.stage);
              const GateIcon = gateInfo.icon;
              const stateReason = item.progression?.reason || item.nextAction || item.alphaReview.reasoning;
              const nextGateLabel = item.nextGate || item.progression?.nextGate || 'Governance Sign-Off';

              return (
                <div
                  key={item.id}
                  onClick={() => onSelectStrategy(item)}
                  className="bg-white rounded-2xl p-3.5 border border-slate-200 shadow-2xs hover:border-blue-400 hover:shadow-xs transition-all cursor-pointer group flex flex-col justify-between space-y-3"
                >
                  <div className="space-y-2.5">
                    {/* VISUAL CURRENT STAGE GATE HEADER BANNER */}
                    <div className={`p-2 rounded-xl border flex items-center justify-between gap-1.5 ${gateInfo.bannerBg} ${gateInfo.bannerBorder}`}>
                      <div className="flex items-center gap-1.5">
                        <div className="w-5 h-5 rounded-md bg-white/90 border border-slate-200/80 flex items-center justify-center shrink-0 shadow-2xs">
                          <GateIcon className={`w-3.5 h-3.5 ${gateInfo.accentColor}`} />
                        </div>
                        <div>
                          <div className="text-[9px] font-black uppercase tracking-wider text-slate-500 leading-none">
                            Current Stage Gate
                          </div>
                          <div className={`text-xs font-black tracking-tight ${gateInfo.bannerText} mt-0.5`}>
                            {gateInfo.gateKey}
                          </div>
                        </div>
                      </div>

                      <span className={`px-2 py-0.5 rounded-full text-[9px] font-black border uppercase tracking-wider ${gateInfo.pillClasses}`}>
                        {gateInfo.stepNumber > 0 ? `Step ${gateInfo.stepNumber}/4` : (gateInfo.isPaused ? 'Paused' : 'Retired')}
                      </span>
                    </div>

                    {/* MINI 4-GATE PROGRESSION STEPPER */}
                    {!gateInfo.isPausedOrRetired ? (
                      <div className="grid grid-cols-4 gap-1 p-1 bg-slate-100/90 rounded-lg border border-slate-200/80 text-[9px] font-bold">
                        {[
                          { num: 1, name: 'Backtest' },
                          { num: 2, name: 'Tournament' },
                          { num: 3, name: 'Risk Review' },
                          { num: 4, name: 'Paper Trading' }
                        ].map(step => {
                          const isCurrent = step.num === gateInfo.stepNumber;
                          const isPassed = step.num < gateInfo.stepNumber;
                          return (
                            <div
                              key={step.num}
                              className={`flex items-center justify-center gap-1 py-1 px-1 rounded-md text-center transition-all ${
                                isCurrent
                                  ? 'bg-blue-600 text-white font-black shadow-2xs ring-1 ring-blue-700'
                                  : isPassed
                                  ? 'bg-emerald-100 text-emerald-800 font-extrabold'
                                  : 'text-slate-400 font-medium'
                              }`}
                            >
                              {isPassed ? (
                                <Check className="w-2.5 h-2.5 stroke-[3] text-emerald-700" />
                              ) : (
                                <span className={`w-3 h-3 rounded-full flex items-center justify-center text-[8px] ${
                                  isCurrent ? 'bg-white text-blue-700 font-black' : 'bg-slate-200 text-slate-500'
                                }`}>
                                  {step.num}
                                </span>
                              )}
                              <span className="truncate">{step.name}</span>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div className={`p-1.5 rounded-lg border text-[10px] flex items-center justify-between ${
                        gateInfo.isPaused ? 'bg-amber-50/90 border-amber-300 text-amber-900' : 'bg-rose-50/90 border-rose-300 text-rose-900'
                      }`}>
                        <div className="flex items-center gap-1.5 font-bold">
                          <GateIcon className="w-3.5 h-3.5 shrink-0" />
                          <span>Status:</span>
                          <span className={`px-1.5 py-0.2 rounded font-black text-[9px] uppercase ${
                            gateInfo.isPaused ? 'bg-amber-200 text-amber-900' : 'bg-rose-200 text-rose-900'
                          }`}>
                            {gateInfo.isPaused ? 'Paused (Fix Required)' : 'Retired (Archived)'}
                          </span>
                        </div>
                        <span className="text-[9px] font-semibold opacity-80">Pipeline Halted</span>
                      </div>
                    )}

                    {/* Header: Market, Alpha Decision & ID */}
                    <div className="flex items-center justify-between gap-1 pt-0.5">
                      <div className="flex items-center gap-1.5">
                        <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
                          {item.market}
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono">
                          {item.id} • {item.type}
                        </span>
                      </div>
                      <div className={`flex items-center gap-1 px-2 py-0.5 rounded-full border text-[9px] font-extrabold ${alpha.bg}`}>
                        <Sparkles className="w-2.5 h-2.5" />
                        <span>{alpha.label}</span>
                      </div>
                    </div>

                    {/* Name */}
                    <div>
                      <h3 className="text-xs font-black text-slate-900 group-hover:text-blue-600 transition-colors leading-snug">
                        {item.name}
                      </h3>
                      <div className="text-[10px] text-slate-500 line-clamp-1 mt-0.5">
                        Universe: <span className="font-semibold text-slate-700">{item.universe}</span>
                      </div>
                    </div>

                    {/* Key Quant Metrics with Out-of-Sample Context */}
                    <div className="grid grid-cols-4 gap-1 py-1.5 px-1.5 rounded-lg bg-slate-50 border border-slate-100 text-center text-[10px]">
                      <div>
                        <div className="text-[8px] text-slate-400 font-bold uppercase">Sharpe</div>
                        <div className="font-black text-slate-900">{item.backtestSummary.sharpe.toFixed(2)}</div>
                      </div>
                      <div>
                        <div className="text-[8px] text-slate-400 font-bold uppercase">Win Rate</div>
                        <div className="font-black text-emerald-600">{item.backtestSummary.winRate}%</div>
                      </div>
                      <div>
                        <div className="text-[8px] text-slate-400 font-bold uppercase">Max DD</div>
                        <div className={`font-black ${item.backtestSummary.maxDrawdown > 4.0 ? 'text-rose-600' : 'text-slate-700'}`}>
                          {item.backtestSummary.maxDrawdown}%
                        </div>
                      </div>
                      <div>
                        <div className="text-[8px] text-slate-400 font-bold uppercase">Profit F.</div>
                        <div className="font-black text-blue-700">{item.backtestSummary.profitFactor.toFixed(2)}</div>
                      </div>
                    </div>

                    {/* Performance Evidence: Test Period, Trade Count, Fees & Slippage */}
                    <div className="p-2 rounded-lg bg-slate-50 border border-slate-200/70 text-[10px] space-y-1">
                      <div className="flex items-center justify-between text-slate-600">
                        <span>Sample: <strong>{item.performanceEvidence?.testPeriod || item.backtestSummary.testRange}</strong></span>
                        <span className="font-semibold text-slate-800">{item.performanceEvidence?.tradeCount || item.backtestSummary.totalTrades} Trades</span>
                      </div>
                      <div className="flex items-center justify-between text-slate-500 text-[9px]">
                        <span>Slippage: {item.performanceEvidence?.slippageAssumptions || item.robustness.slippageAssumptions}</span>
                        <span className={`px-1 rounded font-bold ${
                          item.performanceEvidence?.outOfSampleStatus === 'Passed' ? 'text-emerald-700 bg-emerald-50' :
                          item.performanceEvidence?.outOfSampleStatus === 'Failed' ? 'text-rose-700 bg-rose-50' : 'text-amber-700 bg-amber-50'
                        }`}>
                          OOS: {item.performanceEvidence?.outOfSampleStatus || item.backtestSummary.outOfSampleStatus}
                        </span>
                      </div>
                    </div>

                    {/* FOREX SPECIFIC METRICS STRIP */}
                    {item.forexDetails && (
                      <div className="p-2 rounded-lg bg-emerald-50/70 border border-emerald-200/90 text-[10px] space-y-1">
                        <div className="flex items-center justify-between font-black text-emerald-900 text-[9px] uppercase">
                          <span>Forex Specification</span>
                          <span className="font-mono">{item.forexDetails.currencyPair}</span>
                        </div>
                        <div className="grid grid-cols-2 gap-1 text-[9px] text-slate-700">
                          <div><span className="text-slate-400">Session:</span> {item.forexDetails.tradingSession}</div>
                          <div><span className="text-slate-400">Entry:</span> {item.forexDetails.pipEntry}</div>
                          <div><span className="text-slate-400">Stop:</span> {item.forexDetails.pipStop}</div>
                          <div><span className="text-slate-400">Spread:</span> {item.forexDetails.spread}</div>
                          <div><span className="text-slate-400">Costs:</span> {item.forexDetails.estimatedExecutionCosts}</div>
                          <div><span className="text-slate-400">Feed:</span> {item.forexDetails.dataFeed}</div>
                        </div>
                      </div>
                    )}

                    {/* REASON FOR CURRENT STATE CONTAINER */}
                    <div className="p-2.5 rounded-xl bg-slate-50/95 border border-slate-200 space-y-1">
                      <div className="flex items-center justify-between text-[10px]">
                        <div className="flex items-center gap-1.5 text-slate-600 font-black uppercase tracking-wider text-[9px]">
                          <Info className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                          <span>Reason for Current State:</span>
                        </div>
                        <span className={`px-1.5 py-0.2 rounded-full font-black text-[8px] border uppercase ${
                          item.progression?.status === 'Advanced' ? 'bg-emerald-50 text-emerald-800 border-emerald-300' :
                          item.progression?.status === 'Rejected' ? 'bg-rose-50 text-rose-800 border-rose-300' :
                          item.progression?.status === 'Waiting' ? 'bg-blue-50 text-blue-800 border-blue-300' :
                          'bg-amber-50 text-amber-800 border-amber-300'
                        }`}>
                          {item.progression?.status || 'Active'}
                        </span>
                      </div>
                      <p className="text-[11px] font-semibold text-slate-800 leading-snug">
                        {stateReason}
                      </p>
                    </div>

                    {/* NEXT GATE CALLOUT WITH EXPLICIT LABEL */}
                    <div className="p-2.5 rounded-xl bg-gradient-to-r from-purple-50/90 via-purple-50/60 to-blue-50/60 border border-purple-200/90 space-y-1">
                      <div className="flex items-center justify-between text-[10px]">
                        <div className="flex items-center gap-1.5 font-black uppercase text-purple-900 tracking-wider text-[9px]">
                          <ArrowRight className="w-3.5 h-3.5 text-purple-600 shrink-0" />
                          <span>Next Gate:</span>
                        </div>
                        <span className="text-[8px] font-extrabold uppercase px-1.5 py-0.2 rounded bg-purple-100 text-purple-800 border border-purple-200 font-mono">
                          Handoff Gate
                        </span>
                      </div>
                      <div className="text-[11px] font-extrabold text-purple-950 leading-tight">
                        {nextGateLabel}
                      </div>
                    </div>
                  </div>

                  {/* Card Footer: Owner & Actions */}
                  <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-1.5">
                      <img
                        src={item.owner.avatar}
                        alt={item.owner.name}
                        className="w-4 h-4 rounded-full object-cover border border-slate-200"
                      />
                      <span className="text-[10px] font-medium text-slate-700">{item.owner.name.split(' ')[0]}</span>
                    </div>

                    <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                      {onOpenBacktestReport && (
                        <button
                          type="button"
                          onClick={() => onOpenBacktestReport(item.performanceEvidence?.backtestReportId || 'bt-run-7412', item)}
                          title="Open Supporting Backtest Report"
                          className="px-2 py-0.5 rounded text-blue-700 hover:bg-blue-50 border border-blue-200 text-[10px] font-bold flex items-center gap-1 transition-colors cursor-pointer"
                        >
                          <FileText className="w-3 h-3" />
                          <span>Report</span>
                        </button>
                      )}

                      <button
                        type="button"
                        onClick={() => onRunBacktestForStrategy(item)}
                        title="Run Quant Backtest Simulation"
                        className="p-1 rounded text-slate-500 hover:text-blue-600 hover:bg-blue-50 transition-colors cursor-pointer"
                      >
                        <Play className="w-3 h-3" />
                      </button>

                      <button
                        type="button"
                        onClick={() => onSelectStrategy(item)}
                        title="View Strategy Workspace"
                        className="p-1 rounded text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors cursor-pointer"
                      >
                        <Eye className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Kanban View */}
      {viewMode === 'kanban' && (
        <div className="flex-1 min-h-0 overflow-x-auto overflow-y-hidden custom-scrollbar pb-1">
          <div className="flex items-start gap-3 min-w-[1350px] h-full">
            {PIPELINE_GATE_COLUMNS.map(column => {
              const stageItems = filteredStrategies.filter(s => getStageGateDetails(s.stage).gateKey === column.id);

              return (
                <div key={column.id} className="w-72 shrink-0 bg-slate-100/70 rounded-xl p-2.5 border border-slate-200/70 flex flex-col h-full overflow-hidden">
                  <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-200/80 shrink-0">
                    <div>
                      <span className="text-xs font-black text-slate-800 tracking-tight">{column.label}</span>
                      <div className="text-[9px] text-slate-500 truncate">{column.description}</div>
                    </div>
                    <span className={`text-[10px] font-extrabold px-2 py-0.2 rounded-full ${column.countColor}`}>
                      {stageItems.length}
                    </span>
                  </div>

                  <div className="space-y-2 overflow-y-auto custom-scrollbar flex-1 min-h-0 pr-0.5">
                    {stageItems.map(item => {
                      const gateInfo = getStageGateDetails(item.stage);
                      const stateReason = item.progression?.reason || item.nextAction || item.alphaReview.reasoning;
                      const nextGateLabel = item.nextGate || item.progression?.nextGate || 'Governance Sign-Off';

                      return (
                        <div
                          key={item.id}
                          onClick={() => onSelectStrategy(item)}
                          className="bg-white rounded-xl p-2.5 border border-slate-200 shadow-2xs hover:border-blue-400 transition-all cursor-pointer space-y-2"
                        >
                          {/* Card Top: Stage Gate Badge */}
                          <div className="flex items-center justify-between">
                            <span className={`px-2 py-0.5 rounded-full text-[9px] font-black border uppercase ${gateInfo.pillClasses}`}>
                              {gateInfo.gateKey}
                            </span>
                            <span className="text-[10px] font-mono text-slate-400">{item.id}</span>
                          </div>

                          <h4 className="text-xs font-black text-slate-900 leading-snug">{item.name}</h4>

                          <div className="flex items-center justify-between text-[10px] text-slate-600 bg-slate-50 p-1.5 rounded">
                            <span>Sharpe: <strong className="text-slate-900">{item.backtestSummary.sharpe.toFixed(2)}</strong></span>
                            <span>DD: <strong className={item.backtestSummary.maxDrawdown > 4.0 ? 'text-rose-600' : 'text-slate-900'}>{item.backtestSummary.maxDrawdown}%</strong></span>
                            <span>Win: <strong className="text-emerald-600">{item.backtestSummary.winRate}%</strong></span>
                          </div>

                          {/* Reason for Current State */}
                          <div className="p-1.5 rounded-lg bg-slate-50 border border-slate-200/80 text-[10px] space-y-0.5">
                            <div className="font-extrabold text-[8px] uppercase tracking-wider text-slate-500">
                              Reason for Current State:
                            </div>
                            <p className="text-[10px] text-slate-800 font-medium line-clamp-2 leading-tight">
                              {stateReason}
                            </p>
                          </div>

                          {/* Next Gate */}
                          <div className="p-1.5 rounded-lg bg-purple-50/80 border border-purple-200 text-[10px] space-y-0.5">
                            <div className="font-extrabold text-[8px] uppercase tracking-wider text-purple-700 flex items-center gap-1">
                              <ArrowRight className="w-2.5 h-2.5" />
                              <span>Next Gate:</span>
                            </div>
                            <div className="text-[10px] font-bold text-purple-950 truncate">
                              {nextGateLabel}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Table View */}
      {viewMode === 'table' && (
        <div className="flex-1 min-h-0 bg-white rounded-xl border border-slate-200 overflow-hidden flex flex-col">
          <div className="overflow-x-auto overflow-y-auto custom-scrollbar flex-1">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase text-[10px] font-bold sticky top-0 z-10">
                <tr>
                  <th className="py-2 px-3">Strategy</th>
                  <th className="py-2 px-2">Current Stage Gate</th>
                  <th className="py-2 px-2">Next Gate</th>
                  <th className="py-2 px-2">Reason for Current State</th>
                  <th className="py-2 px-2 text-center">Sharpe</th>
                  <th className="py-2 px-2 text-center">Win Rate</th>
                  <th className="py-2 px-2 text-center">Max DD</th>
                  <th className="py-2 px-2 text-center">Trades</th>
                  <th className="py-2 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {filteredStrategies.map(item => {
                  const gateInfo = getStageGateDetails(item.stage);
                  const GateIcon = gateInfo.icon;
                  const stateReason = item.progression?.reason || item.nextAction || item.alphaReview.reasoning;
                  const nextGateLabel = item.nextGate || item.progression?.nextGate || 'Governance Sign-Off';

                  return (
                    <tr key={item.id} className="hover:bg-slate-50/80 transition-colors cursor-pointer" onClick={() => onSelectStrategy(item)}>
                      <td className="py-2 px-3">
                        <div className="font-extrabold text-slate-900">{item.name}</div>
                        <div className="text-[10px] text-slate-400 font-mono">{item.id} • {item.market}</div>
                      </td>
                      <td className="py-2 px-2">
                        <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[9px] font-black border uppercase ${gateInfo.pillClasses}`}>
                          <GateIcon className="w-3 h-3" />
                          <span>{gateInfo.gateKey}</span>
                        </span>
                      </td>
                      <td className="py-2 px-2">
                        <div className="text-[9px] font-extrabold text-purple-700 uppercase flex items-center gap-1">
                          <ArrowRight className="w-2.5 h-2.5" />
                          <span>Next Gate:</span>
                        </div>
                        <div className="text-[10px] text-purple-950 font-bold max-w-[190px] truncate" title={nextGateLabel}>
                          {nextGateLabel}
                        </div>
                      </td>
                      <td className="py-2 px-2">
                        <div className="text-[10px] text-slate-800 font-medium max-w-[240px] truncate" title={stateReason}>
                          {stateReason}
                        </div>
                      </td>
                      <td className="py-2 px-2 text-center font-bold text-slate-900">{item.backtestSummary.sharpe.toFixed(2)}</td>
                      <td className="py-2 px-2 text-center font-bold text-emerald-600">{item.backtestSummary.winRate}%</td>
                      <td className={`py-2 px-2 text-center font-bold ${item.backtestSummary.maxDrawdown > 4.0 ? 'text-rose-600' : 'text-slate-700'}`}>
                        {item.backtestSummary.maxDrawdown}%
                      </td>
                      <td className="py-2 px-2 text-center text-slate-600">{item.performanceEvidence?.tradeCount || item.backtestSummary.totalTrades}</td>
                      <td className="py-2 px-3 text-right" onClick={e => e.stopPropagation()}>
                        <div className="flex items-center justify-end gap-1">
                          {onOpenBacktestReport && (
                            <button
                              type="button"
                              onClick={() => onOpenBacktestReport(item.performanceEvidence?.backtestReportId || 'bt-run-7412', item)}
                              className="p-1 rounded text-blue-600 hover:bg-blue-50"
                              title="View Backtest Report"
                            >
                              <FileText className="w-3.5 h-3.5" />
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => onSelectStrategy(item)}
                            className="p-1 rounded text-slate-500 hover:text-slate-900 hover:bg-slate-100"
                            title="Inspect Details"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
