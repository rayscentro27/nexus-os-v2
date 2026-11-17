import React, { useMemo, useState } from 'react';
import {
  FlaskConical,
  AlertTriangle,
  CheckCircle2,
  ArrowRight,
  Terminal,
  ShieldAlert,
  Search,
  Sparkles,
  ExternalLink,
  RotateCw,
  FolderKanban,
  Layers,
} from 'lucide-react';
import { useNexus } from '../context/NexusContext';
import { TruthBadge } from '../components/common/TruthBadge';
import { NexusLabExperiment } from '../types';
import { UnavailableState } from '../components/live/UnavailableState';

export const DevelopmentLabsPage: React.FC = () => {
  const {
    projects,
    approvals,
    navigateToObject,
    setCurrentPage,
    sendMessage,
    setIsNovaDrawerOpen,
  } = useNexus();

  const labExperiments: NexusLabExperiment[] = [];
  const [filterEnv, setFilterEnv] = useState<string>('ALL');
  const [filterStatus, setFilterStatus] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedExpId, setSelectedExpId] = useState<string>(
    labExperiments[0]?.id || ''
  );
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  const filteredExperiments = useMemo(() => {
    return labExperiments.filter(exp => {
      if (filterEnv !== 'ALL' && exp.environment !== filterEnv) return false;
      if (filterStatus !== 'ALL' && exp.status !== filterStatus) return false;
      if (searchTerm.trim()) {
        const q = searchTerm.toLowerCase();
        return (
          exp.name.toLowerCase().includes(q) ||
          exp.hypothesis.toLowerCase().includes(q) ||
          exp.owner.toLowerCase().includes(q) ||
          exp.benchmarkSummary.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [labExperiments, filterEnv, filterStatus, searchTerm]);

  const activeExp: NexusLabExperiment | undefined =
    labExperiments.find(e => e.id === selectedExpId) ||
    filteredExperiments[0] ||
    labExperiments[0];

  const validatedCount = labExperiments.filter(e => e.status === 'VALIDATED').length;
  const runningCount = labExperiments.filter(e => e.status === 'RUNNING').length;
  const blockedCount = labExperiments.filter(e => e.status === 'BLOCKED').length;
  const promotedCount = labExperiments.filter(
    e => e.status === 'PROMOTED_TO_UPGRADE_CONTROL'
  ).length;

  const linkedProject = activeExp?.linkedProjectId
    ? projects.find(p => p.id === activeExp.linkedProjectId)
    : undefined;
  const linkedApproval = activeExp?.linkedApprovalId
    ? approvals.find(a => a.id === activeExp.linkedApprovalId)
    : undefined;

  const renderStatusBadge = (status: NexusLabExperiment['status']) => {
    switch (status) {
      case 'VALIDATED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            VALIDATED
          </span>
        );
      case 'RUNNING':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
            <RotateCw className="w-3 h-3 text-blue-600 animate-spin" />
            RUNNING
          </span>
        );
      case 'BLOCKED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200">
            <AlertTriangle className="w-3 h-3 text-amber-600" />
            BLOCKED
          </span>
        );
      case 'PROMOTED_TO_UPGRADE_CONTROL':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-teal-50 text-teal-800 border border-teal-200">
            <ArrowRight className="w-3 h-3 text-teal-600" />
            IN UPGRADE CONTROL
          </span>
        );
    }
  };

  const renderEnvLabel = (env: NexusLabExperiment['environment']) => {
    switch (env) {
      case 'MAC_MINI_LOCAL':
        return 'Mac mini (Local Sandbox)';
      case 'ISOLATED_SANDBOX':
        return 'Isolated Sandbox Container';
      case 'ORACLE_EVAL':
        return 'Oracle Eval (Scoped)';
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
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <div className="w-8 h-8 rounded-lg bg-purple-50 border border-purple-200 text-purple-700 flex items-center justify-center shrink-0">
              <FlaskConical className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="text-base font-bold text-slate-900 tracking-tight">
                  Development / Labs
                </h1>
                <TruthBadge truth="NOT_CONNECTED" />
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-rose-50 text-rose-800 border border-rose-200">
                  <ShieldAlert className="w-3 h-3 text-rose-600" />
                  CAN DEPLOY DIRECTLY: FALSE
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Development Labs data is not connected to a live source.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={() => setCurrentPage('upgrade-control')}
            className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 flex items-center gap-1.5 cursor-pointer"
          >
            <Layers className="w-3.5 h-3.5 text-teal-600" />
            <span>Open Upgrade Control</span>
          </button>
          <button
            type="button"
            onClick={() => {
              sendMessage('Which lab experiments are validated and ready for Upgrade Control?');
              setIsNovaDrawerOpen(true);
            }}
            className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold flex items-center gap-1.5 cursor-pointer"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Ask Nova</span>
          </button>
        </div>
      </header>

      {/* Compact Metrics Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="bg-white rounded-xl p-3.5 border border-slate-200/80 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-500 block">Active Sandboxes</span>
          <span className="text-sm font-semibold text-slate-500">Not connected</span>
          <span className="text-[11px] text-slate-500 block mt-0.5">Running isolated benchmarks</span>
        </div>
        <div className="bg-white rounded-xl p-3.5 border border-slate-200/80 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-500 block">Validated Candidates</span>
          <span className="text-sm font-semibold text-slate-500">Not connected</span>
          <span className="text-[11px] text-slate-500 block mt-0.5">Ready for Upgrade Control</span>
        </div>
        <div className="bg-white rounded-xl p-3.5 border border-slate-200/80 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-500 block">Blocked in Lab</span>
          <span className="text-sm font-semibold text-slate-500">Not connected</span>
          <span className="text-[11px] text-slate-500 block mt-0.5">Stopped by policy guardrail</span>
        </div>
        <div className="bg-white rounded-xl p-3.5 border border-slate-200/80 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-500 block">Promoted to Upgrade</span>
          <span className="text-sm font-semibold text-slate-500">Not connected</span>
          <span className="text-[11px] text-slate-500 block mt-0.5">Transferred for review</span>
        </div>
      </div>

      {/* Main Two-Column Lab Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
        {/* Left: Authoritative Experiments List */}
        <section className="lg:col-span-7 bg-white rounded-xl border border-slate-200/80 shadow-2xs overflow-hidden">
          <div className="p-3 border-b border-slate-100 bg-slate-50/60 flex flex-wrap items-center justify-between gap-2">
            <div className="relative flex-1 min-w-[180px]">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
              <input
                type="text"
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                placeholder="Search lab experiments or hypotheses..."
                className="w-full bg-white border border-slate-200 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-hidden focus:border-blue-500"
              />
            </div>
            <div className="flex items-center gap-2 text-xs">
              <select
                value={filterEnv}
                onChange={e => setFilterEnv(e.target.value)}
                className="px-2.5 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 text-xs font-medium"
              >
                <option value="ALL">All Environments</option>
                <option value="MAC_MINI_LOCAL">Mac mini Local</option>
                <option value="ISOLATED_SANDBOX">Isolated Sandbox</option>
                <option value="ORACLE_EVAL">Oracle Eval</option>
              </select>
              <select
                value={filterStatus}
                onChange={e => setFilterStatus(e.target.value)}
                className="px-2.5 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 text-xs font-medium"
              >
                <option value="ALL">All ({labExperiments.length})</option>
                <option value="VALIDATED">Validated ({validatedCount})</option>
                <option value="RUNNING">Running ({runningCount})</option>
                <option value="BLOCKED">Blocked ({blockedCount})</option>
                <option value="PROMOTED_TO_UPGRADE_CONTROL">Promoted ({promotedCount})</option>
              </select>
            </div>
          </div>

          <div className="divide-y divide-slate-100">
            {filteredExperiments.length === 0 ? (
              <div className="p-4"><UnavailableState>Development Labs are not connected to a live source.</UnavailableState></div>
            ) : (
              filteredExperiments.map(exp => {
                const isSelected = activeExp?.id === exp.id;
                return (
                  <button
                    key={exp.id}
                    type="button"
                    onClick={() => setSelectedExpId(exp.id)}
                    className={`w-full text-left p-4 transition-colors cursor-pointer ${
                      isSelected
                        ? 'bg-blue-50/50 border-l-2 border-l-blue-600'
                        : 'hover:bg-slate-50/70'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 space-y-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-sm font-semibold text-slate-900">
                            {exp.name}
                          </span>
                          <TruthBadge truth={exp.truthClass} />
                        </div>
                        <p className="text-xs text-slate-600 leading-relaxed">
                          {exp.hypothesis}
                        </p>
                      </div>
                      <div className="shrink-0">{renderStatusBadge(exp.status)}</div>
                    </div>

                    <div className="mt-2.5 flex flex-wrap items-center gap-3 text-[11px] text-slate-500">
                      <span>Owner: <strong className="text-slate-700">{exp.owner}</strong></span>
                      <span>·</span>
                      <span>Env: <strong className="text-slate-700">{renderEnvLabel(exp.environment)}</strong></span>
                      <span>·</span>
                      <span className="text-slate-700 font-medium">{exp.benchmarkSummary}</span>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </section>

        {/* Right: Detailed Sandbox Inspector & Promotion Gate */}
        <section className="lg:col-span-5 bg-white rounded-xl border border-slate-200/80 shadow-2xs overflow-hidden">
          {activeExp ? (
            <>
              <div className="p-3.5 border-b border-slate-100 bg-slate-50/60 flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-purple-600" />
                  <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                    Sandbox Inspection
                  </h2>
                </div>
                <TruthBadge truth={activeExp.truthClass} />
              </div>

              <div className="p-4 space-y-4 text-xs">
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <span className="text-[11px] font-semibold text-slate-500">
                      {renderEnvLabel(activeExp.environment)} · {activeExp.owner}
                    </span>
                    {renderStatusBadge(activeExp.status)}
                  </div>
                  <h3 className="text-base font-bold text-slate-900">{activeExp.name}</h3>
                  <p className="text-xs text-slate-600 leading-relaxed">{activeExp.hypothesis}</p>
                </div>

                <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1">
                  <span className="text-[10px] font-bold uppercase tracking-wide text-slate-500 block">
                    Benchmark Result
                  </span>
                  <p className="text-xs font-semibold text-slate-900">{activeExp.benchmarkSummary}</p>
                </div>

                {/* Boundary Guardrail */}
                <div className="p-3 rounded-lg bg-rose-50/80 border border-rose-200 text-rose-950 space-y-1">
                  <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase text-rose-800">
                    <ShieldAlert className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                    <span>Sandbox Boundary Policy (canDeployDirectly: {String(activeExp.canDeployDirectly).toUpperCase()})</span>
                  </div>
                  <p className="text-[11px] text-rose-900 leading-relaxed">
                    Experiments in Development / Labs cannot modify live production nodes or Oracle control-plane services directly. Validated experiments promote strictly into Upgrade Control.
                  </p>
                </div>

                {/* Linked Objects */}
                {(linkedProject || linkedApproval) && (
                  <div className="space-y-2">
                    <span className="text-[10px] font-bold uppercase tracking-wide text-slate-500 block">
                      Linked Control-Plane Objects
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {linkedProject && (
                        <button
                          type="button"
                          onClick={() => navigateToObject('projects', linkedProject.id, 'project')}
                          className="px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 flex items-center gap-1.5 cursor-pointer"
                        >
                          <FolderKanban className="w-3.5 h-3.5 text-blue-600" />
                          <span>Project: {linkedProject.name}</span>
                          <ExternalLink className="w-3 h-3 text-slate-400" />
                        </button>
                      )}
                      {linkedApproval && (
                        <button
                          type="button"
                          onClick={() => navigateToObject('approvals', linkedApproval.id, 'approval')}
                          className="px-2.5 py-1.5 rounded-lg border border-amber-200 bg-amber-50 hover:bg-amber-100/70 text-xs font-semibold text-amber-900 flex items-center gap-1.5 cursor-pointer"
                        >
                          <span>Approval: {linkedApproval.title} ({linkedApproval.status})</span>
                          <ExternalLink className="w-3 h-3 text-amber-700" />
                        </button>
                      )}
                    </div>
                  </div>
                )}

                {/* Promotion Action */}
                {activeExp.status === 'VALIDATED' && (
                  <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 space-y-2">
                    <span className="text-[11px] font-bold uppercase text-emerald-800 block">
                      Ready for Upgrade Control Handoff
                    </span>
                    <p className="text-[11px] text-emerald-900 leading-relaxed">
                      Promote this validated experiment to Upgrade Control for security verification, cost review, and rollback planning.
                    </p>
                    <button
                      type="button"
                      disabled
                      onClick={() => showToast('Development Labs actions are not connected.')}
                      className="w-full py-2 px-3 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs flex items-center justify-center gap-1.5 cursor-pointer"
                    >
                      <ArrowRight className="w-3.5 h-3.5" />
                      <span>Promote to Upgrade Control</span>
                    </button>
                  </div>
                )}

                {activeExp.status === 'PROMOTED_TO_UPGRADE_CONTROL' && (
                  <div className="p-3 rounded-lg bg-teal-50 border border-teal-200 space-y-2">
                    <span className="text-[11px] font-bold uppercase text-teal-800 block">
                      Handed Off to Upgrade Control
                    </span>
                    <button
                      type="button"
                      onClick={() => setCurrentPage('upgrade-control')}
                      className="w-full py-2 px-3 rounded-lg bg-teal-600 hover:bg-teal-700 text-white font-semibold text-xs flex items-center justify-center gap-1.5 cursor-pointer"
                    >
                      <ArrowRight className="w-3.5 h-3.5" />
                      <span>Inspect Candidate in Upgrade Control →</span>
                    </button>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="p-6 text-center text-xs text-slate-500">
              Select an experiment to inspect benchmark results and handoff eligibility.
            </div>
          )}
        </section>
      </div>
    </div>
  );
};
