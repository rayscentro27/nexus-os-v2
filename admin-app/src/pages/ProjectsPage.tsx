import React, { useState, useMemo } from 'react';
import {
  FolderKanban,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ArrowRight,
  Plus,
  ExternalLink,
} from 'lucide-react';
import { useNexus } from '../context/NexusContext';
import { TruthBadge } from '../components/common/TruthBadge';

export const ProjectsPage: React.FC = () => {
  const {
    projects,
    selectedProjectId,
    setSelectedProjectId,
    nexus_get_project_approvals,
    campaigns,
    creativeAssets,
    commerceOffers,
    navigateToObject,
    setIsNewProjectModalOpen,
  } = useNexus();

  const [detailTab, setDetailTab] = useState<
    'workflow' | 'approvals' | 'creative' | 'campaigns' | 'commerce' | 'activity'
  >('workflow');

  const activeProject = useMemo(
    () => projects.find(p => p.id === selectedProjectId) || projects[0],
    [projects, selectedProjectId]
  );

  const projectApprovals = useMemo(
    () => (activeProject ? nexus_get_project_approvals(activeProject.id) : []),
    [activeProject, nexus_get_project_approvals]
  );

  const projectCampaigns = useMemo(
    () => (activeProject ? campaigns.filter(c => c.projectId === activeProject.id) : []),
    [activeProject, campaigns]
  );

  const projectAssets = useMemo(() => {
    if (!activeProject) return [];
    const linkedIds = new Set(activeProject.linkedAssetIds);
    const campaignIds = new Set(projectCampaigns.map(c => c.id));
    return creativeAssets.filter(a => linkedIds.has(a.id) || campaignIds.has(a.campaign_id));
  }, [activeProject, creativeAssets, projectCampaigns]);

  const projectOffer = useMemo(
    () =>
      activeProject
        ? commerceOffers.find(o => o.projectId === activeProject.id || o.id === activeProject.linkedOfferId)
        : undefined,
    [activeProject, commerceOffers]
  );

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Projects
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            First-class durable projects running across Research, Marketing, Creative, Commerce, and Distribution.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setIsNewProjectModalOpen(true)}
          className="px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold flex items-center gap-1.5 cursor-pointer shrink-0 transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>New Project</span>
        </button>
      </div>

      {/* Main Layout: Project List (Left) + Project Workspace (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Left Project Selector (4 cols) */}
        <div className="lg:col-span-4 bg-white rounded-2xl border border-slate-200/90 overflow-hidden divide-y divide-slate-100">
          {projects.map(p => {
            const isSelected = activeProject?.id === p.id;
            const pendingCount = nexus_get_project_approvals(p.id).filter(
              a => a.status === 'PENDING'
            ).length;

            return (
              <button
                key={p.id}
                type="button"
                onClick={() => {
                  setSelectedProjectId(p.id);
                  setDetailTab('workflow');
                }}
                className={`w-full text-left p-4 transition-colors cursor-pointer ${
                  isSelected ? 'bg-blue-50/70' : 'hover:bg-slate-50'
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="text-[11px] font-mono text-slate-400 truncate">{p.id}</span>
                  <span
                    className={`text-[10px] font-semibold px-2 py-0.5 rounded border shrink-0 ${
                      p.status === 'ACTIVE'
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : p.status === 'BLOCKED'
                        ? 'bg-rose-50 text-rose-700 border-rose-200'
                        : 'bg-amber-50 text-amber-800 border-amber-200'
                    }`}
                  >
                    {p.status}
                  </span>
                </div>

                <div className="text-sm font-bold text-slate-900">{p.name}</div>
                <div className="text-xs text-slate-500 mt-1 flex items-center justify-between gap-2">
                  <span>
                    {p.currentDepartment} · {p.stage}
                  </span>
                  {pendingCount > 0 && (
                    <span className="text-[11px] font-semibold text-amber-700 shrink-0 tabular-nums">
                      {pendingCount} approval{pendingCount > 1 ? 's' : ''}
                    </span>
                  )}
                </div>
              </button>
            );
          })}
        </div>

        {/* Right Project Detail (8 cols) */}
        {activeProject && (
          <div className="lg:col-span-8 bg-white rounded-2xl border border-slate-200/90 p-5 sm:p-6 space-y-5">
            {/* Project Identity & Next Action */}
            <div className="pb-4 border-b border-slate-100 space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <FolderKanban className="w-4 h-4 text-blue-600" />
                  <h2 className="text-lg font-bold text-slate-900">{activeProject.name}</h2>
                  <TruthBadge truth={activeProject.truthClass} />
                </div>
                <span className="text-xs font-mono text-slate-500">{activeProject.id}</span>
              </div>

              {(activeProject.ventureId || activeProject.opportunityId) && (
                <div className="text-[11px] font-mono text-slate-500 flex flex-wrap items-center gap-3">
                  {activeProject.ventureId && <span>VENTURE_ID: {activeProject.ventureId}</span>}
                  {activeProject.opportunityId && (
                    <span>OPPORTUNITY_ID: {activeProject.opportunityId}</span>
                  )}
                </div>
              )}

              <p className="text-xs text-slate-600 leading-relaxed">{activeProject.summary}</p>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 text-xs">
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
                  <div className="text-[11px] text-slate-500 font-medium">Current Department &amp; Stage</div>
                  <div className="font-semibold text-slate-900 mt-0.5">
                    {activeProject.currentDepartment} ·{' '}
                    <span className="font-mono text-[11px]">{activeProject.stage}</span>
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-blue-50/70 border border-blue-200/80 sm:col-span-2">
                  <div className="text-[11px] text-blue-700 font-medium">Next Action</div>
                  <div className="font-semibold text-blue-950 mt-0.5 flex items-center gap-1.5">
                    <ArrowRight className="w-3.5 h-3.5 shrink-0" />
                    <span>{activeProject.nextAction}</span>
                  </div>
                </div>
              </div>

              {activeProject.blocker && (
                <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-900 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
                  <span>
                    <strong>Active Blocker (gated action paused only):</strong> {activeProject.blocker}
                  </span>
                </div>
              )}
            </div>

            {/* Detail Sub-tabs */}
            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl overflow-x-auto">
              {(
                [
                  { id: 'workflow', label: 'Workflow & Evidence' },
                  { id: 'approvals', label: `Approvals (${projectApprovals.length})` },
                  { id: 'creative', label: `Creative (${projectAssets.length})` },
                  { id: 'campaigns', label: `Campaigns (${projectCampaigns.length})` },
                  { id: 'commerce', label: 'Commerce' },
                  { id: 'activity', label: `Activity (${activeProject.activityLog.length})` },
                ] as const
              ).map(t => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setDetailTab(t.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap cursor-pointer transition-colors ${
                    detailTab === t.id
                      ? 'bg-white text-slate-900 shadow-2xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {/* Tab Panels */}
            {detailTab === 'workflow' && (
              <div className="space-y-5">
                {/* 9-Step Nexus Workflow */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                  {activeProject.workflowSteps.map((step, i) => {
                    const tone =
                      step.status === 'COMPLETE'
                        ? 'bg-emerald-50/70 border-emerald-200 text-emerald-950'
                        : step.status === 'WAITING_APPROVAL'
                        ? 'bg-amber-50 border-amber-300 text-amber-950'
                        : step.status === 'ACTIVE'
                        ? 'bg-blue-50 border-blue-300 text-blue-950'
                        : step.status === 'BLOCKED'
                        ? 'bg-rose-50 border-rose-200 text-rose-950'
                        : 'bg-slate-50 border-slate-200 text-slate-600';

                    return (
                      <div key={step.stage} className={`p-3 rounded-xl border text-xs space-y-1 ${tone}`}>
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-bold">
                            {i + 1}. {step.stage}
                          </span>
                          {step.status === 'COMPLETE' ? (
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                          ) : (
                            <Clock className="w-3.5 h-3.5 shrink-0 opacity-70" />
                          )}
                        </div>
                        <div className="text-[11px] opacity-80">{step.status.replace(/_/g, ' ')}</div>
                        <p className="text-[11px] leading-snug opacity-90">{step.summary}</p>
                      </div>
                    );
                  })}
                </div>

                {/* Project Evidence */}
                {activeProject.evidence.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="text-xs font-bold text-slate-800">Verified &amp; Staged Evidence</h3>
                    <div className="divide-y divide-slate-100 rounded-xl border border-slate-200">
                      {activeProject.evidence.map(ev => (
                        <div
                          key={ev.id}
                          className="px-4 py-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs"
                        >
                          <div>
                            <div className="font-semibold text-slate-800">{ev.label}</div>
                            <div className="text-[11px] text-slate-500">Source: {ev.source}</div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-slate-900 tabular-nums">{ev.value}</span>
                            <TruthBadge truth={ev.truthClass} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {detailTab === 'approvals' && (
              <div className="divide-y divide-slate-100 rounded-xl border border-slate-200">
                {projectApprovals.length === 0 ? (
                  <div className="p-6 text-center text-xs text-slate-500">No approvals linked to this project.</div>
                ) : (
                  projectApprovals.map(a => (
                    <div
                      key={a.id}
                      className="p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                    >
                      <div>
                        <div className="font-semibold text-slate-900">{a.title}</div>
                        <div className="text-slate-500 mt-0.5">
                          {a.type} · {a.status} · {a.blockedAction}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => navigateToObject('approvals', a.id, 'approval')}
                        className="px-3 py-1.5 rounded-lg bg-slate-900 text-white font-semibold cursor-pointer shrink-0"
                      >
                        Inspect Approval
                      </button>
                    </div>
                  ))
                )}
              </div>
            )}

            {detailTab === 'creative' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {projectAssets.length === 0 ? (
                  <div className="col-span-2 p-6 text-center text-xs text-slate-500 border border-dashed border-slate-200 rounded-xl">
                    No Creative assets attached to this project.
                  </div>
                ) : (
                  projectAssets.map(ast => (
                    <div
                      key={ast.id}
                      onClick={() => navigateToObject('creative', ast.id, 'asset')}
                      className="rounded-xl border border-slate-200 overflow-hidden hover:border-blue-300 cursor-pointer transition-colors"
                    >
                      <div className="aspect-4/3 bg-slate-100 overflow-hidden">
                        <img
                          src={ast.thumbnail_url}
                          alt={ast.title}
                          referrerPolicy="no-referrer"
                          className="w-full h-full object-cover"
                        />
                      </div>
                      <div className="p-3 text-xs space-y-1">
                        <div className="font-semibold text-slate-900 truncate">{ast.title}</div>
                        <div className="flex items-center justify-between text-slate-500">
                          <span>{ast.asset_type}</span>
                          <span>{ast.approval_state}</span>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {detailTab === 'campaigns' && (
              <div className="space-y-3">
                {projectCampaigns.length === 0 ? (
                  <div className="p-6 text-center text-xs text-slate-500 border border-dashed border-slate-200 rounded-xl">
                    No campaigns attached to this project.
                  </div>
                ) : (
                  projectCampaigns.map(cmp => (
                    <div
                      key={cmp.id}
                      className="p-4 rounded-xl border border-slate-200 space-y-2 text-xs"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-bold text-slate-900 text-sm">{cmp.name}</span>
                        <TruthBadge truth={cmp.truthClass} />
                      </div>
                      <p className="text-slate-600">{cmp.objective}</p>
                      <div className="flex items-center justify-between pt-1">
                        <span className="text-slate-500">
                          Approval: <strong>{cmp.approvalStatus}</strong> · Publication:{' '}
                          <strong>{cmp.publicationStatus}</strong>
                        </span>
                        <button
                          type="button"
                          onClick={() => navigateToObject('campaigns', cmp.id, 'campaign')}
                          className="text-blue-600 font-semibold hover:underline flex items-center gap-1 cursor-pointer"
                        >
                          <span>Campaign Detail</span>
                          <ExternalLink className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {detailTab === 'commerce' && (
              <div>
                {!projectOffer ? (
                  <div className="p-6 text-center text-xs text-slate-500 border border-dashed border-slate-200 rounded-xl">
                    No Commerce SKU linked to this project.
                  </div>
                ) : (
                  <div className="p-4 rounded-xl border border-slate-200 space-y-3 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <div>
                        <div className="font-bold text-sm text-slate-900">{projectOffer.title}</div>
                        <div className="text-slate-500 font-mono">
                          Printify {projectOffer.externalProductId} · Variant {projectOffer.variantId}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => navigateToObject('business-hub', projectOffer.id, 'offer')}
                        className="px-3 py-1.5 rounded-lg bg-slate-900 text-white font-semibold cursor-pointer"
                      >
                        Open Commerce Truth
                      </button>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1">
                      <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                        <div className="text-slate-500">Base Cost</div>
                        <div className="font-bold text-slate-900 tabular-nums mt-0.5">
                          ${projectOffer.productTruth.baseCost.toFixed(2)}{' '}
                          <TruthBadge truth="VERIFIED" />
                        </div>
                      </div>
                      <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                        <div className="text-slate-500">US Shipping</div>
                        <div className="font-bold text-slate-900 tabular-nums mt-0.5">
                          ${projectOffer.productTruth.firstItemShipping.toFixed(2)}{' '}
                          <TruthBadge truth="VERIFIED" />
                        </div>
                      </div>
                      <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                        <div className="text-slate-500">Retail Price</div>
                        <div className="font-bold text-slate-900 tabular-nums mt-0.5">
                          ${projectOffer.productTruth.stagedPrice.toFixed(2)}{' '}
                          <TruthBadge truth="PROPOSED" />
                        </div>
                      </div>
                      <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200">
                        <div className="text-rose-700">Live Checkout</div>
                        <div className="font-bold text-rose-900 mt-0.5">
                          {projectOffer.liveSales.checkoutStatus}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {detailTab === 'activity' && (
              <div className="divide-y divide-slate-100 rounded-xl border border-slate-200">
                {activeProject.activityLog.map(act => (
                  <div
                    key={act.id}
                    className="px-4 py-3 flex items-center justify-between gap-3 text-xs"
                  >
                    <div>
                      <div className="text-slate-800">{act.event}</div>
                      <div className="text-[11px] text-slate-500 mt-0.5">
                        {act.department} · {act.timestamp}
                      </div>
                    </div>
                    <TruthBadge truth={act.truthClass} />
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
