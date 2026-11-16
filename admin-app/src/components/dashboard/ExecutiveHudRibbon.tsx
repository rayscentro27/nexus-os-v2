import React from 'react';
import {
  ShieldAlert,
  Activity,
  Lock,
  Cpu,
  Zap,
  Server,
  ArrowRight,
  TrendingUp,
  Radio,
  CheckCircle2,
  AlertTriangle,
  Layers,
  ChevronRight
} from 'lucide-react';
import { useNexus } from '../../context/NexusContext';

interface ExecutiveHudRibbonProps {
  onOpenKillSwitch?: () => void;
  onOpenNeedsRay?: () => void;
  onOpenWorkflow?: () => void;
  onOpenAgentHealth?: () => void;
  pendingApprovalsCount?: number;
}

export const ExecutiveHudRibbon: React.FC<ExecutiveHudRibbonProps> = ({
  onOpenKillSwitch,
  onOpenNeedsRay,
  onOpenWorkflow,
  onOpenAgentHealth,
  pendingApprovalsCount = 3
}) => {
  const { setCurrentPage, needsRayDecisions, setIsNeedsRayDrawerOpen } = useNexus();

  const unresolvedDecisions = needsRayDecisions.filter(d => d.status === 'PENDING').length;

  return (
    <div className="w-full bg-slate-950 text-slate-100 rounded-xl border border-slate-800 shadow-md p-2.5 flex flex-col gap-2 shrink-0 select-none">
      {/* Top Header / Status Line */}
      <div className="flex items-center justify-between gap-2 border-b border-slate-800/80 pb-1.5 flex-wrap">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span className="text-[10px] font-mono font-black tracking-widest text-slate-300 uppercase">
            RAY EXECUTIVE HUD // LIVE TELEMETRY
          </span>
          <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-cyan-300 border border-slate-700">
            CLOCK 12ms · SYNCHRONIZED
          </span>
        </div>

        <div className="flex items-center gap-2 text-[9px] font-mono">
          {onOpenAgentHealth && (
            <button
              type="button"
              onClick={onOpenAgentHealth}
              className="px-2 py-0.5 rounded bg-slate-900 hover:bg-slate-800 text-cyan-300 border border-slate-700 flex items-center gap-1 cursor-pointer transition-colors"
              title="Click to view full AI Agent Fleet Health & Latency Monitor"
            >
              <Radio className="w-2.5 h-2.5 text-emerald-400 animate-pulse" />
              <span>Fleet: 10 Agents (11ms · 99.96%)</span>
            </button>
          )}
          <span className="text-slate-400 hidden sm:inline">Operating Authority:</span>
          <span className="text-emerald-400 font-bold bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-800/80">
            AUTONOMOUS UNPROMPTED (7 DEPTS)
          </span>
          <span className="text-slate-400 hidden md:inline">·</span>
          <span className="text-rose-400 font-bold bg-rose-950/80 px-2 py-0.5 rounded border border-rose-800/80 flex items-center gap-1">
            <Lock className="w-2.5 h-2.5 text-rose-400" />
            LIVE CAPITAL: LOCKED
          </span>
        </div>
      </div>

      {/* 4 Telemetry Invariant Pillars */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
        {/* 1. TRADING GUARDRAILS */}
        <div className="bg-slate-900/90 rounded-lg p-2 border border-slate-800 hover:border-slate-700 transition-colors flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[9px] font-mono uppercase text-slate-400 font-bold tracking-wider flex items-center gap-1">
              <Lock className="w-3 h-3 text-rose-400" />
              Trading Guardrails
            </span>
            <span className="text-[8px] font-black font-mono text-rose-300 bg-rose-950/90 px-1 rounded border border-rose-800">
              STRICT HARD-LIMIT
            </span>
          </div>

          <div className="mt-1 flex items-baseline justify-between">
            <div className="flex items-baseline gap-1.5">
              <span className="text-sm font-black text-white font-mono tabular-nums">OFF</span>
              <span className="text-[9px] font-mono text-slate-400 font-medium">(Paper Only)</span>
            </div>
            <span className="text-[10px] font-mono tabular-nums text-emerald-400 font-bold">$0.00 At Risk</span>
          </div>

          <div className="mt-1 pt-1 border-t border-slate-800/80 flex items-center justify-between text-[8.5px] text-slate-400 font-mono">
            <span>OANDA / Webull Sim</span>
            <button
              type="button"
              onClick={() => setCurrentPage('trading-engine')}
              className="text-cyan-400 hover:text-cyan-300 hover:underline cursor-pointer flex items-center gap-0.5"
            >
              <span>Sandbox</span>
              <ChevronRight className="w-2.5 h-2.5" />
            </button>
          </div>
        </div>

        {/* 2. AUTONOMY & DRIFT */}
        <div className="bg-slate-900/90 rounded-lg p-2 border border-slate-800 hover:border-slate-700 transition-colors flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[9px] font-mono uppercase text-slate-400 font-bold tracking-wider flex items-center gap-1">
              <Activity className="w-3 h-3 text-cyan-400" />
              Autonomy Health
            </span>
            <span className="text-[8px] font-black font-mono text-emerald-300 bg-emerald-950/90 px-1 rounded border border-emerald-800">
              UNPROMPTED
            </span>
          </div>

          <div className="mt-1 flex items-baseline justify-between">
            <div className="flex items-baseline gap-1.5">
              <span className="text-sm font-black text-cyan-300 font-mono tabular-nums">98.4%</span>
              <span className="text-[9px] font-mono text-slate-400">Score</span>
            </div>
            <span className="text-[10px] font-mono tabular-nums text-emerald-400 font-semibold">Drift: 0.00%</span>
          </div>

          <div className="mt-1 pt-1 border-t border-slate-800/80 flex items-center justify-between text-[8.5px] text-slate-400 font-mono">
            <span>10 AI Agents (11ms ping)</span>
            {onOpenAgentHealth ? (
              <button
                type="button"
                onClick={onOpenAgentHealth}
                className="text-cyan-400 hover:text-cyan-300 hover:underline cursor-pointer flex items-center gap-0.5 font-bold"
              >
                <span>Fleet Telemetry</span>
                <ChevronRight className="w-2.5 h-2.5" />
              </button>
            ) : (
              <span className="text-slate-300">0 Stale Leases</span>
            )}
          </div>
        </div>

        {/* 3. KILL-SWITCH & BREAKER */}
        <div className="bg-slate-900/90 rounded-lg p-2 border border-slate-800 hover:border-slate-700 transition-colors flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[9px] font-mono uppercase text-slate-400 font-bold tracking-wider flex items-center gap-1">
              <ShieldAlert className="w-3 h-3 text-emerald-400" />
              Kill-Switch Ready
            </span>
            <span className="text-[8px] font-black font-mono text-emerald-300 bg-emerald-950/90 px-1 rounded border border-emerald-800">
              ARMED 0ms
            </span>
          </div>

          <div className="mt-1 flex items-baseline justify-between">
            <div className="flex items-baseline gap-1.5">
              <span className="text-sm font-black text-emerald-400 font-mono">STANDBY</span>
              <span className="text-[9px] font-mono text-slate-400">Scope: NONE</span>
            </div>
            <button
              type="button"
              onClick={onOpenKillSwitch}
              className="text-[9px] font-bold font-mono px-1.5 py-0.5 rounded bg-rose-950 text-rose-300 hover:bg-rose-900 border border-rose-800 transition-colors cursor-pointer"
            >
              Test Breaker
            </button>
          </div>

          <div className="mt-1 pt-1 border-t border-slate-800/80 flex items-center justify-between text-[8.5px] text-slate-400 font-mono">
            <span>Trip Threshold: 2% DD</span>
            <span className="text-slate-400">Sub-ms Isolation</span>
          </div>
        </div>

        {/* 4. EXECUTIVE ATTENTION GATE */}
        <div className="bg-gradient-to-br from-slate-900 to-indigo-950/40 rounded-lg p-2 border border-indigo-900/60 hover:border-indigo-700/80 transition-colors flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[9px] font-mono uppercase text-indigo-300 font-bold tracking-wider flex items-center gap-1">
              <Zap className="w-3 h-3 text-amber-400" />
              What Needs Ray
            </span>
            <span className="text-[8px] font-black font-mono text-amber-300 bg-amber-950/90 px-1 rounded border border-amber-800">
              {unresolvedDecisions} PENDING
            </span>
          </div>

          <div className="mt-1 flex items-baseline justify-between">
            <div className="flex items-baseline gap-1.5">
              <span className="text-sm font-black text-amber-300 font-mono tabular-nums">{unresolvedDecisions}</span>
              <span className="text-[9px] font-mono text-slate-400">Decisions</span>
            </div>
            <button
              type="button"
              onClick={() => setIsNeedsRayDrawerOpen(true)}
              className="text-[9px] font-bold font-mono px-2 py-0.5 rounded bg-amber-500 hover:bg-amber-400 text-slate-950 transition-all cursor-pointer shadow-xs active:scale-95 flex items-center gap-1"
            >
              <span>Review</span>
              <ArrowRight className="w-2.5 h-2.5" />
            </button>
          </div>

          <div className="mt-1 pt-1 border-t border-slate-800/80 flex items-center justify-between text-[8.5px] text-slate-400 font-mono">
            <span className="truncate">Client Portal &amp; Clyde</span>
            {onOpenWorkflow && (
              <button
                type="button"
                onClick={onOpenWorkflow}
                className="text-indigo-300 hover:text-white cursor-pointer hover:underline"
              >
                Gate 06 →
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
