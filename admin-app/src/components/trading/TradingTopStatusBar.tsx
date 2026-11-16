import React from 'react';
import { 
  ShieldAlert, 
  Activity, 
  PauseCircle, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  Cpu, 
  Database,
  ExternalLink,
  Sliders,
  DollarSign
} from 'lucide-react';
import { TradingEngineStatus, TradingMode, KillSwitchScope } from '../../types';

interface TradingTopStatusBarProps {
  status: TradingEngineStatus;
  mode: TradingMode;
  killSwitchScope: KillSwitchScope;
  marketsOpenCount: number;
  marketsTotalCount: number;
  activeStrategiesCount: number;
  strategiesUnderReviewCount: number;
  activePaperPositionsCount: number;
  openSignalsCount: number;
  pendingApprovalsCount: number;
  dataProviderStatus: string;
  lastTradingCycle: string;
  lastMarketRefresh: string;
  estimatedDailyComputeCost: string;
  onOpenModeModal: () => void;
  onOpenKillSwitchModal: () => void;
}

export const TradingTopStatusBar: React.FC<TradingTopStatusBarProps> = ({
  status,
  mode,
  killSwitchScope,
  marketsOpenCount,
  marketsTotalCount,
  activeStrategiesCount,
  strategiesUnderReviewCount,
  activePaperPositionsCount,
  openSignalsCount,
  pendingApprovalsCount,
  dataProviderStatus,
  lastTradingCycle,
  lastMarketRefresh,
  estimatedDailyComputeCost,
  onOpenModeModal,
  onOpenKillSwitchModal,
}) => {
  const isPaused = killSwitchScope !== 'NONE' || status === 'Paused';

  // Mode badge formatting
  const getModeBadge = (currentMode: TradingMode) => {
    switch (currentMode) {
      case 'RESEARCH_ONLY':
        return { label: 'RESEARCH ONLY', bg: 'bg-indigo-50 border-indigo-200 text-indigo-700', dot: 'bg-indigo-500' };
      case 'BACKTEST_ONLY':
        return { label: 'BACKTEST ONLY', bg: 'bg-blue-50 border-blue-200 text-blue-700', dot: 'bg-blue-500' };
      case 'PAPER_TRADING':
        return { label: 'PAPER TRADING (DEFAULT)', bg: 'bg-emerald-50 border-emerald-300 text-emerald-800', dot: 'bg-emerald-500' };
      case 'LIVE_TRADING_DISABLED':
        return { label: 'LIVE TRADING DISABLED (GOVERNANCE LOCK)', bg: 'bg-slate-100 border-slate-300 text-slate-700', dot: 'bg-slate-500' };
      case 'LIVE_TRADING_APPROVAL_REQUIRED':
        return { label: 'LIVE APPROVAL REQUIRED', bg: 'bg-amber-50 border-amber-300 text-amber-800', dot: 'bg-amber-500' };
      default:
        return { label: currentMode, bg: 'bg-slate-100 border-slate-200 text-slate-700', dot: 'bg-slate-400' };
    }
  };

  const modeBadge = getModeBadge(mode);

  return (
    <div className="space-y-3">
      {/* Kill-switch Active Warning Banner if engaged */}
      {isPaused && (
        <div className="p-3.5 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-amber-500 text-white flex items-center justify-center shrink-0 shadow-xs">
              <ShieldAlert className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <div className="text-sm font-bold text-amber-950 flex items-center gap-2">
                <span>SYSTEM PAUSE CONTROL ENGAGED: {killSwitchScope.replace(/_/g, ' ')}</span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-amber-200 text-amber-900 uppercase">Audit Logged</span>
              </div>
              <p className="text-xs text-amber-800/90 font-medium">
                Trading activities are bounded under governance policy. Simulated executions or signals are paused.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onOpenKillSwitchModal}
            className="px-3 py-1.5 rounded-xl bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold transition-all shadow-xs cursor-pointer"
          >
            Manage Pause State
          </button>
        </div>
      )}

      {/* Main Top Status Container */}
      <div className="bg-white rounded-2xl border border-slate-200/90 p-4 shadow-[0_2px_10px_rgba(15,23,42,0.03)] space-y-4">
        {/* Top Control Bar: Status + Mode + Governance Buttons */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 pb-3 border-b border-slate-100">
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            {/* System Status Pill */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-800">
              <span className="text-slate-500 font-medium">System Health:</span>
              <span className="flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full ${status === 'Healthy' ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`} />
                <span className="font-bold text-slate-900">{status}</span>
              </span>
            </div>

            {/* Operating Mode Pill with Visual Radar */}
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-semibold ${modeBadge.bg}`}>
              <span className="opacity-80 font-medium">Operating Mode:</span>
              <span className="flex items-center gap-1.5 font-bold tracking-tight">
                <span className={`w-2 h-2 rounded-full ${modeBadge.dot}`} />
                <span>{modeBadge.label}</span>
              </span>
            </div>

            {/* Markets Status */}
            <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 text-xs font-medium text-slate-700">
              <Activity className="w-3.5 h-3.5 text-blue-600" />
              <span>Markets Open:</span>
              <span className="font-bold text-slate-900">{marketsOpenCount}/{marketsTotalCount}</span>
              <span className="text-[10px] text-emerald-600 font-bold bg-emerald-50 px-1.5 py-0.5 rounded-md border border-emerald-200">US + Crypto 24/7</span>
            </div>
          </div>

          {/* Action Buttons: Operating Mode Governance & Kill-Switch */}
          <div className="flex items-center gap-2 self-end lg:self-auto">
            <button
              type="button"
              onClick={onOpenModeModal}
              className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-bold transition-all border border-slate-200 cursor-pointer"
            >
              <Sliders className="w-3.5 h-3.5 text-slate-600" />
              <span>Operating Mode Governance</span>
            </button>

            <button
              type="button"
              onClick={onOpenKillSwitchModal}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all border cursor-pointer ${
                isPaused
                  ? 'bg-amber-500 text-white border-amber-600 shadow-xs'
                  : 'bg-rose-50 hover:bg-rose-100 text-rose-700 border-rose-200'
              }`}
            >
              <ShieldAlert className="w-3.5 h-3.5" />
              <span>{isPaused ? 'Pause Switch Active' : 'Kill Switch / Pause'}</span>
            </button>
          </div>
        </div>

        {/* Real-Time Operational Telemetry Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {/* Active Strategies */}
          <div className="p-3 rounded-xl bg-slate-50/80 border border-slate-100 flex flex-col justify-between">
            <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Active Strategies</div>
            <div className="mt-1 flex items-baseline gap-1.5">
              <span className="text-xl font-extrabold text-slate-900">{activeStrategiesCount}</span>
              <span className="text-[11px] text-slate-500 font-semibold">in rotation</span>
            </div>
            <div className="mt-1 text-[10px] text-blue-600 font-bold flex items-center gap-1">
              <span>{strategiesUnderReviewCount} under review</span>
            </div>
          </div>

          {/* Open Paper Positions */}
          <div className="p-3 rounded-xl bg-slate-50/80 border border-slate-100 flex flex-col justify-between">
            <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider flex items-center justify-between">
              <span>Paper Positions</span>
              <span className="px-1.5 py-0.2 rounded text-[9px] font-black bg-blue-100 text-blue-700">SIM</span>
            </div>
            <div className="mt-1 flex items-baseline gap-1.5">
              <span className="text-xl font-extrabold text-slate-900">{activePaperPositionsCount}</span>
              <span className="text-[11px] text-emerald-600 font-bold">+$4,280 PnL</span>
            </div>
            <div className="mt-1 text-[10px] text-slate-500 font-medium">
              3 Longs • 2 Shorts
            </div>
          </div>

          {/* Open Signals */}
          <div className="p-3 rounded-xl bg-slate-50/80 border border-slate-100 flex flex-col justify-between">
            <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Open Signals</div>
            <div className="mt-1 flex items-baseline gap-1.5">
              <span className="text-xl font-extrabold text-slate-900">{openSignalsCount}</span>
              <span className="text-[11px] text-indigo-600 font-bold">evaluated</span>
            </div>
            <div className="mt-1 text-[10px] text-slate-500 font-medium">
              Avg confidence 84%
            </div>
          </div>

          {/* Pending Approvals */}
          <div className="p-3 rounded-xl bg-slate-50/80 border border-slate-100 flex flex-col justify-between">
            <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Pending Approvals</div>
            <div className="mt-1 flex items-baseline gap-1.5">
              <span className="text-xl font-extrabold text-amber-600">{pendingApprovalsCount}</span>
              <span className="text-[11px] text-slate-500 font-semibold">governance</span>
            </div>
            <div className="mt-1 text-[10px] text-amber-700 font-bold">
              Review required
            </div>
          </div>

          {/* Data Providers & Latency */}
          <div className="p-3 rounded-xl bg-slate-50/80 border border-slate-100 flex flex-col justify-between">
            <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1">
              <Database className="w-3 h-3 text-slate-400" />
              <span>Data Feeds</span>
            </div>
            <div className="mt-1 flex items-baseline gap-1.5">
              <span className="text-sm font-extrabold text-slate-900">4/4 Feeds</span>
              <span className="text-[10px] text-emerald-600 font-bold">Healthy</span>
            </div>
            <div className="mt-1 text-[10px] text-slate-500 font-medium truncate">
              {lastMarketRefresh} • 38ms avg
            </div>
          </div>

          {/* Compute & API Cost */}
          <div className="p-3 rounded-xl bg-slate-50/80 border border-slate-100 flex flex-col justify-between">
            <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1">
              <Cpu className="w-3 h-3 text-slate-400" />
              <span>Compute Cost</span>
            </div>
            <div className="mt-1 flex items-baseline gap-1.5">
              <span className="text-sm font-extrabold text-slate-900">{estimatedDailyComputeCost.split(' ')[0]}</span>
              <span className="text-[10px] text-slate-500 font-semibold">/ day</span>
            </div>
            <div className="mt-1 text-[10px] text-slate-500 font-medium truncate">
              Cycle: {lastTradingCycle.split(' ')[0]}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
