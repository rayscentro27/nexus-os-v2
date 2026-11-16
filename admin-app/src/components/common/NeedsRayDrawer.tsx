import React, { useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  X,
  ArrowRight,
  ShieldCheck,
  Check,
  DollarSign,
  TrendingUp,
  Sparkles,
  FlaskConical,
  Building,
  Server,
  FileCheck,
} from 'lucide-react';
import { useNexus } from '../../context/NexusContext';
import { NexusApproval } from '../../types';

export const NeedsRayDrawer: React.FC = () => {
  const {
    isNeedsRayDrawerOpen,
    setIsNeedsRayDrawerOpen,
    approvals,
    approveDecision,
    rejectDecision,
    approveAllLowRiskDecisions,
    navigateToObject,
  } = useNexus();

  const [activeFilter, setActiveFilter] = useState<'PENDING' | 'ALL' | 'APPROVED'>('PENDING');

  if (!isNeedsRayDrawerOpen) return null;

  const pendingApprovals = approvals.filter(a => a.status === 'PENDING');
  const approvedApprovals = approvals.filter(a => a.status === 'APPROVED');
  const lowRiskPendingCount = pendingApprovals.filter(a => a.riskLevel === 'LOW').length;

  const displayed = approvals.filter(a => {
    if (activeFilter === 'PENDING') return a.status === 'PENDING';
    if (activeFilter === 'APPROVED') return a.status === 'APPROVED';
    return true;
  });

  const getDeptIcon = (dept: NexusApproval['department']) => {
    switch (dept) {
      case 'Finance':
        return <DollarSign className="w-3.5 h-3.5 text-emerald-600" />;
      case 'Trading':
        return <TrendingUp className="w-3.5 h-3.5 text-blue-600" />;
      case 'Creative':
        return <Sparkles className="w-3.5 h-3.5 text-purple-600" />;
      case 'Development / Labs':
      case 'Upgrade Control':
        return <FlaskConical className="w-3.5 h-3.5 text-indigo-600" />;
      case 'Systems':
        return <Server className="w-3.5 h-3.5 text-slate-700" />;
      case 'Research':
        return <FileCheck className="w-3.5 h-3.5 text-cyan-600" />;
      default:
        return <Building className="w-3.5 h-3.5 text-slate-600" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div
        className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs"
        onClick={() => setIsNeedsRayDrawerOpen(false)}
      />

      <div className="relative z-10 w-full max-w-lg h-full bg-white shadow-2xl flex flex-col border-l border-slate-200">
        <div className="p-4 sm:p-5 border-b border-slate-200 bg-slate-50/70 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-amber-100 text-amber-700 border border-amber-200 flex items-center justify-center">
              <AlertTriangle className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm sm:text-base font-bold text-slate-900">
                Needs Ray Queue ({pendingApprovals.length})
              </h2>
              <p className="text-xs text-slate-500">
                Synced directly with the authoritative Approvals queue
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => setIsNeedsRayDrawerOpen(false)}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="px-4 py-2.5 bg-white border-b border-slate-200 flex items-center justify-between gap-2 shrink-0">
          <div className="flex items-center gap-1 text-xs">
            {(['PENDING', 'ALL', 'APPROVED'] as const).map(f => (
              <button
                key={f}
                type="button"
                onClick={() => setActiveFilter(f)}
                className={`px-2.5 py-1 rounded-lg font-semibold text-xs transition-colors cursor-pointer ${
                  activeFilter === f
                    ? 'bg-slate-900 text-white'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                {f === 'PENDING'
                  ? `Pending (${pendingApprovals.length})`
                  : f === 'APPROVED'
                  ? `Approved (${approvedApprovals.length})`
                  : `All (${approvals.length})`}
              </button>
            ))}
          </div>

          {lowRiskPendingCount > 0 && activeFilter !== 'APPROVED' && (
            <button
              type="button"
              onClick={approveAllLowRiskDecisions}
              className="px-2.5 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs flex items-center gap-1 cursor-pointer shrink-0"
            >
              <Check className="w-3.5 h-3.5" />
              <span>Approve Low Risk ({lowRiskPendingCount})</span>
            </button>
          )}
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-3">
          {displayed.length === 0 ? (
            <div className="h-56 flex flex-col items-center justify-center text-center p-6 rounded-xl border border-dashed border-slate-200 text-slate-500">
              <CheckCircle2 className="w-10 h-10 text-emerald-500 mb-2" />
              <div className="text-sm font-semibold text-slate-800">Queue clear</div>
              <p className="text-xs text-slate-500 mt-1">
                No items matching this filter currently require your attention.
              </p>
            </div>
          ) : (
            displayed.map(item => {
              const isPending = item.status === 'PENDING';
              const isApproved = item.status === 'APPROVED';

              return (
                <div
                  key={item.id}
                  className={`rounded-xl border p-3.5 space-y-2.5 ${
                    isPending
                      ? 'bg-white border-slate-200 shadow-2xs'
                      : 'bg-slate-50 border-slate-200/80 opacity-85'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-start gap-2.5 min-w-0">
                      <div className="p-1.5 rounded-lg bg-slate-100 border border-slate-200 shrink-0 mt-0.5">
                        {getDeptIcon(item.department)}
                      </div>
                      <div className="min-w-0">
                        <div className="text-[11px] text-slate-500 flex items-center gap-1.5 flex-wrap">
                          <span className="font-semibold text-slate-700">{item.department}</span>
                          <span>·</span>
                          <span>{item.type}</span>
                          <span>·</span>
                          <span>{item.projectName}</span>
                        </div>
                        <h3 className="text-xs sm:text-sm font-bold text-slate-900 leading-snug mt-0.5">
                          {item.title}
                        </h3>
                      </div>
                    </div>

                    <span
                      className={`text-[10px] font-semibold px-2 py-0.5 rounded border shrink-0 ${
                        isPending
                          ? item.priority === 'HIGH'
                            ? 'bg-rose-50 text-rose-700 border-rose-200'
                            : 'bg-amber-50 text-amber-800 border-amber-200'
                          : isApproved
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : 'bg-slate-100 text-slate-600 border-slate-200'
                      }`}
                    >
                      {isPending ? `${item.priority}` : item.status}
                    </span>
                  </div>

                  <p className="text-xs text-slate-600 leading-relaxed">
                    {item.plainEnglishExplanation}
                  </p>

                  <div className="text-[11px] text-slate-600 bg-slate-50 rounded-lg px-2.5 py-1.5 border border-slate-200/70 space-y-1">
                    <div>
                      <span className="font-semibold text-slate-700">Impact: </span>
                      {item.costImpact}
                    </div>
                    <div className="flex items-center gap-1 text-blue-700 font-medium">
                      <ArrowRight className="w-3 h-3 shrink-0" />
                      <span>Next: {item.nextAction}</span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between gap-2 pt-1">
                    {isPending ? (
                      <>
                        <div className="flex items-center gap-2 flex-1">
                          <button
                            type="button"
                            onClick={() => approveDecision(item.id)}
                            className="flex-1 py-1.5 px-3 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs flex items-center justify-center gap-1.5 cursor-pointer"
                          >
                            <Check className="w-3.5 h-3.5" />
                            <span>Approve</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => rejectDecision(item.id)}
                            className="py-1.5 px-3 rounded-lg bg-white border border-slate-300 hover:bg-rose-50 hover:text-rose-700 text-slate-700 font-semibold text-xs cursor-pointer"
                          >
                            Reject
                          </button>
                        </div>
                      </>
                    ) : (
                      <span className="text-[11px] text-slate-500">
                        {item.decisionBy || 'Ray Davis'} · {item.decisionTimestamp || item.createdAt}
                      </span>
                    )}
                    <button
                      type="button"
                      onClick={() => {
                        setIsNeedsRayDrawerOpen(false);
                        navigateToObject('approvals', item.id, 'approval');
                      }}
                      className="text-xs font-semibold text-blue-600 hover:underline cursor-pointer shrink-0"
                    >
                      Inspect →
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>

        <div className="p-3 bg-slate-50 border-t border-slate-200 text-xs flex items-center justify-between shrink-0">
          <div className="flex items-center gap-1.5 text-slate-600">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>Single authoritative queue</span>
          </div>
          <button
            type="button"
            onClick={() => {
              setIsNeedsRayDrawerOpen(false);
              navigateToObject('approvals');
            }}
            className="text-blue-600 hover:text-blue-800 font-semibold cursor-pointer"
          >
            Open Full Approvals Desk →
          </button>
        </div>
      </div>
    </div>
  );
};
