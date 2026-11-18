import React, { useMemo, useState } from 'react';
import { Cpu } from 'lucide-react';
import { useNexus } from '../context/NexusContext';
import { TruthBadge } from '../components/common/TruthBadge';
import { Card, Field, LiveProvenance, when } from '../components/live/LiveBits';

const STATUS_STYLE: Record<string, string> = {
  COMPLETE: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  RUNNING: 'bg-blue-50 text-blue-700 border-blue-200',
  QUEUED: 'bg-slate-50 text-slate-700 border-slate-200',
  BLOCKED: 'bg-amber-50 text-amber-800 border-amber-200',
  FAILED: 'bg-rose-50 text-rose-700 border-rose-200',
};

export const ReaPage: React.FC = () => {
  const { liveAreas } = useNexus();
  const jobs: any[] = liveAreas.rea || [];
  const [selected, setSelected] = useState<string | null>(null);
  const active = useMemo(() => jobs.find(j => j.reaJobId === selected) || jobs[0], [jobs, selected]);
  const counts = useMemo(() => jobs.reduce((m: Record<string, number>, j) => ({ ...m, [j.status]: (m[j.status] || 0) + 1 }), {}), [jobs]);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">REA Workspace</h1>
        <p className="text-sm text-slate-500 mt-0.5">Reverse-engineering &amp; analysis jobs on the Contabo REA harness. Read-only view of durable REA_EXECUTION jobs.</p>
        <div className="mt-2"><LiveProvenance source="nexus_durable_jobs (REA_EXECUTION), latest 20" /></div>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {['COMPLETE', 'RUNNING', 'QUEUED', 'BLOCKED', 'FAILED'].map(s => (
          <div key={s} className="bg-white rounded-2xl border border-slate-200/90 p-3">
            <div className="text-[11px] font-semibold text-slate-500">{s}</div>
            <div className="text-xl font-bold text-slate-900">{counts[s] || 0}</div>
          </div>
        ))}
      </div>
      {jobs.length === 0 ? (
        <Card><p className="text-sm text-slate-500">No REA jobs in the read model (NOT CONNECTED or none recorded).</p></Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
          <div className="lg:col-span-5 bg-white rounded-2xl border border-slate-200/90 overflow-hidden divide-y divide-slate-100 max-h-[70vh] overflow-y-auto">
            {jobs.map(j => (
              <button key={j.reaJobId} type="button" onClick={() => setSelected(j.reaJobId)}
                className={`w-full text-left p-3.5 cursor-pointer transition-colors ${active?.reaJobId === j.reaJobId ? 'bg-blue-50/60' : 'hover:bg-slate-50'}`}>
                <div className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 text-xs font-mono text-slate-600"><Cpu className="w-3.5 h-3.5 text-slate-400" />{j.reaJobId}</span>
                  <span className={`px-2 py-0.5 rounded-full border text-[10px] font-semibold ${STATUS_STYLE[j.status] || STATUS_STYLE.QUEUED}`}>{j.status}</span>
                </div>
                <div className="mt-1 text-xs text-slate-800 line-clamp-2">{j.objective || 'UNKNOWN objective'}</div>
                <div className="mt-1 text-[11px] text-slate-500">{j.workType || 'UNKNOWN'} · {when(j.createdAt)}</div>
              </button>
            ))}
          </div>
          {active && (
            <div className="lg:col-span-7 space-y-4">
              <Card title="Job" right={<TruthBadge truth="VERIFIED" size="xs" />}>
                <Field label="REA job ID" value={active.reaJobId} />
                <Field label="Status" value={active.status} />
                <Field label="Project ID" value={active.projectId} fallback="— (not project-linked)" />
                <Field label="Target" value={active.target} />
                <Field label="Work type" value={active.workType} />
                <Field label="Provider mode" value={active.providerMode} />
                <Field label="Model" value={active.model} />
                <Field label="Tool profile" value={active.toolProfile} />
                <Field label="Session" value={active.sessionId} />
                <Field label="Started" value={when(active.startedAt)} />
                <Field label="Completed" value={active.completedAt ? when(active.completedAt) : null} fallback="—" />
              </Card>
              <Card title="Objective"><p className="text-xs text-slate-700 whitespace-pre-wrap">{active.objective || 'UNKNOWN'}</p></Card>
              <Card title="Result summary">
                {active.resultSummary ? (
                  <pre className="text-[11px] text-slate-700 whitespace-pre-wrap break-words max-h-64 overflow-y-auto">{JSON.stringify(active.resultSummary, null, 2)}</pre>
                ) : <p className="text-xs text-slate-500">No structured result summary recorded.</p>}
                {active.blocker && <div className="mt-2 text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-xl px-3 py-2">Blocker: {String(active.blocker)}</div>}
              </Card>
              <Card title={`Evidence (${(active.evidence || []).length})`}>
                {(active.evidence || []).length === 0 ? <p className="text-xs text-slate-500">No receipts recorded.</p> : (
                  <ul className="space-y-1">{active.evidence.map((e: any, i: number) => (
                    <li key={i} className="text-[11px] font-mono text-slate-600 break-all">{typeof e === 'string' ? e : JSON.stringify(e).slice(0, 220)}</li>
                  ))}</ul>
                )}
              </Card>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
