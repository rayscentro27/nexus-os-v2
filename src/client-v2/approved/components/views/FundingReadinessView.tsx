import React from 'react';
import { usePortal } from '../../context/PortalContext';
import { GiantIcon } from '../common/GiantIcon';

export const FundingReadinessView: React.FC = () => {
  const { setActiveTab, openClydeWithPrompt, facts, profile, liveMode } = usePortal();

  // Matched Institutional Facilities
  const fundingPrograms = liveMode ? [] : [
    {
      name: 'Prime Commercial Line of Credit',
      amount: '$150,000 - $250,000',
      type: 'Revolving Unsecured Facility',
      rate: 'Prime + 1.25%',
      readinessStatus: 'NEEDS WORK',
      readinessPercent: 74,
      readinessColor: 'text-amber-400',
      holdReason: 'Awaiting 90-day bank statement verification in Document Vault',
      actionTab: 'documents',
      actionLabel: 'Upload Statements'
    },
    {
      name: 'Equipment & Fleet Financing',
      amount: '$75,000 - $125,000',
      type: 'Asset-Backed Capital Lease',
      rate: '6.49% Fixed APR',
      readinessStatus: 'READY',
      readinessPercent: 91,
      readinessColor: 'text-emerald-400',
      holdReason: 'Fleet quotes validated. Pre-cleared for submission.',
      actionTab: 'request-review',
      actionLabel: 'Request Term Sheet'
    },
    {
      name: 'Revenue-Based Working Capital',
      amount: '$100,000',
      type: 'Non-Dilutive Growth Capital',
      rate: '1.12 Factor Rate',
      readinessStatus: 'READY',
      readinessPercent: 88,
      readinessColor: 'text-emerald-400',
      holdReason: 'Qualifies based on $35k+ monthly freight revenue history.',
      actionTab: 'request-review',
      actionLabel: 'Review Terms'
    },
    {
      name: 'SBA 7(a) Working Capital Loan',
      amount: '$350,000',
      type: 'Government-Guaranteed Senior Debt',
      rate: 'Prime + 2.75%',
      readinessStatus: 'BLOCKED',
      readinessPercent: 54,
      readinessColor: 'text-rose-400',
      holdReason: 'Requires 2 full tax years (currently at 14 months).',
      actionTab: 'recommendations',
      actionLabel: 'Alternatives'
    }
  ];

  // Readiness Signals
  const readinessSignals = [
    { label: 'Credit readiness', score: facts.creditScore ? `${facts.creditScore}` : 'Not available', status: facts.creditScore ? 'READY' : 'PENDING', pass: Boolean(facts.creditScore) },
    { label: 'Business entity', score: profile.entityType, status: profile.entityType !== 'Not available' ? 'READY' : 'PENDING', pass: profile.entityType !== 'Not available' },
    { label: 'Funding target', score: facts.fundingTargetLabel, status: facts.fundingTargetLabel !== 'No funding target recorded' ? 'READY' : 'PENDING', pass: facts.fundingTargetLabel !== 'No funding target recorded' },
    { label: 'Document verification', score: facts.documentTotalCount ? `${facts.documentVerifiedCount}/${facts.documentTotalCount} verified` : 'Not available', status: facts.documentVerifiedCount ? 'READY' : 'PENDING', pass: facts.documentVerifiedCount > 0 },
    { label: 'Bankability score', score: facts.bankabilityScore ? `${facts.bankabilityScore}/100` : 'Not available', status: facts.bankabilityScore ? 'READY' : 'PENDING', pass: facts.bankabilityScore > 0 },
    { label: 'Credit utilization ratio', score: facts.utilizationPercent ? `${facts.utilizationPercent}% (Target ${facts.utilizationTargetPercent}%)` : 'Not available', status: facts.utilizationPercent ? 'OBSERVED' : 'PENDING', pass: Boolean(facts.utilizationPercent) }
  ];

  return (
    <div className="h-full flex flex-col gap-2.5 overflow-hidden animate-fade-in select-none">
      {/* Consolidated Header Banner (Clean White Surface) */}
      <div className="flex items-center justify-between gap-3 p-3 rounded-xl border border-slate-200/90 bg-white shadow-xs shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-teal-50 border border-teal-200 shrink-0 text-teal-600">
            <GiantIcon type="target" size="sm" glow={false} />
          </div>
          <div>
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-teal-700 font-bold">
              <span>Capital Program Matching & Underwriting Probability</span>
              <span className="text-slate-300">·</span>
              <span className="text-slate-500 font-medium">Target: {facts.fundingTargetLabel}</span>
            </div>
            <h1 className="text-base font-bold text-slate-900 tracking-tight">
              Funding Readiness Command · {fundingPrograms.length} Facilities Available
            </h1>
          </div>
        </div>

        <button
          onClick={() => setActiveTab('request-review')}
          className="px-3.5 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs transition-all shadow-xs cursor-pointer whitespace-nowrap active:scale-95"
        >
          Submit Committee Dossier →
        </button>
      </div>

      {/* 2-Column Consolidated Cockpit (Fits without scrolling) */}
      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-12 gap-2.5 overflow-hidden">
        {/* Left: 6 Readiness Signals (Clean White Surface - 5 cols) */}
        <div className="lg:col-span-5 rounded-xl border border-slate-200/90 bg-white p-3 flex flex-col justify-between shadow-xs overflow-hidden">
          <div className="flex items-center justify-between pb-1.5 border-b border-slate-100 shrink-0">
            <span className="text-[10px] font-bold text-teal-700 uppercase tracking-wider">
              Underwriting Underpinning Signals
            </span>
            <span className="text-[10px] font-mono text-slate-400">{readinessSignals.filter((signal) => signal.pass).length} of {readinessSignals.length} Observed</span>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto space-y-1.5 pt-2 pr-1 scrollbar-thin">
            {readinessSignals.map((signal, idx) => (
              <div
                key={idx}
                className="p-2 rounded-lg border border-slate-200 bg-slate-50/80 flex items-center justify-between gap-2"
              >
                <div className="min-w-0">
                  <div className="text-xs font-bold text-slate-900 truncate">{signal.label}</div>
                  <div className="text-[11px] text-slate-600 font-mono mt-0.5">{signal.score}</div>
                </div>

                <span
                  className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded shrink-0 ${
                    signal.status === 'READY'
                      ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                      : signal.status === 'BLOCKED'
                      ? 'bg-rose-100 text-rose-800 border border-rose-200'
                      : 'bg-amber-100 text-amber-800 border border-amber-200'
                  }`}
                >
                  {signal.status}
                </span>
              </div>
            ))}
          </div>

          {/* Clyde Funding Tip (Clean Light Highlight) */}
          <div className="mt-2 p-2 rounded-lg border border-teal-200/80 bg-teal-50/50 text-slate-800 shadow-xs flex items-center justify-between text-xs">
            <div className="text-[11px] text-slate-600 leading-tight">
              <span className="text-teal-800 font-bold block">⚡ Clyde Underwriting Tip</span>
              Equipment financing ($125k) is 100% pre-cleared right now.
            </div>
            <button
              onClick={() => openClydeWithPrompt("Can I draw the $125k equipment lease and the $250k line at the same time?")}
              className="text-[10px] text-teal-700 font-bold hover:underline shrink-0 ml-2 cursor-pointer"
            >
              Ask Clyde →
            </button>
          </div>
        </div>

        {/* Right: 4 Matched Funding Facilities (Clean White Surface - 7 cols) */}
        <div className="lg:col-span-7 rounded-xl border border-slate-200/90 bg-white p-3 flex flex-col justify-between shadow-xs overflow-hidden">
          <div className="flex items-center justify-between pb-1.5 border-b border-slate-100 shrink-0">
            <span className="text-[10px] font-bold text-teal-700 uppercase tracking-wider">
              Matched Lending Programs
            </span>
            <span className="text-[10px] font-mono text-slate-400">Institutional Term Sheets</span>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto space-y-2 pt-2 pr-1 scrollbar-thin">
            {fundingPrograms.map((prog, idx) => (
              <div
                key={idx}
                className="p-2.5 rounded-lg border border-slate-200 bg-slate-50/80 hover:bg-white hover:border-slate-300 transition-all text-xs"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <h4 className="font-bold text-slate-900 text-xs truncate">{prog.name}</h4>
                      <span className="font-mono text-teal-700 text-xs font-bold shrink-0">
                        {prog.amount}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-500 mt-0.5 flex items-center gap-2">
                      <span>{prog.type}</span>
                      <span>·</span>
                      <span className="text-slate-700 font-medium">{prog.rate}</span>
                    </div>
                    <p className="text-[11px] text-slate-600 mt-1 line-clamp-1">
                      {prog.holdReason}
                    </p>
                  </div>

                  <div className="text-right shrink-0 flex flex-col items-end gap-1.5">
                    <span
                      className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded ${
                        prog.readinessStatus === 'READY'
                          ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                          : prog.readinessStatus === 'BLOCKED'
                          ? 'bg-rose-100 text-rose-800 border border-rose-200'
                          : 'bg-amber-100 text-amber-800 border border-amber-200'
                      }`}
                    >
                      {prog.readinessStatus} ({prog.readinessPercent}%)
                    </span>
                    <button
                      onClick={() => setActiveTab(prog.actionTab as any)}
                      className="px-2.5 py-1 rounded bg-teal-600 hover:bg-teal-700 text-white font-bold text-[10px] transition-all shadow-xs cursor-pointer whitespace-nowrap active:scale-95"
                    >
                      {prog.actionLabel} →
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
