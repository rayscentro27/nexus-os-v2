import React, { useState } from 'react';
import { usePortal } from '../../context/PortalContext';
import { GiantIcon } from '../common/GiantIcon';

export const CreditProfileView: React.FC = () => {
  const { setActiveTab, openClydeWithPrompt, facts, liveMode } = usePortal();
  const [activeTabSub, setActiveTabSub] = useState<'matrix' | 'strategy'>('matrix');

  // Bureau Scores
  const bureaus = [
    { name: 'Credit readiness', score: facts.creditScore, rating: facts.creditScore ? 'Available' : 'Awaiting data', color: 'from-emerald-400 to-teal-500' },
    { name: 'Bureau coverage', score: liveMode ? 0 : 738, rating: liveMode ? 'Awaiting data' : 'Very Good', color: 'from-teal-400 to-sky-500' },
    { name: 'Credit profile', score: liveMode ? 0 : 748, rating: liveMode ? 'Awaiting data' : 'Very Good', color: 'from-sky-400 to-indigo-500' }
  ];

  // Core Credit Health Zones
  const healthFactors = [
    {
      label: 'Payment History',
      value: '100%',
      rating: 'Exceptional',
      detail: '0 late payments across 48 reported cycles',
      status: 'pass'
    },
    {
      label: 'Credit Utilization',
      value: facts.utilizationPercent ? `${facts.utilizationPercent}%` : 'Not available',
      rating: facts.utilizationPercent ? `Target ${facts.utilizationTargetPercent}%` : 'Awaiting data',
      detail: facts.utilizationPercent ? 'Live utilization percentage returned by the client-scoped profile.' : 'No live utilization record returned.',
      status: 'attention'
    },
    {
      label: 'Credit Age & Depth',
      value: '4.8 Yrs',
      rating: 'Strong',
      detail: 'Oldest trade line 7 yrs 4 mos (Amex)',
      status: 'pass'
    },
    {
      label: 'Total Accounts',
      value: '9 Active',
      rating: 'Balanced',
      detail: '6 revolving lines, 2 auto loans, 1 installment',
      status: 'pass'
    },
    {
      label: 'Hard Inquiries (12 Mo)',
      value: '2 Inquiries',
      rating: 'Low Risk',
      detail: '1 auto pre-qual, 1 business card',
      status: 'pass'
    },
    {
      label: 'Derogatory Marks',
      value: '0 Marks',
      rating: 'Pristine',
      detail: 'Zero bankruptcies, judgments, or collections',
      status: 'pass'
    }
  ];

  return (
    <div className="h-full flex flex-col gap-2.5 overflow-hidden animate-fade-in select-none">
      {/* Consolidated Header Banner (Clean White Surface) */}
      <div className="flex items-center justify-between gap-3 p-3 rounded-xl border border-slate-200/90 bg-white shadow-xs shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-teal-50 border border-teal-200 shrink-0 text-teal-600">
            <GiantIcon type="shield" size="sm" glow={false} />
          </div>
          <div>
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-teal-700 font-bold">
              <span>Personal Guarantor Credit Audit</span>
              <span className="text-slate-300">·</span>
              <span className="text-slate-500 font-medium">Updated 3 Days Ago</span>
            </div>
            <h1 className="text-base font-bold text-slate-900 tracking-tight">
              Credit Profile · <span className="text-teal-700 font-mono">{facts.creditScore ? `${facts.creditScore} readiness score` : 'Awaiting live data'}</span>
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Ask Clyde (Clean Light Highlight) */}
          <button
            onClick={() => openClydeWithPrompt("How will paying off revolving debt impact my Experian score?")}
            className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-teal-800 text-xs font-semibold cursor-pointer shadow-xs transition-colors"
          >
            <span>Ask Clyde</span>
          </button>
          <button
            onClick={() => setActiveTab('credit-utilization')}
            className="px-3.5 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs transition-all shadow-xs cursor-pointer whitespace-nowrap active:scale-95"
          >
            View Utilization Gauge →
          </button>
        </div>
      </div>

      {/* Tri-Bureau Compact Score Ribbon */}
      <div className="grid grid-cols-3 gap-2.5 shrink-0">
        {bureaus.map((bureau) => (
          <div
            key={bureau.name}
            className="relative overflow-hidden rounded-xl border border-slate-200/90 bg-white p-3 text-center shadow-xs"
          >
            <div className="flex items-center justify-between text-[11px] text-slate-600 mb-1">
              <span className="font-bold uppercase tracking-wider text-slate-700">{bureau.name}</span>
              <span className="text-teal-700 font-semibold text-[10px]">{bureau.rating}</span>
            </div>

            <div className="my-1 flex items-baseline justify-center gap-1">
              <span className="text-3xl font-black tracking-tight text-slate-900 tabular-nums">
                {bureau.score}
              </span>
              <span className="text-[10px] text-slate-400">/ 850</span>
            </div>

            <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden mt-1.5">
              <div
                className={`h-full bg-gradient-to-r ${bureau.color} rounded-full`}
                style={{ width: `${(bureau.score / 850) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Main Workspace (Matrix vs Strategic Action) */}
      <div className="flex-1 min-h-0 rounded-xl border border-slate-200/90 bg-white p-3.5 flex flex-col overflow-hidden shadow-xs">
        <div className="flex items-center justify-between pb-2.5 border-b border-slate-100 shrink-0">
          <div className="flex items-center gap-1.5 p-1 bg-slate-100 rounded-lg border border-slate-200/80">
            <button
              onClick={() => setActiveTabSub('matrix')}
              className={`text-xs px-3 py-1 rounded-md transition-all cursor-pointer ${
                activeTabSub === 'matrix'
                  ? 'bg-white text-slate-900 font-bold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 font-medium'
              }`}
            >
              Factor Matrix (6 Zones)
            </button>
            <button
              onClick={() => setActiveTabSub('strategy')}
              className={`text-xs px-3 py-1 rounded-md transition-all cursor-pointer ${
                activeTabSub === 'strategy'
                  ? 'bg-white text-slate-900 font-bold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 font-medium'
              }`}
            >
              Strategic Underwriter Analysis
            </button>
          </div>

          <span className="text-[11px] text-slate-500 font-mono bg-slate-50 px-2 py-0.5 rounded border border-slate-200">
            Experian Commercial Sync · Verified
          </span>
        </div>

        {activeTabSub === 'matrix' ? (
          <div className="flex-1 min-h-0 overflow-y-auto pt-2.5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 scrollbar-thin">
            {healthFactors.map((factor, idx) => (
              <div
                key={idx}
                className="p-3 rounded-xl border border-slate-200 bg-slate-50/70 hover:bg-white hover:border-slate-300 hover:shadow-xs transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between text-[11px] text-slate-600">
                    <span className="font-semibold text-slate-800">{factor.label}</span>
                    <span
                      className={`font-semibold text-[10px] px-1.5 py-0.5 rounded ${
                        factor.status === 'pass'
                          ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                          : 'bg-amber-50 text-amber-800 border border-amber-200'
                      }`}
                    >
                      {factor.rating}
                    </span>
                  </div>
                  <div className="mt-1 text-xl font-bold text-slate-900 tabular-nums">
                    {factor.value}
                  </div>
                </div>
                <p className="mt-1.5 text-[11px] text-slate-600 pt-1.5 border-t border-slate-200/80 line-clamp-2">
                  {factor.detail}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex-1 min-h-0 overflow-y-auto pt-2.5 grid grid-cols-1 md:grid-cols-3 gap-3 scrollbar-thin">
            {/* What is Strong */}
            <div className="rounded-xl border border-emerald-200 bg-emerald-50/40 p-3 flex flex-col">
              <div className="flex items-center gap-1.5 mb-2 font-bold text-xs text-emerald-800 uppercase">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <span>What Is Strong</span>
              </div>
              <div className="space-y-2 text-xs flex-1">
                <div className="p-2.5 rounded-lg bg-white border border-emerald-100 shadow-xs">
                  <div className="font-bold text-slate-900">100% On-Time Payment History</div>
                  <p className="text-[11px] text-slate-600 mt-0.5">0 late payments across 48 reported cycles.</p>
                </div>
                <div className="p-2.5 rounded-lg bg-white border border-emerald-100 shadow-xs">
                  <div className="font-bold text-slate-900">Clean Public Records</div>
                  <p className="text-[11px] text-slate-600 mt-0.5">Zero bankruptcies, charge-offs, or collections.</p>
                </div>
              </div>
            </div>

            {/* What Needs Attention */}
            <div className="rounded-xl border border-amber-200 bg-amber-50/40 p-3 flex flex-col">
              <div className="flex items-center gap-1.5 mb-2 font-bold text-xs text-amber-800 uppercase">
                <span className="w-2 h-2 rounded-full bg-amber-500" />
                <span>What Needs Attention</span>
              </div>
              <div className="space-y-2 text-xs flex-1">
                <div className="p-2.5 rounded-lg bg-white border border-amber-100 shadow-xs">
                  <div className="font-bold text-slate-900">Revolving Utilization at {facts.utilizationPercent ? `${facts.utilizationPercent}%` : 'Not available'}</div>
                  <p className="text-[11px] text-slate-600 mt-0.5">Target utilization: {facts.utilizationPercent ? `${facts.utilizationTargetPercent}%` : 'not available'}.</p>
                </div>
                <div className="p-2.5 rounded-lg bg-white border border-amber-100 shadow-xs">
                  <div className="font-bold text-slate-900">Chase Ink Concentration</div>
                  <p className="text-[11px] text-slate-600 mt-0.5">$5,200 balance on $25,000 line represents 61% of total debt.</p>
                </div>
              </div>
            </div>

            {/* What To Do Next (Clean Light Highlight Card) */}
            <div className="rounded-xl border border-teal-200/90 bg-gradient-to-br from-teal-50/50 via-white to-sky-50/30 p-3 flex flex-col text-slate-900 shadow-xs">
              <div className="flex items-center gap-1.5 mb-2 font-bold text-xs text-teal-800 uppercase tracking-wider">
                <span className="w-2 h-2 rounded-full bg-teal-500" />
                <span>What To Do Next</span>
              </div>
              <div className="space-y-2 text-xs flex-1">
                <div className="p-2.5 rounded-lg bg-white border border-teal-100 shadow-xs">
                  <div className="font-bold text-slate-900">1. Pay Down $2,000 on Chase Ink</div>
                  <p className="text-[11px] text-slate-600 mt-0.5">Drops utilization to 14.5% instantly (+15 pts).</p>
                </div>
                <div className="p-2.5 rounded-lg bg-white border border-teal-100 shadow-xs">
                  <div className="font-bold text-slate-900">2. Time Statement Closing</div>
                  <p className="text-[11px] text-slate-600 mt-0.5">Pay 3 days prior to statement close date.</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
