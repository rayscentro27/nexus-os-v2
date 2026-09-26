import React, { useState } from 'react';
import { usePortal } from '../../context/PortalContext';
import { GiantIcon } from '../common/GiantIcon';

export const CreditUtilizationView: React.FC = () => {
  const { simulatedBalance, updateRevolvingBalance, completeMission, openClydeWithPrompt, facts, liveMode } = usePortal();

  const totalCreditLimit = liveMode ? 0 : 45000;
  const targetUtilizationRate = (facts.utilizationTargetPercent || 10) / 100;
  const targetBalance = totalCreditLimit * targetUtilizationRate; // $4,500

  // Local state for interactive slider
  const [paydownAmount, setPaydownAmount] = useState<number>(2000);

  const currentBalance = Math.max(0, simulatedBalance - paydownAmount);
  const currentUtilization = liveMode ? facts.utilizationPercent : ((currentBalance / totalCreditLimit) * 100);
  const distanceToTarget = Math.max(0, currentBalance - targetBalance);

  // Accounts
  const accounts = liveMode ? [] : [
    {
      name: 'Chase Ink Business Unlimited',
      issuer: 'JPMorgan Chase',
      balance: Math.max(500, 5200 - paydownAmount * 0.7),
      limit: 25000,
      apr: '18.24% Variable',
      closingDate: 'Closes 14th'
    },
    {
      name: 'Amex Blue Business Plus',
      issuer: 'American Express',
      balance: Math.max(300, 2350 - paydownAmount * 0.2),
      limit: 12000,
      apr: '16.99% Variable',
      closingDate: 'Closes 22nd'
    },
    {
      name: 'Capital One Spark Cash Plus',
      issuer: 'Capital One',
      balance: Math.max(200, 1000 - paydownAmount * 0.1),
      limit: 8000,
      apr: 'Pay-in-Full Line',
      closingDate: 'Closes 3rd'
    }
  ];

  // Semicircular Gauge Geometry
  const gaugeAngle = Math.min(180, (currentUtilization / 100) * 180);
  const strokeDash = (gaugeAngle / 180) * 283;

  return (
    <div className="h-full flex flex-col gap-2.5 overflow-hidden animate-fade-in select-none">
      {/* Consolidated Header Banner (Clean White Surface) */}
      <div className="flex items-center justify-between gap-3 p-3 rounded-xl border border-slate-200/90 bg-white shadow-xs shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-amber-50 border border-amber-200 shrink-0 text-amber-600">
            <GiantIcon type="gauge" size="sm" glow={false} />
          </div>
          <div>
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-amber-700 font-bold">
              <span>Revolving Balance Optimization</span>
              <span className="text-slate-300">·</span>
              <span className="text-slate-500 font-medium">Aggregate Limit: {liveMode ? 'Not available' : '$45,000'}</span>
            </div>
            <h1 className="text-base font-bold text-slate-900 tracking-tight">
              Credit Utilization Command · Target &lt;{facts.utilizationTargetPercent}%
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs">
          <div className="text-right hidden sm:block">
            <span className="text-[10px] text-slate-400">Total Revolving Limit</span>
            <div className="font-mono font-bold text-slate-900 tabular-nums">{liveMode ? 'Not available' : '$45,000'}</div>
          </div>
          {/* Ask Clyde Strategy (Clean Light Highlight) */}
          <button
            onClick={() => openClydeWithPrompt("What is the quickest way to reduce revolving balance without hurting cash flow?")}
            className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-teal-800 font-bold text-xs transition-all shadow-xs cursor-pointer"
          >
            Ask Clyde Strategy
          </button>
        </div>
      </div>

      {/* 3-Column Consolidated Cockpit (Fits without scrolling) */}
      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-12 gap-2.5 overflow-hidden">
        {/* Left: Semicircular Gauge (Clean Light Card - 4 cols) */}
        <div className="lg:col-span-4 rounded-xl border border-slate-200/90 bg-white p-3 flex flex-col justify-between shadow-xs text-slate-900">
          <div className="text-center">
            <span className="text-[10px] font-bold text-teal-800 uppercase tracking-wider">
              Composite Utilization
            </span>
            <h3 className="text-xs font-bold text-slate-900 mt-0.5">Aggregate Ratio Gauge</h3>
          </div>

          {/* Semicircular Gauge SVG */}
          <div className="relative flex flex-col items-center justify-center my-auto py-2">
            <svg className="w-56 h-32 overflow-visible" viewBox="0 0 200 115">
              <defs>
                <linearGradient id="gaugeGradCompact" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#00D2B4" />
                  <stop offset="50%" stopColor="#38BDF8" />
                  <stop offset="100%" stopColor="#F59E0B" />
                </linearGradient>
              </defs>
              {/* Background Track */}
              <path
                d="M 20 100 A 80 80 0 0 1 180 100"
                fill="none"
                stroke="#F1F5F9"
                strokeWidth="16"
                strokeLinecap="round"
              />
              {/* Active Progress Arc */}
              <path
                d="M 20 100 A 80 80 0 0 1 180 100"
                fill="none"
                stroke="url(#gaugeGradCompact)"
                strokeWidth="16"
                strokeDasharray="283"
                strokeDashoffset={283 - strokeDash}
                strokeLinecap="round"
                style={{ transition: 'stroke-dashoffset 0.5s ease' }}
              />
              {/* 10% Target Marker */}
              <circle cx="48" cy="44" r="3.5" fill="#00D2B4" />
            </svg>

            {/* Centered Gauge Value */}
            <div className="absolute bottom-2 flex flex-col items-center text-center">
              <span className="text-3xl font-black text-slate-900 tracking-tight tabular-nums">
                {currentUtilization.toFixed(1)}%
              </span>
              <span className="text-[10px] font-semibold text-slate-600">
                {liveMode ? 'Live utilization' : `$${Math.round(currentBalance).toLocaleString()} / $45,000`}
              </span>
            </div>
          </div>

          {/* Target Indicators */}
          <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px]">
            <div>
              <span className="text-[10px] text-slate-500">Target Level</span>
              <div className="font-bold text-teal-700 font-mono">&lt; {facts.utilizationTargetPercent}%</div>
            </div>
            <div className="text-right">
              <span className="text-[10px] text-slate-500">Distance to Prime</span>
              <div className="font-bold text-amber-700 font-mono">
                {distanceToTarget > 0 ? `$${Math.round(distanceToTarget).toLocaleString()}` : 'GOAL REACHED!'}
              </div>
            </div>
          </div>
        </div>

        {/* Center: Interactive Paydown Simulator (Clean White Surface - 4 cols) */}
        <div className="lg:col-span-4 rounded-xl border border-slate-200/90 bg-white p-3 flex flex-col justify-between shadow-xs">
          <div>
            <div className="flex items-center justify-between pb-1.5 border-b border-slate-100">
              <span className="text-[10px] font-bold text-teal-700 uppercase tracking-wider">
                Interactive Simulator
              </span>
              <span className="text-[10px] font-mono text-emerald-700 font-bold">
                +{Math.round((paydownAmount / 4000) * 14)} Readiness Pts
              </span>
            </div>

            <div className="mt-3">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-600 font-medium">Simulate Paydown Amount:</span>
                <span className="text-base font-bold font-mono text-slate-900 tabular-nums">
                  ${paydownAmount.toLocaleString()}
                </span>
              </div>

              <input
                type="range"
                min="0"
                max="8000"
                step="250"
                value={paydownAmount}
                aria-label="Simulate Paydown Amount"
                onChange={(e) => setPaydownAmount(Number(e.target.value))}
                className="w-full mt-2 accent-teal-600 cursor-pointer h-2 bg-slate-200 rounded-lg"
              />

              <div className="flex justify-between text-[10px] text-slate-400 mt-1 font-mono">
                <span>$0</span>
                <span>$4,050 (Target)</span>
                <span>$8,000</span>
              </div>
            </div>

            {/* Impact Calculation Box */}
            <div className="mt-3 p-2.5 rounded-lg border border-slate-200 bg-slate-50/80 space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-600">Projected Utilization:</span>
                <span className="font-bold text-teal-700 font-mono">
                  {currentUtilization.toFixed(1)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-600">Estimated Annual APR Savings:</span>
                <span className="font-bold text-emerald-700 font-mono">
                  ${Math.round(paydownAmount * 0.178).toLocaleString()} / yr
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-600">Underwriting Grade:</span>
                <span className="font-bold text-slate-900">
                  {currentUtilization < 10 ? 'Prime Tier 1 (Maximum Limit)' : 'Prime Tier 2 (Standard)'}
                </span>
              </div>
            </div>
          </div>

          <button
            onClick={() => {
              updateRevolvingBalance(Math.round(currentBalance));
              completeMission('mission-utilization');
            }}
            className="w-full mt-2 py-2 bg-gradient-to-r from-teal-600 to-sky-600 hover:from-teal-500 hover:to-sky-500 text-white font-bold text-xs rounded-lg transition-all shadow-xs active:scale-95 cursor-pointer text-center"
          >
            Apply Paydown Plan (+14 Points)
          </button>
        </div>

        {/* Right: Active Revolving Accounts (Clean White Surface - 4 cols) */}
        <div className="lg:col-span-4 rounded-xl border border-slate-200/90 bg-white p-3 flex flex-col justify-between shadow-xs overflow-hidden">
          <div className="flex items-center justify-between pb-1.5 border-b border-slate-100 shrink-0">
            <span className="text-[10px] font-bold text-teal-700 uppercase tracking-wider">
              Revolving Trade Lines
            </span>
            <span className="text-[10px] font-mono text-slate-400">3 Accounts</span>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto space-y-1.5 pt-2 pr-1 scrollbar-thin">
            {accounts.map((acc) => (
              <div
                key={acc.name}
                className="p-2 rounded-lg border border-slate-200 bg-slate-50/80 text-xs"
              >
                <div className="flex items-start justify-between">
                  <div className="min-w-0 flex-1">
                    <h4 className="font-bold text-slate-900 truncate text-[11px]">{acc.name}</h4>
                    <p className="text-[10px] text-slate-500">{acc.issuer}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <span className="font-bold font-mono text-slate-900 text-xs">
                      ${Math.round(acc.balance).toLocaleString()}
                    </span>
                    <span className="text-[10px] text-slate-400 block">
                      of ${acc.limit.toLocaleString()}
                    </span>
                  </div>
                </div>

                <div className="mt-1 pt-1 border-t border-slate-200/80 flex items-center justify-between text-[10px] text-slate-500">
                  <span>{acc.apr}</span>
                  <span className="text-teal-700 font-medium">{acc.closingDate}</span>
                </div>
              </div>
            ))}

            {/* Clyde Advisory Callout (Clean Light Accent) */}
            <div className="p-2 rounded-lg border border-teal-200/80 bg-teal-50/50 text-[11px] text-slate-700 shadow-xs">
              <span className="font-bold text-teal-800 block">💡 Underwriter Timing Tip</span>
              Pay balances 3 business days before the monthly statement closing date so lower balances are reported to bureaus.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
