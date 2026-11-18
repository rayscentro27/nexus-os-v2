import React, { useState } from 'react';
import { 
  X, 
  ShieldAlert, 
  PauseCircle, 
  PlayCircle, 
  AlertOctagon, 
  FileText, 
  CheckCircle2, 
  AlertTriangle 
} from 'lucide-react';
import { KillSwitchScope } from '../../types';

interface KillSwitchModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentScope: KillSwitchScope;
  onApplyKillSwitch: (newScope: KillSwitchScope, reason: string) => void;
}

export const KillSwitchModal: React.FC<KillSwitchModalProps> = ({
  isOpen,
  onClose,
  currentScope,
  onApplyKillSwitch,
}) => {
  const [selectedScope, setSelectedScope] = useState<KillSwitchScope>(
    currentScope === 'NONE' ? 'PAUSE_SIGNALS' : 'NONE'
  );
  const [reason, setReason] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  if (!isOpen) return null;

  const isCurrentlyPaused = currentScope !== 'NONE';

  const SCOPES: {
    id: KillSwitchScope;
    title: string;
    description: string;
    impact: string;
    level: 'Warning' | 'High' | 'Emergency' | 'Normal';
  }[] = [
    {
      id: 'PAUSE_SIGNALS',
      title: 'Pause New Signals',
      description: 'Halts inbound signal ingestion and automated model evaluations. Active paper positions remain monitored with existing stop losses.',
      impact: 'Zero new signals will be pushed to the queue. Existing positions unaffected.',
      level: 'Warning'
    },
    {
      id: 'PAUSE_PAPER_ORDERS',
      title: 'Pause Paper Orders',
      description: 'Blocks all simulated paper order routing to Alpaca and Nexus Sandboxes. Signals can still generate and be watched by researchers.',
      impact: 'No simulated executions or fills will take place.',
      level: 'High'
    },
    {
      id: 'PAUSE_ALL_ACTIONS',
      title: 'Pause All Trading Actions (Hard Emergency Stop)',
      description: 'Complete operational freeze. Halts new signals, paper order routing, and active backtest batch clusters immediately.',
      impact: 'Total sandbox freeze. All automated quantitative loops enter standby state.',
      level: 'Emergency'
    },
    {
      id: 'NONE',
      title: 'Resume Normal Operations (Disengage Kill Switch)',
      description: 'Restores regular paper trading and signal generation under active risk policy RP-2026.4.',
      impact: 'Re-enables signal queue processing and paper order generation.',
      level: 'Normal'
    }
  ];

  const handleExecute = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');

    if (selectedScope === currentScope) {
      setErrorMsg('Selected scope matches current state.');
      return;
    }

    if (!reason.trim() || reason.trim().length < 8) {
      setErrorMsg('Mandatory Audit Field: Please provide a valid justification for this pause action.');
      return;
    }

    if (!confirmed) {
      setErrorMsg('Please confirm acknowledgment of the governance audit trail.');
      return;
    }

    onApplyKillSwitch(selectedScope, reason);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white rounded-3xl max-w-xl w-full border border-slate-200 shadow-2xl overflow-hidden flex flex-col max-h-[92vh]">
        {/* Header */}
        <div className="px-6 py-4.5 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-rose-50/70 via-slate-50 to-white">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-rose-100 border border-rose-200 text-rose-700 flex items-center justify-center shrink-0">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-black text-slate-900 flex items-center gap-2">
                <span>Emergency Pause & Kill Switch</span>
                <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded-full bg-rose-100 text-rose-700">Governance Gate</span>
              </h2>
              <p className="text-xs text-slate-500 font-medium">
                Immediate system-level safeguard with immutable audit logging.
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

        {/* Body */}
        <div className="p-6 overflow-y-auto custom-scrollbar space-y-4 flex-1">
          {/* Current State Info */}
          <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-slate-500 font-medium">Current Status:</span>
              <span className={`font-bold flex items-center gap-1.5 ${isCurrentlyPaused ? 'text-amber-700' : 'text-emerald-700'}`}>
                <span className={`w-2 h-2 rounded-full ${isCurrentlyPaused ? 'bg-amber-500 animate-pulse' : 'bg-emerald-500'}`} />
                {isCurrentlyPaused ? `ENGAGED (${currentScope})` : 'DISENGAGED (NORMAL)'}
              </span>
            </div>
            <span className="text-[11px] text-slate-500 font-semibold">Dual-Signoff Ready</span>
          </div>

          {/* Scope Select Cards */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-800 uppercase tracking-wider block">
              Select Pause Scope
            </label>

            <div className="space-y-2">
              {SCOPES.map(s => {
                const isSelected = selectedScope === s.id;
                const isResume = s.id === 'NONE';

                return (
                  <div
                    key={s.id}
                    onClick={() => setSelectedScope(s.id)}
                    className={`p-3.5 rounded-2xl border transition-all cursor-pointer ${
                      isSelected
                        ? isResume
                          ? 'border-emerald-500 bg-emerald-50/70 ring-2 ring-emerald-300/60'
                          : 'border-rose-500 bg-rose-50/70 ring-2 ring-rose-300/60'
                        : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`mt-0.5 w-4 h-4 rounded-full border flex items-center justify-center shrink-0 ${
                        isSelected 
                          ? isResume ? 'border-emerald-600 bg-emerald-600 text-white' : 'border-rose-600 bg-rose-600 text-white'
                          : 'border-slate-300 bg-white'
                      }`}>
                        {isSelected && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                      </div>
                      <div className="flex-1">
                        <div className="text-xs font-bold text-slate-900 flex items-center justify-between">
                          <span>{s.title}</span>
                          <span className={`text-[10px] font-bold px-2 py-0.2 rounded-full ${
                            s.level === 'Emergency' ? 'bg-rose-100 text-rose-800' :
                            s.level === 'High' ? 'bg-amber-100 text-amber-800' :
                            s.level === 'Normal' ? 'bg-emerald-100 text-emerald-800' :
                            'bg-slate-100 text-slate-700'
                          }`}>
                            {s.level}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-600 mt-0.5 leading-relaxed font-normal">
                          {s.description}
                        </p>
                        <div className="mt-1 text-[10px] font-semibold text-slate-500">
                          ⚡ <span className="text-slate-700">{s.impact}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Reason Input */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-800 uppercase tracking-wider block">
              Audit Reason (Mandatory)
            </label>
            <input
              type="text"
              value={reason}
              onChange={e => setReason(e.target.value)}
              placeholder="E.g., High volatility spike ahead of CPI announcement; anomalous feed latency detected..."
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-rose-500/30 focus:border-rose-500"
            />
          </div>

          {/* Confirmation Checkbox */}
          <label className="flex items-start gap-2.5 p-3 rounded-xl bg-slate-50 border border-slate-200 cursor-pointer">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={e => setConfirmed(e.target.checked)}
              className="mt-0.5 rounded text-rose-600 focus:ring-rose-500"
            />
            <span className="text-xs text-slate-600 leading-relaxed font-medium">
              I certify that this pause action is authorized under Nexus Quant Risk guidelines and agree that an immutable audit log entry will be stamped with my operator ID.
            </span>
          </label>

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
            Actor: <span className="font-bold text-slate-800">Alex Chen (Principal Quant)</span>
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
              onClick={handleExecute}
              className={`px-4 py-2 rounded-xl text-xs font-bold text-white transition-all shadow-xs cursor-pointer ${
                selectedScope === 'NONE'
                  ? 'bg-emerald-600 hover:bg-emerald-700'
                  : 'bg-rose-600 hover:bg-rose-700'
              }`}
            >
              {selectedScope === 'NONE' ? 'Disengage & Resume Normal' : 'Confirm & Execute Pause'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
