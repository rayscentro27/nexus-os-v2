import React, { useState } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  Activity,
  AlertTriangle,
  RotateCw,
  CheckCircle2,
  Clock,
  Layers,
  Server,
  Database,
  ArrowRight,
  GitBranch,
  XCircle,
  HelpCircle,
  ExternalLink
} from 'lucide-react';
import { ServiceHealthState } from '../data/systemsOperationsData';
import { useNexus } from '../context/NexusContext';
import { TruthBadge } from '../components/common/TruthBadge';
import { ResourceUsageDashboard } from '../components/dashboard/ResourceUsageDashboard';
import { UnavailableState } from '../components/live/UnavailableState';

type SystemsTab =
  | 'overview'
  | 'incidents'
  | 'recovery'
  | 'handoffs'
  | 'agents';

export const SystemsPage: React.FC = () => {
  const {
    distributedSystems,
    approvals,
    navigateToObject,
  } = useNexus();

  const [activeTab, setActiveTab] = useState<SystemsTab>('overview');
  const [serviceStateFilter, setServiceStateFilter] = useState<'ALL' | ServiceHealthState>('ALL');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3200);
  };

  const filteredServices = distributedSystems.filter(s =>
    serviceStateFilter === 'ALL' || (serviceStateFilter === 'STOPPED'
      ? s.status === 'BLOCKED' || s.status === 'NOT_CONNECTED'
      : s.status === serviceStateFilter)
  );

  const systemsPendingApprovals = approvals.filter(
    a => (a.department === 'Systems' || a.type === 'Production changes' || a.type === 'Credentials') && a.status === 'PENDING'
  );

  const healthyNodesCount = distributedSystems.filter(n => n.status === 'HEALTHY').length;
  const blockedOrNotConnectedCount = distributedSystems.filter(
    n => n.status === 'BLOCKED' || n.status === 'NOT_CONNECTED'
  ).length;

  const getNodeStatusBadge = (status: string) => {
    switch (status) {
      case 'HEALTHY':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'PAPER_MODE':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'DEGRADED':
        return 'bg-amber-50 text-amber-800 border-amber-200';
      case 'BLOCKED':
      case 'NOT_CONNECTED':
      default:
        return 'bg-rose-50 text-rose-700 border-rose-200';
    }
  };

  const getServiceStateBadge = (state: ServiceHealthState) => {
    switch (state) {
      case 'HEALTHY':
        return (
          <span className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 inline-flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            Healthy
          </span>
        );
      case 'DEGRADED':
        return (
          <span className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-amber-50 text-amber-800 border border-amber-200 inline-flex items-center gap-1">
            <AlertTriangle className="w-3 h-3 text-amber-600" />
            Degraded
          </span>
        );
      case 'STALE':
        return (
          <span className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-orange-50 text-orange-800 border border-orange-200 inline-flex items-center gap-1">
            <Clock className="w-3 h-3 text-orange-600" />
            Stale
          </span>
        );
      case 'STOPPED':
        return (
          <span className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-rose-50 text-rose-700 border border-rose-200 inline-flex items-center gap-1">
            <XCircle className="w-3 h-3 text-rose-600" />
            Blocked / Stopped
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-slate-100 text-slate-700 border border-slate-200 inline-flex items-center gap-1">
            <HelpCircle className="w-3 h-3 text-slate-500" />
            Unknown
          </span>
        );
    }
  };

  return (
    <div className="space-y-4 pb-10">
      {toastMessage && (
        <div className="fixed top-14 right-6 z-50 animate-in slide-in-from-top duration-200">
          <div className="bg-slate-900 text-white px-4 py-2.5 rounded-xl shadow-lg flex items-center gap-2 text-xs font-medium border border-slate-700">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{toastMessage}</span>
          </div>
        </div>
      )}

      {/* Header + Primary Question */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Server className="w-4 h-4 text-blue-600" />
            <h1 className="text-lg font-semibold text-slate-900 tracking-tight">
              Systems &amp; Distributed Infrastructure
            </h1>
            <TruthBadge truth="VERIFIED" label="Runtime Topology" />
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Is Nexus operating correctly? Oracle reserved strictly for Nova/Hermes &amp; essential coordination (zero heavy LLM/batch jobs).
          </p>
        </div>

        <button
          type="button"
          disabled
          className="px-3.5 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white text-xs font-medium inline-flex items-center gap-1.5 cursor-pointer shrink-0"
        >
          <RotateCw className="w-3.5 h-3.5" />
          Health probes not connected
        </button>
      </div>

      {/* 4 Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="bg-white rounded-xl border border-slate-200/80 p-3.5 shadow-2xs">
          <div className="text-[11px] font-medium text-slate-500">Distributed Nodes</div>
          <div className="text-xl font-semibold text-slate-900 mt-1 tabular-nums">
            {healthyNodesCount} / {distributedSystems.length} Healthy
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">
            Current live system records
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200/80 p-3.5 shadow-2xs">
          <div className="text-[11px] font-medium text-slate-500">Oracle Workload Policy</div>
          <div className="text-xl font-semibold text-emerald-700 mt-1">
            {distributedSystems.find(s => /oracle/i.test(s.name))?.workloadPolicy || 'UNKNOWN'}
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">
            Nova/Hermes routing · Zero heavy batch workloads
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200/80 p-3.5 shadow-2xs">
          <div className="text-[11px] font-medium text-slate-500">Blocked / Missing Auth</div>
          <div className="text-xl font-semibold text-rose-700 mt-1 tabular-nums">
            {blockedOrNotConnectedCount}
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">
            Live blockers returned by the systems read model
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200/80 p-3.5 shadow-2xs">
          <div className="text-[11px] font-medium text-slate-500">Production Gates</div>
          <div className="text-xl font-semibold text-amber-700 mt-1 tabular-nums">
            {systemsPendingApprovals.length} Pending
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">
            Requires Ray sign-off in Approvals
          </div>
        </div>
      </div>

      {/* Sub-navigation Tabs */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-1.5 flex items-center gap-1 overflow-x-auto shadow-2xs">
        {[
          { id: 'overview', label: 'Topology & Service Health' },
          { id: 'incidents', label: 'Incidents & Blockers (not connected)' },
          { id: 'recovery', label: 'Recovery Policies & Receipts' },
          { id: 'handoffs', label: 'Department Handoffs' },
          { id: 'agents', label: 'Agent Fleet & Providers' },
        ].map(tab => (
          <button
            key={tab.id}
            type="button"
            disabled={tab.id !== 'overview'}
            onClick={() => tab.id === 'overview' && setActiveTab(tab.id as SystemsTab)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${tab.id !== 'overview' ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'} ${
              activeTab === tab.id
                ? 'bg-blue-600 text-white'
                : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* TAB 1: TOPOLOGY & SERVICE HEALTH */}
      {activeTab === 'overview' && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs"><UnavailableState>Resource telemetry is not connected to a live source.</UnavailableState></div>

          {/* Distributed Architecture Cards */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <div>
                <h2 className="text-sm font-semibold text-slate-900">
                  Distributed Host &amp; Subsystem Topology
                </h2>
                <p className="text-xs text-slate-500">
                  Authoritative node allocation across Oracle Cloud, Contabo, Mac mini, and department engines.
                </p>
              </div>
              <TruthBadge truth="VERIFIED" />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {distributedSystems.map(node => (
                <div
                  key={node.id}
                  className="p-3.5 rounded-xl border border-slate-200/80 bg-slate-50/60 flex flex-col justify-between gap-2.5"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-semibold text-slate-900">{node.name}</span>
                      <span
                        className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${getNodeStatusBadge(
                          node.status
                        )}`}
                      >
                        {node.status.replace('_', ' ')}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-500 mt-0.5">{node.role}</div>
                    <p className="text-xs text-slate-700 mt-2 leading-relaxed">
                      {node.workloadPolicy}
                    </p>
                  </div>

                  <div className="space-y-1.5 pt-2 border-t border-slate-200/60">
                    <div className="flex flex-wrap gap-1">
                      {node.activeServices.map(svc => (
                        <span
                          key={svc}
                          className="text-[10px] px-1.5 py-0.5 rounded bg-white border border-slate-200 text-slate-600"
                        >
                          {svc}
                        </span>
                      ))}
                    </div>
                    {node.blocker && (
                      <div className="text-[11px] text-rose-700 bg-rose-50 border border-rose-200 rounded px-2 py-1">
                        Blocker: {node.blocker}
                      </div>
                    )}
                    <div className="flex items-center justify-between text-[10px] text-slate-400">
                      <span>Checked {node.lastChecked}</span>
                      <TruthBadge truth={node.truthClass} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Pending Systems / Production Approvals */}
          {systemsPendingApprovals.length > 0 && (
            <div className="bg-amber-50/70 border border-amber-200 rounded-xl p-3.5 flex flex-wrap items-center justify-between gap-3 text-xs">
              <div>
                <span className="font-semibold text-amber-950">Production Release Gate Waiting: </span>
                <span className="text-amber-900">
                  {systemsPendingApprovals[0].title} — {systemsPendingApprovals[0].blockedAction}
                </span>
              </div>
              <button
                type="button"
                onClick={() =>
                  navigateToObject('approvals', systemsPendingApprovals[0].id, 'approval')
                }
                className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-medium inline-flex items-center gap-1 cursor-pointer"
              >
                Open in Approvals <ExternalLink className="w-3 h-3" />
              </button>
            </div>
          )}

          {/* Detailed Daemon & Service Table */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-100">
              <h2 className="text-sm font-semibold text-slate-900">
                Service Health Inventory ({distributedSystems.length})
              </h2>
              <div className="flex items-center gap-1 text-xs">
                {(['ALL', 'HEALTHY', 'DEGRADED', 'STOPPED'] as const).map(tab => (
                  <button
                    key={tab}
                    type="button"
                    onClick={() => setServiceStateFilter(tab)}
                    className={`px-2.5 py-1 rounded-md font-medium cursor-pointer ${
                      serviceStateFilter === tab
                        ? 'bg-slate-900 text-white'
                        : 'text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead className="bg-slate-50 text-[10px] font-semibold text-slate-500 uppercase border-b border-slate-200">
                  <tr>
                    <th className="py-2 px-3">Service</th>
                    <th className="py-2 px-3">Host</th>
                    <th className="py-2 px-3">State</th>
                    <th className="py-2 px-3">Heartbeat</th>
                    <th className="py-2 px-3">Current Note</th>
                    <th className="py-2 px-3 text-right">Truth</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredServices.map(srv => (
                    <tr key={srv.id} className="hover:bg-slate-50/70">
                      <td className="py-2.5 px-3 font-medium text-slate-900">{srv.name}</td>
                      <td className="py-2.5 px-3 font-mono text-[11px] text-slate-600">
                        {srv.role || 'UNKNOWN'}
                      </td>
                      <td className="py-2.5 px-3">{getServiceStateBadge(srv.status as ServiceHealthState)}</td>
                      <td className="py-2.5 px-3 text-slate-600">{srv.lastChecked}</td>
                      <td className="py-2.5 px-3 text-slate-600">
                        {srv.blocker || srv.activeServices.join(', ') || 'UNKNOWN'}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <TruthBadge truth={srv.truthClass} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab !== 'overview' && (
        <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs">
          <UnavailableState>This Systems view is not connected to a live source.</UnavailableState>
        </div>
      )}

    </div>
  );
};
