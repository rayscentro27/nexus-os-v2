import React, { useState, useMemo } from 'react';
import {
  Check,
  RotateCcw,
  FolderKanban,
  Target,
  Image as ImageIcon,
  Video,
  FileText,
  Globe,
  Megaphone,
  X,
} from 'lucide-react';
import { useNexus } from '../context/NexusContext';
import { CreativeAsset, CreativeAssetType } from '../data/creativeMarketingData';
import { TruthBadge } from '../components/common/TruthBadge';

export const CreativePage: React.FC = () => {
  const {
    creativeAssets,
    projects,
    campaigns,
    approvals,
    selectedAssetId,
    setSelectedAssetId,
    updateCreativeAssetStatus,
    navigateToObject,
  } = useNexus();

  const [typeFilter, setTypeFilter] = useState<'ALL' | CreativeAssetType>('ALL');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'APPROVED' | 'WAITING_RAY' | 'IN_REVISION'>('ALL');
  const [projectFilter, setProjectFilter] = useState<string>('ALL');
  const [inspectAsset, setInspectAsset] = useState<CreativeAsset | null>(null);
  const [revisionNote, setRevisionNote] = useState('');

  const counts = useMemo(() => {
    const total = creativeAssets.length;
    const approved = creativeAssets.filter(a => a.approval_state === 'APPROVED').length;
    const waiting = creativeAssets.filter(a => a.approval_state === 'WAITING_RAY').length;
    const revision = creativeAssets.filter(a => a.approval_state === 'IN_REVISION').length;
    return { total, approved, waiting, revision };
  }, [creativeAssets]);

  const filteredAssets = useMemo(() => {
    return creativeAssets.filter(a => {
      const matchType = typeFilter === 'ALL' || a.asset_type === typeFilter;
      const matchStatus = statusFilter === 'ALL' || a.approval_state === statusFilter;
      if (!matchType || !matchStatus) return false;
      if (projectFilter === 'ALL') return true;
      const proj = projects.find(p => p.id === projectFilter);
      if (!proj) return true;
      const linkedCampIds = campaigns.filter(c => c.projectId === proj.id).map(c => c.id);
      return proj.linkedAssetIds.includes(a.id) || linkedCampIds.includes(a.campaign_id);
    });
  }, [creativeAssets, typeFilter, statusFilter, projectFilter, projects, campaigns]);

  const activeAsset =
    inspectAsset || creativeAssets.find(a => a.id === selectedAssetId) || null;

  const getTypeIcon = (t: CreativeAssetType) => {
    switch (t) {
      case 'VIDEO':
        return <Video className="w-3.5 h-3.5" />;
      case 'LANDING_PAGE':
        return <Globe className="w-3.5 h-3.5" />;
      case 'AD_CREATIVE':
        return <Megaphone className="w-3.5 h-3.5" />;
      case 'PRESENTATION':
        return <FileText className="w-3.5 h-3.5" />;
      default:
        return <ImageIcon className="w-3.5 h-3.5" />;
    }
  };

  const getProjectForAsset = (asset: CreativeAsset) => {
    const camp = campaigns.find(c => c.id === asset.campaign_id);
    if (camp) return projects.find(p => p.id === camp.projectId);
    return projects.find(p => p.linkedAssetIds.includes(asset.id));
  };

  const getApprovalForAsset = (asset: CreativeAsset) =>
    approvals.find(
      ap =>
        (ap.linkedEntity?.kind === 'asset' && ap.linkedEntity.id === asset.id) ||
        (ap.linkedEntity?.kind === 'campaign' && ap.linkedEntity.id === asset.campaign_id)
    );

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Creative Asset Library
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            What Creative generated across projects and campaigns, with direct preview and approval status.
          </p>
        </div>

        <button
          type="button"
          onClick={() => navigateToObject('approvals')}
          className="px-3.5 py-2 rounded-xl bg-white border border-slate-200 hover:bg-slate-50 text-xs font-semibold text-slate-700 cursor-pointer shrink-0"
        >
          Open Approval Queue ({counts.waiting + counts.revision} awaiting review)
        </button>
      </div>

      {/* Live Summary Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
        <div className="bg-white rounded-2xl border border-slate-200/90 p-4">
          <div className="text-xs text-slate-500 font-medium">Total Library Assets</div>
          <div className="text-2xl font-bold text-slate-900 mt-1 tabular-nums">{counts.total}</div>
        </div>
        <div className="bg-white rounded-2xl border border-slate-200/90 p-4">
          <div className="text-xs text-slate-500 font-medium">Approved</div>
          <div className="text-2xl font-bold text-emerald-700 mt-1 tabular-nums">{counts.approved}</div>
        </div>
        <div className="bg-white rounded-2xl border border-slate-200/90 p-4">
          <div className="text-xs text-slate-500 font-medium">Waiting Ray</div>
          <div className="text-2xl font-bold text-amber-700 mt-1 tabular-nums">{counts.waiting}</div>
        </div>
        <div className="bg-white rounded-2xl border border-slate-200/90 p-4">
          <div className="text-xs text-slate-500 font-medium">Revision Requested</div>
          <div className="text-2xl font-bold text-slate-700 mt-1 tabular-nums">{counts.revision}</div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-2xl border border-slate-200/90 p-3.5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl flex-wrap">
          {(
            [
              { id: 'ALL', label: 'All Types' },
              { id: 'AD_CREATIVE', label: 'Ad Creatives' },
              { id: 'IMAGE', label: 'Images' },
              { id: 'SOCIAL_POST', label: 'Social Posts' },
              { id: 'VIDEO', label: 'Videos' },
              { id: 'LANDING_PAGE', label: 'Landing Pages' },
              { id: 'PRESENTATION', label: 'Decks' },
            ] as const
          ).map(tab => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setTypeFilter(tab.id)}
              className={`px-3 py-1 rounded-lg text-xs font-semibold cursor-pointer transition-colors ${
                typeFilter === tab.id
                  ? 'bg-white text-slate-900 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value as any)}
            className="px-3 py-1.5 rounded-xl border border-slate-200 bg-white text-xs font-medium text-slate-700 outline-none"
          >
            <option value="ALL">All Statuses</option>
            <option value="WAITING_RAY">Waiting Ray</option>
            <option value="IN_REVISION">In Revision</option>
            <option value="APPROVED">Approved</option>
          </select>

          <select
            value={projectFilter}
            onChange={e => setProjectFilter(e.target.value)}
            className="px-3 py-1.5 rounded-xl border border-slate-200 bg-white text-xs font-medium text-slate-700 outline-none"
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

      {/* Visual Gallery Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
        {filteredAssets.map(asset => {
          const proj = getProjectForAsset(asset);
          return (
            <div
              key={asset.id}
              onClick={() => {
                setSelectedAssetId(asset.id);
                setInspectAsset(asset);
              }}
              className="bg-white rounded-2xl border border-slate-200/90 overflow-hidden hover:border-blue-300 transition-colors cursor-pointer flex flex-col"
            >
              <div className="aspect-4/3 bg-slate-100 relative overflow-hidden">
                <img
                  src={asset.thumbnail_url}
                  alt={asset.title}
                  referrerPolicy="no-referrer"
                  className="w-full h-full object-cover"
                />
              </div>

              <div className="p-4 flex-1 flex flex-col justify-between space-y-3">
                <div>
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-500">
                      {getTypeIcon(asset.asset_type)}
                      <span>{asset.asset_type.replace('_', ' ')}</span>
                      <span>·</span>
                      <span>{asset.platform}</span>
                    </span>
                    <span
                      className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${
                        asset.approval_state === 'APPROVED'
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : asset.approval_state === 'WAITING_RAY'
                          ? 'bg-amber-50 text-amber-800 border-amber-200'
                          : 'bg-slate-100 text-slate-700 border-slate-200'
                      }`}
                    >
                      {asset.approval_state.replace('_', ' ')}
                    </span>
                  </div>

                  <h3 className="text-sm font-bold text-slate-900 leading-snug">{asset.title}</h3>
                  <div className="text-xs text-slate-500 mt-1">
                    {proj ? proj.name : asset.campaign_name} · {asset.provider}
                  </div>
                </div>

                <div className="pt-2.5 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                  <span className="font-mono">{asset.id}</span>
                  <div className="flex items-center gap-2">
                    <TruthBadge truth={asset.truth_class} />
                    <span className="font-semibold text-blue-600">Preview →</span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Asset Preview & Review Modal */}
      {inspectAsset && activeAsset && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto border border-slate-200 shadow-2xl">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between sticky top-0 bg-white z-10">
              <div>
                <div className="text-[11px] font-mono text-slate-400">
                  {activeAsset.id} · {activeAsset.asset_type} · {activeAsset.prompt_version}
                </div>
                <h2 className="text-base font-bold text-slate-900">{activeAsset.title}</h2>
              </div>
              <button
                type="button"
                onClick={() => setInspectAsset(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-5 space-y-5">
              <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
                <div className="md:col-span-6 rounded-xl overflow-hidden border border-slate-200 bg-slate-100 aspect-4/3">
                  <img
                    src={activeAsset.preview_data.full_image_url || activeAsset.thumbnail_url}
                    alt={activeAsset.title}
                    referrerPolicy="no-referrer"
                    className="w-full h-full object-cover"
                  />
                </div>

                <div className="md:col-span-6 space-y-3 text-xs">
                  <div className="flex items-center justify-between py-1.5 border-b border-slate-100">
                    <span className="text-slate-500">Status</span>
                    <span className="font-semibold text-slate-900">
                      {activeAsset.current_stage} ({activeAsset.approval_state})
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-1.5 border-b border-slate-100">
                    <span className="text-slate-500">Provider</span>
                    <span className="font-medium text-slate-800">{activeAsset.provider}</span>
                  </div>
                  <div className="flex items-center justify-between py-1.5 border-b border-slate-100">
                    <span className="text-slate-500">Created</span>
                    <span className="text-slate-700 tabular-nums">{activeAsset.created_at}</span>
                  </div>
                  <div className="flex items-center justify-between py-1.5 border-b border-slate-100">
                    <span className="text-slate-500">Truth Classification</span>
                    <TruthBadge truth={activeAsset.truth_class} />
                  </div>

                  {activeAsset.preview_data.social_caption && (
                    <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
                      <div className="font-semibold text-slate-600">Staged Caption</div>
                      <p className="text-slate-800 leading-relaxed">
                        {activeAsset.preview_data.social_caption}
                      </p>
                    </div>
                  )}

                  <div className="flex flex-wrap gap-2 pt-1">
                    {(() => {
                      const p = getProjectForAsset(activeAsset);
                      return p ? (
                        <button
                          type="button"
                          onClick={() => {
                            setInspectAsset(null);
                            navigateToObject('projects', p.id, 'project');
                          }}
                          className="px-2.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold flex items-center gap-1 cursor-pointer"
                        >
                          <FolderKanban className="w-3.5 h-3.5" />
                          <span>{p.name}</span>
                        </button>
                      ) : null;
                    })()}
                    <button
                      type="button"
                      onClick={() => {
                        setInspectAsset(null);
                        navigateToObject('campaigns', activeAsset.campaign_id, 'campaign');
                      }}
                      className="px-2.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold flex items-center gap-1 cursor-pointer"
                    >
                      <Target className="w-3.5 h-3.5" />
                      <span>{activeAsset.campaign_name}</span>
                    </button>
                  </div>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 text-xs space-y-1">
                <div className="font-semibold text-slate-600">Creative Prompt ({activeAsset.prompt_id})</div>
                <p className="text-slate-700 whitespace-pre-line font-mono text-[11px]">
                  {activeAsset.exact_approved_creative_prompt}
                </p>
              </div>

              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-slate-100">
                <div className="flex items-center gap-2 flex-1">
                  <input
                    type="text"
                    value={revisionNote}
                    onChange={e => setRevisionNote(e.target.value)}
                    placeholder="Optional revision note..."
                    className="flex-1 px-3 py-1.5 rounded-xl border border-slate-200 text-xs outline-none focus:border-blue-500"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      updateCreativeAssetStatus(
                        activeAsset.id,
                        'IN_REVISION',
                        revisionNote || 'Revision requested from Creative Library.'
                      );
                      setRevisionNote('');
                      setInspectAsset(null);
                    }}
                    className="px-3 py-1.5 rounded-xl border border-slate-300 hover:bg-amber-50 text-xs font-semibold text-slate-700 flex items-center gap-1 cursor-pointer"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Request Revision</span>
                  </button>
                </div>

                <div className="flex items-center gap-2">
                  {(() => {
                    const ap = getApprovalForAsset(activeAsset);
                    return ap ? (
                      <button
                        type="button"
                        onClick={() => {
                          setInspectAsset(null);
                          navigateToObject('approvals', ap.id, 'approval');
                        }}
                        className="px-3 py-1.5 rounded-xl border border-slate-200 hover:bg-slate-50 text-xs font-semibold text-slate-700 cursor-pointer"
                      >
                        Open Approval
                      </button>
                    ) : null;
                  })()}
                  {activeAsset.approval_state !== 'APPROVED' && (
                    <button
                      type="button"
                      onClick={() => {
                        updateCreativeAssetStatus(activeAsset.id, 'APPROVED', 'Approved in Creative Library.');
                        setInspectAsset(null);
                      }}
                      className="px-4 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold flex items-center gap-1 cursor-pointer"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>Approve Asset</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
