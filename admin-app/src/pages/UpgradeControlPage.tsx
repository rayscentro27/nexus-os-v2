import React, { useState } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  CheckCircle2,
  ArrowRight,
  Lock,
  FileCheck,
  Layers,
  UserCheck,
  Sparkles,
  ExternalLink,
  AlertTriangle,
} from 'lucide-react';
import { useNexus } from '../context/NexusContext';
import { TruthBadge } from '../components/common/TruthBadge';
import { NexusUpgradeCandidate } from '../types';
import { UnavailableState } from '../components/live/UnavailableState';

export const UpgradeControlPage: React.FC = () => {
  const {
    approvals,
    navigateToObject,
    setCurrentPage,
    sendMessage,
    setIsNovaDrawerOpen,
  } = useNexus();

  const upgradeCandidates: NexusUpgradeCandidate[] = [];
  const [selectedCandId, setSelectedCandId] = useState<string>(
    upgradeCandidates[0]?.id || ''
  );
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  const filteredCandidates = upgradeCandidates;

  const activeCand: NexusUpgradeCandidate | undefined =
    upgradeCandidates.find(c => c.id === selectedCandId) ||
    filteredCandidates[0] ||
    upgradeCandidates[0];

  const linkedApproval = activeCand?.linkedApprovalId
    ? approvals.find(a => a.id === activeCand.linkedApprovalId)
    : undefined;

  const getStatusBadge = (status: NexusUpgradeCandidate['status']) => {
    switch (status) {
      case 'CERTIFIED':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'HUMAN_REVIEW':
        return 'bg-amber-50 text-amber-800 border-amber-200';
      case 'REJECTED':
        return 'bg-rose-50 text-rose-700 border-rose-200';
    }
  };

  const getSecurityBadge = (sec: NexusUpgradeCandidate['securityReview']) => {
    switch (sec) {
      case 'PASSED':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'PENDING':
        return 'bg-amber-50 text-amber-800 border-amber-200';
      case 'FAILED':
        return 'bg-rose-50 text-rose-700 border-rose-200';
    }
  };

  return (
    <div className="space-y-4 pb-10">
      {toastMessage && (
        <div className="fixed top-14 right-6 z-50">
          <div className="bg-slate-900 text-white px-3.5 py-2 rounded-xl shadow-lg flex items-center gap-2 text-xs font-semibold border border-slate-700">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{toastMessage}</span>
          </div>
        </div>
      )}

      {/* Clean Executive Header */}
      <header className="bg-white rounded-xl p-4 border border-slate-200/80 shadow-2xs flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-lg bg-teal-50 border border-teal-200 text-teal-700 flex items-center justify-center shrink-0 mt-0.5">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-base font-bold text-slate-900 tracking-tight">
                Upgrade Control
              </h1>
              <TruthBadge truth="VERIFIED" label="CERTIFICATION GATE" />
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-rose-50 text-rose-800 border border-rose-200">
                <Lock className="w-3 h-3 text-rose-600" />
                UPGRADE CONTROL DOES NOT DEPLOY PRODUCTION CHANGES
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Reviews promoted Labs candidates for security, target node compliance, cost impact, and rollback safety before Systems deployment.
            </p>
          </div>
        </div>

        {/* Lifecycle Position Breadcrumb */}
        <div className="flex items-center gap-1.5 bg-slate-50 px-2.5 py-1.5 rounded-lg border border-slate-200 text-[11px] font-medium text-slate-600 flex-wrap">
          <button
            type="button"
            onClick={() => setCurrentPage('research')}
            className="hover:text-blue-600 cursor-pointer"
          >
            Research
          </button>
          <ArrowRight className="w-3 h-3 text-slate-400" />
          <button
            type="button"
            onClick={() => setCurrentPage('development-labs')}
            className="hover:text-blue-600 cursor-pointer"
          >
            Development / Labs
          </button>
          <ArrowRight className="w-3 h-3 text-slate-400" />
          <span className="text-teal-800 font-semibold bg-teal-100/80 px-1.5 py-0.5 rounded">
            Upgrade Control
          </span>
          <ArrowRight className="w-3 h-3 text-slate-400" />
          <button
            type="button"
            onClick={() => setCurrentPage('systems')}
            className="hover:text-blue-600 cursor-pointer"
          >
            Systems
          </button>
        </div>
      </header>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="bg-white rounded-xl p-3.5 border border-slate-200/80 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-500 block">Total Candidates</span>
          <span className="text-sm font-semibold text-slate-500">Not connected</span>
          <span className="text-[11px] text-slate-500 block mt-0.5">Tracked upgrade packages</span>
        </div>
        <div className="bg-white rounded-xl p-3.5 border border-slate-200/80 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-500 block">Awaiting Human Review</span>
          <span className="text-sm font-semibold text-slate-500">Not connected</span>
          <span className="text-[11px] text-slate-500 block mt-0.5">Requires certification or Ray approval</span>
        </div>
        <div className="bg-white rounded-xl p-3.5 border border-slate-200/80 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-500 block">Certified for Systems</span>
          <span className="text-sm font-semibold text-slate-500">Not connected</span>
          <span className="text-[11px] text-slate-500 block mt-0.5">Ready for controlled rollout</span>
        </div>
        <div className="bg-white rounded-xl p-3.5 border border-slate-200/80 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-500 block">Oracle Protection Rule</span>
          <span className="text-sm font-bold text-slate-900 block mt-1">Zero Heavy Builds</span>
          <span className="text-[11px] text-slate-500 block mt-0.5">All upgrades target Mac mini / Contabo</span>
        </div>
      </div>

      {/* Main Two-Column Certification Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
        {/* Left: Candidate Pipeline */}
        <section className="lg:col-span-7 bg-white rounded-xl border border-slate-200/80 shadow-2xs overflow-hidden">
          <div className="p-3 border-b border-slate-100 bg-slate-50/60 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-teal-600" />
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                Certification Queue
              </h2>
            </div>

            <span className="text-xs font-semibold text-slate-500">Status data not connected</span>
          </div>

          <div className="divide-y divide-slate-100">
            {filteredCandidates.length === 0 ? (
              <div className="p-4"><UnavailableState>Upgrade Control is not connected to a live release source.</UnavailableState></div>
            ) : (
              filteredCandidates.map(cand => {
                const isSelected = activeCand?.id === cand.id;
                const candApproval = cand.linkedApprovalId
                  ? approvals.find(a => a.id === cand.linkedApprovalId)
                  : undefined;

                return (
                  <button
                    key={cand.id}
                    type="button"
                    onClick={() => setSelectedCandId(cand.id)}
                    className={`w-full text-left p-4 transition-colors cursor-pointer ${
                      isSelected
                        ? 'bg-teal-50/40 border-l-2 border-l-teal-600'
                        : 'hover:bg-slate-50/70'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 space-y-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-mono text-[11px] font-semibold text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded">
                            {cand.fromVersion} → {cand.toVersion}
                          </span>
                          <span className="text-sm font-semibold text-slate-900">
                            {cand.name}
                          </span>
                          <TruthBadge truth={cand.truthClass} />
                        </div>
                        <p className="text-xs text-slate-600">
                          Target Node: <strong className="text-slate-800">{cand.targetNode}</strong>
                        </p>
                      </div>

                      <span
                        className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-md border shrink-0 ${getStatusBadge(
                          cand.status
                        )}`}
                      >
                        {cand.status.replace('_', ' ')}
                      </span>
                    </div>

                    <div className="mt-2.5 flex flex-wrap items-center gap-2 text-[11px]">
                      <span
                        className={`px-2 py-0.5 rounded border font-semibold ${getSecurityBadge(
                          cand.securityReview
                        )}`}
                      >
                        Security: {cand.securityReview}
                      </span>
                      <span className="px-2 py-0.5 rounded border border-slate-200 bg-slate-50 text-slate-700 font-medium">
                        Cost: {cand.costImpact}
                      </span>
                      {candApproval && (
                        <span className="px-2 py-0.5 rounded border border-amber-200 bg-amber-50 text-amber-900 font-medium">
                          Approval: {candApproval.status}
                        </span>
                      )}
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </section>

        {/* Right: Certification Checklist & Rollback Verification */}
        <section className="lg:col-span-5 bg-white rounded-xl border border-slate-200/80 shadow-2xs overflow-hidden">
          {activeCand ? (
            <>
              <div className="p-3.5 border-b border-slate-100 bg-slate-50/60 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileCheck className="w-4 h-4 text-teal-600" />
                  <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                    Certification Audit
                  </h2>
                </div>
                <TruthBadge truth={activeCand.truthClass} />
              </div>

              <div className="p-4 space-y-3.5 text-xs">
                <div className="space-y-1">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <span className="font-mono text-[11px] font-semibold text-slate-600">
                      {activeCand.fromVersion} → {activeCand.toVersion}
                    </span>
                    <span
                      className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded border ${getStatusBadge(
                        activeCand.status
                      )}`}
                    >
                      {activeCand.status.replace('_', ' ')}
                    </span>
                  </div>
                  <h3 className="text-base font-bold text-slate-900">{activeCand.name}</h3>
                </div>

                <div className="grid grid-cols-1 gap-2.5">
                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                    <span className="text-[10px] font-bold uppercase text-slate-500 block">
                      Target Node Compliance
                    </span>
                    <span className="text-xs font-semibold text-slate-900 font-mono">
                      {activeCand.targetNode}
                    </span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between">
                    <div>
                      <span className="text-[10px] font-bold uppercase text-slate-500 block">
                        Security & Boundary Review
                      </span>
                      <span className="text-xs text-slate-700">
                        Verified against non-Oracle runtime rules
                      </span>
                    </div>
                    <span
                      className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded border ${getSecurityBadge(
                        activeCand.securityReview
                      )}`}
                    >
                      {activeCand.securityReview}
                    </span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                    <span className="text-[10px] font-bold uppercase text-slate-500 block">
                      Cost Impact
                    </span>
                    <span className="text-xs font-semibold text-slate-900">
                      {activeCand.costImpact}
                    </span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                    <span className="text-[10px] font-bold uppercase text-slate-500 block">
                      Verified Rollback Plan
                    </span>
                    <p className="text-xs text-slate-700 mt-0.5 leading-relaxed">
                      {activeCand.rollbackPlan}
                    </p>
                  </div>
                </div>

                {/* Boundary Guardrail */}
                <div className="p-3 rounded-lg bg-rose-50/80 border border-rose-200 text-rose-950 space-y-1">
                  <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase text-rose-800">
                    <ShieldAlert className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                    <span>Upgrade Control Does Not Deploy Production Changes</span>
                  </div>
                  <p className="text-[11px] text-rose-900 leading-relaxed">
                    Upgrade Control certifies manifests and rollback readiness only. Production execution and service recovery remain owned exclusively by Systems.
                  </p>
                </div>

                {/* Actions */}
                <div className="space-y-2 pt-1">
                  {linkedApproval && (
                    <button
                      type="button"
                      onClick={() => navigateToObject('approvals', linkedApproval.id, 'approval')}
                      className="w-full py-2 px-3 rounded-lg border border-amber-300 bg-amber-50 hover:bg-amber-100/70 text-amber-900 font-semibold text-xs flex items-center justify-center gap-1.5 cursor-pointer"
                    >
                      <UserCheck className="w-3.5 h-3.5" />
                      <span>
                        Open Linked Approval ({linkedApproval.status})
                      </span>
                      <ExternalLink className="w-3 h-3" />
                    </button>
                  )}

                  {activeCand.status === 'HUMAN_REVIEW' && (
                    <button
                      type="button"
                      disabled
                      onClick={() => showToast('Upgrade certification is not connected to a live backend.')}
                      className="w-full py-2 px-3 rounded-lg bg-teal-600 hover:bg-teal-700 text-white font-semibold text-xs flex items-center justify-center gap-1.5 cursor-pointer"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Certify Candidate for Systems</span>
                    </button>
                  )}

                  {activeCand.status === 'CERTIFIED' && (
                    <button
                      type="button"
                      onClick={() => setCurrentPage('systems')}
                      className="w-full py-2 px-3 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs flex items-center justify-center gap-1.5 cursor-pointer"
                    >
                      <ArrowRight className="w-3.5 h-3.5" />
                      <span>Inspect in Systems →</span>
                    </button>
                  )}

                  <button
                    type="button"
                    onClick={() => {
                      sendMessage(`Summarize certification status and rollback plan for ${activeCand.name}.`);
                      setIsNovaDrawerOpen(true);
                    }}
                    className="w-full py-1.5 px-3 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs flex items-center justify-center gap-1.5 cursor-pointer"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                    <span>Ask Nova about this upgrade</span>
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="p-6 text-center text-xs text-slate-500">
              Select an upgrade candidate to review its certification checklist.
            </div>
          )}
        </section>
      </div>
    </div>
  );
};
