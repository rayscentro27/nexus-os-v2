import React, { useState } from 'react';
import { 
  ThreeDIcon 
} from '../components/common/ThreeDIcon';
import { 
  TradingModeGovernanceModal 
} from '../components/trading/TradingModeGovernanceModal';
import { 
  KillSwitchModal 
} from '../components/trading/KillSwitchModal';
import { 
  StrategyPipelineView 
} from '../components/trading/StrategyPipelineView';
import { 
  StrategyDetailWorkspace 
} from '../components/trading/StrategyDetailWorkspace';
import { 
  BacktestCenterView 
} from '../components/trading/BacktestCenterView';
import { 
  PaperTradingView 
} from '../components/trading/PaperTradingView';
import { 
  SignalCenterView 
} from '../components/trading/SignalCenterView';
import { 
  MarketMonitorView 
} from '../components/trading/MarketMonitorView';
import { 
  MarketIntelligenceView 
} from '../components/trading/MarketIntelligenceView';
import { 
  RiskCenterView 
} from '../components/trading/RiskCenterView';
import { 
  PerformanceAnalyticsView 
} from '../components/trading/PerformanceAnalyticsView';
import { 
  AlphaReviewWorkspace 
} from '../components/trading/AlphaReviewWorkspace';
import { 
  ProviderHealthAuditView 
} from '../components/trading/ProviderHealthAuditView';
import { 
  TradingTournamentView 
} from '../components/trading/TradingTournamentView';
import { 
  TradingWorkflowHub 
} from '../components/trading/TradingWorkflowHub';
import { 
  BacktestReportModal 
} from '../components/trading/BacktestReportModal';
import { 
  LiveChartAndReplayTerminal 
} from '../components/trading/LiveChartAndReplayTerminal';
import { 
  ParameterSensitivityHeatmap 
} from '../components/trading/ParameterSensitivityHeatmap';
import { 
  ExecutionQualityInspector 
} from '../components/trading/ExecutionQualityInspector';
import { 
  PostTradeScorecardView 
} from '../components/trading/PostTradeScorecardView';
import { TruthBadge } from '../components/common/TruthBadge';
import { UnavailableState } from '../components/live/UnavailableState';
import { useNexus } from '../context/NexusContext';



import { 
  TradingMode, 
  KillSwitchScope, 
  StrategyItem, 
  StrategyStage, 
  TradingSignal, 
  SignalStatus, 
  BacktestResultRecord,
  PaperOrder,
  PaperPosition,
  TournamentRound,
  TournamentEntry
} from '../types';

import { 
  Layers, 
  Play, 
  Radio, 
  Activity, 
  Sparkles, 
  ShieldCheck, 
  BarChart2, 
  Database,
  CheckCircle2,
  Sliders,
  DollarSign,
  ShieldAlert,
  Cpu,
  Clock,
  Grid,
  Trophy,
  AlertTriangle,
  Info,
  Zap,
  Award,
  Target,
  X
} from 'lucide-react';

// Active Workspace Views
export type TradingTab =
  | 'overview'
  | 'workflow'
  | 'charts'
  | 'pipeline'
  | 'tournament'
  | 'paper'
  | 'signals'
  | 'backtest'
  | 'monitor'
  | 'intelligence'
  | 'risk'
  | 'analytics'
  | 'sensitivity'
  | 'execution_audit'
  | 'scorecard'
  | 'alpha'
  | 'infrastructure'
  | 'radar';

export const TradingEnginePage: React.FC = () => {
  const { navigateToObject, approvals, liveAreas } = useNexus();
  const liveTrading = liveAreas.trading || {};
  // CSS Grid-based Compact Mode State (Defaulted to ON)
  const [compactMode, setCompactMode] = useState<boolean>(true);

  // Master Operating State
  const [tradingStatus] = useState<any>({ status: 'UNKNOWN', mode: 'UNKNOWN' });
  const [killSwitchScope] = useState<KillSwitchScope>('NONE');

  // Domain Datasets
  const [strategies, setStrategies] = useState<StrategyItem[]>([]);
  const [paperPositions, setPaperPositions] = useState<PaperPosition[]>([]);
  const [paperOrders, setPaperOrders] = useState<PaperOrder[]>([]);
  const [signals, setSignals] = useState<TradingSignal[]>([]);
  const [watchlist, setWatchlist] = useState<any[]>([]);
  const [intelligence, setIntelligence] = useState<any[]>([]);
  const [riskLimits, setRiskLimits] = useState<any[]>([]);
  const [dataProviders, setDataProviders] = useState<any[]>([]);
  const [auditLog, setAuditLog] = useState<any[]>([]);
  const [pastBacktests, setPastBacktests] = useState<BacktestResultRecord[]>([]);

  // Tournament Data
  const [tournamentRound] = useState<TournamentRound | null>(null);
  const [tournamentEntries, setTournamentEntries] = useState<TournamentEntry[]>([]);

  const [activeTab, setActiveTab] = useState<TradingTab>('overview');
  const [selectedChartSymbol, setSelectedChartSymbol] = useState<string>('EUR/USD');
  const [showExecutiveBarOnChart, setShowExecutiveBarOnChart] = useState<boolean>(false);

  const handleOpenChartForSymbol = (symbol: string) => {
    setSelectedChartSymbol(symbol);
    setActiveTab('charts');
  };

  // Modals & Drawers
  const [isModeModalOpen, setIsModeModalOpen] = useState(false);
  const [isKillSwitchModalOpen, setIsKillSwitchModalOpen] = useState(false);
  const [isRadarModalOpen, setIsRadarModalOpen] = useState(false);
  const [isQuickChartModalOpen, setIsQuickChartModalOpen] = useState(false);
  const [isExecutiveSummaryOpen, setIsExecutiveSummaryOpen] = useState(false);
  const [isExecutiveSummaryModalOpen, setIsExecutiveSummaryModalOpen] = useState(false);
  const [selectedStrategyForDetail, setSelectedStrategyForDetail] = useState<StrategyItem | null>(null);
  const [backtestStrategyPreset, setBacktestStrategyPreset] = useState<StrategyItem | null>(null);

  // Supporting Backtest Report Modal
  const [isBacktestReportModalOpen, setIsBacktestReportModalOpen] = useState(false);
  const [selectedBacktestReportForModal, setSelectedBacktestReportForModal] = useState<BacktestResultRecord | null>(null);

  // Notification Toast
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showNotification = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 3500);
  };

  // HANDLERS: Open Supporting Backtest Report
  const handleOpenBacktestReport = (reportId: string, strategy?: StrategyItem) => {
    const found = pastBacktests.find(b => b.id === reportId || b.strategyId === strategy?.id);
    if (found) {
      setSelectedBacktestReportForModal(found);
      setIsBacktestReportModalOpen(true);
    } else if (pastBacktests.length > 0) {
      setSelectedBacktestReportForModal(pastBacktests[0]);
      setIsBacktestReportModalOpen(true);
    }
  };

  // HANDLERS: Operating Mode Change
  const handleApplyModeChange = (_newMode: TradingMode, _reason: string, _policy: string) => showNotification('Trading controls are not connected to a durable backend.');

  // HANDLERS: Kill Switch Toggle
  const handleApplyKillSwitch = (_newScope: KillSwitchScope, _reason: string) => showNotification('Trading controls are not connected to a durable backend.');

  // HANDLERS: Stage Promotion
  const handlePromoteStage = (_strategyId: string, _nextStage: StrategyStage) => showNotification('Strategy updates are unavailable until durable Trading actions are connected.');

  // HANDLER: Tournament Advance to Risk Review
  const handlePromoteToRiskReview = (_strategyId: string) => showNotification('Tournament actions are not connected to durable Trading state.');

  // HANDLERS: Close Position
  const handleClosePosition = (_positionId: string) => showNotification('Position actions are unavailable until durable Trading execution is connected.');

  // HANDLERS: Signal to Paper Order
  const handleCreatePaperOrderFromSignal = (_signal: TradingSignal) => showNotification('Paper order routing is unavailable.');

  const handleUpdateSignalStatus = (_signalId: string, _newStatus: SignalStatus) => showNotification('Signal updates are unavailable until durable Trading actions are connected.');

  const handleRunBacktestForStrategy = (strategy: StrategyItem) => {
    setBacktestStrategyPreset(strategy);
    setActiveTab('backtest');
    if (selectedStrategyForDetail) {
      setSelectedStrategyForDetail(null);
    }
  };

  const handleSaveBacktestResult = (result: BacktestResultRecord) => {
    setPastBacktests(prev => [result, ...prev]);
    showNotification(`Backtest ${result.id} artifacts persisted to audit ledger.`);
  };

  const handleUpdateRiskLimit = (id: string, newLimit: number) => {
    setRiskLimits(prev => prev.map(l => (l.id === id ? { ...l, limitValue: newLimit } : l)));
    showNotification(`Risk threshold for ${id} updated to ${newLimit}.`);
  };

  const isPaused = killSwitchScope !== 'NONE' || tradingStatus.status === 'Paused';

  return (
    <div className={`h-full max-h-screen min-h-0 w-full overflow-hidden flex flex-col ${compactMode ? 'gap-1' : 'gap-1.5'}`}>
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-16 right-6 z-50 animate-in slide-in-from-top duration-200">
          <div className="bg-slate-900 text-white px-3.5 py-2 rounded-xl shadow-xl flex items-center gap-2 border border-slate-700 text-xs font-bold">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span>{toastMessage}</span>
          </div>
        </div>
      )}

      {/* Clean Executive Header (Removed noisy multi-department summary banner) */}
      {activeTab === 'charts' && !showExecutiveBarOnChart && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5 flex items-center justify-between text-xs text-slate-300 shrink-0 shadow-2xs">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            <span className="font-semibold text-white text-xs">Dedicated Full-Viewport Chart Terminal</span>
          </div>
          <button
            type="button"
            onClick={() => setShowExecutiveBarOnChart(true)}
            className="text-[11px] text-blue-400 hover:text-blue-300 font-medium underline cursor-pointer"
          >
            Show Overview Header
          </button>
        </div>
      )}

      {/* TOP COMMAND CONSOLE HEADER */}
      <div className="bg-white rounded-xl border border-slate-200/90 shadow-2xs px-3 py-1.5 space-y-1 shrink-0">
        {/* ROW 1: Title, Mode, Inlined KPIs, Telemetry & Controls */}
        <div className="flex flex-wrap items-center justify-between gap-1.5">
          {/* Left Lockup */}
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 shrink-0">
              <ThreeDIcon name="trading-engine" size="sm" />
            </div>
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-xs font-black text-slate-900 tracking-tight">TRADING ENGINE</span>
              <span className="text-[9px] font-bold text-blue-700 bg-blue-50 px-1.5 py-0.2 rounded border border-blue-200">
                Quant Ops
              </span>

              {/* Status Pill: Reflects Feed Degradation (Binance L3 Latency) */}
              <span
                className="inline-flex items-center gap-1 px-1.5 py-0.2 rounded-full text-[9px] font-extrabold bg-amber-50 text-amber-800 border border-amber-300"
                title="Trading status from the Nexus read model."
              >
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                <span>{liveTrading.status || 'UNKNOWN'}</span>
              </span>

              {/* Mode Pill */}
              <button
                type="button"
                disabled
                onClick={() => setIsModeModalOpen(true)}
                className="inline-flex items-center gap-1 px-2 py-0.2 rounded-full text-[9px] font-extrabold bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-300 transition-colors cursor-pointer"
                title="Click to change operating mode with dual governance"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-blue-600" />
                <span>{liveTrading.mode || 'UNKNOWN'}</span>
              </button>
            </div>
          </div>

          {/* Middle: Integrated Compact KPI telemetry strip (Explicitly labeled as Simulated Paper Results) */}
          <div className="hidden xl:grid grid-cols-[repeat(auto-fit,minmax(115px,1fr))] gap-1 text-[11px] flex-1 max-w-4xl mx-1.5">
            <div className="px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between gap-1" title="Simulated Paper Equity">
              <span className="text-slate-400 font-medium">Paper Eq:</span>
              <span className="font-extrabold text-slate-900">{liveTrading.performance?.equity ?? 'Not connected'}</span>
            </div>
            <div className="px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between gap-1" title="Simulated Buying Power">
              <span className="text-slate-400 font-medium">Paper Pwr:</span>
              <span className="font-extrabold text-slate-800">{liveTrading.performance?.buying_power ?? 'Not connected'}</span>
            </div>
            <div className="px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between gap-1">
              <span className="text-slate-400 font-medium">Tournament:</span>
              <span className="font-bold text-slate-700">Not connected</span>
            </div>
            <div className="px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between gap-1" title="Open Simulated Positions">
              <span className="text-slate-400 font-medium">Paper Fills:</span>
              <span className="font-bold text-slate-800">{liveTrading.counts?.positions ?? 'UNKNOWN'} positions</span>
            </div>
            <div className="px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between gap-1">
              <span className="text-slate-400 font-medium">Signals:</span>
              <span className="font-bold text-slate-800">{liveTrading.counts?.signals ?? 'UNKNOWN'}</span>
            </div>
            <div className="px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between gap-1">
              <span className="text-slate-400 font-medium">Risk Gate:</span>
              <span className="font-bold text-slate-700">{liveTrading.performance?.risk_status ?? 'UNKNOWN'}</span>
            </div>
          </div>

          {/* Right Controls & Telemetry: Separate Feeds & Workers */}
          <div className="flex items-center gap-1.5 text-xs">
            {/* Feeds Status (Separated: Shows Alert for Binance L3) */}
            <div
              onClick={() => setActiveTab('infrastructure')}
              className="hidden md:flex items-center gap-1 text-[10px] text-amber-900 bg-amber-50 px-2 py-0.5 rounded-md border border-amber-200 cursor-pointer hover:bg-amber-100 transition-colors"
              title="Feed Alert: 3/4 Feeds Operational. Binance L3 latency is 142ms (> 50ms SLA). Click to view audit."
            >
              <Database className="w-3 h-3 text-amber-600" />
              <span>Feed health: {liveTrading.feed_status || 'UNKNOWN'}</span>
            </div>

            {/* Workers Status (Separated from Feeds) */}
            <div
              className="hidden lg:flex items-center gap-1 text-[10px] text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200"
              title="Worker health is not part of the Trading read model."
            >
              <Cpu className="w-3 h-3 text-emerald-600" />
              <span>Workers: UNKNOWN</span>
            </div>

            {/* Clickable Link / Button to Open Executive Visual Review Radar Modal */}
            <button
              type="button"
              disabled
              onClick={() => setIsRadarModalOpen(true)}
              className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[10px] font-black bg-cyan-950 text-cyan-300 border border-cyan-500/50 hover:bg-cyan-900/70 shadow-2xs transition-all cursor-pointer"
              title="Open Executive Visual Review Radar (Equity Sparkline, Asset Allocation, Worker Fleet)"
            >
              <Activity className="w-3 h-3 text-cyan-400 animate-pulse" />
              <span>Review Radar</span>
              <span className="px-1 py-0.2 rounded text-[7.5px] bg-cyan-500/20 text-cyan-300 font-mono">GRAPHS</span>
            </button>

            {/* Clickable Link / Button to Open Quick Recharts Dock Modal */}
            <button
              type="button"
              disabled
              onClick={() => setIsQuickChartModalOpen(true)}
              className="hidden sm:flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 transition-colors cursor-pointer"
              title="Open Floating Quick Recharts Dock with Live Brackets"
            >
              <BarChart2 className="w-3 h-3 text-cyan-600" />
              <span>Quick Dock</span>
            </button>

            {/* Compact Mode Toggle */}
            <button
              type="button"
              onClick={() => setCompactMode(prev => !prev)}
              className={`flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold border transition-all cursor-pointer ${
                compactMode
                  ? 'bg-blue-600 text-white border-blue-700 shadow-2xs'
                  : 'bg-slate-100 hover:bg-slate-200 text-slate-700 border-slate-200'
              }`}
              title="Toggle Compact Mode"
            >
              <Grid className="w-3 h-3" />
              <span>Compact: {compactMode ? 'ON' : 'OFF'}</span>
            </button>

            {/* Governance Mode Button */}
            <button
              type="button"
              disabled
              onClick={() => setIsModeModalOpen(true)}
              className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 text-[10px] font-bold border border-slate-200 transition-colors cursor-pointer"
            >
              <Sliders className="w-3 h-3" />
              <span>Mode</span>
            </button>

            {/* Kill Switch Button with Explanation */}
            <button
              type="button"
              disabled
              onClick={() => setIsKillSwitchModalOpen(true)}
              className={`flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold border transition-colors cursor-pointer ${
                isPaused
                  ? 'bg-amber-500 text-white border-amber-600 shadow-2xs'
                  : 'bg-rose-50 hover:bg-rose-100 text-rose-700 border-rose-200'
              }`}
              title="Emergency Kill Switch: Currently Disengaged. Click to configure pause scope (Inbound Signals, Paper Orders, or All Actions)."
            >
              <ShieldAlert className="w-3 h-3" />
              <span>Risk controls not connected</span>
            </button>
          </div>
        </div>

        {/* ROW 2: Integrated Workspace Navigation Tabs */}
        <div className="flex items-center gap-1 overflow-x-auto custom-scrollbar pt-1 border-t border-slate-100 text-[11px] font-bold text-slate-600">
          {/* Trading Overview (Primary R1 View) */}
          <button
            type="button"
            onClick={() => setActiveTab('overview')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'overview'
                ? 'bg-blue-600 text-white font-extrabold shadow-2xs'
                : 'hover:bg-slate-100 hover:text-slate-900 text-slate-800'
            }`}
          >
            <Target className="w-3 h-3" />
            <span>Trading Overview (R1)</span>
          </button>

          {/* Real Workflow (A-I) */}
          <button
            type="button"
            onClick={() => setActiveTab('workflow')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'workflow'
                ? 'bg-blue-600 text-white font-extrabold shadow-2xs'
                : 'hover:bg-slate-100 hover:text-slate-900 text-blue-900'
            }`}
          >
            <Activity className="w-3 h-3 text-cyan-400" />
            <span>Workflow &amp; Lifecycle (A-I)</span>
          </button>

          {/* Live Charts & Trade Replay (DVR) */}
          <button
            type="button"
            onClick={() => setActiveTab('charts')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'charts'
                ? 'bg-blue-600 text-white font-extrabold shadow-2xs'
                : 'hover:bg-slate-100 hover:text-slate-900 text-cyan-900 font-extrabold'
            }`}
          >
            <BarChart2 className="w-3 h-3 text-cyan-500" />
            <span>Live Chart &amp; Replay (DVR)</span>
            <span className="px-1 py-0.2 rounded text-[8px] font-black bg-cyan-100 text-cyan-800">
              SL / TP
            </span>
          </button>

          {/* Executive Radar Dedicated Tab */}
          <button
            type="button"
            onClick={() => setActiveTab('radar')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'radar'
                ? 'bg-cyan-600 text-white font-extrabold shadow-2xs'
                : 'hover:bg-slate-100 hover:text-slate-900 text-cyan-900'
            }`}
          >
            <Activity className="w-3 h-3 text-cyan-500" />
            <span>Executive Radar</span>
            <span className="px-1 py-0.2 rounded text-[8px] font-black bg-cyan-100 text-cyan-800">RADAR</span>
          </button>

          {/* Pipeline */}
          <button
            type="button"
            onClick={() => setActiveTab('pipeline')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'pipeline'
                ? 'bg-blue-600 text-white font-extrabold shadow-2xs'
                : 'hover:bg-slate-100 hover:text-slate-900'
            }`}
          >
            <Layers className="w-3 h-3" />
            <span>Strategy Pipeline ({strategies.length})</span>
          </button>

          {/* Tournament (Requested Tab) */}
          <button
            type="button"
            onClick={() => setActiveTab('tournament')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'tournament'
                ? 'bg-amber-600 text-white font-extrabold shadow-2xs'
                : 'hover:bg-slate-100 hover:text-slate-900 text-amber-900'
            }`}
          >
            <Trophy className="w-3 h-3 text-amber-500" />
            <span>Tournament ({tournamentEntries.length})</span>
            <span className="px-1 py-0.2 rounded text-[8px] font-black bg-amber-100 text-amber-800">NOT CONNECTED</span>
          </button>

          {/* Paper Trading */}
          <button
            type="button"
            onClick={() => setActiveTab('paper')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'paper'
                ? 'bg-blue-600 text-white font-extrabold shadow-2xs'
                : 'hover:bg-slate-100 hover:text-slate-900'
            }`}
          >
            <DollarSign className="w-3 h-3" />
            <span>Paper Trading ({paperPositions.length})</span>
            <span className="px-1 py-0.2 rounded text-[8px] font-black bg-blue-100 text-blue-700">SIM</span>
          </button>

          {/* Signals */}
          <button
            type="button"
            onClick={() => setActiveTab('signals')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'signals'
                ? 'bg-blue-600 text-white font-extrabold shadow-2xs'
                : 'hover:bg-slate-100 hover:text-slate-900'
            }`}
          >
            <Radio className="w-3 h-3" />
            <span>Signals ({signals.length})</span>
          </button>

          {/* Backtest Center */}
          <button
            type="button"
            onClick={() => setActiveTab('backtest')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'backtest'
                ? 'bg-blue-600 text-white font-extrabold shadow-2xs'
                : 'hover:bg-slate-100 hover:text-slate-900'
            }`}
          >
            <Play className="w-3 h-3" />
            <span>Backtest Center</span>
          </button>

          {/* Watchlist */}
          <button
            type="button"
            onClick={() => setActiveTab('monitor')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'monitor'
                ? 'bg-blue-600 text-white font-extrabold shadow-2xs'
                : 'hover:bg-slate-100 hover:text-slate-900'
            }`}
          >
            <Activity className="w-3 h-3" />
            <span>Watchlist ({watchlist.length})</span>
          </button>

          {/* Market Intel */}
          <button
            type="button"
            onClick={() => setActiveTab('intelligence')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'intelligence'
                ? 'bg-blue-600 text-white font-extrabold shadow-2xs'
                : 'hover:bg-slate-100 hover:text-slate-900'
            }`}
          >
            <Sparkles className="w-3 h-3" />
            <span>Market Intel ({intelligence.length})</span>
          </button>

          {/* Risk Center */}
          <button
            type="button"
            onClick={() => setActiveTab('risk')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'risk'
                ? 'bg-blue-600 text-white font-extrabold shadow-2xs'
                : 'hover:bg-slate-100 hover:text-slate-900'
            }`}
          >
            <ShieldCheck className="w-3 h-3" />
            <span>Risk Center</span>
          </button>

          {/* Performance */}
          <button
            type="button"
            onClick={() => setActiveTab('analytics')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'analytics'
                ? 'bg-blue-600 text-white font-extrabold shadow-2xs'
                : 'hover:bg-slate-100 hover:text-slate-900'
            }`}
          >
            <BarChart2 className="w-3 h-3" />
            <span>Performance</span>
          </button>

          {/* Parameter Sensitivity Heatmap */}
          <button
            type="button"
            onClick={() => setActiveTab('sensitivity')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'sensitivity'
                ? 'bg-blue-600 text-white font-extrabold shadow-2xs'
                : 'hover:bg-slate-100 hover:text-slate-900 text-blue-900'
            }`}
          >
            <Layers className="w-3 h-3 text-blue-500" />
            <span>Sensitivity Matrix</span>
            <span className="px-1 py-0.2 rounded text-[8px] font-black bg-blue-100 text-blue-800">2D</span>
          </button>

          {/* Execution Quality & TCA */}
          <button
            type="button"
            onClick={() => setActiveTab('execution_audit')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'execution_audit'
                ? 'bg-amber-600 text-white font-extrabold shadow-2xs'
                : 'hover:bg-slate-100 hover:text-slate-900 text-amber-900'
            }`}
          >
            <Zap className="w-3 h-3 text-amber-500" />
            <span>Execution &amp; TCA</span>
            <span className="px-1 py-0.2 rounded text-[8px] font-black bg-amber-100 text-amber-800">SLIPPAGE</span>
          </button>

          {/* Post-Trade Scorecard & MAE/MFE */}
          <button
            type="button"
            onClick={() => setActiveTab('scorecard')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'scorecard'
                ? 'bg-emerald-600 text-white font-extrabold shadow-2xs'
                : 'hover:bg-slate-100 hover:text-slate-900 text-emerald-900'
            }`}
          >
            <Award className="w-3 h-3 text-emerald-500" />
            <span>Trade Post-Mortem</span>
            <span className="px-1 py-0.2 rounded text-[8px] font-black bg-emerald-100 text-emerald-800">MAE/MFE</span>
          </button>

          {/* Trading Alpha Review */}
          <button
            type="button"
            onClick={() => setActiveTab('alpha')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'alpha'
                ? 'bg-purple-600 text-white font-extrabold shadow-2xs'
                : 'hover:bg-slate-100 hover:text-slate-900'
            }`}
          >
            <Sparkles className="w-3 h-3 text-purple-600" />
            <span>Trading Alpha Review</span>
          </button>

          {/* Infrastructure */}
          <button
            type="button"
            onClick={() => setActiveTab('infrastructure')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'infrastructure'
                ? 'bg-blue-600 text-white font-extrabold shadow-2xs'
                : 'hover:bg-slate-100 hover:text-slate-900'
            }`}
          >
            <Database className="w-3 h-3" />
            <span>Infrastructure & Feeds</span>
          </button>
        </div>
      </div>

      {/* ACTIVE WORKSPACE VIEW: live read-model records only */}
      <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
        {activeTab === 'overview' ? (
          <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-1 space-y-3">
            <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs">
              <div className="flex items-center justify-between gap-2 pb-2 border-b border-slate-100">
                <h2 className="text-sm font-semibold text-slate-900">Durable Trading Read Model</h2>
                <TruthBadge truth={liveTrading.mode ? 'PAPER' : 'NOT_CONNECTED'} />
              </div>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 pt-3 text-xs">
                <div><div className="text-slate-500">Mode</div><div className="font-semibold text-slate-900">{liveTrading.mode || 'UNKNOWN'}</div></div>
                <div><div className="text-slate-500">Broker</div><div className="font-semibold text-slate-900">{liveTrading.broker || 'UNKNOWN'}</div></div>
                <div><div className="text-slate-500">Live trading</div><div className="font-semibold text-slate-900">{liveTrading.liveTradingEnabled === false ? 'DISABLED' : liveTrading.liveTradingEnabled === true ? 'ENABLED' : 'UNKNOWN'}</div></div>
                <div><div className="text-slate-500">Truth class</div><div className="font-semibold text-slate-900">{liveTrading.truthClass || 'UNKNOWN'}</div></div>
              </div>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs">
                <h3 className="text-sm font-semibold text-slate-900 mb-2">Durable Strategies</h3>
                {Array.isArray(liveTrading.strategies) && liveTrading.strategies.length ? liveTrading.strategies.map((item: any, i: number) => <div key={item.id || item.strategy_id || i} className="py-2 border-t border-slate-100 text-xs text-slate-700">{item.name || item.strategy || item.id || JSON.stringify(item)}</div>) : <UnavailableState>Strategy records are not connected.</UnavailableState>}
              </div>
              <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs">
                <h3 className="text-sm font-semibold text-slate-900 mb-2">Durable Trading Results</h3>
                {Array.isArray(liveTrading.trades) && liveTrading.trades.length ? liveTrading.trades.slice(0, 10).map((item: any, i: number) => <div key={item.id || item.trade_id || i} className="py-2 border-t border-slate-100 text-xs text-slate-700">{item.symbol || item.instrument || 'UNKNOWN'} · {item.status || item.result || 'UNKNOWN'} · {item.timestamp || item.created_at || 'UNKNOWN'}</div>) : <UnavailableState>Trade and performance records are not connected.</UnavailableState>}
              </div>
            </div>
            <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs">
              <h3 className="text-sm font-semibold text-slate-900 mb-2">Live Performance Snapshot</h3>
              {liveTrading.performance ? <pre className="text-xs text-slate-700 whitespace-pre-wrap break-words">{JSON.stringify(liveTrading.performance, null, 2)}</pre> : <UnavailableState>Performance metrics are not connected.</UnavailableState>}
            </div>
          </div>
        ) : <div className="p-1"><UnavailableState>This Trading view has no connected durable data source.</UnavailableState></div>}
      </div>

      {/* MODALS */}
      <StrategyDetailWorkspace
        strategy={selectedStrategyForDetail}
        onClose={() => setSelectedStrategyForDetail(null)}
        onRunBacktest={handleRunBacktestForStrategy}
        onPromoteStage={handlePromoteStage}
        onOpenBacktestReport={handleOpenBacktestReport}
      />

      <BacktestReportModal
        isOpen={isBacktestReportModalOpen}
        onClose={() => setIsBacktestReportModalOpen(false)}
        report={selectedBacktestReportForModal}
        strategy={strategies.find(s => s.id === selectedBacktestReportForModal?.strategyId)}
        onAdvanceToRiskReview={handlePromoteToRiskReview}
      />

      <TradingModeGovernanceModal
        isOpen={isModeModalOpen}
        onClose={() => setIsModeModalOpen(false)}
        currentMode={tradingStatus.mode}
        modeChangedBy={tradingStatus.modeChangedBy}
        modeChangedAt={tradingStatus.modeChangedAt}
        modeChangeReason={tradingStatus.modeChangeReason}
        approvalStatus={tradingStatus.approvalStatus}
        riskPolicy={tradingStatus.riskPolicy}
        allowedProviders={tradingStatus.allowedProviders}
        allowedAccounts={tradingStatus.allowedAccounts}
        onApplyModeChange={handleApplyModeChange}
      />

      <KillSwitchModal
        isOpen={isKillSwitchModalOpen}
        onClose={() => setIsKillSwitchModalOpen(false)}
        currentScope={killSwitchScope}
        onApplyKillSwitch={handleApplyKillSwitch}
      />

    </div>
  );
};
