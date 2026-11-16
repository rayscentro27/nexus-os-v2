import React, { useState } from 'react';
import { 
  ShieldCheck, 
  ShieldAlert, 
  AlertTriangle, 
  CheckCircle2, 
  Activity, 
  Clock, 
  Sliders, 
  FileText,
  AlertOctagon,
  Percent,
  DollarSign
} from 'lucide-react';
import { RiskLimitItem, KillSwitchScope } from '../../types';

interface RiskCenterViewProps {
  riskLimits: RiskLimitItem[];
  killSwitchScope: KillSwitchScope;
  onOpenKillSwitchModal: () => void;
  onUpdateLimit: (id: string, newLimit: number) => void;
  compactMode?: boolean;
}

export const RiskCenterView: React.FC<RiskCenterViewProps> = ({
  riskLimits,
  killSwitchScope,
  onOpenKillSwitchModal,
  onUpdateLimit,
  compactMode = true,
}) => {
  const [selectedLimit, setSelectedLimit] = useState<RiskLimitItem | null>(null);
  const [editVal, setEditVal] = useState<number>(0);
  const [stressTestMode, setStressTestMode] = useState<string | null>(null);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'SAFE':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'WARNING':
        return 'bg-amber-50 text-amber-700 border-amber-200 font-bold';
      case 'BREACH':
        return 'bg-rose-100 text-rose-800 border-rose-300 font-black animate-pulse';
      case 'TRADING_PAUSED':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300 font-black';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  const handleOpenEdit = (limit: RiskLimitItem) => {
    setSelectedLimit(limit);
    setEditVal(limit.limitValue);
  };

  const handleSaveEdit = () => {
    if (selectedLimit) {
      onUpdateLimit(selectedLimit.id, editVal);
      setSelectedLimit(null);
    }
  };

  return (
    <div className="h-full flex flex-col min-h-0 space-y-1.5 overflow-hidden">
      {/* Top Banner & Safety Policy */}
      <div className="bg-white rounded-xl p-2.5 border border-slate-200/90 shadow-2xs space-y-1.5 shrink-0">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span className="text-xs font-black text-slate-900">Quantitative Risk Governance Center</span>
            <span className="text-[10px] font-bold px-2 py-0.2 rounded-full bg-emerald-100 text-emerald-800">
              Policy RP-2026.4 Active
            </span>
            <span className="text-[11px] text-slate-400 hidden md:inline">
              • Strict mathematical guardrails, portfolio exposure & circuit breakers
            </span>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={onOpenKillSwitchModal}
              className="px-2.5 py-1 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs font-bold border border-rose-200 transition-all flex items-center gap-1.5 cursor-pointer"
            >
              <ShieldAlert className="w-3.5 h-3.5" />
              <span>Circuit Breaker</span>
            </button>
          </div>
        </div>

        {/* Stress Test Simulator Chips */}
        <div className="pt-1 border-t border-slate-100 flex flex-wrap items-center gap-1.5 text-xs">
          <span className="text-slate-500 font-medium text-[11px]">Stress Tests:</span>
          <button
            type="button"
            onClick={() => setStressTestMode(stressTestMode === '2020-covid' ? null : '2020-covid')}
            className={`px-2 py-0.5 rounded-md text-[10px] font-bold transition-all cursor-pointer ${
              stressTestMode === '2020-covid' ? 'bg-purple-600 text-white shadow-2xs' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            2020 COVID Shock
          </button>
          <button
            type="button"
            onClick={() => setStressTestMode(stressTestMode === '2022-rate' ? null : '2022-rate')}
            className={`px-2 py-0.5 rounded-md text-[10px] font-bold transition-all cursor-pointer ${
              stressTestMode === '2022-rate' ? 'bg-purple-600 text-white shadow-2xs' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            2022 Fed Rate Hike
          </button>
          <button
            type="button"
            onClick={() => setStressTestMode(stressTestMode === 'crypto-liquidation' ? null : 'crypto-liquidation')}
            className={`px-2 py-0.5 rounded-md text-[10px] font-bold transition-all cursor-pointer ${
              stressTestMode === 'crypto-liquidation' ? 'bg-purple-600 text-white shadow-2xs' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            Crypto Flash Crash
          </button>
        </div>

        {/* Visual VaR & Drawdown Telemetry Strip */}
        <div className="pt-1.5 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono">
          <div className="flex items-center gap-2">
            <span className="text-slate-400 font-bold uppercase text-[9px]">Portfolio DD:</span>
            <div className="w-28 h-2 bg-slate-100 rounded-full overflow-hidden relative border border-slate-200">
              <div 
                className="bg-gradient-to-r from-emerald-500 to-amber-500 h-full rounded-full" 
                style={{ width: '35%' }} 
                title="Current Drawdown: 1.4% (Hard limit: 4.0%)" 
              />
            </div>
            <span className="text-emerald-700 font-black">1.4% / 4.0%</span>
            <span className="text-emerald-600 font-bold bg-emerald-50 px-1 rounded border border-emerald-200">SAFE</span>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-slate-500">
              1-Day VaR (99%): <strong className="text-slate-900 font-bold">$3,450 (0.67%)</strong>
            </span>
            <span className="text-slate-500">
              Gross Leverage: <strong className="text-blue-700 font-bold">1.82x / 4.0x</strong>
            </span>
          </div>
        </div>

        {stressTestMode && (
          <div className="p-2 rounded-lg bg-purple-50 border border-purple-200 text-xs text-purple-900 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="w-3.5 h-3.5 text-purple-600" />
              <span className="text-[11px]">
                Stress Regime: <strong>{stressTestMode}</strong>. Modeled DD: <strong>2.94%</strong> (Below 4.0% hard limit).
              </span>
            </div>
            <button
              type="button"
              onClick={() => setStressTestMode(null)}
              className="text-purple-700 font-bold hover:underline text-[11px]"
            >
              Clear
            </button>
          </div>
        )}
      </div>

      {/* Configured Limits Dials Grid - CSS Grid Auto-Fit Container strictly within viewport */}
      <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar grid grid-cols-[repeat(auto-fit,minmax(270px,1fr))] gap-2 pr-0.5">
        {riskLimits.map(limit => {
          const ratio = (limit.currentValue / limit.limitValue) * 100;
          const isWarning = ratio >= 75 && ratio < 90;
          const isBreach = ratio >= 90;

          return (
            <div
              key={limit.id}
              className="bg-white rounded-xl p-3 border border-slate-200 shadow-2xs space-y-2 flex flex-col justify-between"
            >
              <div className="space-y-1.5">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">{limit.category}</span>
                    <h3 className="text-xs font-black text-slate-900 mt-0.5">{limit.name}</h3>
                  </div>

                  <span className={`px-1.5 py-0.2 rounded text-[9px] font-extrabold border ${getStatusBadge(limit.status)}`}>
                    {limit.status}
                  </span>
                </div>

                <p className="text-[10px] text-slate-500 font-medium leading-snug line-clamp-2">
                  {limit.description}
                </p>

                {/* Progress bar and values */}
                <div className="pt-1">
                  <div className="flex items-baseline justify-between text-xs mb-1">
                    <span className="text-slate-600 font-bold text-[11px]">
                      Current: <strong className="text-slate-900 text-xs font-black">{limit.currentValue.toLocaleString()}</strong> {limit.unit}
                    </span>
                    <span className="text-slate-500 font-semibold text-[10px]">
                      Limit: {limit.limitValue.toLocaleString()} {limit.unit}
                    </span>
                  </div>

                  <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-300 ${
                        isBreach ? 'bg-rose-500' : isWarning ? 'bg-amber-500' : 'bg-emerald-500'
                      }`}
                      style={{ width: `${Math.min(100, ratio)}%` }}
                    />
                  </div>
                  <div className="mt-0.5 text-[9px] text-slate-400 text-right font-medium">
                    {ratio.toFixed(1)}% Capacity Utilized
                  </div>
                </div>
              </div>

              <div className="pt-1.5 border-t border-slate-100 flex items-center justify-between text-xs">
                <span className="text-[9px] text-slate-400 font-mono">{limit.id}</span>
                <button
                  type="button"
                  onClick={() => handleOpenEdit(limit)}
                  className="text-blue-600 hover:text-blue-700 font-bold text-[10px] flex items-center gap-1 cursor-pointer"
                >
                  <Sliders className="w-3 h-3" />
                  <span>Configure Threshold</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Edit Limit Modal */}
      {selectedLimit && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white rounded-3xl max-w-md w-full border border-slate-200 shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-sm font-black text-slate-900">Configure Limit: {selectedLimit.name}</h3>
              <button
                type="button"
                onClick={() => setSelectedLimit(null)}
                className="text-slate-400 hover:text-slate-700"
              >
                ✕
              </button>
            </div>

            <div className="space-y-2 text-xs">
              <label className="font-bold text-slate-700">New Threshold ({selectedLimit.unit})</label>
              <input
                type="number"
                value={editVal}
                onChange={e => setEditVal(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-bold"
              />
              <p className="text-[11px] text-slate-500">
                Updating this limit requires operator confirmation and updates the active quantitative risk policy.
              </p>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setSelectedLimit(null)}
                className="px-3.5 py-1.5 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-100"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveEdit}
                className="px-4 py-1.5 rounded-xl text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white"
              >
                Save Threshold
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
