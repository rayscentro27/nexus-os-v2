import React from 'react';
import {
  CheckCircle2,
  DollarSign,
  ShieldAlert,
  AlertTriangle,
  RotateCw,
  ArrowUpRight,
  ShieldCheck,
  TrendingUp,
  Layers,
  Sparkles,
  Lock,
  ChevronRight,
  Zap,
  Activity,
  ArrowRight
} from 'lucide-react';
import { DataTruthClass } from '../../data/executiveCommandData';
import { useNexus } from '../../context/NexusContext';

export interface SummaryMetricItem {
  label: string;
  value: string | number;
  sub?: string;
  isPaper?: boolean;
}

export interface ExecutiveSummaryBarProps {
  departmentName: string;
  departmentKicker?: string;
  truthClass?: DataTruthClass;

  // Universal 4 operational counts:
  operationalCounts?: {
    workingOn: number | string;
    completedToday: number | string;
    needsRay: number | string;
    attention: number | string;
  };

  // Universal 3 questions:
  threeQuestions?: {
    mostImportantThing: string;
    whatNexusIsDoing: string;
    whatHappensNext: string;
  };

  // 1. SUCCESS / GREEN
  success: {
    highlight: string; // e.g. "26 Findings Verified"
    headline: string; // e.g. "Completed Work & Passed Tests"
    metrics: SummaryMetricItem[];
    wins?: string[]; // e.g. ["NotebookLM Structured Extractions Verified", "Zero Data Loss"]
  };

  // 2. VALUE / REVENUE
  value: {
    highlight: string; // e.g. "+$4,210.50 (PAPER)"
    headline: string; // e.g. "Value Produced & Pipeline"
    paperOrDemoTag?: string; // e.g. "PAPER P&L ONLY" or "DEMO PIPELINE"
    metrics: SummaryMetricItem[];
    truthDisclaimer?: string; // e.g. "Simulated practice data · Live trading OFF"
  };

  // 3. NEEDS RAY / GOLD
  needsRay: {
    count: number;
    highlight: string; // e.g. "1 Decision Gate"
    headline: string; // e.g. "Owner Approval Required"
    items: {
      title: string;
      category: string; // e.g. "LIVE TRADING APPROVAL"
      actionLabel?: string;
      onAction?: () => void;
    }[];
    nominalNote?: string;
  };

  // 4. ATTENTION / RED
  attention: {
    count: number;
    highlight: string; // e.g. "0 Broken Systems" or "1 Latency Alert"
    headline: string; // e.g. "Failed Systems & Blockers"
    items?: {
      title: string;
      detail: string;
      severity?: 'warning' | 'critical';
    }[];
    nominalNote?: string;
  };

  // 5. RUNNING / BLUE
  running: {
    count: number;
    highlight: string; // e.g. "4 Workers Active"
    headline: string; // e.g. "Active Jobs & Current Processing"
    metrics: SummaryMetricItem[];
  };
}

export const ExecutiveDepartmentSummaryBar: React.FC<ExecutiveSummaryBarProps> = ({
  departmentName,
  departmentKicker,
  truthClass = 'LIVE_VERIFIED',
  operationalCounts,
  threeQuestions,
  success,
  value,
  needsRay,
  attention,
  running
}) => {
  const { setIsNeedsRayDrawerOpen } = useNexus();

  const renderTruthBadge = (cls?: DataTruthClass) => {
    switch (cls) {
      case 'LIVE_VERIFIED':
        return (
          <span className="text-[7.5px] font-black uppercase px-1 py-0.2 rounded bg-emerald-100 text-emerald-900 border border-emerald-300 tracking-wider">
            LIVE_VERIFIED
          </span>
        );
      case 'TEST_CANARY':
        return (
          <span className="text-[7.5px] font-black uppercase px-1 py-0.2 rounded bg-blue-100 text-blue-900 border border-blue-300 tracking-wider">
            TEST_CANARY
          </span>
        );
      case 'SAMPLE':
        return (
          <span className="text-[7.5px] font-black uppercase px-1 py-0.2 rounded bg-purple-100 text-purple-900 border border-purple-300 tracking-wider">
            SAMPLE
          </span>
        );
      case 'NOT CONNECTED':
        return (
          <span className="text-[7.5px] font-black uppercase px-1 py-0.2 rounded bg-rose-100 text-rose-900 border border-rose-300 tracking-wider">
            NOT CONNECTED
          </span>
        );
      case 'NOT PROVEN':
        return (
          <span className="text-[7.5px] font-black uppercase px-1 py-0.2 rounded bg-amber-100 text-amber-900 border border-amber-300 tracking-wider">
            NOT PROVEN
          </span>
        );
      case 'DEMO':
        return (
          <span className="text-[7.5px] font-black uppercase px-1 py-0.2 rounded bg-cyan-100 text-cyan-900 border border-cyan-300 tracking-wider">
            DEMO
          </span>
        );
      case 'PROTOTYPE':
      default:
        return (
          <span className="text-[7.5px] font-black uppercase px-1 py-0.2 rounded bg-amber-100 text-amber-900 border border-amber-300 tracking-wider">
            PROTOTYPE
          </span>
        );
    }
  };

  return (
    <div className="w-full space-y-2 shrink-0 animate-in fade-in duration-300">
      {/* Executive Answer Header Bar */}
      <div className="bg-slate-900 text-white rounded-xl px-3 py-1.5 flex flex-wrap items-center justify-between gap-2 shadow-2xs border border-slate-800">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shrink-0" />
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[11px] font-black uppercase tracking-wider text-emerald-400">
              {departmentName}
            </span>
            <span className="text-slate-600 text-xs hidden sm:inline">|</span>
            <span className="text-xs font-black tracking-tight text-white">
              EXECUTIVE SIGNALS: SUCCESS · VALUE · APPROVALS
            </span>
            {departmentKicker && (
              <span className="text-[10px] text-slate-400 font-medium hidden md:inline">
                · {departmentKicker}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1.5 text-[9px] font-bold">
          <span className="text-slate-400 hidden lg:inline font-mono">
            5-SECOND EXECUTIVE SCAN
          </span>
          {renderTruthBadge(truthClass)}
        </div>
      </div>

      {/* Universal 4 Operational States & 3 Core Questions Direct Scan Box */}
      {(operationalCounts || threeQuestions) && (
        <div className="bg-white rounded-xl border border-slate-200/90 shadow-2xs p-2 sm:p-2.5 space-y-2">
          {operationalCounts && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 text-xs">
              <div className="p-1 sm:p-1.5 rounded-lg bg-blue-50/70 border border-blue-200/70 flex items-center justify-between transition-all hover:bg-blue-50">
                <span className="text-[9.5px] font-bold text-blue-900 uppercase">Working On</span>
                <span className="text-xs font-black text-blue-950 font-mono bg-white px-1.5 py-0.2 rounded border border-blue-200">{operationalCounts.workingOn}</span>
              </div>
              <div className="p-1 sm:p-1.5 rounded-lg bg-emerald-50/70 border border-emerald-200/70 flex items-center justify-between transition-all hover:bg-emerald-50">
                <span className="text-[9.5px] font-bold text-emerald-900 uppercase">Completed Today</span>
                <span className="text-xs font-black text-emerald-950 font-mono bg-white px-1.5 py-0.2 rounded border border-emerald-200">{operationalCounts.completedToday}</span>
              </div>
              <div className="p-1 sm:p-1.5 rounded-lg bg-amber-50/70 border border-amber-200/70 flex items-center justify-between transition-all hover:bg-amber-50">
                <span className="text-[9.5px] font-bold text-amber-900 uppercase">Needs Ray</span>
                <span className="text-xs font-black text-amber-950 font-mono bg-white px-1.5 py-0.2 rounded border border-amber-200">{operationalCounts.needsRay}</span>
              </div>
              <div className="p-1 sm:p-1.5 rounded-lg bg-rose-50/70 border border-rose-200/70 flex items-center justify-between transition-all hover:bg-rose-50">
                <span className="text-[9.5px] font-bold text-rose-900 uppercase">Attention</span>
                <span className="text-xs font-black text-rose-950 font-mono bg-white px-1.5 py-0.2 rounded border border-rose-200">{operationalCounts.attention}</span>
              </div>
            </div>
          )}

          {threeQuestions && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs">
              <div className="p-2 rounded-lg bg-amber-50/40 border border-amber-200/80 transition-all hover:shadow-2xs">
                <div className="text-[8.5px] font-black uppercase text-amber-900 flex items-center gap-1 mb-0.5">
                  <Sparkles className="w-3 h-3 text-amber-600" />
                  <span>MOST IMPORTANT THING</span>
                </div>
                <p className="text-[11px] font-semibold text-slate-900 leading-snug">
                  {threeQuestions.mostImportantThing}
                </p>
              </div>

              <div className="p-2 rounded-lg bg-blue-50/40 border border-blue-200/80 transition-all hover:shadow-2xs">
                <div className="text-[8.5px] font-black uppercase text-blue-900 flex items-center gap-1 mb-0.5">
                  <Activity className="w-3 h-3 text-blue-600" />
                  <span>WHAT NEXUS IS DOING</span>
                </div>
                <p className="text-[11px] font-semibold text-slate-900 leading-snug">
                  {threeQuestions.whatNexusIsDoing}
                </p>
              </div>

              <div className="p-2 rounded-lg bg-emerald-50/40 border border-emerald-200/80 transition-all hover:shadow-2xs">
                <div className="text-[8.5px] font-black uppercase text-emerald-900 flex items-center gap-1 mb-0.5">
                  <ArrowRight className="w-3 h-3 text-emerald-600" />
                  <span>WHAT HAPPENS NEXT</span>
                </div>
                <p className="text-[11px] font-semibold text-slate-900 leading-snug">
                  {threeQuestions.whatHappensNext}
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 5-Pillar Universal Executive Matrix */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-2">
        {/* =================================================================== */}
        {/* 1. WHAT SUCCEEDED? (SUCCESS / GREEN - PRIMARY EXECUTIVE SIGNAL)   */}
        {/* =================================================================== */}
        <div className="rounded-xl border-2 border-emerald-400 bg-gradient-to-b from-emerald-50/80 to-white p-2.5 flex flex-col justify-between shadow-2xs space-y-2">
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[9px] font-black uppercase tracking-wider text-emerald-900 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                <span>1. WHAT SUCCEEDED</span>
              </span>
              <span className="text-[7.5px] font-black px-1.5 py-0.2 rounded bg-emerald-600 text-white uppercase tracking-wider">
                SUCCESS
              </span>
            </div>

            <div className="pt-0.5">
              <div className="text-base sm:text-lg font-black text-emerald-950 leading-tight">
                {success.highlight}
              </div>
              <div className="text-[10px] text-emerald-800 font-semibold leading-snug">
                {success.headline}
              </div>
            </div>
          </div>

          <div className="space-y-1.5 pt-1 border-t border-emerald-200/80">
            <div className="space-y-1 text-[9.5px]">
              {success.metrics.map((m, idx) => (
                <div key={idx} className="flex items-center justify-between text-slate-700">
                  <span className="text-slate-600 font-medium truncate max-w-[130px]">
                    {m.label}:
                  </span>
                  <span className="font-extrabold text-emerald-950 text-right ml-1">
                    {m.value}
                  </span>
                </div>
              ))}
            </div>

            {success.wins && success.wins.length > 0 && (
              <div className="bg-emerald-100/70 p-1.5 rounded-lg border border-emerald-200/90 text-[8.5px] font-bold text-emerald-950 space-y-0.5">
                <div className="text-[7.5px] uppercase font-black text-emerald-800">Verified Wins:</div>
                {success.wins.map((w, idx) => (
                  <div key={idx} className="flex items-start gap-1 leading-tight">
                    <span className="text-emerald-700 font-black">✓</span>
                    <span className="line-clamp-1">{w}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* =================================================================== */}
        {/* 2. WHAT PRODUCED VALUE OR REVENUE? (VALUE / REVENUE)               */}
        {/* =================================================================== */}
        <div className="rounded-xl border border-emerald-300 bg-gradient-to-b from-emerald-50/40 via-white to-white p-2.5 flex flex-col justify-between shadow-2xs space-y-2">
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[9px] font-black uppercase tracking-wider text-emerald-950 flex items-center gap-1">
                <TrendingUp className="w-3.5 h-3.5 text-emerald-700" />
                <span>2. VALUE & REVENUE</span>
              </span>
              {value.paperOrDemoTag && (
                <span className="text-[7.5px] font-black px-1.5 py-0.2 rounded bg-amber-100 text-amber-950 border border-amber-300 uppercase tracking-wider font-mono">
                  {value.paperOrDemoTag}
                </span>
              )}
            </div>

            <div className="pt-0.5">
              <div className="text-base sm:text-lg font-black text-slate-900 leading-tight">
                {value.highlight}
              </div>
              <div className="text-[10px] text-slate-600 font-semibold leading-snug">
                {value.headline}
              </div>
            </div>
          </div>

          <div className="space-y-1.5 pt-1 border-t border-slate-200/90">
            <div className="space-y-1 text-[9.5px]">
              {value.metrics.map((m, idx) => (
                <div key={idx} className="flex items-center justify-between text-slate-700">
                  <span className="text-slate-600 font-medium truncate max-w-[130px]">
                    {m.label}:
                  </span>
                  <span
                    className={`font-black text-right ml-1 ${
                      m.isPaper
                        ? 'text-blue-900 font-mono'
                        : 'text-emerald-900'
                    }`}
                  >
                    {m.value}
                  </span>
                </div>
              ))}
            </div>

            {value.truthDisclaimer && (
              <div className="bg-slate-50 p-1 rounded border border-slate-200 text-[8px] font-medium text-slate-500 leading-tight">
                <strong className="text-slate-700 uppercase">Truth Rule:</strong> {value.truthDisclaimer}
              </div>
            )}
          </div>
        </div>

        {/* =================================================================== */}
        {/* 3. WHAT NEEDS RAY'S APPROVAL? (NEEDS RAY / GOLD - HERO DECISION)  */}
        {/* =================================================================== */}
        <div
          className={`rounded-xl border-2 p-2.5 flex flex-col justify-between shadow-2xs space-y-2 ${
            needsRay.count > 0
              ? 'border-amber-400 bg-gradient-to-b from-amber-50/90 to-white'
              : 'border-slate-200 bg-slate-50/50'
          }`}
        >
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[9px] font-black uppercase tracking-wider text-amber-950 flex items-center gap-1">
                <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
                <span>3. NEEDS RAY</span>
              </span>
              <span
                className={`text-[7.5px] font-black px-1.5 py-0.2 rounded uppercase tracking-wider ${
                  needsRay.count > 0
                    ? 'bg-amber-500 text-white font-extrabold shadow-2xs'
                    : 'bg-slate-200 text-slate-600'
                }`}
              >
                {needsRay.count > 0 ? `${needsRay.count} PENDING` : '0 GATES'}
              </span>
            </div>

            <div className="pt-0.5">
              <div className="text-base sm:text-lg font-black text-slate-900 leading-tight">
                {needsRay.highlight}
              </div>
              <div className="text-[10px] text-amber-900 font-semibold leading-snug">
                {needsRay.headline}
              </div>
            </div>
          </div>

          <div className="space-y-1.5 pt-1 border-t border-amber-200/80">
            {needsRay.items.length > 0 ? (
              <div className="space-y-1">
                {needsRay.items.map((item, idx) => (
                  <div
                    key={idx}
                    className="p-1.5 rounded-lg bg-white border border-amber-200 shadow-2xs space-y-1 text-[9px]"
                  >
                    <div className="flex items-center justify-between gap-1">
                      <span className="text-[7.5px] font-black uppercase px-1 py-0.2 rounded bg-amber-100 text-amber-950 border border-amber-300">
                        {item.category}
                      </span>
                    </div>
                    <div className="font-bold text-slate-900 leading-tight">
                      {item.title}
                    </div>
                    {item.actionLabel && (
                      <button
                        type="button"
                        onClick={item.onAction}
                        className="w-full py-0.5 px-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white font-black text-[8px] transition-colors cursor-pointer flex items-center justify-center gap-0.5"
                      >
                        <span>{item.actionLabel}</span>
                        <ChevronRight className="w-2.5 h-2.5" />
                      </button>
                    )}
                  </div>
                ))}

                <button
                  type="button"
                  onClick={() => setIsNeedsRayDrawerOpen(true)}
                  className="w-full mt-1 py-1 px-2 rounded-lg bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white font-black text-[8.5px] shadow-xs flex items-center justify-center gap-1 active:scale-95 transition-all cursor-pointer"
                >
                  <Zap className="w-3 h-3 text-white" />
                  <span>Review in Decision Center ({needsRay.count})</span>
                </button>
              </div>
            ) : (
              <div className="bg-emerald-50/70 p-2 rounded-lg border border-emerald-200 text-[8.5px] text-emerald-900 font-semibold flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                <span>{needsRay.nominalNote || 'No owner approvals pending. Operating autonomously.'}</span>
              </div>
            )}
          </div>
        </div>

        {/* =================================================================== */}
        {/* 4. WHAT IS BROKEN? (ATTENTION / RED - SYSTEM HEALTH & BLOCKERS)    */}
        {/* =================================================================== */}
        <div
          className={`rounded-xl border p-2.5 flex flex-col justify-between shadow-2xs space-y-2 ${
            attention.count > 0
              ? 'border-rose-300 bg-rose-50/60'
              : 'border-slate-200 bg-white'
          }`}
        >
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[9px] font-black uppercase tracking-wider text-slate-800 flex items-center gap-1">
                <AlertTriangle
                  className={`w-3.5 h-3.5 ${
                    attention.count > 0 ? 'text-rose-600' : 'text-slate-400'
                  }`}
                />
                <span>4. ATTENTION & BLOCKERS</span>
              </span>
              <span
                className={`text-[7.5px] font-black px-1.5 py-0.2 rounded uppercase tracking-wider ${
                  attention.count > 0
                    ? 'bg-rose-600 text-white'
                    : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                }`}
              >
                {attention.count > 0 ? `${attention.count} ATTENTION` : 'NOMINAL'}
              </span>
            </div>

            <div className="pt-0.5">
              <div
                className={`text-base sm:text-lg font-black leading-tight ${
                  attention.count > 0 ? 'text-rose-950' : 'text-slate-900'
                }`}
              >
                {attention.highlight}
              </div>
              <div className="text-[10px] text-slate-600 font-semibold leading-snug">
                {attention.headline}
              </div>
            </div>
          </div>

          <div className="space-y-1.5 pt-1 border-t border-slate-200/90">
            {attention.items && attention.items.length > 0 ? (
              <div className="space-y-1">
                {attention.items.map((it, idx) => (
                  <div
                    key={idx}
                    className="p-1.5 rounded-lg bg-white border border-rose-200 text-[8.5px] space-y-0.5"
                  >
                    <div className="font-black text-rose-900">{it.title}</div>
                    <div className="text-slate-600 leading-tight">{it.detail}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-emerald-50/60 p-2 rounded-lg border border-emerald-200 text-[8.5px] text-emerald-900 font-semibold flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                <span>{attention.nominalNote || '0 critical incidents · 0 retry exhaustion events'}</span>
              </div>
            )}
          </div>
        </div>

        {/* =================================================================== */}
        {/* 5. WHAT IS CURRENTLY RUNNING? (RUNNING / BLUE - ACTIVE FLEET)       */}
        {/* =================================================================== */}
        <div className="rounded-xl border border-blue-200 bg-gradient-to-b from-blue-50/50 to-white p-2.5 flex flex-col justify-between shadow-2xs space-y-2">
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[9px] font-black uppercase tracking-wider text-blue-950 flex items-center gap-1">
                <RotateCw className="w-3.5 h-3.5 text-blue-600 animate-spin" />
                <span>5. CURRENTLY RUNNING</span>
              </span>
              <span className="text-[7.5px] font-black px-1.5 py-0.2 rounded bg-blue-100 text-blue-900 border border-blue-300 uppercase tracking-wider">
                ACTIVE
              </span>
            </div>

            <div className="pt-0.5">
              <div className="text-base sm:text-lg font-black text-blue-950 leading-tight">
                {running.highlight}
              </div>
              <div className="text-[10px] text-blue-800 font-semibold leading-snug">
                {running.headline}
              </div>
            </div>
          </div>

          <div className="space-y-1.5 pt-1 border-t border-blue-200/80">
            <div className="space-y-1 text-[9.5px]">
              {running.metrics.map((m, idx) => (
                <div key={idx} className="flex items-center justify-between text-slate-700">
                  <span className="text-slate-600 font-medium truncate max-w-[130px]">
                    {m.label}:
                  </span>
                  <span className="font-extrabold text-blue-950 text-right ml-1">
                    {m.value}
                  </span>
                </div>
              ))}
            </div>

            <div className="bg-blue-100/60 px-1.5 py-1 rounded text-[8px] text-blue-950 font-mono font-medium truncate">
              Continuous background daemon lease active
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
