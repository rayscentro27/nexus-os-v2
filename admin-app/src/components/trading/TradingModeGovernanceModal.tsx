import React, { useState } from 'react';
import { 
  X, 
  ShieldAlert, 
  CheckCircle2, 
  Lock, 
  AlertTriangle, 
  FileText, 
  Users, 
  Clock, 
  SlidersHorizontal,
  KeyRound
} from 'lucide-react';
import { TradingMode } from '../../types';

interface TradingModeGovernanceModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentMode: TradingMode;
  modeChangedBy: string;
  modeChangedAt: string;
  modeChangeReason: string;
  approvalStatus: string;
  riskPolicy: string;
  allowedProviders: string[];
  allowedAccounts: string[];
  onApplyModeChange: (newMode: TradingMode, reason: string, policy: string) => void;
}

export const TradingModeGovernanceModal: React.FC<TradingModeGovernanceModalProps> = ({
  isOpen,
  onClose,
  currentMode,
  modeChangedBy,
  modeChangedAt,
  modeChangeReason,
  approvalStatus,
  riskPolicy,
  allowedProviders,
  allowedAccounts,
  onApplyModeChange,
}) => {
  const [selectedMode, setSelectedMode] = useState<TradingMode>(currentMode);
  const [reason, setReason] = useState('');
  const [selectedPolicy, setSelectedPolicy] = useState(riskPolicy);
  const [adminPin, setAdminPin] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  if (!isOpen) return null;

  const MODES: {
    id: TradingMode;
    label: string;
    description: string;
    riskCategory: 'Safe' | 'Guarded' | 'Restricted' | 'Prohibited';
    isLive: boolean;
  }[] = [
    {
      id: 'RESEARCH_ONLY',
      label: 'RESEARCH ONLY',
      description: 'Disables all order generation and automated signal queues. Only allows quantitative research, data scraping, and factor exploration.',
      riskCategory: 'Safe',
      isLive: false
    },
    {
      id: 'BACKTEST_ONLY',
      label: 'BACKTEST ONLY',
      description: 'Allows historical and bounded out-of-sample backtests on compute clusters. Order execution engines and broker gateways remain blocked.',
      riskCategory: 'Safe',
      isLive: false
    },
    {
      id: 'PAPER_TRADING',
      label: 'PAPER TRADING (DEFAULT OPERATING MODE)',
      description: 'Generates real-time signals and routes executions exclusively to simulated paper-trading sandboxes (Alpaca Sandbox & Nexus Sim Engine). Zero real capital exposure.',
      riskCategory: 'Guarded',
      isLive: false
    },
    {
      id: 'LIVE_TRADING_DISABLED',
      label: 'LIVE TRADING DISABLED (HARD CODED LOCK)',
      description: 'System safety lock enforcing that all live broker execution gateways are disconnected and live order generation is completely prohibited.',
      riskCategory: 'Safe',
      isLive: false
    },
    {
      id: 'LIVE_TRADING_APPROVAL_REQUIRED',
      label: 'LIVE TRADING APPROVAL REQUIRED (MULTI-SIG LOCKED)',
      description: 'Requires dual-custody multi-signature cryptographic authorization from the Nexus Governance Committee and Risk Director. Single-click live execution is impossible.',
      riskCategory: 'Restricted',
      isLive: true
    }
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');

    if (selectedMode === currentMode) {
      setErrorMsg('Target operating mode is already active.');
      return;
    }

    if (selectedMode === 'LIVE_TRADING_APPROVAL_REQUIRED') {
      setErrorMsg('Governance Error: Live trading authorization requires physical multi-sig key presence. Cannot enable live execution from administrative sandbox console.');
      return;
    }

    if (!reason.trim() || reason.trim().length < 10) {
      setErrorMsg('Governance Compliance: Please provide a detailed operational justification (at least 10 characters).');
      return;
    }

    onApplyModeChange(selectedMode, reason, selectedPolicy);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white rounded-3xl max-w-2xl w-full border border-slate-200 shadow-2xl overflow-hidden flex flex-col max-h-[92vh]">
        {/* Header */}
        <div className="px-6 py-4.5 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-slate-50 to-white">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-blue-50 border border-blue-200 text-blue-700 flex items-center justify-center shrink-0">
              <SlidersHorizontal className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-black text-slate-900 flex items-center gap-2">
                <span>Trading Mode Governance</span>
                <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">Audit Protocol</span>
              </h2>
              <p className="text-xs text-slate-500 font-medium">
                Mandatory multi-tiered safety controls. Live execution is strictly bounded.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Body */}
        <div className="p-6 overflow-y-auto custom-scrollbar space-y-5 flex-1">
          {/* Active Mode Audit Snapshot Card */}
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2.5">
            <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-slate-400" />
              <span>Current Operating Configuration</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div>
                <span className="text-slate-500">Current Mode: </span>
                <span className="font-bold text-slate-900">{currentMode}</span>
              </div>
              <div>
                <span className="text-slate-500">Authorized By: </span>
                <span className="font-semibold text-slate-800">{modeChangedBy}</span>
              </div>
              <div>
                <span className="text-slate-500">Last Changed: </span>
                <span className="font-semibold text-slate-800">{modeChangedAt}</span>
              </div>
              <div>
                <span className="text-slate-500">Approval Status: </span>
                <span className="font-bold text-emerald-700">{approvalStatus}</span>
              </div>
              <div className="sm:col-span-2">
                <span className="text-slate-500">Active Risk Policy: </span>
                <span className="font-semibold text-slate-800">{riskPolicy}</span>
              </div>
              <div className="sm:col-span-2 text-[11px] text-slate-600 bg-white p-2 rounded-xl border border-slate-200/60">
                <span className="font-bold text-slate-700">Reason: </span>
                <span>{modeChangeReason}</span>
              </div>
            </div>
          </div>

          {/* Mode Selection Options */}
          <div className="space-y-2.5">
            <label className="text-xs font-bold text-slate-800 uppercase tracking-wider block">
              Select New Operating Mode
            </label>

            <div className="space-y-2">
              {MODES.map(m => {
                const isSelected = selectedMode === m.id;
                const isLiveOption = m.id === 'LIVE_TRADING_APPROVAL_REQUIRED';

                return (
                  <div
                    key={m.id}
                    onClick={() => setSelectedMode(m.id)}
                    className={`p-3.5 rounded-2xl border transition-all cursor-pointer relative ${
                      isSelected
                        ? isLiveOption 
                          ? 'border-amber-400 bg-amber-50/60 ring-2 ring-amber-300/60'
                          : 'border-blue-500 bg-blue-50/60 ring-2 ring-blue-300/60'
                        : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-3">
                        <div className={`mt-0.5 w-4 h-4 rounded-full border flex items-center justify-center shrink-0 ${
                          isSelected ? 'border-blue-600 bg-blue-600 text-white' : 'border-slate-300 bg-white'
                        }`}>
                          {isSelected && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                        </div>
                        <div>
                          <div className="text-xs font-bold text-slate-900 flex items-center gap-2">
                            <span>{m.label}</span>
                            {m.isLive && (
                              <span className="px-2 py-0.2 rounded text-[10px] font-black bg-rose-100 text-rose-700 uppercase flex items-center gap-1">
                                <Lock className="w-2.5 h-2.5" /> High Governance
                              </span>
                            )}
                          </div>
                          <p className="text-[11px] text-slate-600 mt-0.5 leading-relaxed font-normal">
                            {m.description}
                          </p>
                        </div>
                      </div>

                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0 ${
                        m.riskCategory === 'Safe' ? 'bg-slate-100 text-slate-700' :
                        m.riskCategory === 'Guarded' ? 'bg-emerald-100 text-emerald-800' :
                        m.riskCategory === 'Restricted' ? 'bg-amber-100 text-amber-800' :
                        'bg-rose-100 text-rose-800'
                      }`}>
                        {m.riskCategory}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Operational Justification / Reason */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center justify-between">
              <span>Operational Justification (Audit Log Mandatory)</span>
              <span className="text-[10px] text-slate-400 font-normal">Min. 10 characters</span>
            </label>
            <textarea
              value={reason}
              onChange={e => setReason(e.target.value)}
              placeholder="E.g., Authorized scheduled walk-forward testing cycle for Volatility Breakout models..."
              rows={2}
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 placeholder:text-slate-400"
            />
          </div>

          {/* Risk Policy Attachment */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-800 uppercase tracking-wider block">
              Attach Quantitative Risk Policy
            </label>
            <select
              value={selectedPolicy}
              onChange={e => setSelectedPolicy(e.target.value)}
              className="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-800 bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500/30"
            >
              <option value="RP-2026.4: Standard Multi-Asset Quantitative Risk Limits (Max DD 4.0%)">
                RP-2026.4: Standard Multi-Asset Quantitative Risk Limits (Max DD 4.0%)
              </option>
              <option value="RP-2026.3: Conservative Research Policy (Max DD 2.5%, Single-Asset 5%)">
                RP-2026.3: Conservative Research Policy (Max DD 2.5%, Single-Asset 5%)
              </option>
              <option value="RP-2026.5: High-Frequency Crypto Sandbox Guardrails (Max 2 Concurrent)">
                RP-2026.5: High-Frequency Crypto Sandbox Guardrails (Max 2 Concurrent)
              </option>
            </select>
          </div>

          {/* Security Notice */}
          <div className="p-3 rounded-xl bg-blue-50/70 border border-blue-200/60 text-xs text-blue-900 flex items-start gap-2.5">
            <ShieldAlert className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
            <div className="text-[11px] leading-relaxed">
              <span className="font-bold">Governance Safety Guarantee: </span>
              Every mode transition produces an immutable cryptographic audit record. Live trading cannot be unlocked from this console without external multi-sig approval.
            </div>
          </div>

          {errorMsg && (
            <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-800 font-semibold flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div className="text-[11px] text-slate-500 font-medium">
            Operator: <span className="font-bold text-slate-700">Alex Chen (Principal Quant)</span>
          </div>
          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-bold text-slate-600 hover:text-slate-800 hover:bg-slate-200/60 transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              className="px-4 py-2 rounded-xl text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white transition-all shadow-xs cursor-pointer"
            >
              Apply Mode Change & Sign Audit Log
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
