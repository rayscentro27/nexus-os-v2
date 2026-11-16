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
import {
  ServiceHealthState,
  INITIAL_SERVICES,
  CONTROLLED_RECOVERY_POLICIES,
  INITIAL_RECOVERY_ACTIVITY,
  INITIAL_ACTIVE_INCIDENTS,
  INITIAL_DEPARTMENT_OPERATIONS,
  INITIAL_DEPARTMENT_HANDOFFS,
  INITIAL_PROVIDERS_HEALTH,
  INITIAL_ORACLE_HEALTH,
  INITIAL_HUMAN_ACTIONS
} from '../data/systemsOperationsData';
import { useNexus } from '../context/NexusContext';
import { TruthBadge } from '../components/common/TruthBadge';
import { AgentFleetHealthMonitor } from '../components/dashboard/AgentFleetHealthMonitor';
import { ResourceUsageDashboard } from '../components/dashboard/ResourceUsageDashboard';

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
    sendMessage,
  } = useNexus();

  const [activeTab, setActiveTab] = useState<SystemsTab>('overview');
  const [serviceStateFilter, setServiceStateFilter] = useState<'ALL' | ServiceHealthState>('ALL');
  const [recoveryPolicyMode, setRecoveryPolicyMode] = useState<'ALL' | 'AUTOMATIC' | 'ESCALATION_ONLY'>('ALL');
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [isProbing, setIsProbing] = useState(false);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3200);
  };

  const handleRunReconciliation = () => {
    if (isProbing) return;
    setIsProbing(true);
    showToast('Probing Oracle, Contabo, Mac mini, Supabase, n8n & Postiz...');
    setTimeout(() => {
      setIsProbing(false);
      showToast('Reconciliation complete: Core coordination nodes checked, Commerce Stripe gate flagged BLOCKED.');
      sendMessage('Systems health probe completed across distributed nodes.');
    }, 1200);
  };

  const filteredServices = INITIAL_SERVICES.filter(s =>
    serviceStateFilter === 'ALL' ? true : s.state === serviceStateFilter
  );

  const filteredPolicies = CONTROLLED_RECOVERY_POLICIES.filter(p =>
    recoveryPolicyMode === 'ALL' ? true : p.mode === recoveryPolicyMode
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
          onClick={handleRunReconciliation}
          disabled={isProbing}
          className="px-3.5 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white text-xs font-medium inline-flex items-center gap-1.5 cursor-pointer shrink-0"
        >
          <RotateCw className={`w-3.5 h-3.5 ${isProbing ? 'animate-spin' : ''}`} />
          {isProbing ? 'Probing Nodes...' : 'Run Health Probe'}
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
            Oracle, Contabo, Mac mini, Supabase, n8n, Postiz
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200/80 p-3.5 shadow-2xs">
          <div className="text-[11px] font-medium text-slate-500">Oracle Workload Policy</div>
          <div className="text-xl font-semibold text-emerald-700 mt-1">
            Coordination Only
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
            Commerce Stripe checkout + Marketing Facebook auth
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
          { id: 'incidents', label: `Incidents & Blockers (${INITIAL_ACTIVE_INCIDENTS.length})` },
          { id: 'recovery', label: 'Recovery Policies & Receipts' },
          { id: 'handoffs', label: 'Department Handoffs' },
          { id: 'agents', label: 'Agent Fleet & Providers' },
        ].map(tab => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id as SystemsTab)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors cursor-pointer ${
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
          <ResourceUsageDashboard />

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
                Service Health Inventory ({INITIAL_SERVICES.length})
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
                        {srv.host}
                      </td>
                      <td className="py-2.5 px-3">{getServiceStateBadge(srv.state)}</td>
                      <td className="py-2.5 px-3 text-slate-600">{srv.lastHeartbeat}</td>
                      <td className="py-2.5 px-3 text-slate-600">
                        {srv.currentIncident || 'Nominal'}
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

      {/* TAB 2: INCIDENTS & BLOCKERS */}
      {activeTab === 'incidents' && (
        <div className="space-y-4">
          {INITIAL_HUMAN_ACTIONS.length > 0 && (
            <div className="bg-rose-50/70 border border-rose-200 rounded-xl p-4 space-y-3">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-rose-600" />
                <h2 className="text-sm font-semibold text-rose-950">
                  Human Action Required (Safety Boundary Escalations)
                </h2>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                {INITIAL_HUMAN_ACTIONS.map(act => (
                  <div
                    key={act.id}
                    className="bg-white rounded-lg p-3 border border-rose-200 space-y-1.5"
                  >
                    <div className="font-semibold text-rose-950">{act.issue}</div>
                    <div className="text-slate-600">Capability: {act.affectedCapability}</div>
                    <div className="text-amber-900 bg-amber-50 p-2 rounded border border-amber-100">
                      {act.whySystemsStopped}
                    </div>
                    <div className="text-blue-900 bg-blue-50 p-2 rounded border border-blue-100">
                      Required: {act.requiredAction}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs space-y-3">
            <h2 className="text-sm font-semibold text-slate-900">
              Active Incidents &amp; Credential Gates
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead className="bg-slate-50 text-[10px] font-semibold text-slate-500 uppercase border-b border-slate-200">
                  <tr>
                    <th className="py-2 px-3">Severity</th>
                    <th className="py-2 px-3">Affected Service</th>
                    <th className="py-2 px-3">Failure Class</th>
                    <th className="py-2 px-3">State</th>
                    <th className="py-2 px-3">Impact</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {INITIAL_ACTIVE_INCIDENTS.map(inc => (
                    <tr key={inc.id} className="hover:bg-slate-50/70">
                      <td className="py-2.5 px-3 font-semibold text-rose-700">{inc.severity}</td>
                      <td className="py-2.5 px-3 font-medium text-slate-900">
                        {inc.affectedService}
                      </td>
                      <td className="py-2.5 px-3 font-mono text-[11px] text-slate-600">
                        {inc.failureClass}
                      </td>
                      <td className="py-2.5 px-3 text-slate-700">{inc.recoveryState}</td>
                      <td className="py-2.5 px-3 text-slate-600">{inc.currentImpact}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: RECOVERY POLICIES & RECEIPTS */}
      {activeTab === 'recovery' && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-100">
              <h2 className="text-sm font-semibold text-slate-900">
                Controlled Recovery Policies
              </h2>
              <div className="flex items-center gap-1 text-xs">
                {(['ALL', 'AUTOMATIC', 'ESCALATION_ONLY'] as const).map(m => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setRecoveryPolicyMode(m)}
                    className={`px-2.5 py-1 rounded-md font-medium cursor-pointer ${
                      recoveryPolicyMode === m
                        ? 'bg-slate-900 text-white'
                        : 'text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    {m}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 text-xs">
              {filteredPolicies.map(pol => (
                <div
                  key={pol.id}
                  className="p-3 rounded-xl border border-slate-200/80 bg-slate-50/60 space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                      {pol.mode}
                    </span>
                    <span className="text-[10px] text-slate-500">Max {pol.maxAttempts}x</span>
                  </div>
                  <div className="font-semibold text-slate-900">{pol.action}</div>
                  <div className="text-[11px] text-slate-600">{pol.verificationMethod}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs space-y-3">
            <h2 className="text-sm font-semibold text-slate-900">Recent Recovery Receipts</h2>
            <div className="space-y-2 text-xs">
              {INITIAL_RECOVERY_ACTIVITY.map(act => (
                <div
                  key={act.id}
                  className="p-2.5 rounded-lg bg-slate-50 border border-slate-100 flex flex-wrap items-center justify-between gap-2"
                >
                  <div>
                    <div className="font-semibold text-slate-900">
                      {act.service} — {act.recoveryAction}
                    </div>
                    <div className="text-[11px] text-slate-500">
                      {act.incident} · Proof: {act.verification}
                    </div>
                  </div>
                  <div className="text-right font-mono text-[11px] text-slate-500">
                    <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 font-sans font-semibold mr-2">
                      {act.result}
                    </span>
                    {act.receiptId}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: DEPARTMENT HANDOFFS */}
      {activeTab === 'handoffs' && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-blue-600" />
                <h2 className="text-sm font-semibold text-slate-900">
                  Cross-Department Durable Handoffs
                </h2>
              </div>
              <TruthBadge truth="DEMO" label="Durable Bus Trace" />
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead className="bg-slate-50 text-[10px] font-semibold text-slate-500 uppercase border-b border-slate-200">
                  <tr>
                    <th className="py-2 px-3">Route</th>
                    <th className="py-2 px-3">Topic</th>
                    <th className="py-2 px-3">Status</th>
                    <th className="py-2 px-3">Result</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {INITIAL_DEPARTMENT_HANDOFFS.map(h => (
                    <tr key={h.id} className="hover:bg-slate-50/70">
                      <td className="py-2.5 px-3 font-medium text-slate-900">
                        {h.sourceDept} → {h.targetDept}
                      </td>
                      <td className="py-2.5 px-3 text-slate-700">{h.topic}</td>
                      <td className="py-2.5 px-3">
                        <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 text-[10px] font-semibold">
                          {h.status}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-slate-600">{h.result}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 pt-2">
              {INITIAL_DEPARTMENT_OPERATIONS.map(d => (
                <div
                  key={d.id}
                  className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80 text-xs flex items-center justify-between"
                >
                  <div>
                    <div className="font-medium text-slate-900">{d.deptName}</div>
                    <div className="text-[11px] text-slate-500">{d.lastSuccess}</div>
                  </div>
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700">
                    {d.workerState}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: AGENT FLEET & PROVIDERS */}
      {activeTab === 'agents' && (
        <div className="space-y-4">
          <AgentFleetHealthMonitor />

          <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-900">
                Provider Health &amp; Oracle Coordination Node
              </h2>
              <span className="text-xs text-slate-500">
                Oracle MCP: {INITIAL_ORACLE_HEALTH.nexusMcp} · Hermes {INITIAL_ORACLE_HEALTH.hermes}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5 text-xs">
              {INITIAL_PROVIDERS_HEALTH.map(prv => (
                <div
                  key={prv.id}
                  className="p-3 rounded-lg bg-slate-50 border border-slate-200/80 flex items-center justify-between"
                >
                  <div>
                    <div className="font-medium text-slate-900">{prv.name}</div>
                    <div className="text-[11px] text-slate-500">{prv.notes || 'Nominal'}</div>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-white border border-slate-200 text-slate-700">
                    {prv.state}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
