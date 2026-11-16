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
  PersistentLiveMarketChart 
} from '../components/trading/PersistentLiveMarketChart';
import { 
  TradingExecutiveVisualReviewBar 
} from '../components/trading/TradingExecutiveVisualReviewBar';
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
import { useNexus } from '../context/NexusContext';

import {
  INITIAL_TRADING_STATUS,
  INITIAL_STRATEGIES,
  INITIAL_PAPER_POSITIONS,
  INITIAL_PAPER_ORDERS,
  INITIAL_SIGNALS,
  INITIAL_WATCHLIST,
  INITIAL_MARKET_INTELLIGENCE,
  INITIAL_RISK_LIMITS,
  INITIAL_DATA_PROVIDERS,
  INITIAL_AUDIT_LOG,
  INITIAL_PAST_BACKTESTS,
  CURRENT_TOURNAMENT_ROUND,
  INITIAL_TOURNAMENT_ENTRIES,
  EXECUTION_RECEIPTS_R1,
  RECONCILIATION_EVENTS_R1
} from '../data/tradingEngineData';

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
  const { navigateToObject, approvals } = useNexus();
  // CSS Grid-based Compact Mode State (Defaulted to ON)
  const [compactMode, setCompactMode] = useState<boolean>(true);

  // Master Operating State
  const [tradingStatus, setTradingStatus] = useState(INITIAL_TRADING_STATUS);
  const [killSwitchScope, setKillSwitchScope] = useState<KillSwitchScope>('NONE');

  // Domain Datasets
  const [strategies, setStrategies] = useState<StrategyItem[]>(INITIAL_STRATEGIES);
  const [paperPositions, setPaperPositions] = useState<PaperPosition[]>(INITIAL_PAPER_POSITIONS);
  const [paperOrders, setPaperOrders] = useState<PaperOrder[]>(INITIAL_PAPER_ORDERS);
  const [signals, setSignals] = useState<TradingSignal[]>(INITIAL_SIGNALS);
  const [watchlist, setWatchlist] = useState(INITIAL_WATCHLIST);
  const [intelligence, setIntelligence] = useState(INITIAL_MARKET_INTELLIGENCE);
  const [riskLimits, setRiskLimits] = useState(INITIAL_RISK_LIMITS);
  const [dataProviders, setDataProviders] = useState(INITIAL_DATA_PROVIDERS);
  const [auditLog, setAuditLog] = useState(INITIAL_AUDIT_LOG);
  const [pastBacktests, setPastBacktests] = useState(INITIAL_PAST_BACKTESTS);

  // Tournament Data
  const [tournamentRound, setTournamentRound] = useState<TournamentRound>(CURRENT_TOURNAMENT_ROUND);
  const [tournamentEntries, setTournamentEntries] = useState<TournamentEntry[]>(INITIAL_TOURNAMENT_ENTRIES);

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
  const [selectedBacktestReportForModal, setSelectedBacktestReportForModal] = useState<BacktestResultRecord | null>(INITIAL_PAST_BACKTESTS[0] || null);

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
  const handleApplyModeChange = (newMode: TradingMode, reason: string, policy: string) => {
    const timestamp = 'Today, ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' EST';
    setTradingStatus(prev => ({
      ...prev,
      mode: newMode,
      modeChangedBy: 'Alex Chen (Principal Quant)',
      modeChangedAt: timestamp,
      modeChangeReason: reason,
      riskPolicy: policy,
    }));

    const auditRecord = {
      id: `aud-${Date.now().toString().slice(-4)}`,
      timestamp,
      actor: 'Alex Chen (Principal Quant)',
      action: 'OPERATING_MODE_CHANGE',
      scope: 'Global Engine Governance',
      previousState: tradingStatus.mode,
      newState: newMode,
      reason,
      governanceHash: `sha256:${Math.random().toString(36).substring(2, 14)}...`
    };

    setAuditLog(prev => [auditRecord, ...prev]);
    showNotification(`Operating Mode updated to ${newMode}.`);
  };

  // HANDLERS: Kill Switch Toggle
  const handleApplyKillSwitch = (newScope: KillSwitchScope, reason: string) => {
    const timestamp = 'Today, ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' EST';
    setKillSwitchScope(newScope);

    setTradingStatus(prev => ({
      ...prev,
      status: newScope === 'NONE' ? 'Degraded' : 'Paused',
    }));

    const auditRecord = {
      id: `aud-${Date.now().toString().slice(-4)}`,
      timestamp,
      actor: 'Alex Chen (Principal Quant)',
      action: newScope === 'NONE' ? 'KILL_SWITCH_DISENGAGED' : 'KILL_SWITCH_ENGAGED',
      scope: `Emergency Pause (${newScope})`,
      previousState: killSwitchScope,
      newState: newScope,
      reason,
      governanceHash: `sha256:${Math.random().toString(36).substring(2, 14)}...`
    };

    setAuditLog(prev => [auditRecord, ...prev]);
    showNotification(`Kill Switch: ${newScope === 'NONE' ? 'Disengaged (Normal Operations)' : `Engaged (${newScope})`}.`);
  };

  // HANDLERS: Stage Promotion
  const handlePromoteStage = (strategyId: string, nextStage: StrategyStage) => {
    const strat = strategies.find(s => s.id === strategyId);
    if (!strat) return;

    setStrategies(prev => prev.map(s => (s.id === strategyId ? { ...s, stage: nextStage } : s)));

    if (selectedStrategyForDetail && selectedStrategyForDetail.id === strategyId) {
      setSelectedStrategyForDetail(prev => (prev ? { ...prev, stage: nextStage } : null));
    }

    const timestamp = 'Today, ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' EST';
    const auditRecord = {
      id: `aud-${Date.now().toString().slice(-4)}`,
      timestamp,
      actor: 'Alex Chen (Principal Quant)',
      action: 'STRATEGY_STAGE_TRANSITION',
      scope: `${strat.name} (${strat.id})`,
      previousState: strat.stage,
      newState: nextStage,
      reason: `Promoted strategy through governance pipeline to ${nextStage}`,
      governanceHash: `sha256:${Math.random().toString(36).substring(2, 14)}...`
    };

    setAuditLog(prev => [auditRecord, ...prev]);
    showNotification(`Strategy ${strat.name} promoted to ${nextStage}.`);
  };

  // HANDLER: Tournament Advance to Risk Review
  const handlePromoteToRiskReview = (strategyId: string) => {
    handlePromoteStage(strategyId, 'RISK_REVIEW');
    showNotification(`Strategy promoted from Tournament to Risk Review. Formal risk sign-off required before simulated paper trading.`);
  };

  // HANDLERS: Close Position
  const handleClosePosition = (positionId: string) => {
    const pos = paperPositions.find(p => p.id === positionId);
    if (!pos) return;

    setPaperPositions(prev => prev.filter(p => p.id !== positionId));

    const newOrder: PaperOrder = {
      id: `ord-sim-${Math.floor(1000 + Math.random() * 9000)}`,
      symbol: pos.symbol,
      side: pos.side === 'LONG' ? 'SELL' : 'BUY',
      type: 'MARKET',
      quantity: pos.quantity,
      submittedAt: 'Today, ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' EST',
      filledAt: 'Today, ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' EST',
      fillPrice: pos.currentPrice,
      status: 'FILLED',
      strategyName: pos.strategyName,
      reason: `Manual administrative close of simulated paper position (PnL: $${pos.unrealizedPnl.toFixed(2)})`
    };

    setPaperOrders(prev => [newOrder, ...prev]);
    showNotification(`Closed simulated paper position on ${pos.symbol} at $${pos.currentPrice.toFixed(2)}.`);
  };

  // HANDLERS: Signal to Paper Order
  const handleCreatePaperOrderFromSignal = (signal: TradingSignal) => {
    if (killSwitchScope === 'PAUSE_PAPER_ORDERS' || killSwitchScope === 'PAUSE_ALL_ACTIONS') {
      showNotification('Action Blocked: Paper order routing is currently paused by Kill-Switch control.');
      return;
    }

    const newOrder: PaperOrder = {
      id: `ord-sim-${Math.floor(1000 + Math.random() * 9000)}`,
      symbol: signal.symbol,
      side: signal.direction === 'LONG' ? 'BUY' : 'SELL',
      type: 'MARKET',
      quantity: 100,
      submittedAt: 'Today, ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' EST',
      filledAt: 'Today, ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' EST',
      fillPrice: signal.proposedEntry,
      status: 'FILLED',
      strategyName: signal.strategyName,
      reason: `Converted from Signal #${signal.id} (${signal.direction} on ${signal.symbol}) · Checked Risk Limits`
    };

    setPaperOrders(prev => [newOrder, ...prev]);
    setSignals(prev => prev.map(s => (s.id === signal.id ? { 
      ...s, 
      status: 'PAPER_ORDER_CREATED',
      resultingPaperAction: {
        actionType: 'ROUTED_PAPER_ORDER',
        paperOrderId: newOrder.id,
        details: `Simulated paper market fill executed for 100 shares @ $${signal.proposedEntry.toFixed(2)}.`,
        timestamp: 'Just now'
      }
    } : s)));
    showNotification(`Simulated paper order created for ${signal.symbol} at $${signal.proposedEntry.toFixed(2)}.`);
  };

  const handleUpdateSignalStatus = (signalId: string, newStatus: SignalStatus) => {
    setSignals(prev => prev.map(s => (s.id === signalId ? { ...s, status: newStatus } : s)));
    showNotification(`Signal #${signalId} marked as ${newStatus}.`);
  };

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
                title="Status: Degraded due to Binance Microstructure L3 latency (142ms > 50ms SLA). Workers remain healthy."
              >
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
                <span>{tradingStatus.status} (Feed Alert)</span>
              </span>

              {/* Mode Pill */}
              <button
                type="button"
                onClick={() => setIsModeModalOpen(true)}
                className="inline-flex items-center gap-1 px-2 py-0.2 rounded-full text-[9px] font-extrabold bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-300 transition-colors cursor-pointer"
                title="Click to change operating mode with dual governance"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-blue-600" />
                <span>{tradingStatus.mode}</span>
              </button>
            </div>
          </div>

          {/* Middle: Integrated Compact KPI telemetry strip (Explicitly labeled as Simulated Paper Results) */}
          <div className="hidden xl:grid grid-cols-[repeat(auto-fit,minmax(115px,1fr))] gap-1 text-[11px] flex-1 max-w-4xl mx-1.5">
            <div className="px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between gap-1" title="Simulated Paper Equity">
              <span className="text-slate-400 font-medium">Paper Eq:</span>
              <span className="font-extrabold text-slate-900">$512.5k <span className="text-emerald-600 font-bold text-[10px]">(+0.8%)</span></span>
            </div>
            <div className="px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between gap-1" title="Simulated Buying Power">
              <span className="text-slate-400 font-medium">Paper Pwr:</span>
              <span className="font-extrabold text-slate-800">$425.8k</span>
            </div>
            <div className="px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between gap-1">
              <span className="text-slate-400 font-medium">Tournament:</span>
              <span className="font-bold text-amber-700">{tournamentRound.advancedCount} Adv <span className="text-slate-400 font-normal">/ {tournamentRound.totalParticipants}</span></span>
            </div>
            <div className="px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between gap-1" title="Open Simulated Positions">
              <span className="text-slate-400 font-medium">Paper Fills:</span>
              <span className="font-bold text-slate-800">{paperPositions.length} pos <span className="text-emerald-600 text-[10px]">(+$4.2k)</span></span>
            </div>
            <div className="px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between gap-1">
              <span className="text-slate-400 font-medium">Signals:</span>
              <span className="font-bold text-slate-800">{signals.filter(s => s.status !== 'EXPIRED' && s.status !== 'REJECTED').length} active</span>
            </div>
            <div className="px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between gap-1">
              <span className="text-slate-400 font-medium">Risk Gate:</span>
              <span className="font-bold text-emerald-700">Safe <span className="text-slate-400 font-normal text-[10px]">(DD 1.4% / 4%)</span></span>
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
              <span>3/4 Feeds (1 Alert)</span>
            </div>

            {/* Workers Status (Separated from Feeds) */}
            <div
              className="hidden lg:flex items-center gap-1 text-[10px] text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200"
              title="Worker Fleet: 4/4 Workers Operational (A100 Compute Cluster, Alpaca Sim, Risk Guard, Tick Ingest)"
            >
              <Cpu className="w-3 h-3 text-emerald-600" />
              <span>4 Workers (100%)</span>
            </div>

            {/* Clickable Link / Button to Open Executive Visual Review Radar Modal */}
            <button
              type="button"
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
              onClick={() => setIsModeModalOpen(true)}
              className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 text-[10px] font-bold border border-slate-200 transition-colors cursor-pointer"
            >
              <Sliders className="w-3 h-3" />
              <span>Mode</span>
            </button>

            {/* Kill Switch Button with Explanation */}
            <button
              type="button"
              onClick={() => setIsKillSwitchModalOpen(true)}
              className={`flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold border transition-colors cursor-pointer ${
                isPaused
                  ? 'bg-amber-500 text-white border-amber-600 shadow-2xs'
                  : 'bg-rose-50 hover:bg-rose-100 text-rose-700 border-rose-200'
              }`}
              title="Emergency Kill Switch: Currently Disengaged. Click to configure pause scope (Inbound Signals, Paper Orders, or All Actions)."
            >
              <ShieldAlert className="w-3 h-3" />
              <span>{isPaused ? 'Paused' : 'Kill Switch (Ready)'}</span>
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
            <span className="px-1 py-0.2 rounded text-[8px] font-black bg-amber-100 text-amber-800">ROUND 4</span>
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

      {/* ACTIVE WORKSPACE VIEW */}
      <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
        {activeTab === 'overview' && (
          <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-1 space-y-3">
            {/* Top R1 Status Strip */}
            <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-semibold text-slate-900">
                    Trading R1 Core · Wick Sequence Breakout v1 (EUR_USD · H1)
                  </span>
                  <TruthBadge truth="PAPER" label="OANDA Practice · Live Disabled" />
                  <TruthBadge truth="VERIFIED" label="Deterministic Parity" />
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  What strategies, signals, trades, risks, and results currently exist? OANDA Practice paper execution active; real-capital routing locked OFF.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    const r1 = strategies.find(s => s.id === 'strat-r1-wick') || strategies[0];
                    setSelectedStrategyForDetail(r1);
                  }}
                  className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium cursor-pointer"
                >
                  Inspect R1 Strategy
                </button>
                <button
                  type="button"
                  onClick={() => handleOpenChartForSymbol('EUR/USD')}
                  className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium cursor-pointer"
                >
                  Open EUR/USD Chart
                </button>
              </div>
            </div>

            {/* 4 Executive Trading Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="bg-white rounded-xl border border-slate-200/80 p-3.5 shadow-2xs">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-medium text-slate-500">Paper Equity (OANDA)</span>
                  <TruthBadge truth="PAPER" />
                </div>
                <div className="text-xl font-semibold text-slate-900 mt-1 tabular-nums">$512,500</div>
                <div className="text-[11px] text-emerald-700 mt-0.5">+$4,210.50 Paper P&amp;L ($0.00 Live Risk)</div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200/80 p-3.5 shadow-2xs">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-medium text-slate-500">Certified R1 Performance</span>
                  <TruthBadge truth="PAPER" />
                </div>
                <div className="text-xl font-semibold text-slate-900 mt-1 tabular-nums">1.91 Sharpe</div>
                <div className="text-[11px] text-slate-500 mt-0.5">PF 1.94 · Win Rate 58.6% · 914 trades</div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200/80 p-3.5 shadow-2xs">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-medium text-slate-500">Positions &amp; Signals</span>
                  <TruthBadge truth="PAPER" />
                </div>
                <div className="text-xl font-semibold text-slate-900 mt-1 tabular-nums">
                  {paperPositions.length} Open / {signals.filter(s => s.status !== 'EXPIRED' && s.status !== 'REJECTED').length} Signals
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5">All fills routed through Risk Guard</div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200/80 p-3.5 shadow-2xs">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-medium text-slate-500">Risk &amp; Kill Switch</span>
                  <TruthBadge truth="VERIFIED" />
                </div>
                <div className="text-xl font-semibold text-emerald-700 mt-1 tabular-nums">
                  {isPaused ? 'PAUSED' : '1.4% / 4.0% DD'}
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5">Kill switch {killSwitchScope === 'NONE' ? 'Disengaged' : killSwitchScope}</div>
              </div>
            </div>

            {/* Execution Receipts & Reconciliation Events */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs space-y-2.5">
                <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-900">Execution Receipts (OANDA Practice)</h3>
                    <p className="text-[11px] text-slate-500">Deterministic paper fill receipts and slippage verification</p>
                  </div>
                  <TruthBadge truth="PAPER" />
                </div>
                <div className="space-y-2">
                  {EXECUTION_RECEIPTS_R1.map(r => (
                    <div key={r.id} className="p-2.5 rounded-lg bg-slate-50 border border-slate-100 flex items-center justify-between text-xs">
                      <div>
                        <div className="font-semibold text-slate-900">
                          {r.symbol} ({r.timeframe}) · {r.side} {r.units} @ {r.fillPrice}
                        </div>
                        <div className="text-[11px] text-slate-500 font-mono">
                          {r.orderId} · Slippage {r.slippagePips} · {r.receiptHash}
                        </div>
                      </div>
                      <div className="text-right shrink-0">
                        <TruthBadge truth={r.truthClass} />
                        <div className="text-[10px] text-slate-400 mt-0.5">{r.timestamp}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs space-y-2.5">
                <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-900">Reconciliation Events</h3>
                    <p className="text-[11px] text-slate-500">Broker parity &amp; live-trading lock checks</p>
                  </div>
                  <TruthBadge truth="VERIFIED" />
                </div>
                <div className="space-y-2">
                  {RECONCILIATION_EVENTS_R1.map(ev => (
                    <div key={ev.id} className="p-2.5 rounded-lg bg-slate-50 border border-slate-100 flex items-center justify-between text-xs">
                      <div>
                        <div className="font-semibold text-slate-900">{ev.check}</div>
                        <div className="text-[11px] text-slate-500">
                          Local {ev.localPositions} / Broker {ev.brokerPositions} · {ev.variance}
                        </div>
                      </div>
                      <div className="text-right shrink-0">
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          {ev.status}
                        </span>
                        <div className="text-[10px] text-slate-400 mt-0.5">{ev.timestamp}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Linked Pending Trading Approval (Synced to Approvals Desk) */}
            {approvals.some(a => a.department === 'Trading' && a.status === 'PENDING') && (
              <div className="bg-amber-50/70 border border-amber-200 rounded-xl p-3.5 flex flex-wrap items-center justify-between gap-3 text-xs">
                <div>
                  <span className="font-semibold text-amber-950">Pending Trading Budget Gate: </span>
                  <span className="text-amber-900">
                    Optional Direct FIX Gateway test budget ($45) waiting for Ray review — deterministic OANDA Practice remains active regardless.
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => navigateToObject('approvals', 'apr_trading_fix_budget', 'approval')}
                  className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-medium cursor-pointer"
                >
                  Open in Approvals
                </button>
              </div>
            )}
          </div>
        )}
        {activeTab === 'radar' && (
          <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-1.5">
            <TradingExecutiveVisualReviewBar
              activeTab={activeTab}
              onSelectTab={setActiveTab}
              openPositionsCount={paperPositions.length}
              activeSignalsCount={signals.filter(s => s.status !== 'EXPIRED' && s.status !== 'REJECTED').length}
              currentDrawdown={1.4}
              maxDrawdownLimit={4.0}
              dayPnl={4280.50}
              totalEquity={512480.00}
              isModal={false}
            />
          </div>
        )}

        {activeTab === 'workflow' && (
          <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-1">
            <TradingWorkflowHub onOpenChart={handleOpenChartForSymbol} />
          </div>
        )}

        {activeTab === 'charts' && (
          <div className="flex-1 min-h-0 overflow-hidden p-1">
            <LiveChartAndReplayTerminal
              initialSymbol={selectedChartSymbol}
              compactMode={compactMode}
              onNavigateTab={(tab) => setActiveTab(tab as any)}
              isDedicatedSection={true}
            />
          </div>
        )}

        {activeTab === 'pipeline' && (
          <StrategyPipelineView
            strategies={strategies}
            onSelectStrategy={strat => setSelectedStrategyForDetail(strat)}
            onRunBacktestForStrategy={strat => handleRunBacktestForStrategy(strat)}
            onPromoteStage={handlePromoteStage}
            onOpenBacktestReport={handleOpenBacktestReport}
            compactMode={compactMode}
          />
        )}

        {activeTab === 'tournament' && (
          <TradingTournamentView
            round={tournamentRound}
            entries={tournamentEntries}
            strategies={strategies}
            onSelectStrategy={strat => setSelectedStrategyForDetail(strat)}
            onOpenBacktestReport={handleOpenBacktestReport}
            onPromoteToRiskReview={handlePromoteToRiskReview}
            compactMode={compactMode}
          />
        )}

        {activeTab === 'paper' && (
          <PaperTradingView
            positions={paperPositions}
            orders={paperOrders}
            onClosePosition={handleClosePosition}
            onOpenChart={handleOpenChartForSymbol}
            compactMode={compactMode}
          />
        )}

        {activeTab === 'signals' && (
          <SignalCenterView
            signals={signals}
            onCreatePaperOrder={handleCreatePaperOrderFromSignal}
            onUpdateSignalStatus={handleUpdateSignalStatus}
            onOpenChart={handleOpenChartForSymbol}
            compactMode={compactMode}
          />
        )}

        {activeTab === 'backtest' && (
          <BacktestCenterView
            strategies={strategies}
            pastBacktests={pastBacktests}
            onSaveBacktestResult={handleSaveBacktestResult}
            selectedStrategyPreset={backtestStrategyPreset}
            compactMode={compactMode}
          />
        )}

        {activeTab === 'monitor' && (
          <MarketMonitorView
            watchlist={watchlist}
            onOpenChart={handleOpenChartForSymbol}
            compactMode={compactMode}
          />
        )}

        {activeTab === 'intelligence' && (
          <MarketIntelligenceView
            intelligence={intelligence}
            compactMode={compactMode}
          />
        )}

        {activeTab === 'risk' && (
          <RiskCenterView
            riskLimits={riskLimits}
            killSwitchScope={killSwitchScope}
            onOpenKillSwitchModal={() => setIsKillSwitchModalOpen(true)}
            onUpdateLimit={handleUpdateRiskLimit}
            compactMode={compactMode}
          />
        )}

        {activeTab === 'analytics' && (
          <PerformanceAnalyticsView
            strategies={strategies}
            compactMode={compactMode}
          />
        )}

        {activeTab === 'sensitivity' && (
          <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-1">
            <ParameterSensitivityHeatmap
              initialSymbol={selectedChartSymbol}
              onSelectStrategy={handleOpenChartForSymbol}
              compactMode={compactMode}
            />
          </div>
        )}

        {activeTab === 'execution_audit' && (
          <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-1">
            <ExecutionQualityInspector
              compactMode={compactMode}
            />
          </div>
        )}

        {activeTab === 'scorecard' && (
          <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-1">
            <PostTradeScorecardView
              compactMode={compactMode}
              onOpenChart={handleOpenChartForSymbol}
            />
          </div>
        )}

        {activeTab === 'alpha' && (
          <AlphaReviewWorkspace
            strategies={strategies}
            onSelectStrategy={strat => setSelectedStrategyForDetail(strat)}
            compactMode={compactMode}
          />
        )}

        {activeTab === 'infrastructure' && (
          <ProviderHealthAuditView
            providers={dataProviders}
            auditLog={auditLog}
            compactMode={compactMode}
          />
        )}
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

      {/* EXECUTIVE VISUAL REVIEW RADAR MODAL OVERLAY */}
      {isRadarModalOpen && (
        <TradingExecutiveVisualReviewBar
          activeTab={activeTab}
          onSelectTab={(tab) => {
            setActiveTab(tab);
            setIsRadarModalOpen(false);
          }}
          openPositionsCount={paperPositions.length}
          activeSignalsCount={signals.filter(s => s.status !== 'EXPIRED' && s.status !== 'REJECTED').length}
          currentDrawdown={1.4}
          maxDrawdownLimit={4.0}
          dayPnl={4280.50}
          totalEquity={512480.00}
          isModal={true}
          onClose={() => setIsRadarModalOpen(false)}
        />
      )}

      {/* QUICK RECHARTS LIVE TICKER DOCK MODAL */}
      {isQuickChartModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl max-w-5xl w-full max-h-[92vh] overflow-y-auto custom-scrollbar flex flex-col text-white">
            <div className="px-4 py-2.5 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <BarChart2 className="w-4 h-4 text-cyan-400" />
                <span className="font-black text-white text-xs tracking-wide">
                  QUICK RECHARTS LIVE TICKER DOCK
                </span>
                <span className="px-1.5 py-0.2 rounded text-[8.5px] bg-blue-950 text-blue-300 border border-blue-800 font-mono font-bold">
                  ACTIVE BRACKETS &amp; SL/TP
                </span>
              </div>
              <button
                type="button"
                onClick={() => setIsQuickChartModalOpen(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 cursor-pointer transition-colors"
                title="Close Quick Dock"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <PersistentLiveMarketChart
              activePositions={paperPositions}
              selectedSymbol={selectedChartSymbol}
              onSelectSymbol={(sym) => setSelectedChartSymbol(sym)}
              onClosePosition={handleClosePosition}
              onOpenFullCharts={() => {
                setIsQuickChartModalOpen(false);
                setActiveTab('charts');
              }}
              defaultExpanded={true}
            />
          </div>
        </div>
      )}
    </div>
  );
};
