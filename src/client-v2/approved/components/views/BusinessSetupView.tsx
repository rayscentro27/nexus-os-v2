import React from 'react';
import { usePortal } from '../../context/PortalContext';
import { GiantIcon } from '../common/GiantIcon';

export const BusinessSetupView: React.FC = () => {
  const { setupSteps, toggleSetupStep, setActiveTab, openClydeWithPrompt, profile, liveMode } = usePortal();

  const completedCount = setupSteps.filter((s) => s.status === 'completed').length;
  const totalCount = setupSteps.length;
  const completionPercentage = totalCount ? Math.round((completedCount / totalCount) * 100) : 0;

  return (
    <div className="h-full flex flex-col gap-2.5 overflow-hidden animate-fade-in select-none">
      {/* Consolidated Header Banner (Clean White Surface) */}
      <div className="flex items-center justify-between gap-3 p-3 rounded-xl border border-slate-200/90 bg-white shadow-xs shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-sky-50 border border-sky-200 shrink-0 text-sky-600">
            <GiantIcon type="building" size="sm" glow={false} />
          </div>
          <div>
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-sky-700 font-bold">
              <span>Corporate Compliance & Credibility</span>
              <span className="text-slate-300">·</span>
              <span className="text-slate-500 font-medium">{profile.entityType}</span>
            </div>
            <h1 className="text-base font-bold text-slate-900 tracking-tight">
              Business Foundation Roadmap · {completedCount} of {totalCount} Certified ({completionPercentage}%)
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2 w-36">
            <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-sky-500 to-teal-500 rounded-full"
                style={{ width: `${completionPercentage}%` }}
              />
            </div>
            <span className="text-xs font-mono font-bold text-sky-700">{completionPercentage}%</span>
          </div>
          <button
            onClick={() => setActiveTab('business-bankability')}
            className="px-3.5 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-700 text-white font-bold text-xs transition-all shadow-xs cursor-pointer whitespace-nowrap active:scale-95"
          >
            View Bankability Score →
          </button>
        </div>
      </div>

      {/* 2-Column Consolidated Workspace (Fits on screen without scrolling) */}
      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-12 gap-2.5 overflow-hidden">
        {/* Left: Corporate Credibility Summary & Clyde Tip (4 cols) */}
        <div className="lg:col-span-4 rounded-xl border border-slate-200/90 bg-white p-3 flex flex-col justify-between shadow-xs">
          <div>
            <div className="flex items-center justify-between pb-1.5 border-b border-slate-100">
              <span className="text-[10px] font-bold text-sky-700 uppercase tracking-wider">
                Corporate Dossier
              </span>
              <span className="text-[10px] text-emerald-700 font-mono font-bold">Good Standing</span>
            </div>

            <div className="mt-3 p-3 rounded-lg border border-slate-200 bg-slate-50/80 space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-500">Legal Entity:</span>
                <span className="font-bold text-slate-900">{profile.companyName}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Jurisdiction:</span>
                <span className="font-bold text-slate-900">{profile.stateOfFormation}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Filing Date:</span>
                <span className="font-mono text-slate-900">14 Months Active</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">EIN Issuance:</span>
                <span className="font-mono text-teal-700 font-semibold">IRS Form 147C on File</span>
              </div>
            </div>

            {/* Clyde Context 411 Tip (Clean Light Highlight) */}
            <div className="mt-3 p-2.5 rounded-lg border border-amber-200/80 bg-amber-50/50 text-slate-800 shadow-xs">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-amber-800 uppercase">
                  ⚡ 411 Directory Sync
                </span>
                <button
                  onClick={() => openClydeWithPrompt(`How do I improve ${profile.companyName}'s public business directory consistency?`)}
                  className="text-[10px] text-teal-700 font-bold hover:underline cursor-pointer"
                >
                  Ask Clyde →
                </button>
              </div>
              <p className="text-[11px] text-slate-600 mt-1 leading-snug">
                Step 10 (411 Directory Listing) is marked 'Attention'. Commercial loan automated algorithms scrub national 411 records before routing to human underwriters.
              </p>
            </div>
          </div>

          <div className="mt-2 text-[10px] text-slate-400 text-center">
            Click any checkpoint to toggle compliance status
          </div>
        </div>

        {/* Right: Interactive 10-Point Checklist (8 cols) */}
        <div className="lg:col-span-8 rounded-xl border border-slate-200/90 bg-white p-3 flex flex-col justify-between shadow-xs overflow-hidden">
          <div className="flex items-center justify-between pb-1.5 border-b border-slate-100 shrink-0">
            <span className="text-[10px] font-bold text-teal-700 uppercase tracking-wider">
              10 Foundation Compliance Protocols
            </span>
            <span className="text-[10px] font-mono text-slate-400">
              {completedCount} of {totalCount} Cleared
            </span>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto space-y-1.5 pt-2 pr-1 scrollbar-thin">
            {setupSteps.map((step) => {
              const isDone = step.status === 'completed';
              return (
                <div
                  key={step.id}
                  onClick={() => { if (!liveMode) toggleSetupStep(step.id); }}
                  aria-disabled={liveMode}
                  title={liveMode ? 'Business setup changes are governed by the existing client workflow.' : undefined}
                  className={`p-2 rounded-lg border transition-all cursor-pointer flex items-center justify-between gap-3 ${
                    isDone
                      ? 'border-emerald-200 bg-emerald-50/70 hover:bg-emerald-50'
                      : 'border-slate-200 bg-slate-50/80 hover:bg-white hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div
                      className={`w-6 h-6 rounded-md flex items-center justify-center font-mono font-bold text-xs shrink-0 ${
                        isDone
                          ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                          : 'bg-white text-slate-500 border border-slate-200'
                      }`}
                    >
                      {isDone ? '✓' : step.stepNumber}
                    </div>

                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <h4 className="text-xs font-bold text-slate-900 truncate">
                          {step.title}
                        </h4>
                        <span className="text-[10px] text-teal-700 font-mono font-semibold hidden sm:inline">
                          +{step.points} Pts
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-600 truncate">
                        {step.whyItMatters}
                      </p>
                    </div>
                  </div>

                  <span
                    className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded shrink-0 ${
                      isDone
                        ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                        : 'bg-amber-100 text-amber-800 border border-amber-200'
                    }`}
                  >
                    {isDone ? 'VERIFIED' : 'PENDING'}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
