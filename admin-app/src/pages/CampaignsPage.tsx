import React, { useMemo } from 'react';
import {
  Target,
  FolderKanban,
  ExternalLink,
  AlertTriangle,
  Link2,
  CheckCircle2,
} from 'lucide-react';
import { useNexus } from '../context/NexusContext';
import { TruthBadge } from '../components/common/TruthBadge';
import { UnavailableState } from '../components/live/UnavailableState';

export const CampaignsPage: React.FC = () => {
  const {
    campaigns,
    creativeAssets,
    selectedCampaignId,
    setSelectedCampaignId,
    navigateToObject,
  } = useNexus();

  const activeCampaign = useMemo(
    () => campaigns.find(c => c.id === selectedCampaignId) || campaigns[0],
    [campaigns, selectedCampaignId]
  );

  const linkedAssets = useMemo(() => {
    if (!activeCampaign) return [];
    const setIds = new Set(activeCampaign.linkedAssetIds);
    return creativeAssets.filter(a => setIds.has(a.id) || a.campaign_id === activeCampaign.id);
  }, [activeCampaign, creativeAssets]);

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Campaigns
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            First-class campaign records showing hooks, copy, UTM links, Creative assets, approval gates, and publication state.
          </p>
        </div>

        <button
          type="button"
          onClick={() => navigateToObject('marketing')}
          className="px-3.5 py-2 rounded-xl bg-white border border-slate-200 hover:bg-slate-50 text-xs font-semibold text-slate-700 cursor-pointer shrink-0"
        >
          Marketing Schedule &amp; Audience →
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Campaign List (4 cols) */}
        <div className="lg:col-span-4 bg-white rounded-2xl border border-slate-200/90 overflow-hidden divide-y divide-slate-100">
          {campaigns.map(c => {
            const isSelected = activeCampaign?.id === c.id;
            return (
              <button
                key={c.id}
                type="button"
                onClick={() => setSelectedCampaignId(c.id)}
                className={`w-full text-left p-4 transition-colors cursor-pointer ${
                  isSelected ? 'bg-blue-50/70' : 'hover:bg-slate-50'
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="text-[11px] font-mono text-slate-400">{c.id}</span>
                  <TruthBadge truth={c.truthClass} />
                </div>
                <div className="text-sm font-bold text-slate-900">{c.name}</div>
                <div className="text-xs text-slate-500 mt-1">{c.projectName}</div>
                <div className="mt-2 flex items-center justify-between text-[11px]">
                  <span className="font-medium text-slate-700">{c.approvalStatus.replace(/_/g, ' ')}</span>
                  <span className="text-slate-400">{c.publicationStatus}</span>
                </div>
              </button>
            );
          })}
          {campaigns.length === 0 && <div className="p-4"><UnavailableState>Campaign records are not connected to the live Nexus read model.</UnavailableState></div>}
        </div>

        {/* Campaign Detail Panel (8 cols) */}
        {activeCampaign ? (
          <div className="lg:col-span-8 bg-white rounded-2xl border border-slate-200/90 p-5 sm:p-6 space-y-5">
            <div className="pb-4 border-b border-slate-100 space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <Target className="w-4 h-4 text-blue-600" />
                  <h2 className="text-lg font-bold text-slate-900">{activeCampaign.name}</h2>
                  <TruthBadge truth={activeCampaign.truthClass} />
                </div>
                <button
                  type="button"
                  onClick={() => navigateToObject('projects', activeCampaign.projectId, 'project')}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-600 hover:underline cursor-pointer"
                >
                  <FolderKanban className="w-3.5 h-3.5" />
                  <span>{activeCampaign.projectName}</span>
                </button>
              </div>

              <div className="text-xs text-slate-500">
                {activeCampaign.stageLabel} · Budget: <strong className="text-slate-800">{activeCampaign.estimatedBudget}</strong>
              </div>
              <p className="text-xs text-slate-700 leading-relaxed">{activeCampaign.objective}</p>
            </div>

            {/* State Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
                <div className="text-slate-500">Approval Status</div>
                <div className="font-bold text-slate-900 mt-1">
                  {activeCampaign.approvalStatus.replace(/_/g, ' ')}
                </div>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
                <div className="text-slate-500">Publication</div>
                <div className="font-bold text-slate-900 mt-1">{activeCampaign.publicationStatus}</div>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
                <div className="text-slate-500">Measurement</div>
                <div className="font-bold text-slate-900 mt-1">
                  {activeCampaign.measurementStatus.replace(/_/g, ' ')}
                </div>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
                <div className="text-slate-500">Channels</div>
                <div className="font-bold text-slate-900 mt-1">{activeCampaign.channels.join(', ')}</div>
              </div>
            </div>

            {activeCampaign.channelConnectionState === 'NOT_CONNECTED' && (
              <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-950 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                  <span>
                    Facebook direct API is <strong>NOT_CONNECTED</strong>. Stage A routes via Postiz once publication approval is signed off.
                  </span>
                </div>
                {activeCampaign.approvalId && (
                  <button
                    type="button"
                    onClick={() => navigateToObject('approvals', activeCampaign.approvalId, 'approval')}
                    className="px-3 py-1.5 rounded-lg bg-slate-900 text-white font-semibold shrink-0 cursor-pointer"
                  >
                    Review Approval
                  </button>
                )}
              </div>
            )}

            {/* Hooks & Primary Copy */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-2">
                <div className="font-bold text-slate-800">Hooks &amp; Variants ({activeCampaign.variant})</div>
                <ul className="space-y-1.5 text-slate-700">
                  {activeCampaign.hooks.map((h, i) => (
                    <li key={i} className="flex items-start gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-blue-600 shrink-0 mt-0.5" />
                      <span>{h}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-2">
                <div className="font-bold text-slate-800">Primary Campaign Copy</div>
                <p className="text-slate-700 leading-relaxed">{activeCampaign.primaryCopy}</p>
                <div className="pt-2 border-t border-slate-200/70 text-[11px] text-slate-500">
                  <strong>Results:</strong> {activeCampaign.resultsSummary}
                </div>
              </div>
            </div>

            {/* Tracked URLs & UTMs */}
            <div className="space-y-2">
              <h3 className="text-xs font-bold text-slate-800">Tracked URLs &amp; UTMs</h3>
              <div className="divide-y divide-slate-100 rounded-xl border border-slate-200">
                {activeCampaign.trackedUrls.map((u, idx) => (
                  <div
                    key={idx}
                    className="px-4 py-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <Link2 className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      <span className="font-semibold text-slate-800">{u.label}</span>
                    </div>
                    <span className="font-mono text-[11px] text-slate-500 truncate">{u.url}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Linked Creative Assets */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-slate-800">
                  Linked Creative Assets ({linkedAssets.length})
                </h3>
                <button
                  type="button"
                  onClick={() => navigateToObject('creative')}
                  className="text-xs font-semibold text-blue-600 hover:underline flex items-center gap-1 cursor-pointer"
                >
                  <span>Open Creative Library</span>
                  <ExternalLink className="w-3 h-3" />
                </button>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {linkedAssets.map(ast => (
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
                    <div className="p-2.5 text-xs">
                      <div className="font-semibold text-slate-900 truncate">{ast.title}</div>
                      <div className="text-[11px] text-slate-500 mt-0.5">{ast.approval_state}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : <div className="lg:col-span-8"><UnavailableState>No live campaign record is available.</UnavailableState></div>}
      </div>
    </div>
  );
};
