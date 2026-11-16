import React, { useState, useMemo } from 'react';
import {
  Check,
  XCircle,
  RotateCcw,
  ArrowRight,
  Eye,
  FolderKanban,
  AlertTriangle,
  CheckCircle2,
  Image as ImageIcon,
} from 'lucide-react';
import { useNexus } from '../context/NexusContext';
import { NexusApproval, NexusApprovalType } from '../types';
import { TruthBadge } from '../components/common/TruthBadge';
import { ExecutiveDossierModal, DossierData } from '../components/common/ExecutiveDossierModal';
import { createDossierFromDecision } from '../data/dossierData';

const APPROVAL_TYPES: ('All' | NexusApprovalType)[] = [
  'All',
  'Campaign publication',
  'Commerce go-live',
  'Creative',
  'Spend',
  'Trading actions',
  'Production changes',
  'Credentials',
];

export const ApprovalsPage: React.FC = () => {
  const {
    approvals,
    projects,
    selectedApprovalId,
    setSelectedApprovalId,
    approveDecision,
    rejectDecision,
    requestRevisionDecision,
    approveAllLowRiskDecisions,
    navigateToObject,
    needsRayDecisions,
  } = useNexus();

  const [statusFilter, setStatusFilter] = useState<'PENDING' | 'APPROVED' | 'REVISION_REQUESTED' | 'REJECTED' | 'ALL'>('PENDING');
  const [typeFilter, setTypeFilter] = useState<'All' | NexusApprovalType>('All');
  const [projectFilter, setProjectFilter] = useState<string>('ALL');
  const [revisionNote, setRevisionNote] = useState('');
  const [showRevisionBox, setShowRevisionBox] = useState(false);

  const [dossierOpen, setDossierOpen] = useState(false);
  const [dossierData, setDossierData] = useState<DossierData | null>(null);

  const filtered = useMemo(() => {
    return approvals.filter(a => {
      const matchStatus = statusFilter === 'ALL' || a.status === statusFilter;
      const matchType = typeFilter === 'All' || a.type === typeFilter;
      const matchProj = projectFilter === 'ALL' || a.projectId === projectFilter;
      return matchStatus && matchType && matchProj;
    });
  }, [approvals, statusFilter, typeFilter, projectFilter]);

  const activeApproval: NexusApproval | undefined =
    approvals.find(a => a.id === selectedApprovalId) || filtered[0] || approvals[0];

  const pendingCount = approvals.filter(a => a.status === 'PENDING').length;
  const lowRiskPendingCount = approvals.filter(
    a => a.status === 'PENDING' && a.riskLevel === 'LOW'
  ).length;

  const handleOpenDossier = (approval: NexusApproval) => {
    const compat = needsRayDecisions.find(d => d.id === approval.id);
    if (compat) {
      setDossierData(createDossierFromDecision(compat));
      setDossierOpen(true);
    }
  };

  const handleSendRevision = () => {
    if (!activeApproval) return;
    requestRevisionDecision(
      activeApproval.id,
      revisionNote.trim() || 'Requested revision and updated evidence verification.'
    );
    setRevisionNote('');
    setShowRevisionBox(false);
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Approvals
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            What Nexus is waiting for Ray to approve, reject, or revise. Only gated actions pause; parent projects continue where possible.
          </p>
        </div>

        {lowRiskPendingCount > 0 && (
          <button
            type="button"
            onClick={approveAllLowRiskDecisions}
            className="px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold flex items-center gap-1.5 cursor-pointer shrink-0 transition-colors"
          >
            <Check className="w-3.5 h-3.5" />
            <span>Approve Low Risk ({lowRiskPendingCount})</span>
          </button>
        )}
      </div>

      {/* Filter Bar */}
      <div className="bg-white rounded-2xl border border-slate-200/90 p-3.5 flex flex-wrap items-center justify-between gap-3">
        {/* Status Tabs */}
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl flex-wrap">
          {(
            [
              { id: 'PENDING', label: `Pending (${pendingCount})` },
              { id: 'APPROVED', label: 'Approved' },
              { id: 'REVISION_REQUESTED', label: 'Revision Requested' },
              { id: 'REJECTED', label: 'Rejected' },
              { id: 'ALL', label: `All (${approvals.length})` },
            ] as const
          ).map(tab => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setStatusFilter(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors cursor-pointer whitespace-nowrap ${
                statusFilter === tab.id
                  ? 'bg-white text-slate-900 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Type + Project Selectors */}
        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={typeFilter}
            onChange={e => setTypeFilter(e.target.value as 'All' | NexusApprovalType)}
            className="px-3 py-1.5 rounded-xl border border-slate-200 bg-white text-xs font-medium text-slate-700 outline-none focus:border-blue-500"
          >
            {APPROVAL_TYPES.map(t => (
              <option key={t} value={t}>
                Type: {t}
              </option>
            ))}
          </select>

          <select
            value={projectFilter}
            onChange={e => setProjectFilter(e.target.value)}
            className="px-3 py-1.5 rounded-xl border border-slate-200 bg-white text-xs font-medium text-slate-700 outline-none focus:border-blue-500"
          >
            <option value="ALL">All Projects</option>
            {projects.map(p => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Master-Detail Split */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Left List (5 cols) */}
        <div className="lg:col-span-5 bg-white rounded-2xl border border-slate-200/90 overflow-hidden divide-y divide-slate-100">
          {filtered.length === 0 ? (
            <div className="p-8 text-center">
              <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
              <div className="text-sm font-semibold text-slate-800">No approvals in this view</div>
              <p className="text-xs text-slate-500 mt-1">Try switching status or project filters above.</p>
            </div>
          ) : (
            filtered.map(item => {
              const isSelected = activeApproval?.id === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => {
                    setSelectedApprovalId(item.id);
                    setShowRevisionBox(false);
                  }}
                  className={`w-full text-left p-4 transition-colors cursor-pointer ${
                    isSelected ? 'bg-blue-50/70' : 'hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-[11px] font-mono text-slate-400">{item.id}</span>
                    <span
                      className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${
                        item.status === 'PENDING'
                          ? item.priority === 'HIGH'
                            ? 'bg-rose-50 text-rose-700 border-rose-200'
                            : 'bg-amber-50 text-amber-800 border-amber-200'
                          : item.status === 'APPROVED'
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : 'bg-slate-100 text-slate-600 border-slate-200'
                      }`}
                    >
                      {item.status === 'PENDING' ? `${item.priority} PRIORITY` : item.status}
                    </span>
                  </div>

                  <div className="text-sm font-semibold text-slate-900 leading-snug">
                    {item.title}
                  </div>
                  <div className="mt-1.5 flex items-center gap-2 text-xs text-slate-500 flex-wrap">
                    <span className="font-medium text-slate-700">{item.type}</span>
                    <span>·</span>
                    <span>{item.projectName}</span>
                    <span>·</span>
                    <span>{item.createdAt}</span>
                  </div>
                </button>
              );
            })
          )}
        </div>

        {/* Right Detail Panel (7 cols) */}
        <div className="lg:col-span-7 bg-white rounded-2xl border border-slate-200/90 p-5 sm:p-6 space-y-5">
          {!activeApproval ? (
            <div className="p-8 text-center text-xs text-slate-500">
              Select an approval item from the left to inspect its preview, blocked action, and next steps.
            </div>
          ) : (
            <>
              {/* Top Metadata Header */}
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 pb-4 border-b border-slate-100">
                <div className="space-y-1">
                  <div className="flex items-center gap-2 flex-wrap text-xs text-slate-500">
                    <span className="font-mono text-slate-400">{activeApproval.id}</span>
                    <span>·</span>
                    <span className="font-semibold text-slate-700">{activeApproval.type}</span>
                    <span>·</span>
                    <span>{activeApproval.department}</span>
                    <span>·</span>
                    <span>{activeApproval.createdAt}</span>
                  </div>
                  <h2 className="text-lg font-bold text-slate-900 leading-snug">
                    {activeApproval.title}
                  </h2>
                  <button
                    type="button"
                    onClick={() => navigateToObject('projects', activeApproval.projectId, 'project')}
                    className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-600 hover:underline cursor-pointer"
                  >
                    <FolderKanban className="w-3.5 h-3.5" />
                    <span>
                      Project: {activeApproval.projectName} ({activeApproval.projectId})
                    </span>
                  </button>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <span
                    className={`px-2.5 py-1 rounded-lg text-xs font-semibold border ${
                      activeApproval.riskLevel === 'HIGH'
                        ? 'bg-rose-50 text-rose-700 border-rose-200'
                        : activeApproval.riskLevel === 'MEDIUM'
                        ? 'bg-amber-50 text-amber-800 border-amber-200'
                        : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                    }`}
                  >
                    Risk: {activeApproval.riskLevel}
                  </span>
                </div>
              </div>

              {/* Reason & Summary */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
                  <div className="font-semibold text-slate-500">Reason For Approval Gate</div>
                  <p className="text-slate-800 leading-relaxed">{activeApproval.reason}</p>
                </div>
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
                  <div className="font-semibold text-slate-500">Cost &amp; Financial Impact</div>
                  <p className="text-slate-800 font-medium leading-relaxed tabular-nums">
                    {activeApproval.costImpact}
                  </p>
                </div>
              </div>

              {/* Context-Aware Visual / Data Preview */}
              <div className="rounded-xl border border-slate-200 overflow-hidden">
                <div className="px-4 py-2.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-800">
                    Preview · {activeApproval.preview.headline}
                  </span>
                  {activeApproval.linkedEntity && (
                    <button
                      type="button"
                      onClick={() => {
                        const kind = activeApproval.linkedEntity!.kind;
                        if (kind === 'campaign') navigateToObject('campaigns', activeApproval.linkedEntity!.id, 'campaign');
                        else if (kind === 'asset') navigateToObject('creative', activeApproval.linkedEntity!.id, 'asset');
                        else if (kind === 'offer') navigateToObject('business-hub', activeApproval.linkedEntity!.id, 'offer');
                      }}
                      className="text-blue-600 hover:underline font-semibold cursor-pointer"
                    >
                      Open Source Record →
                    </button>
                  )}
                </div>

                <div className="p-4 grid grid-cols-1 sm:grid-cols-12 gap-4 items-center">
                  {activeApproval.preview.imageUrl ? (
                    <div className="sm:col-span-5 rounded-xl overflow-hidden border border-slate-200 bg-slate-100 aspect-4/3">
                      <img
                        src={activeApproval.preview.imageUrl}
                        alt={activeApproval.title}
                        referrerPolicy="no-referrer"
                        className="w-full h-full object-cover"
                      />
                    </div>
                  ) : (
                    <div className="sm:col-span-4 rounded-xl border border-slate-200 bg-slate-50 p-4 flex flex-col items-center justify-center text-slate-400 aspect-4/3">
                      <ImageIcon className="w-6 h-6 mb-1" />
                      <span className="text-[11px] text-center">{activeApproval.department} Record</span>
                    </div>
                  )}

                  <div className={activeApproval.preview.imageUrl ? 'sm:col-span-7 space-y-3' : 'sm:col-span-8 space-y-3'}>
                    {activeApproval.preview.body && (
                      <p className="text-xs text-slate-700 leading-relaxed">
                        {activeApproval.preview.body}
                      </p>
                    )}

                    <div className="space-y-1.5">
                      {activeApproval.preview.facts.map((fact, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between gap-2 py-1 border-b border-slate-100 last:border-b-0 text-xs"
                        >
                          <span className="text-slate-500">{fact.label}</span>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-slate-800 tabular-nums">
                              {fact.value}
                            </span>
                            <TruthBadge truth={fact.truthClass} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Plain Explanation + Blocked Action + Next Step */}
              <div className="space-y-2.5 text-xs">
                <p className="text-slate-700 leading-relaxed">
                  {activeApproval.plainEnglishExplanation}
                </p>

                <div className="p-3 rounded-xl bg-amber-50/70 border border-amber-200/80 flex items-start gap-2 text-amber-950">
                  <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold">Blocked Action: </span>
                    <span>{activeApproval.blockedAction}</span>
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-blue-50/70 border border-blue-200/80 flex items-start gap-2 text-blue-950">
                  <ArrowRight className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold">What Happens Next: </span>
                    <span>{activeApproval.nextAction}</span>
                  </div>
                </div>
              </div>

              {/* Revision Input Box */}
              {showRevisionBox && (
                <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50 space-y-2.5">
                  <label className="block text-xs font-semibold text-slate-700">
                    Revision Instructions for Nexus
                  </label>
                  <textarea
                    rows={2}
                    value={revisionNote}
                    onChange={e => setRevisionNote(e.target.value)}
                    placeholder="Specify what Creative, Marketing, or Commerce should revise before resubmitting..."
                    className="w-full p-2.5 rounded-lg border border-slate-200 bg-white text-xs text-slate-800 outline-none focus:border-blue-500"
                  />
                  <div className="flex items-center justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => setShowRevisionBox(false)}
                      className="px-3 py-1.5 rounded-lg text-xs text-slate-600 hover:bg-slate-200/60 cursor-pointer"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={handleSendRevision}
                      className="px-3.5 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold cursor-pointer"
                    >
                      Submit Revision Request
                    </button>
                  </div>
                </div>
              )}

              {/* Actions Footer */}
              <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3">
                {activeApproval.status === 'PENDING' ? (
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      onClick={() => approveDecision(activeApproval.id)}
                      className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-colors"
                    >
                      <Check className="w-4 h-4" />
                      <span>Approve</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setShowRevisionBox(prev => !prev)}
                      className="px-3.5 py-2 rounded-xl bg-white border border-slate-300 hover:bg-amber-50 hover:border-amber-300 text-slate-700 text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-colors"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>Request Revision</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => rejectDecision(activeApproval.id)}
                      className="px-3.5 py-2 rounded-xl bg-white border border-slate-300 hover:bg-rose-50 hover:border-rose-300 text-slate-700 hover:text-rose-700 text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-colors"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      <span>Reject</span>
                    </button>
                  </div>
                ) : (
                  <div className="text-xs text-slate-600">
                    Decision: <strong className="text-slate-900">{activeApproval.status}</strong> by{' '}
                    {activeApproval.decisionBy || 'Ray Davis'} ({activeApproval.decisionTimestamp || 'Logged'})
                    {activeApproval.decisionNote && ` — "${activeApproval.decisionNote}"`}
                  </div>
                )}

                <button
                  type="button"
                  onClick={() => handleOpenDossier(activeApproval)}
                  className="px-3 py-2 rounded-xl border border-slate-200 hover:bg-slate-50 text-xs font-semibold text-slate-700 flex items-center gap-1.5 cursor-pointer"
                >
                  <Eye className="w-3.5 h-3.5" />
                  <span>Full Dossier</span>
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {dossierOpen && dossierData && (
        <ExecutiveDossierModal
          isOpen={dossierOpen}
          onClose={() => setDossierOpen(false)}
          data={dossierData}
        />
      )}
    </div>
  );
};
