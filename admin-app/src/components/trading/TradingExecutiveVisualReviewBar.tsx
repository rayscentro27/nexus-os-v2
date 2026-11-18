import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  TrendingUp,
  TrendingDown,
  ShieldCheck,
  ShieldAlert,
  Activity,
  BarChart2,
  DollarSign,
  Radio,
  Layers,
  Cpu,
  Database,
  Sparkles,
  Zap,
  Award,
  ChevronDown,
  ChevronUp,
  Maximize2,
  Eye,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ArrowUpRight,
  ArrowDownRight,
  X
} from 'lucide-react';
import { TradingTab } from '../../pages/TradingEnginePage';

export interface TradingExecutiveVisualReviewBarProps {
  activeTab?: TradingTab;
  onSelectTab?: (tab: TradingTab) => void;
  openPositionsCount: number;
  activeSignalsCount: number;
  currentDrawdown?: number;
  maxDrawdownLimit?: number;
  dayPnl?: number;
  totalEquity?: number;
  isModal?: boolean;
  onClose?: () => void;
}

export const TradingExecutiveVisualReviewBar: React.FC<TradingExecutiveVisualReviewBarProps> = ({
  activeTab,
  onSelectTab,
  openPositionsCount,
  activeSignalsCount,
  currentDrawdown = 1.4,
  maxDrawdownLimit = 4.0,
  dayPnl = 4280.50,
  totalEquity = 512480.00,
  isModal = false,
  onClose
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(true);

  // Close on Escape key if in modal mode
  useEffect(() => {
    if (!isModal || !onClose) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isModal, onClose]);

  // Sparkline data for today's equity progression
  const equitySparkline = [508200, 508900, 509400, 509100, 510200, 511000, 510800, 511900, 512480];
  const minEquity = Math.min(...equitySparkline);
  const maxEquity = Math.max(...equitySparkline);
  const range = maxEquity - minEquity || 1;

  // SVG points for sparkline
  const sparklinePoints = equitySparkline
    .map((val, idx) => {
      const x = (idx / (equitySparkline.length - 1)) * 140;
      const y = 36 - ((val - minEquity) / range) * 28;
      return `${x},${y}`;
    })
    .join(' ');

  const drawdownPctOfLimit = Math.min(100, (currentDrawdown / maxDrawdownLimit) * 100);

  const mainContent = (
    <div className="space-y-3">
      {/* 4 Core Visual Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 text-xs font-mono">
        {/* CARD 1: REAL-TIME EQUITY & PnL SPARKLINE */}
        <div 
          onClick={() => {
            onSelectTab?.('paper');
            onClose?.();
          }}
          className="bg-slate-950/90 border border-slate-800 rounded-xl p-3 space-y-2 cursor-pointer hover:border-cyan-500/50 transition-all shadow-inner group"
        >
          <div className="flex items-center justify-between text-[10px] text-slate-400">
            <span className="flex items-center gap-1.5 uppercase font-bold text-cyan-300">
              <DollarSign className="w-3.5 h-3.5 text-emerald-400" />
              <span>Equity &amp; Day PnL</span>
            </span>
            <span className="text-[9px] bg-blue-950 text-blue-300 px-1.5 py-0.2 rounded border border-blue-800 font-bold">
              PAPER SIM
            </span>
          </div>

          <div className="flex items-baseline justify-between">
            <div>
              <div className="text-lg font-black text-white">
                ${totalEquity.toLocaleString('en-US', { minimumFractionDigits: 2 })}
              </div>
              <div className="text-emerald-400 text-xs font-bold flex items-center gap-0.5 mt-0.5">
                <ArrowUpRight className="w-3.5 h-3.5" />
                <span>+${dayPnl.toLocaleString('en-US', { minimumFractionDigits: 2 })} (+0.84%)</span>
              </div>
            </div>

            {/* SVG Micro Sparkline */}
            <div className="w-32 h-10 relative">
              <svg viewBox="0 0 140 40" className="w-full h-full overflow-visible">
                <defs>
                  <linearGradient id="eqSparkGradModal" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#10b981" stopOpacity={0.4} />
                    <stop offset="100%" stopColor="#10b981" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <polygon
                  points={`0,40 ${sparklinePoints} 140,40`}
                  fill="url(#eqSparkGradModal)"
                />
                <polyline
                  points={sparklinePoints}
                  fill="none"
                  stroke="#10b981"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <circle 
                  cx="140" 
                  cy={36 - ((equitySparkline[equitySparkline.length - 1] - minEquity) / range) * 28} 
                  r="3.5" 
                  fill="#10b981" 
                  className="animate-pulse"
                />
              </svg>
            </div>
          </div>

          <div className="flex items-center justify-between text-[9px] text-slate-500 pt-1 border-t border-slate-900">
            <span>Buying Power: <strong className="text-slate-300">$425.8k</strong></span>
            <span className="text-cyan-400 group-hover:underline font-bold">Inspect Paper Sim →</span>
          </div>
        </div>

        {/* CARD 2: ASSET EXPOSURE & ACTIVE POSITIONS */}
        <div 
          onClick={() => {
            onSelectTab?.('paper');
            onClose?.();
          }}
          className="bg-slate-950/90 border border-slate-800 rounded-xl p-3 space-y-2 cursor-pointer hover:border-blue-500/50 transition-all shadow-inner group"
        >
          <div className="flex items-center justify-between text-[10px] text-slate-400">
            <span className="flex items-center gap-1.5 uppercase font-bold text-blue-300">
              <Layers className="w-3.5 h-3.5 text-blue-400" />
              <span>Asset Allocation</span>
            </span>
            <span className="text-[10px] font-bold text-slate-300">
              {openPositionsCount} Positions
            </span>
          </div>

          {/* Segmented Exposure Visual Bar */}
          <div className="space-y-1.5 pt-1">
            <div className="h-3 w-full bg-slate-900 rounded-full overflow-hidden flex border border-slate-800">
              <div className="bg-blue-500 h-full" style={{ width: '45%' }} title="Forex: 45% ($230k notional)" />
              <div className="bg-indigo-500 h-full" style={{ width: '35%' }} title="Equities: 35% ($180k notional)" />
              <div className="bg-purple-500 h-full" style={{ width: '20%' }} title="Crypto: 20% ($102k notional)" />
            </div>

            <div className="flex items-center justify-between text-[9.5px] text-slate-400">
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                <span>Forex 45%</span>
              </span>
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                <span>Equities 35%</span>
              </span>
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-purple-500" />
                <span>Crypto 20%</span>
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between text-[9px] text-slate-500 pt-1 border-t border-slate-900">
            <span>Gross Leverage: <strong className="text-slate-300">1.82x</strong></span>
            <span className="text-blue-400 group-hover:underline font-bold">Portfolio Details →</span>
          </div>
        </div>

        {/* CARD 3: RISK CEILING & DRAWDOWN THERMOMETER */}
        <div 
          onClick={() => {
            onSelectTab?.('risk');
            onClose?.();
          }}
          className="bg-slate-950/90 border border-slate-800 rounded-xl p-3 space-y-2 cursor-pointer hover:border-emerald-500/50 transition-all shadow-inner group"
        >
          <div className="flex items-center justify-between text-[10px] text-slate-400">
            <span className="flex items-center gap-1.5 uppercase font-bold text-emerald-300">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Risk Governance</span>
            </span>
            <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-bold">
              GATE: SAFE
            </span>
          </div>

          {/* Drawdown Visual Progress Bar */}
          <div className="space-y-1.5 pt-1">
            <div className="flex items-baseline justify-between text-[11px]">
              <span className="text-slate-300 font-bold">Drawdown: <strong className="text-emerald-400">{currentDrawdown}%</strong></span>
              <span className="text-slate-500 text-[10px]">Kill Switch: {maxDrawdownLimit}%</span>
            </div>

            <div className="h-2.5 w-full bg-slate-900 rounded-full overflow-hidden relative border border-slate-800">
              <div 
                className="h-full bg-gradient-to-r from-emerald-500 via-amber-500 to-rose-500 rounded-full"
                style={{ width: `${drawdownPctOfLimit}%` }}
              />
            </div>
          </div>

          <div className="flex items-center justify-between text-[9px] text-slate-500 pt-1 border-t border-slate-900">
            <span>1-Day VaR (99%): <strong className="text-slate-300">$3,450</strong></span>
            <span className="text-emerald-400 group-hover:underline font-bold">Risk Controls →</span>
          </div>
        </div>

        {/* CARD 4: ENGINE WORKER FLEET & FEED HEALTH RADAR */}
        <div 
          onClick={() => {
            onSelectTab?.('infrastructure');
            onClose?.();
          }}
          className="bg-slate-950/90 border border-slate-800 rounded-xl p-3 space-y-2 cursor-pointer hover:border-purple-500/50 transition-all shadow-inner group"
        >
          <div className="flex items-center justify-between text-[10px] text-slate-400">
            <span className="flex items-center gap-1.5 uppercase font-bold text-purple-300">
              <Cpu className="w-3.5 h-3.5 text-purple-400" />
              <span>Worker Fleet &amp; Feeds</span>
            </span>
            <span className="text-[9px] text-emerald-400 font-bold">
              4/4 OPERATIONAL
            </span>
          </div>

          {/* 4 Animated Radar Pulse Nodes */}
          <div className="grid grid-cols-2 gap-1.5 text-[9px] pt-0.5">
            <div className="bg-slate-900/90 px-2 py-1 rounded border border-slate-800 flex items-center justify-between">
              <span className="text-slate-400">A100 Compute:</span>
              <span className="flex items-center gap-1 text-emerald-400 font-bold">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                <span>98%</span>
              </span>
            </div>
            <div className="bg-slate-900/90 px-2 py-1 rounded border border-slate-800 flex items-center justify-between">
              <span className="text-slate-400">Tick Ingest:</span>
              <span className="text-cyan-400 font-bold">12ms</span>
            </div>
            <div className="bg-slate-900/90 px-2 py-1 rounded border border-slate-800 flex items-center justify-between">
              <span className="text-slate-400">Binance L3:</span>
              <span className="text-amber-400 font-bold">142ms (!)</span>
            </div>
            <div className="bg-slate-900/90 px-2 py-1 rounded border border-slate-800 flex items-center justify-between">
              <span className="text-slate-400">Risk Guard:</span>
              <span className="text-emerald-400 font-bold">0.4ms</span>
            </div>
          </div>

          <div className="flex items-center justify-between text-[9px] text-slate-500 pt-1 border-t border-slate-900">
            <span>Active Signals: <strong className="text-slate-300">{activeSignalsCount}</strong></span>
            <span className="text-purple-400 group-hover:underline font-bold">Feed Audit →</span>
          </div>
        </div>
      </div>

      {/* Quick Launchpad to Workspaces */}
      <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-2.5 flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
        <span className="text-slate-400 text-[10px] font-bold uppercase">
          Jump to Specialized Quantitative Workspaces:
        </span>
        <div className="flex items-center gap-1.5 flex-wrap">
          <button
            type="button"
            onClick={() => {
              onSelectTab?.('charts');
              onClose?.();
            }}
            className="px-2.5 py-1 rounded-lg bg-blue-600/80 hover:bg-blue-600 text-white font-bold flex items-center gap-1 cursor-pointer transition-colors text-[11px]"
          >
            <BarChart2 className="w-3.5 h-3.5 text-cyan-300" />
            <span>Live Chart &amp; DVR</span>
          </button>
          <button
            type="button"
            onClick={() => {
              onSelectTab?.('sensitivity');
              onClose?.();
            }}
            className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-blue-300 border border-blue-500/30 font-bold flex items-center gap-1 cursor-pointer transition-colors text-[11px]"
          >
            <Layers className="w-3.5 h-3.5 text-blue-400" />
            <span>Sensitivity Matrix</span>
          </button>
          <button
            type="button"
            onClick={() => {
              onSelectTab?.('execution_audit');
              onClose?.();
            }}
            className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-amber-300 border border-amber-500/30 font-bold flex items-center gap-1 cursor-pointer transition-colors text-[11px]"
          >
            <Zap className="w-3.5 h-3.5 text-amber-400" />
            <span>TCA Slippage Audit</span>
          </button>
          <button
            type="button"
            onClick={() => {
              onSelectTab?.('scorecard');
              onClose?.();
            }}
            className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-emerald-300 border border-emerald-500/30 font-bold flex items-center gap-1 cursor-pointer transition-colors text-[11px]"
          >
            <Award className="w-3.5 h-3.5 text-emerald-400" />
            <span>MAE/MFE Scorecard</span>
          </button>
        </div>
      </div>
    </div>
  );

  // If Modal mode: Render in a backdrop overlay
  if (isModal) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: -8 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: -8 }}
          transition={{ duration: 0.18, ease: 'easeOut' }}
          className="bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl max-w-6xl w-full max-h-[92vh] overflow-y-auto custom-scrollbar flex flex-col text-white"
        >
          {/* Modal Header */}
          <div className="px-4 py-3 bg-slate-950/90 border-b border-slate-800 flex items-center justify-between sticky top-0 z-10 backdrop-blur-sm">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan-400 animate-pulse" />
              <span className="font-black text-white text-sm tracking-wide">
                EXECUTIVE VISUAL REVIEW RADAR
              </span>
              <span className="px-2 py-0.5 rounded text-[9px] font-mono bg-cyan-950 text-cyan-300 border border-cyan-800 font-bold">
                TELEMETRY &amp; GRAPHS
              </span>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-[10px] text-slate-400 font-mono hidden sm:inline">Press Esc or Close</span>
              {onClose && (
                <button
                  type="button"
                  onClick={onClose}
                  className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 cursor-pointer transition-colors"
                  title="Close Radar"
                >
                  <X className="w-5 h-5" />
                </button>
              )}
            </div>
          </div>

          {/* Modal Body */}
          <div className="p-4">
            {mainContent}
          </div>
        </motion.div>
      </div>
    );
  }

  // Standalone Full-Page View (e.g. for activeTab === 'radar')
  return (
    <div className="bg-slate-900 rounded-2xl border border-slate-800 p-4 text-white shadow-xl space-y-3">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800 font-mono">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-cyan-400 animate-pulse" />
          <h2 className="text-sm font-black tracking-wide text-white uppercase">
            Executive Visual Review Radar
          </h2>
          <span className="text-[10px] text-slate-400 hidden sm:inline">
            • Real-time equity progression, risk gates, and worker fleet status
          </span>
        </div>
      </div>
      {mainContent}
    </div>
  );
};
