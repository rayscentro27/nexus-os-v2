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
import {
  ResearchQueueItem,
  MechanicalIngestionStatus,
  WorkOrigin,
  ResearchSourceType,
  DiscoveryHeartbeatStatus,
  INITIAL_RESEARCH_QUEUE,
  INITIAL_DISCOVERY_HEARTBEAT
} from '../data/researchQueueData';
import {
  INITIAL_RESEARCH_FEEDERS,
  RAY_NOVA_OPPORTUNITY_INTAKE
} from '../data/businessHubData';
import { useNexus } from '../context/NexusContext';
import { TruthBadge } from '../components/common/TruthBadge';
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

  // Secondary Diagnostics State (Preserved FIFO Queue & Heartbeat)
  const [researchQueue, setResearchQueue] = useState<ResearchQueueItem[]>(INITIAL_RESEARCH_QUEUE);
  const [discoveryHeartbeat, setDiscoveryHeartbeat] = useState<DiscoveryHeartbeatStatus>(
    INITIAL_DISCOVERY_HEARTBEAT
  );
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<
    | 'All'
    | 'Queued'
    | 'Processing'
    | 'Ingested'
    | 'Failed Retryable'
    | 'Failed Final'
    | 'YouTube'
    | 'TradingView'
  >('All');
  const [selectedItemId, setSelectedItemId] = useState<string>(INITIAL_RESEARCH_QUEUE[0].id);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [isHeartbeatScanning, setIsHeartbeatScanning] = useState(false);
  const [activeFeederView, setActiveFeederView] = useState<'FEEDER_STATUS' | 'WORKFLOW_VISUAL' | 'NONE'>('FEEDER_STATUS');

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

  // Secondary Queue Filtering
  const activeItem: ResearchQueueItem =
    researchQueue.find(r => r.id === selectedItemId) || researchQueue[0];

  const filteredQueue = researchQueue.filter(item => {
    const matchesSearch =
      item.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.sourceName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.sourceType.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.processor.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.origin.toLowerCase().includes(searchTerm.toLowerCase());

    if (!matchesSearch) return false;
    if (statusFilter === 'All') return true;
    if (statusFilter === 'Queued') return item.status === 'QUEUED';
    if (statusFilter === 'Processing') return item.status === 'PROCESSING';
    if (statusFilter === 'Ingested') return item.status === 'INGESTED';
    if (statusFilter === 'Failed Retryable') return item.status === 'FAILED_RETRYABLE';
    if (statusFilter === 'Failed Final') return item.status === 'FAILED_FINAL';
    if (statusFilter === 'YouTube') return item.sourceType === 'YouTube';
    if (statusFilter === 'TradingView') return item.sourceType === 'TradingView';
    return true;
  });

  const queueDepth = researchQueue.filter(
    i => i.status === 'QUEUED' || i.status === 'PROCESSING'
  ).length;
  const countProcessing = researchQueue.filter(i => i.status === 'PROCESSING').length;
  const countIngestedToday = researchQueue.filter(i => i.status === 'INGESTED').length;
  const countFailedRetryable = researchQueue.filter(
    i => i.status === 'FAILED_RETRYABLE'
  ).length;

  const sourceMix = {
    YouTube: researchQueue.filter(i => i.sourceType === 'YouTube').length,
    Web: researchQueue.filter(i => i.sourceType === 'Web').length,
    GitHub: researchQueue.filter(i => i.sourceType === 'GitHub').length,
    TradingView: researchQueue.filter(i => i.sourceType === 'TradingView').length,
    SEO: researchQueue.filter(i => i.sourceType === 'SEO').length,
    Documents: researchQueue.filter(i => i.sourceType === 'Documents').length,
  };

  const handleForceDiscoveryCycle = () => {
    if (isHeartbeatScanning) return;
    setIsHeartbeatScanning(true);
    showToast('Executing discovery cycle across configured source channels...');

    setTimeout(() => {
      setIsHeartbeatScanning(false);
      setDiscoveryHeartbeat(prev => ({
        ...prev,
        lastDiscoveryCycle: `Cycle #${prev.recentHeartbeatLog.length + 144} (Just now)`,
        sourcesDiscoveredCount: prev.sourcesDiscoveredCount + 4,
        itemsAppendedToFifoCount: prev.itemsAppendedToFifoCount + 2,
        secondsUntilNextCycle: 60,
        recentHeartbeatLog: [
          {
            cycleNumber: prev.recentHeartbeatLog.length + 144,
            timestamp: 'Just now',
            sourcesFound: 4,
            appendedToFifo: 2,
            channel: 'YouTube & TradingView Public Feeds',
            summary: 'Discovered 4 candidates; appended 2 deterministic items to Universal FIFO.',
          },
          ...prev.recentHeartbeatLog.slice(0, 3),
        ],
      }));
      showToast('Discovery cycle complete: 2 items appended to Universal FIFO queue.');
    }, 1500);
  };

  const handleVerifyReadback = (item: ResearchQueueItem) => {
    showToast(`Verifying Supabase readback for ${item.canonicalPackageId}...`);
    setTimeout(() => {
      setResearchQueue(prev =>
        prev.map(i =>
          i.id === item.id
            ? {
                ...i,
                readbackResult: 'Verified',
                status: 'INGESTED',
                currentStage: 'SUPABASE_WRITE_CONFIRMED',
              }
            : i
        )
      );
      showToast(`Supabase readback verified on ${item.canonicalPackageId}`);
    }, 500);
  };

  const handlePromoteFinding = (findingId: string, title: string) => {
    promoteResearchFinding(findingId);
    showToast(`Promoted "${title}" to an active Nexus project.`);
  };

  const renderStatusBadge = (status: MechanicalIngestionStatus, diagnostic: string) => {
    switch (status) {
      case 'INGESTED':
        return (
          <span
            className="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 inline-flex items-center gap-1"
            title="SUPABASE_WRITE_CONFIRMED"
          >
            <CheckCircle2 className="w-3 h-3 text-emerald-600 shrink-0" />
            Verified & Saved
          </span>
        );
      case 'PROCESSING':
        return (
          <span className="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200 inline-flex items-center gap-1">
            <RotateCw className="w-3 h-3 text-blue-600 animate-spin shrink-0" />
            Extracting
          </span>
        );
      case 'FAILED_RETRYABLE':
        return (
          <span
            className="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-amber-50 text-amber-800 border border-amber-200 inline-flex items-center gap-1"
            title={diagnostic}
          >
            <Clock className="w-3 h-3 text-amber-600 shrink-0" />
            Retry Queued
          </span>
        );
      case 'FAILED_FINAL':
        return (
          <span className="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-rose-50 text-rose-700 border border-rose-200 inline-flex items-center gap-1">
            <XCircle className="w-3 h-3 text-rose-600 shrink-0" />
            Failed
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200 inline-flex items-center gap-1">
            <Layers className="w-3 h-3 text-slate-500 shrink-0" />
            In Queue
          </span>
        );
    }
  };

  const getSourceIcon = (type: ResearchSourceType) => {
    switch (type) {
      case 'YouTube':
        return <Youtube className="w-3.5 h-3.5 text-rose-600" />;
      case 'TradingView':
        return <TrendingUp className="w-3.5 h-3.5 text-blue-600" />;
      case 'GitHub':
        return <Github className="w-3.5 h-3.5 text-slate-800" />;
      case 'SEO':
        return <Search className="w-3.5 h-3.5 text-purple-600" />;
      case 'Documents':
        return <FileText className="w-3.5 h-3.5 text-emerald-600" />;
      default:
        return <Globe className="w-3.5 h-3.5 text-cyan-600" />;
    }
  };

  const getOriginBadge = (origin: WorkOrigin) => {
    switch (origin) {
      case 'SCHEDULED_DISCOVERY':
        return (
          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-cyan-50 text-cyan-800 border border-cyan-200">
            Automated Scan
          </span>
        );
      case 'SOURCE_MONITOR':
        return (
          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200">
            Channel Monitor
          </span>
        );
      case 'EXPERT_REQUEST':
        return (
          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-purple-50 text-purple-800 border border-purple-200">
            Operator Request
          </span>
        );
      default:
        return (
          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
            {origin}
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
              onClick={() => setActiveTab('diagnostics')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer ${
                activeTab === 'diagnostics'
                  ? 'bg-white text-slate-900 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Ingestion &amp; Queue Diagnostics ({researchQueue.length})
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
      {/* TAB 2: INGESTION & QUEUE DIAGNOSTICS (SECONDARY MECHANICAL VIEW)          */}
      {/* ========================================================================= */}
      {activeTab === 'diagnostics' && (
        <div className="space-y-4">
          {/* Discovery Heartbeat Strip */}
          <div className="bg-white border border-slate-200/80 rounded-xl px-4 py-3 flex flex-wrap items-center justify-between gap-2 text-xs shadow-2xs">
            <div className="flex items-center gap-2.5 flex-wrap">
              <span className="inline-flex h-2 w-2 rounded-full bg-emerald-500" />
              <span className="font-semibold text-slate-900">Universal FIFO & Discovery Heartbeat</span>
              <TruthBadge truth="TEST" label="Queue Telemetry" />
              <span className="text-slate-500">
                {discoveryHeartbeat.lastDiscoveryCycle} · Queue Depth:{' '}
                <strong className="text-slate-900">{queueDepth}</strong> · Verified Today:{' '}
                <strong className="text-emerald-700">{countIngestedToday}</strong> · Retrying:{' '}
                <strong className="text-amber-700">{countFailedRetryable}</strong>
              </span>
            </div>

            <div className="flex items-center gap-1.5">
              <span className="px-2 py-0.5 rounded bg-slate-50 border border-slate-200 text-slate-600 text-[11px]">
                YT {sourceMix.YouTube} · TV {sourceMix.TradingView} · GH {sourceMix.GitHub}
              </span>
              <button
                type="button"
                onClick={handleForceDiscoveryCycle}
                disabled={isHeartbeatScanning}
                className="px-3 py-1 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium text-xs inline-flex items-center gap-1.5 cursor-pointer"
              >
                <Zap className={`w-3.5 h-3.5 ${isHeartbeatScanning ? 'animate-pulse' : ''}`} />
                {isHeartbeatScanning ? 'Scanning...' : 'Run Discovery Cycle'}
              </button>
            </div>
          </div>

          {/* Feeder & Workflow Card */}
          <div className="bg-white border border-slate-200/80 rounded-xl p-4 shadow-2xs space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <h3 className="text-xs font-semibold text-slate-900 uppercase tracking-wider">
                  Research Feeder Intake &amp; Handoff Model
                </h3>
                <TruthBadge truth="DEMO" label="Feeder Sample" />
              </div>

              <div className="inline-flex p-0.5 rounded-lg bg-slate-100 border border-slate-200">
                <button
                  type="button"
                  onClick={() => setActiveFeederView('FEEDER_STATUS')}
                  className={`px-2.5 py-1 rounded-md text-xs font-medium cursor-pointer ${
                    activeFeederView === 'FEEDER_STATUS'
                      ? 'bg-white text-slate-900 shadow-2xs'
                      : 'text-slate-600'
                  }`}
                >
                  Feeder Status
                </button>
                <button
                  type="button"
                  onClick={() => setActiveFeederView('WORKFLOW_VISUAL')}
                  className={`px-2.5 py-1 rounded-md text-xs font-medium cursor-pointer ${
                    activeFeederView === 'WORKFLOW_VISUAL'
                      ? 'bg-white text-slate-900 shadow-2xs'
                      : 'text-slate-600'
                  }`}
                >
                  8-Step Contract
                </button>
                <button
                  type="button"
                  onClick={() =>
                    setActiveFeederView(activeFeederView === 'NONE' ? 'FEEDER_STATUS' : 'NONE')
                  }
                  className="px-2 py-1 text-xs text-slate-500 cursor-pointer"
                >
                  {activeFeederView === 'NONE' ? 'Expand' : 'Collapse'}
                </button>
              </div>
            </div>

            {activeFeederView === 'FEEDER_STATUS' && (
              <div className="space-y-3">
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-slate-50 border-b border-slate-200 text-[10px] font-semibold text-slate-500 uppercase">
                        <th className="py-2 px-3">Feeder Category</th>
                        <th className="py-2 px-3">Status</th>
                        <th className="py-2 px-3">Sources</th>
                        <th className="py-2 px-3">Complete</th>
                        <th className="py-2 px-3">Handed Off</th>
                        <th className="py-2 px-3">Batch Progress</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {INITIAL_RESEARCH_FEEDERS.map(f => (
                        <tr key={f.id} className="hover:bg-slate-50/70">
                          <td className="py-2 px-3">
                            <div className="font-medium text-slate-900">{f.category}</div>
                            <div className="text-[11px] text-slate-400 font-mono">{f.notebook}</div>
                          </td>
                          <td className="py-2 px-3">
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                              {f.status}
                            </span>
                          </td>
                          <td className="py-2 px-3 text-slate-700">{f.sourcesAdded}</td>
                          <td className="py-2 px-3 text-emerald-700 font-medium">
                            {f.questionnaireComplete}
                          </td>
                          <td className="py-2 px-3 text-blue-700 font-medium">{f.handedOff}</td>
                          <td className="py-2 px-3 font-mono text-[11px] text-slate-700">
                            {f.testBatchProgress.completed} / {f.testBatchProgress.target}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <span className="font-medium text-slate-800">
                      Ray / Nova Direct Opportunity Intake:{' '}
                      {RAY_NOVA_OPPORTUNITY_INTAKE.activeSubmissions} active ·{' '}
                      {RAY_NOVA_OPPORTUNITY_INTAKE.lastIntake}
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-500">
                    Processing workers active: {countProcessing}
                  </span>
                </div>
              </div>
            )}

            {activeFeederView === 'WORKFLOW_VISUAL' && (
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
                {[
                  { step: '01', title: 'Source', desc: 'YouTube, Web, APIs' },
                  { step: '02', title: 'Feeder', desc: 'NotebookLM anchor' },
                  { step: '03', title: 'Contract', desc: 'Fixed schema check' },
                  { step: '04', title: 'Output', desc: 'Normalized brief' },
                  { step: '05', title: 'Gap Check', desc: 'Missing facts flagged' },
                  { step: '06', title: 'Enrich', desc: 'Secondary scrape' },
                  { step: '07', title: 'Handoff', desc: 'Durable Supabase write' },
                  { step: '08', title: 'Dept Owner', desc: 'Direct execution' },
                ].map(w => (
                  <div
                    key={w.step}
                    className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs"
                  >
                    <div className="text-[10px] text-slate-400 font-mono">Step {w.step}</div>
                    <div className="font-semibold text-slate-900 mt-0.5">{w.title}</div>
                    <div className="text-[11px] text-slate-500 mt-0.5">{w.desc}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Two-Pane FIFO Queue Table + Receipt Inspector */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            <div className="lg:col-span-7 bg-white rounded-xl border border-slate-200/80 shadow-2xs overflow-hidden flex flex-col">
              <div className="p-3 border-b border-slate-100 flex flex-wrap items-center justify-between gap-2 bg-slate-50/50">
                <div className="relative flex-1 min-w-[160px]">
                  <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={e => setSearchTerm(e.target.value)}
                    placeholder="Search FIFO queue..."
                    className="w-full pl-8 pr-2 py-1 text-xs bg-white border border-slate-200 rounded-lg focus:outline-hidden focus:border-blue-500"
                  />
                </div>
                <div className="flex items-center gap-1 flex-wrap text-[11px]">
                  {(['All', 'Queued', 'Processing', 'Ingested', 'Failed Retryable'] as const).map(
                    tab => (
                      <button
                        key={tab}
                        type="button"
                        onClick={() => setStatusFilter(tab)}
                        className={`px-2 py-1 rounded-md font-medium cursor-pointer ${
                          statusFilter === tab
                            ? 'bg-slate-900 text-white'
                            : 'text-slate-600 hover:bg-slate-200/60'
                        }`}
                      >
                        {tab}
                      </button>
                    )
                  )}
                </div>
              </div>

              <div className="overflow-x-auto max-h-[480px] overflow-y-auto custom-scrollbar">
                <table className="w-full text-left border-collapse text-xs">
                  <thead className="sticky top-0 bg-slate-50 text-[10px] font-semibold text-slate-500 uppercase border-b border-slate-100">
                    <tr>
                      <th className="py-2 px-3">FIFO &amp; Source</th>
                      <th className="py-2 px-3">Origin</th>
                      <th className="py-2 px-3">Status</th>
                      <th className="py-2 px-3">Readback</th>
                      <th className="py-2 px-3 text-right">View</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filteredQueue.map(item => {
                      const isSelected = activeItem.id === item.id;
                      return (
                        <tr
                          key={item.id}
                          onClick={() => setSelectedItemId(item.id)}
                          className={`cursor-pointer ${
                            isSelected ? 'bg-blue-50/70' : 'hover:bg-slate-50'
                          }`}
                        >
                          <td className="py-2.5 px-3">
                            <div className="flex items-center gap-1.5">
                              <span className="font-mono text-[10px] text-slate-600 bg-slate-100 px-1 rounded">
                                #{item.queueSequence}
                              </span>
                              <span className="inline-flex items-center gap-1 text-[11px] text-slate-600">
                                {getSourceIcon(item.sourceType)}
                                {item.sourceType}
                              </span>
                              <TruthBadge truth={item.truthClass} />
                            </div>
                            <div className="font-medium text-slate-900 truncate max-w-[230px] mt-0.5">
                              {item.title}
                            </div>
                          </td>
                          <td className="py-2.5 px-3">{getOriginBadge(item.origin)}</td>
                          <td className="py-2.5 px-3">
                            {renderStatusBadge(item.status, item.technicalDiagnostic)}
                          </td>
                          <td className="py-2.5 px-3 text-[11px] text-slate-600">
                            {item.readbackResult}
                          </td>
                          <td className="py-2.5 px-3 text-right">
                            <ChevronRight
                              className={`w-4 h-4 inline ${
                                isSelected ? 'text-blue-600' : 'text-slate-300'
                              }`}
                            />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="lg:col-span-5 bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs space-y-3">
              <div className="pb-2 border-b border-slate-100 flex items-center justify-between gap-2">
                <div className="flex items-center gap-1.5">
                  <span className="font-mono text-xs font-semibold text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded">
                    FIFO #{activeItem.queueSequence}
                  </span>
                  <TruthBadge truth={activeItem.truthClass} />
                </div>
                {renderStatusBadge(activeItem.status, activeItem.technicalDiagnostic)}
              </div>

              <div>
                <h3 className="text-sm font-semibold text-slate-900">{activeItem.title}</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  {activeItem.sourceName} · {activeItem.processor}
                </p>
              </div>

              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs">
                <div className="text-[10px] font-medium text-slate-500 uppercase">
                  Supabase Canonical Package
                </div>
                <div className="font-mono text-slate-800 mt-0.5">
                  {activeItem.canonicalPackageId}
                </div>
                <div className="text-[11px] text-slate-600 mt-1">
                  Transcript: {activeItem.transcriptStatus}
                </div>
              </div>

              {activeItem.failureReason && (
                <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-900">
                  <div className="font-semibold flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
                    Diagnostic ({activeItem.retryCount} retries)
                  </div>
                  <p className="mt-1">{activeItem.failureReason}</p>
                </div>
              )}

              {activeItem.downstreamAnalysis && (
                <div className="p-2.5 rounded-lg bg-blue-50/50 border border-blue-100 text-xs space-y-1.5">
                  <div className="font-semibold text-slate-800">Downstream Consumption</div>
                  <p className="text-slate-700 leading-relaxed">
                    {activeItem.downstreamAnalysis.researchInterpretation}
                  </p>
                  <div className="text-[11px] text-blue-800 font-medium">
                    Consumer: {activeItem.downstreamAnalysis.expertRouting}
                  </div>
                </div>
              )}

              <button
                type="button"
                onClick={() => handleVerifyReadback(activeItem)}
                className="w-full py-2 px-3 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium inline-flex items-center justify-center gap-1.5 cursor-pointer"
              >
                <Database className="w-3.5 h-3.5 text-emerald-400" />
                Re-Verify Supabase Readback
              </button>
            </div>
          </div>
        </div>
      )}
      {activeTab === 'rooms' && <ResearchRoomWorkspace />}
    </div>
  );
};
