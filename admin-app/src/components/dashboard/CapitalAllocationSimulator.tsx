import React, { useState, useMemo } from 'react';
import {
  Sliders,
  DollarSign,
  TrendingUp,
  ShieldCheck,
  AlertTriangle,
  Sparkles,
  RefreshCw,
  ArrowRight,
  CheckCircle2,
  PieChart,
  Layers,
  FileText,
  Clock,
  Briefcase
} from 'lucide-react';
import { useNexus } from '../../context/NexusContext';

interface AllocationBuckets {
  trading: number; // %
  businessHub: number; // %
  clydeCredit: number; // %
  operatingReserves: number; // %
}

const PRESET_SCENARIOS: Array<{
  id: string;
  name: string;
  description: string;
  badge: string;
  allocations: AllocationBuckets;
}> = [
  {
    id: 'conservative',
    name: 'Conservative Capital Preservation',
    description: 'Prioritizes runway and debt-free non-dilutive credit lines. Zero speculative trading risk.',
    badge: 'LOW RISK · HIGH RUNWAY',
    allocations: {
      trading: 5,
      businessHub: 15,
      clydeCredit: 25,
      operatingReserves: 55
    }
  },
  {
    id: 'balanced',
    name: 'Balanced Autonomous Growth',
    description: 'Optimal balance between SaaS commercialization, modest quantitative alpha, and token buffers.',
    badge: 'RECOMMENDED · DUAL ENGINE',
    allocations: {
      trading: 20,
      businessHub: 40,
      clydeCredit: 15,
      operatingReserves: 25
    }
  },
  {
    id: 'aggressive',
    name: 'Aggressive Commercial Velocity',
    description: 'Maximizes Atlas market launch speed and multi-pair forex paper tests. Tighter cash reserve.',
    badge: 'HIGH VELOCITY · EXPANSION',
    allocations: {
      trading: 30,
      businessHub: 50,
      clydeCredit: 10,
      operatingReserves: 10
    }
  }
];

export const CapitalAllocationSimulator: React.FC = () => {
  const { sendMessage, addRayDecision } = useNexus();
  const [totalCapital, setTotalCapital] = useState<number>(75000);
  const [allocations, setAllocations] = useState<AllocationBuckets>({
    trading: 20,
    businessHub: 40,
    clydeCredit: 15,
    operatingReserves: 25
  });
  const [submittedToDesk, setSubmittedToDesk] = useState(false);

  // Normalize slider updates so total always equals 100%
  const handleSliderChange = (bucket: keyof AllocationBuckets, value: number) => {
    const clampedVal = Math.max(0, Math.min(100, value));
    const currentVal = allocations[bucket];
    const diff = clampedVal - currentVal;

    // Distribute diff proportionally among other buckets
    const otherKeys = (Object.keys(allocations) as Array<keyof AllocationBuckets>).filter(k => k !== bucket);
    const sumOthers = otherKeys.reduce((acc, k) => acc + allocations[k], 0);

    const updated = { ...allocations, [bucket]: clampedVal };

    if (sumOthers > 0) {
      otherKeys.forEach(k => {
        const share = allocations[k] / sumOthers;
        updated[k] = Math.max(0, Math.round(allocations[k] - diff * share));
      });
    }

    // Fix rounding discrepancies to ensure exact sum = 100
    const finalSum = Object.values(updated).reduce((a, b) => a + b, 0);
    const roundingError = 100 - finalSum;
    updated.operatingReserves = Math.max(0, updated.operatingReserves + roundingError);

    setAllocations(updated);
  };

  const handleApplyPreset = (preset: typeof PRESET_SCENARIOS[0]) => {
    setAllocations(preset.allocations);
    sendMessage(`Loaded Capital Allocation preset: "${preset.name}".`);
  };

  // Calculations
  const metrics = useMemo(() => {
    const tradingAmount = (totalCapital * allocations.trading) / 100;
    const businessHubAmount = (totalCapital * allocations.businessHub) / 100;
    const clydeCreditAmount = (totalCapital * allocations.clydeCredit) / 100;
    const reservesAmount = (totalCapital * allocations.operatingReserves) / 100;

    // Projected Monthly Revenue Velocity based on allocation
    // Trading return: ~3.5% monthly on trading capital
    const tradingReturn = tradingAmount * 0.035;
    // Business Hub velocity: ~28% monthly return on active commercial projects
    const businessHubReturn = businessHubAmount * 0.28;
    // Clyde credit line expansion leverage: unlocks 3x non-dilutive facility
    const clydeCreditLeverage = clydeCreditAmount * 3.2;
    const totalMonthlyVelocity = tradingReturn + businessHubReturn;

    // Capital At Risk (Trading + Unproven Business Projects)
    // 70% of business hub capital at risk, 80% of trading capital at risk, 0% of reserves at risk
    const capitalAtRisk = tradingAmount * 0.8 + businessHubAmount * 0.7;
    const capitalAtRiskPct = (capitalAtRisk / totalCapital) * 100;

    // Estimated Runway in Months assuming $3,800 / mo baseline burn
    const monthlyBurn = 3800;
    const netMonthlyCashflow = totalMonthlyVelocity - monthlyBurn;
    const runwayMonths =
      netMonthlyCashflow >= 0
        ? 99 // Self-sustaining
        : Number((reservesAmount / Math.abs(netMonthlyCashflow)).toFixed(1));

    // Maximum acceptable drawdown threshold
    const maxDrawdownThreshold = tradingAmount * 0.05 + businessHubAmount * 0.15;

    // Capital efficiency score (Revenue Velocity / Capital At Risk * 100)
    const efficiencyScore = capitalAtRisk > 0 ? ((totalMonthlyVelocity * 12) / capitalAtRisk).toFixed(2) : '0';

    return {
      tradingAmount,
      businessHubAmount,
      clydeCreditAmount,
      reservesAmount,
      totalMonthlyVelocity,
      capitalAtRisk,
      capitalAtRiskPct,
      runwayMonths,
      maxDrawdownThreshold,
      efficiencyScore,
      clydeCreditLeverage
    };
  }, [totalCapital, allocations]);

  const handleQueueForRay = () => {
    const decisionId = `dec-sim-${Date.now()}`;
    addRayDecision({
      id: decisionId,
      department: 'Finance',
      title: `Capital Allocation Plan: $${totalCapital.toLocaleString()} Deployment Strategy`,
      subtitle: `Simulated Allocation · Business Hub (${allocations.businessHub}%) / Trading (${allocations.trading}%)`,
      whatNexusIsAsking: `Authorize strategic capital rebalancing across 4 departmental envelopes.`,
      plainEnglishExplanation: `Allocates $${metrics.businessHubAmount.toLocaleString()} to Atlas commercialization, $${metrics.tradingAmount.toLocaleString()} to paper/execution envelope, $${metrics.clydeCreditAmount.toLocaleString()} for Clyde tradeline collateral, and reserves $${metrics.reservesAmount.toLocaleString()} for runway.`,
      financialImpact: `Projected +$${Math.round(metrics.totalMonthlyVelocity).toLocaleString()}/mo revenue velocity with $${Math.round(metrics.capitalAtRisk).toLocaleString()} at-risk envelope.`,
      riskLevel: allocations.trading > 25 || allocations.operatingReserves < 15 ? 'HIGH' : 'LOW',
      status: 'PENDING',
      timestamp: 'Just now',
      nextAutonomousStep: 'Finance logs rebalancing ledger entry and programs departmental spend caps.',
      urgency: 'HIGH',
      capitalAmount: `$${totalCapital.toLocaleString()}`,
      notebookRef: 'nb://finance/capital-sim-allocation.ipynb'
    });

    setSubmittedToDesk(true);
    sendMessage(
      `Capital scenario queued on Ray's Desk for review! Total: $${totalCapital.toLocaleString()} (Reserves: ${allocations.operatingReserves}%, Business Hub: ${allocations.businessHub}%).`
    );
    setTimeout(() => setSubmittedToDesk(false), 4000);
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200/90 shadow-2xs p-4 sm:p-5 space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-emerald-600 text-white flex items-center justify-center">
              <Sliders className="w-4 h-4" />
            </div>
            <h2 className="text-sm font-black text-slate-900 tracking-tight flex items-center gap-2">
              <span>Interactive Capital & Strategy Allocation Simulator</span>
              <span className="text-[10px] text-emerald-800 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded font-black uppercase">
                SCENARIO MODELER
              </span>
            </h2>
          </div>
          <p className="text-[11px] text-slate-500 font-medium pt-0.5">
            Model capital deployment tradeoffs across quantitative trading, Atlas business creation, and operating reserves.
          </p>
        </div>

        {/* Preset Selector */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] font-bold text-slate-400 uppercase">Presets:</span>
          {PRESET_SCENARIOS.map(preset => (
            <button
              key={preset.id}
              type="button"
              onClick={() => handleApplyPreset(preset)}
              className="px-2 py-1 rounded-md text-[10px] font-bold border border-slate-200 hover:border-slate-300 text-slate-700 bg-slate-50 hover:bg-white transition-all cursor-pointer"
            >
              {preset.name.split(' ')[0]}
            </button>
          ))}
        </div>
      </div>

      {/* Main Interactive Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* LEFT COLUMN: Controls & Sliders (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          {/* Total Capital Slider */}
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 space-y-2">
            <div className="flex items-center justify-between">
              <div>
                <label htmlFor="capital-envelope-slider" className="text-xs font-black text-slate-900 block">Total Deployment Capital Envelope</label>
                <span className="text-[10px] text-slate-500 font-medium">Liquid & committed funds available for strategic allocation</span>
              </div>
              <div className="text-right">
                <span className="text-base font-black text-emerald-600 font-mono">
                  ${totalCapital.toLocaleString()}
                </span>
              </div>
            </div>

            <input
              id="capital-envelope-slider"
              type="range"
              min={10000}
              max={250000}
              step={5000}
              value={totalCapital}
              onChange={e => setTotalCapital(Number(e.target.value))}
              className="w-full accent-emerald-600 cursor-pointer"
            />

            <div className="flex justify-between text-[10px] text-slate-400 font-mono">
              <span>$10,000</span>
              <span>$100,000</span>
              <span>$250,000</span>
            </div>
          </div>

          {/* Allocation Percentages Sliders */}
          <div className="space-y-3 p-3.5 rounded-xl border border-slate-200 bg-white">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <span className="text-xs font-black text-slate-900 uppercase tracking-tight">
                Departmental Allocation Weights
              </span>
              <span className="text-[10px] font-mono font-bold text-slate-500">
                Sum: {Object.values(allocations).reduce((a, b) => a + b, 0)}%
              </span>
            </div>

            {/* 1. Business Hub & Ventures */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5 font-bold text-slate-800">
                  <span className="w-2 h-2 rounded-full bg-blue-500" />
                  <label htmlFor="business-hub-slider">Business Hub &amp; Atlas Ventures ({allocations.businessHub}%)</label>
                </div>
                <span className="font-mono font-bold text-slate-900">
                  ${Math.round(metrics.businessHubAmount).toLocaleString()}
                </span>
              </div>
              <input
                id="business-hub-slider"
                type="range"
                min={0}
                max={100}
                value={allocations.businessHub}
                onChange={e => handleSliderChange('businessHub', Number(e.target.value))}
                className="w-full accent-blue-600 cursor-pointer"
              />
              <span className="text-[9.5px] text-slate-400 block">
                GovCon proposals, SaaS middleware prototypes, and client acquisition pipelines.
              </span>
            </div>

            {/* 2. Quantitative Trading & Alpha */}
            <div className="space-y-1 pt-1">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5 font-bold text-slate-800">
                  <span className="w-2 h-2 rounded-full bg-amber-500" />
                  <label htmlFor="trading-alpha-slider">Quantitative Trading &amp; Alpha ({allocations.trading}%)</label>
                </div>
                <span className="font-mono font-bold text-slate-900">
                  ${Math.round(metrics.tradingAmount).toLocaleString()}
                </span>
              </div>
              <input
                id="trading-alpha-slider"
                type="range"
                min={0}
                max={100}
                value={allocations.trading}
                onChange={e => handleSliderChange('trading', Number(e.target.value))}
                className="w-full accent-amber-500 cursor-pointer"
              />
              <span className="text-[9.5px] text-slate-400 block">
                Mercury execution envelope, FIX gateway feeds, and model backtesting compute.
              </span>
            </div>

            {/* 3. Clyde Credit & Non-Dilutive Facility */}
            <div className="space-y-1 pt-1">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5 font-bold text-slate-800">
                  <span className="w-2 h-2 rounded-full bg-indigo-500" />
                  <label htmlFor="clyde-credit-slider">Clyde Tradelines &amp; Credit Setup ({allocations.clydeCredit}%)</label>
                </div>
                <span className="font-mono font-bold text-slate-900">
                  ${Math.round(metrics.clydeCreditAmount).toLocaleString()}
                </span>
              </div>
              <input
                id="clyde-credit-slider"
                type="range"
                min={0}
                max={100}
                value={allocations.clydeCredit}
                onChange={e => handleSliderChange('clydeCredit', Number(e.target.value))}
                className="w-full accent-indigo-500 cursor-pointer"
              />
              <span className="text-[9.5px] text-slate-400 block">
                Secured tradeline deposits unlocking ~${Math.round(metrics.clydeCreditLeverage).toLocaleString()} in credit facilities.
              </span>
            </div>

            {/* 4. Operating Reserves & Runway */}
            <div className="space-y-1 pt-1">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5 font-bold text-slate-800">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  <label htmlFor="reserves-runway-slider">Operating Reserves &amp; Token Runway ({allocations.operatingReserves}%)</label>
                </div>
                <span className="font-mono font-bold text-slate-900">
                  ${Math.round(metrics.reservesAmount).toLocaleString()}
                </span>
              </div>
              <input
                id="reserves-runway-slider"
                type="range"
                min={0}
                max={100}
                value={allocations.operatingReserves}
                onChange={e => handleSliderChange('operatingReserves', Number(e.target.value))}
                className="w-full accent-emerald-500 cursor-pointer"
              />
              <span className="text-[9.5px] text-slate-400 block">
                Guaranteed cash buffer covering OpenRouter AI token burn and server recovery.
              </span>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Real-Time Scenario Telemetry & Action (5 cols) */}
        <div className="lg:col-span-5 space-y-3 flex flex-col justify-between">
          <div className="p-4 rounded-xl bg-slate-900 text-white space-y-3.5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="text-[10px] font-black uppercase tracking-wider text-emerald-400">
                Simulated Operating Impact
              </span>
              <span className="text-[9px] font-mono text-slate-400">Deterministic Model</span>
            </div>

            {/* Metric 1: Monthly Revenue Velocity */}
            <div className="flex items-center justify-between">
              <div>
                <span className="text-[10px] text-slate-400 block uppercase">Projected Monthly Velocity</span>
                <span className="text-xl font-black text-emerald-400 font-mono">
                  +${Math.round(metrics.totalMonthlyVelocity).toLocaleString()}
                  <span className="text-xs text-slate-400 font-normal"> / mo</span>
                </span>
              </div>
              <div className="text-right">
                <span className="text-[10px] text-slate-400 block uppercase">Efficiency Score</span>
                <span className="text-sm font-bold text-slate-200 font-mono">
                  {metrics.efficiencyScore}x
                </span>
              </div>
            </div>

            {/* Metric 2: Capital At Risk */}
            <div className="pt-2 border-t border-slate-800 flex items-center justify-between">
              <div>
                <span className="text-[10px] text-slate-400 block uppercase">Capital At Risk</span>
                <span className="text-sm font-black text-rose-400 font-mono">
                  ${Math.round(metrics.capitalAtRisk).toLocaleString()} ({Math.round(metrics.capitalAtRiskPct)}%)
                </span>
              </div>
              <div className="text-right">
                <span className="text-[10px] text-slate-400 block uppercase">Max Drawdown Buffer</span>
                <span className="text-xs font-bold text-amber-400 font-mono">
                  ${Math.round(metrics.maxDrawdownThreshold).toLocaleString()}
                </span>
              </div>
            </div>

            {/* Metric 3: Runway Extension */}
            <div className="pt-2 border-t border-slate-800 flex items-center justify-between">
              <div>
                <span className="text-[10px] text-slate-400 block uppercase">Estimated Cash Runway</span>
                <span className="text-sm font-black text-blue-400">
                  {metrics.runwayMonths >= 99 ? 'Self-Sustaining (>24 mo)' : `${metrics.runwayMonths} Months`}
                </span>
              </div>
              <div className="text-right">
                <span className="text-[10px] text-slate-400 block uppercase">Credit Power</span>
                <span className="text-xs font-bold text-indigo-400 font-mono">
                  +${Math.round(metrics.clydeCreditLeverage).toLocaleString()}
                </span>
              </div>
            </div>

            {/* Allocation Visual Bar */}
            <div className="pt-2">
              <div className="text-[10px] text-slate-400 mb-1 flex justify-between">
                <span>Allocation Visual</span>
                <span>100% Total</span>
              </div>
              <div className="h-2 rounded-full bg-slate-800 flex overflow-hidden">
                <div style={{ width: `${allocations.businessHub}%` }} className="bg-blue-500" title="Business Hub" />
                <div style={{ width: `${allocations.trading}%` }} className="bg-amber-500" title="Trading" />
                <div style={{ width: `${allocations.clydeCredit}%` }} className="bg-indigo-500" title="Clyde Credit" />
                <div style={{ width: `${allocations.operatingReserves}%` }} className="bg-emerald-500" title="Reserves" />
              </div>
            </div>
          </div>

          {/* Action Trigger Block */}
          <div className="space-y-2">
            <button
              type="button"
              onClick={handleQueueForRay}
              disabled={submittedToDesk}
              className={`w-full py-2.5 px-4 rounded-xl font-black text-xs flex items-center justify-center gap-2 cursor-pointer transition-all shadow-md ${
                submittedToDesk
                  ? 'bg-emerald-600 text-white'
                  : 'bg-slate-900 hover:bg-slate-800 text-white active:scale-98'
              }`}
            >
              {submittedToDesk ? (
                <>
                  <CheckCircle2 className="w-4 h-4 text-white" />
                  <span>Submitted to Ray&apos;s Desk!</span>
                </>
              ) : (
                <>
                  <ArrowRight className="w-4 h-4 text-amber-400" />
                  <span>Queue Simulated Plan for Ray&apos;s Strategic Sign-Off</span>
                </>
              )}
            </button>

            <p className="text-[10px] text-slate-500 text-center font-medium">
              Simulation only. No funds are moved without human-in-the-loop sign-off by Ray Davis.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
