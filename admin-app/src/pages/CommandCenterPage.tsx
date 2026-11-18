import React, { useMemo } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  FolderKanban,
  Server,
  ShieldAlert,
  Sparkles,
  Clock,
} from 'lucide-react';
import { useNexus } from '../context/NexusContext';
import { TruthBadge } from '../components/common/TruthBadge';
import { ResourceUsageDashboard } from '../components/dashboard/ResourceUsageDashboard';
import { ASSETS } from '../data/assets';
import { NovaVideo } from '../components/nova/NovaVideo';

export const CommandCenterPage: React.FC = () => {
  const {
    projects,
    approvals,
    notifications,
    distributedSystems,
    commerceOffers,
    navigateToObject,
    setIsNovaDrawerOpen,
    setIsNeedsRayDrawerOpen,
    liveAreas,
  } = useNexus();
  const liveTrading = liveAreas.trading || {};
  const tradingVersion = (liveTrading.versions || [])[0];

  const pendingApprovals = useMemo(
    () => approvals.filter(a => a.status === 'PENDING'),
    [approvals]
  );

  const activeProjects = useMemo(
    () => projects.filter(p => p.status === 'ACTIVE' || p.status === 'AWAITING_APPROVAL'),
    [projects]
  );

  const blockedItems = useMemo(() => {
    const projBlockers = projects.filter(p => p.blocker);
    const sysBlockers = distributedSystems.filter(s => s.blocker);
    return {
      count: projBlockers.length + sysBlockers.length,
      projBlockers,
      sysBlockers,
    };
  }, [projects, distributedSystems]);

  const completedToday = useMemo(() => {
    const today = new Date().toISOString().slice(0, 10);
    return notifications.filter(n => (n.type === 'WORK_COMPLETED' || n.type === 'CREATIVE_CREATED') && String(n.timestamp).startsWith(today));
  }, [notifications]);
  const completedTodayCount = completedToday.length;

  const recentTimeline = useMemo(() => {
    const items: { id: string; timestamp: string; department: string; text: string; truth: string }[] = [];
    projects.forEach(p => {
      p.activityLog.slice(0, 2).forEach(act => {
        items.push({
          id: `${p.id}-${act.id}`,
          timestamp: act.timestamp,
          department: act.department,
          text: `${p.name}: ${act.event}`,
          truth: act.truthClass,
        });
      });
    });
    return items.slice(0, 6);
  }, [projects]);

  const primaryProject =
    projects.find(p => p.id === 'proj_98ef515bccee4b58') || projects[0];
  const primaryOffer = commerceOffers[0];

  const healthyNodesCount = distributedSystems.filter(
    s => s.status === 'HEALTHY' || s.status === 'PAPER_MODE'
  ).length;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Nexus Overview
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            What is Nexus doing, what needs Ray&apos;s attention, and what happens next.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={() => setIsNeedsRayDrawerOpen(true)}
            className="px-3 py-1.5 rounded-xl bg-white border border-slate-200 hover:bg-slate-50 text-xs font-semibold text-slate-700 cursor-pointer transition-colors"
          >
            Quick Queue ({pendingApprovals.length})
          </button>
          <button
            type="button"
            onClick={() => setIsNovaDrawerOpen(true)}
            className="px-3 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Ask Nova</span>
          </button>
        </div>
      </div>

      {/* 4 Compact Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <button
          type="button"
          onClick={() => navigateToObject('approvals')}
          className="bg-white rounded-2xl border border-slate-200/90 p-4 text-left hover:border-amber-300 transition-colors cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Needs Your Approval</span>
            <AlertTriangle className="w-4 h-4 text-amber-600" />
          </div>
          <div className="mt-2 text-2xl font-bold text-slate-900 tabular-nums">
            {pendingApprovals.length}
          </div>
          <div className="mt-1 text-xs text-slate-500">
            {pendingApprovals.filter(a => a.priority === 'HIGH').length} high priority
          </div>
        </button>

        <button
          type="button"
          onClick={() => navigateToObject('projects')}
          className="bg-white rounded-2xl border border-slate-200/90 p-4 text-left hover:border-blue-300 transition-colors cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Active Projects</span>
            <FolderKanban className="w-4 h-4 text-blue-600" />
          </div>
          <div className="mt-2 text-2xl font-bold text-slate-900 tabular-nums">
            {activeProjects.length}
          </div>
          <div className="mt-1 text-xs text-slate-500 truncate">
            Lead: {primaryProject?.name}
          </div>
        </button>

        <button
          type="button"
          onClick={() => navigateToObject('business-hub')}
          className="bg-white rounded-2xl border border-slate-200/90 p-4 text-left hover:border-rose-300 transition-colors cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Blocked Actions</span>
            <ShieldAlert className="w-4 h-4 text-rose-600" />
          </div>
          <div className="mt-2 text-2xl font-bold text-slate-900 tabular-nums">
            {blockedItems.count}
          </div>
          <div className="mt-1 text-xs text-rose-700 truncate">
            {blockedItems.projBlockers[0]?.blocker || blockedItems.sysBlockers[0]?.blocker || 'No blocked actions'}
          </div>
        </button>

        <button
          type="button"
          onClick={() => navigateToObject('trading-engine')}
          className="bg-white rounded-2xl border border-slate-200/90 p-4 text-left hover:border-emerald-300 transition-colors cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Completed Today</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="mt-2 text-2xl font-bold text-slate-900 tabular-nums">
            {completedTodayCount}
          </div>
          <div className="mt-1 text-xs text-slate-500">
            {completedToday[0]?.title || 'No completed work recorded today'}
          </div>
        </button>
      </div>

      {/* Main Content Split */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left 8 Columns: Priority Queue + Active Projects + Activity */}
        <div className="lg:col-span-8 space-y-6">
          {/* Priority Queue */}
          <section className="bg-white rounded-2xl border border-slate-200/90 overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold text-slate-900">Priority Queue</h2>
                <p className="text-xs text-slate-500">
                  Items currently paused for Ray&apos;s approval
                </p>
              </div>
              <button
                type="button"
                onClick={() => navigateToObject('approvals')}
                className="text-xs font-semibold text-blue-600 hover:underline flex items-center gap-1 cursor-pointer"
              >
                <span>Open Approvals</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {pendingApprovals.length === 0 ? (
              <div className="p-6 text-center text-xs text-slate-500">
                All approval gates are currently cleared.
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {pendingApprovals.slice(0, 5).map(item => (
                  <div
                    key={item.id}
                    className="px-5 py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50/70 transition-colors"
                  >
                    <div className="min-w-0 space-y-0.5">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-semibold text-slate-900 truncate">
                          {item.title}
                        </span>
                        <span
                          className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${
                            item.priority === 'HIGH'
                              ? 'bg-rose-50 text-rose-700 border-rose-200'
                              : item.priority === 'MEDIUM'
                              ? 'bg-amber-50 text-amber-800 border-amber-200'
                              : 'bg-slate-100 text-slate-600 border-slate-200'
                          }`}
                        >
                          {item.priority}
                        </span>
                      </div>
                      <div className="text-xs text-slate-500 flex items-center gap-1.5 flex-wrap">
                        <span className="font-medium text-slate-700">{item.type}</span>
                        <span>·</span>
                        <span>{item.projectName}</span>
                        <span>·</span>
                        <span className="truncate">{item.blockedAction}</span>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => navigateToObject('approvals', item.id, 'approval')}
                      className="px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold shrink-0 cursor-pointer transition-colors"
                    >
                      Review
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Active Projects */}
          <section className="bg-white rounded-2xl border border-slate-200/90 overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold text-slate-900">Active Projects</h2>
                <p className="text-xs text-slate-500">
                  Durable cross-department state across Research, Creative, Commerce, and Distribution
                </p>
              </div>
              <button
                type="button"
                onClick={() => navigateToObject('projects')}
                className="text-xs font-semibold text-blue-600 hover:underline flex items-center gap-1 cursor-pointer"
              >
                <span>All Projects</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="divide-y divide-slate-100">
              {projects.map(proj => (
                <div
                  key={proj.id}
                  onClick={() => navigateToObject('projects', proj.id, 'project')}
                  className="px-5 py-3.5 hover:bg-slate-50/70 transition-colors cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                >
                  <div className="min-w-0 space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-semibold text-slate-900">{proj.name}</span>
                      <span className="text-[11px] font-mono text-slate-400">{proj.id}</span>
                      <TruthBadge truth={proj.truthClass} />
                    </div>
                    <div className="text-xs text-slate-600 flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-blue-700">{proj.currentDepartment}</span>
                      <span className="text-slate-300">·</span>
                      <span className="font-mono text-[11px] text-slate-600">{proj.stage}</span>
                      <span className="text-slate-300">·</span>
                      <span>Next: {proj.nextAction}</span>
                    </div>
                    {proj.blocker && (
                      <div className="text-[11px] text-rose-700 font-medium">
                        Blocker: {proj.blocker}
                      </div>
                    )}
                  </div>

                  <span className="text-xs font-semibold text-slate-500 shrink-0">
                    Inspect →
                  </span>
                </div>
              ))}
            </div>
          </section>

          {/* Recent Activity Timeline */}
          <section className="bg-white rounded-2xl border border-slate-200/90 overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between">
              <h2 className="text-sm font-bold text-slate-900">Recent Activity</h2>
              <span className="text-xs text-slate-400">Authoritative event stream</span>
            </div>
            <div className="divide-y divide-slate-100">
              {recentTimeline.map(ev => (
                <div key={ev.id} className="px-5 py-3 flex items-start justify-between gap-3">
                  <div className="flex items-start gap-2.5 min-w-0">
                    <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
                    <div className="min-w-0">
                      <p className="text-xs text-slate-800 leading-snug">{ev.text}</p>
                      <div className="mt-1 flex items-center gap-2 text-[11px] text-slate-500">
                        <span>{ev.department}</span>
                        <span>·</span>
                        <span className="tabular-nums">{ev.timestamp}</span>
                      </div>
                    </div>
                  </div>
                  <TruthBadge truth={ev.truth} />
                </div>
              ))}
            </div>
          </section>
        </div>

        {/* Right 4 Columns: Grounded Nova Summary + Compact System Health */}
        <div className="lg:col-span-4 space-y-6">
          {/* Nova Summary */}
          <section className="bg-white rounded-2xl border border-slate-200/90 p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-full overflow-hidden border border-blue-200 bg-slate-900 shrink-0">
                  <NovaVideo
                    aria-label="Nova"
                    className="w-full h-full object-cover object-[50%_18%]"
                  />
                </div>
                <h2 className="text-sm font-bold text-slate-900">Nova Summary</h2>
              </div>
              <TruthBadge truth="VERIFIED" label="GROUNDED" />
            </div>

            <ul className="space-y-2.5 text-xs text-slate-700 leading-relaxed">
              <li className="flex items-start gap-2">
                <span className="text-blue-600 font-bold">•</span>
                <span>
                  <strong>{pendingApprovals.length} approvals</strong> currently await Ray&apos;s
                  review across projects and infrastructure.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-600 font-bold">•</span>
                <span>
                  <strong>{primaryProject?.name}</strong> is in{' '}
                  <span className="font-mono">{primaryProject?.stage}</span> ({primaryProject?.nextAction})
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-rose-600 font-bold">•</span>
                <span>
                  {primaryOffer ? (
                    <>
                      Printify base cost is <strong>${primaryOffer.productTruth.baseCost ?? 'UNKNOWN'} [{primaryOffer.productTruth.baseCostTruth}]</strong>; live checkout is{' '}
                      <strong>{primaryOffer.liveSales.checkoutStatus}</strong>{primaryOffer.liveSales.blockerReason ? ` (${primaryOffer.liveSales.blockerReason})` : ''}.
                    </>
                  ) : (
                    <>Commerce offer state is NOT CONNECTED.</>
                  )}
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-emerald-600 font-bold">•</span>
                <span>
                  {tradingVersion ? (
                    <>
                      Trading Core (<strong>{tradingVersion.name} · {tradingVersion.instrument} {tradingVersion.timeframe}</strong>) is{' '}
                      {String(tradingVersion.status || 'UNKNOWN').toLowerCase()} in {liveTrading.broker} {liveTrading.mode} mode; live trading{' '}
                      {liveTrading.liveTradingEnabled === false ? 'locked OFF' : 'state UNKNOWN'}.
                    </>
                  ) : (
                    <>Trading state is NOT CONNECTED.</>
                  )}
                </span>
              </li>
            </ul>

            <div className="pt-2 border-t border-slate-100 flex items-center gap-2">
              <button
                type="button"
                onClick={() => navigateToObject('approvals')}
                className="flex-1 py-2 px-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold cursor-pointer transition-colors"
              >
                Open Approvals
              </button>
              <button
                type="button"
                onClick={() => navigateToObject('nova')}
                className="flex-1 py-2 px-3 rounded-xl bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 text-xs font-semibold cursor-pointer transition-colors"
              >
                Open Nova
              </button>
            </div>
          </section>

          {/* Compact System Health Panel */}
          <section className="bg-white rounded-2xl border border-slate-200/90 p-5 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Server className="w-4 h-4 text-slate-500" />
                <h2 className="text-sm font-bold text-slate-900">System Health</h2>
              </div>
              <span className="text-xs font-semibold text-slate-500 tabular-nums">
                {healthyNodesCount}/{distributedSystems.length} nominal
              </span>
            </div>

            <div className="divide-y divide-slate-100">
              {distributedSystems.map(node => {
                const statusColor =
                  node.status === 'HEALTHY'
                    ? 'text-emerald-700'
                    : node.status === 'PAPER_MODE'
                    ? 'text-blue-700'
                    : node.status === 'BLOCKED'
                    ? 'text-rose-700'
                    : 'text-amber-700';

                return (
                  <div
                    key={node.id}
                    className="py-2 flex items-center justify-between gap-2 text-xs"
                  >
                    <div className="min-w-0">
                      <div className="font-medium text-slate-800 truncate">{node.name}</div>
                      {node.id === 'sys-oracle' && (
                        <div className="text-[10px] text-slate-500 truncate">
                          Nova / Hermes coordination only
                        </div>
                      )}
                    </div>
                    <span className={`font-semibold shrink-0 ${statusColor}`}>
                      {node.status === 'PAPER_MODE'
                        ? 'Paper'
                        : node.status === 'HEALTHY'
                        ? 'Healthy'
                        : node.status}
                    </span>
                  </div>
                );
              })}
            </div>

            <button
              type="button"
              onClick={() => navigateToObject('systems')}
              className="w-full py-1.5 text-xs font-semibold text-blue-600 hover:bg-blue-50 rounded-lg transition-colors cursor-pointer"
            >
              View Distributed Architecture →
            </button>
          </section>

          <ResourceUsageDashboard compact />
        </div>
      </div>
    </div>
  );
};
