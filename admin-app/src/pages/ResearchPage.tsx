import React, { useState } from 'react';
import {
  Database,
  ArrowRight,
  Youtube,
  Search,
  Github,
  CheckCircle2,
  Zap,
  AlertTriangle,
  Clock,
  Layers,
  FileText,
  RotateCw,
  Globe,
  TrendingUp,
  ChevronRight,
  XCircle,
  Sparkles,
  Compass,
  FolderKanban,
  ArrowUpRight,
  Bot,
  ListFilter
} from 'lucide-react';
import { useNexus } from '../context/NexusContext';
import { TruthBadge } from '../components/common/TruthBadge';
import { UnavailableState } from '../components/live/UnavailableState';
import { NexusDepartmentName } from '../types';
import ResearchRoomWorkspace from '../../../src/components/ResearchRoomWorkspace';

type ResearchTab = 'findings' | 'diagnostics' | 'rooms';

export const ResearchPage: React.FC = () => {
  const {
    researchFindings,
    promoteResearchFinding,
    navigateToObject,
    sendMessage,
    setIsNovaDrawerOpen,
  } = useNexus();

  const [activeTab, setActiveTab] = useState<ResearchTab>('findings');
  const [findingSearch, setFindingSearch] = useState('');
  const [deptFilter, setDeptFilter] = useState<'ALL' | NexusDepartmentName>('ALL');
  const [selectedFindingId, setSelectedFindingId] = useState<string>(
    researchFindings[0]?.id || ''
  );

  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // Filtered Findings from Authoritative State
  const filteredFindings = researchFindings.filter(f => {
    const matchesSearch =
      !findingSearch.trim() ||
      f.title.toLowerCase().includes(findingSearch.toLowerCase()) ||
      f.source.toLowerCase().includes(findingSearch.toLowerCase()) ||
      f.recommendation.toLowerCase().includes(findingSearch.toLowerCase()) ||
      (f.linkedProjectName || '').toLowerCase().includes(findingSearch.toLowerCase());

    const matchesDept = deptFilter === 'ALL' || f.departmentDestination === deptFilter;
    return matchesSearch && matchesDept;
  });

  const activeFinding =
    filteredFindings.find(f => f.id === selectedFindingId) ||
    filteredFindings[0] ||
    researchFindings[0];

  const verifiedCount = researchFindings.filter(f => f.truthClass === 'VERIFIED').length;
  const promotedCount = researchFindings.filter(f => f.promotedToProject).length;
  const readyToPromoteCount = researchFindings.filter(f => !f.promotedToProject).length;

  const handlePromoteFinding = (findingId: string, title: string) => {
    promoteResearchFinding(findingId);
    showToast(`Promoted "${title}" to an active Nexus project.`);
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

      {/* Header + Page Question */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Compass className="w-4 h-4 text-blue-600" />
            <h1 className="text-lg font-semibold text-slate-900 tracking-tight">
              Research &amp; Recommendations
            </h1>
            <TruthBadge truth="VERIFIED" label="Findings Registry" />
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            What has Research discovered, how strong is the evidence, and what happens next?
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="inline-flex p-0.5 rounded-lg bg-slate-100 border border-slate-200">
            <button
              type="button"
              onClick={() => setActiveTab('findings')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer ${
                activeTab === 'findings'
                  ? 'bg-white text-slate-900 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Findings &amp; Recommendations ({researchFindings.length})
            </button>
            <button
              type="button"
              disabled
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer ${
                'text-slate-400 cursor-not-allowed'
              }`}
              title="Research ingestion diagnostics are not connected to a live API."
            >
              Ingestion &amp; Queue Diagnostics (not connected)
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('rooms')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer ${
                activeTab === 'rooms'
                  ? 'bg-white text-slate-900 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Research Rooms
            </button>
          </div>

          <button
            type="button"
            onClick={() => {
              sendMessage('Summarize active research findings and what should be promoted next.');
              setIsNovaDrawerOpen(true);
            }}
            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 inline-flex items-center gap-1.5 cursor-pointer transition-colors"
          >
            <Bot className="w-3.5 h-3.5" />
            Ask Nova
          </button>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: FINDINGS & RECOMMENDATIONS (PRIMARY EXECUTIVE QUESTION)            */}
      {/* ========================================================================= */}
      {activeTab === 'findings' && (
        <div className="space-y-4">
          {/* Compact 4-Card Summary */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="bg-white rounded-xl border border-slate-200/80 p-3.5 shadow-2xs">
              <div className="text-[11px] font-medium text-slate-500">Tracked Findings</div>
              <div className="text-xl font-semibold text-slate-900 mt-1 tabular-nums">
                {researchFindings.length}
              </div>
              <div className="text-[11px] text-slate-500 mt-0.5">
                Structured deliverables across departments
              </div>
            </div>
            <div className="bg-white rounded-xl border border-slate-200/80 p-3.5 shadow-2xs">
              <div className="text-[11px] font-medium text-slate-500">Evidence-Verified</div>
              <div className="text-xl font-semibold text-emerald-700 mt-1 tabular-nums">
                {verifiedCount}
              </div>
              <div className="text-[11px] text-slate-500 mt-0.5">
                Backed by API readback or deterministic backtest
              </div>
            </div>
            <div className="bg-white rounded-xl border border-slate-200/80 p-3.5 shadow-2xs">
              <div className="text-[11px] font-medium text-slate-500">Active Projects Linked</div>
              <div className="text-xl font-semibold text-blue-700 mt-1 tabular-nums">
                {promotedCount}
              </div>
              <div className="text-[11px] text-slate-500 mt-0.5">
                Handed off into durable Nexus workflows
              </div>
            </div>
            <div className="bg-white rounded-xl border border-slate-200/80 p-3.5 shadow-2xs">
              <div className="text-[11px] font-medium text-slate-500">Ready to Promote</div>
              <div className="text-xl font-semibold text-amber-700 mt-1 tabular-nums">
                {readyToPromoteCount}
              </div>
              <div className="text-[11px] text-slate-500 mt-0.5">
                Awaiting decision or project creation
              </div>
            </div>
          </div>

          {/* Search & Department Filter */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-3 flex flex-wrap items-center justify-between gap-2.5 shadow-2xs">
            <div className="relative flex-1 min-w-[220px]">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={findingSearch}
                onChange={e => setFindingSearch(e.target.value)}
                placeholder="Search findings, sources, recommendations, or linked projects..."
                className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-hidden focus:border-blue-500 focus:bg-white"
              />
            </div>

            <div className="flex items-center gap-1 flex-wrap">
              {(['ALL', 'Marketing', 'Commerce', 'Trading', 'Finance', 'Systems'] as const).map(
                dept => (
                  <button
                    key={dept}
                    type="button"
                    onClick={() => setDeptFilter(dept)}
                    className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                      deptFilter === dept
                        ? 'bg-blue-600 text-white'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {dept === 'ALL' ? 'All Destinations' : dept}
                  </button>
                )
              )}
            </div>
          </div>

          {/* Master-Detail Split for Findings */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            {/* Left List */}
            <div className="lg:col-span-7 space-y-2.5">
              {filteredFindings.length === 0 ? (
                <div className="bg-white rounded-xl border border-slate-200/80 p-8 text-center">
                  <ListFilter className="w-6 h-6 text-slate-300 mx-auto mb-2" />
                  <p className="text-sm font-medium text-slate-700">No matching findings</p>
                  <p className="text-xs text-slate-500 mt-1">
                    Reset filters to inspect all Research discoveries.
                  </p>
                </div>
              ) : (
                filteredFindings.map(finding => {
                  const isSelected = activeFinding?.id === finding.id;
                  return (
                    <div
                      key={finding.id}
                      onClick={() => setSelectedFindingId(finding.id)}
                      className={`bg-white rounded-xl border p-4 cursor-pointer transition-all shadow-2xs ${
                        isSelected
                          ? 'border-blue-500 ring-1 ring-blue-500/20 bg-blue-50/20'
                          : 'border-slate-200/80 hover:border-slate-300'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <TruthBadge truth={finding.truthClass} />
                          <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                            {finding.sourceType}
                          </span>
                          <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-100">
                            → {finding.departmentDestination}
                          </span>
                        </div>
                        <span className="text-[11px] text-slate-400 shrink-0">
                          {finding.discoveredAt}
                        </span>
                      </div>

                      <h3 className="text-sm font-semibold text-slate-900 mt-2 leading-snug">
                        {finding.title}
                      </h3>
                      <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                        {finding.recommendation}
                      </p>

                      <div className="mt-3 pt-2.5 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-[11px]">
                        <div className="flex items-center gap-3 text-slate-500">
                          <span>
                            Source: <strong className="text-slate-700">{finding.source}</strong>
                          </span>
                          <span>
                            Evidence:{' '}
                            <strong className="text-slate-700">{finding.evidenceQuality}</strong>
                          </span>
                          <span>
                            Confidence:{' '}
                            <strong className="text-slate-700">{finding.confidence}</strong>
                          </span>
                        </div>

                        {finding.linkedProjectId ? (
                          <button
                            type="button"
                            onClick={e => {
                              e.stopPropagation();
                              navigateToObject('projects', finding.linkedProjectId, 'project');
                            }}
                            className="inline-flex items-center gap-1 font-medium text-blue-600 hover:text-blue-700 cursor-pointer"
                          >
                            <FolderKanban className="w-3.5 h-3.5" />
                            {finding.linkedProjectName || 'Open Project'}
                            <ArrowUpRight className="w-3 h-3" />
                          </button>
                        ) : (
                          <button
                            type="button"
                            onClick={e => {
                              e.stopPropagation();
                              handlePromoteFinding(finding.id, finding.title);
                            }}
                            className="px-2.5 py-1 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium inline-flex items-center gap-1 cursor-pointer"
                          >
                            Promote to Project
                            <ArrowRight className="w-3 h-3" />
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Right Detail Inspector */}
            <div className="lg:col-span-5">
              {activeFinding && (
                <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs sticky top-4 space-y-4">
                  <div className="pb-3 border-b border-slate-100">
                    <div className="flex items-center justify-between gap-2">
                      <TruthBadge truth={activeFinding.truthClass} size="sm" />
                      <span className="text-xs text-slate-400">{activeFinding.id}</span>
                    </div>
                    <h2 className="text-base font-semibold text-slate-900 mt-2">
                      {activeFinding.title}
                    </h2>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Discovered {activeFinding.discoveredAt} · {activeFinding.source}
                    </p>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                      <div className="text-[10px] text-slate-400 uppercase font-medium">
                        Evidence
                      </div>
                      <div className="font-semibold text-slate-900 mt-0.5">
                        {activeFinding.evidenceQuality}
                      </div>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                      <div className="text-[10px] text-slate-400 uppercase font-medium">
                        Confidence
                      </div>
                      <div className="font-semibold text-slate-900 mt-0.5">
                        {activeFinding.confidence}
                      </div>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                      <div className="text-[10px] text-slate-400 uppercase font-medium">
                        Destination
                      </div>
                      <div className="font-semibold text-blue-700 mt-0.5">
                        {activeFinding.departmentDestination}
                      </div>
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                      Research Recommendation
                    </div>
                    <p className="text-xs text-slate-700 bg-slate-50 border border-slate-100 rounded-lg p-3 leading-relaxed">
                      {activeFinding.recommendation}
                    </p>
                  </div>

                  <div className="space-y-1.5">
                    <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                      What Happens Next
                    </div>
                    <p className="text-xs text-slate-800 bg-blue-50/60 border border-blue-100 rounded-lg p-3 leading-relaxed">
                      {activeFinding.whatHappensNext}
                    </p>
                  </div>

                  <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center gap-2">
                    {activeFinding.linkedProjectId ? (
                      <button
                        type="button"
                        onClick={() =>
                          navigateToObject('projects', activeFinding.linkedProjectId, 'project')
                        }
                        className="flex-1 py-2 px-3 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium inline-flex items-center justify-center gap-1.5 cursor-pointer"
                      >
                        <FolderKanban className="w-3.5 h-3.5" />
                        Open Linked Project
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={() =>
                          handlePromoteFinding(activeFinding.id, activeFinding.title)
                        }
                        className="flex-1 py-2 px-3 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium inline-flex items-center justify-center gap-1.5 cursor-pointer"
                      >
                        <Sparkles className="w-3.5 h-3.5" />
                        Promote to Project
                      </button>
                    )}

                    <button
                      type="button"
                      onClick={() => {
                        sendMessage(`Explain evidence behind research finding: ${activeFinding.title}`);
                        setIsNovaDrawerOpen(true);
                      }}
                      className="py-2 px-3 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium cursor-pointer"
                    >
                      Ask Nova
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {activeTab === 'diagnostics' && (
        <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs">
          <UnavailableState>Research diagnostics are not connected to a live source.</UnavailableState>
        </div>
      )}

      {activeTab === 'rooms' && <ResearchRoomWorkspace />}
    </div>
  );
};
