import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';
import {
  PageId,
  NovaState,
  NovaMessage,
  ApprovalItem,
  NexusProject,
  NexusApproval,
  NexusCampaign,
  NexusCommerceOffer,
  NexusResearchFinding,
  NexusNotification,
  NexusCredentialState,
  NexusLabExperiment,
  NexusUpgradeCandidate,
  DistributedSystemNode,
} from '../types';
import { APPROVALS_DATA } from '../data/mockData';
import { loadLiveSnapshot, redirectToLogin, LIVE_REFRESH_MS, type LiveStatus } from '../integration/live';
import { mapApprovals, mapCommerce, mapCreative, mapNotifications, mapProjects, mapResearch, mapSystems } from '../integration/mapLive';
import { NeedsRayDecisionItem } from '../data/needsRayData';
import { CreativeAsset, CreativeApprovalState } from '../data/creativeMarketingData';
import {
  INITIAL_NEXUS_PROJECTS,
  INITIAL_NEXUS_APPROVALS,
  INITIAL_NEXUS_CAMPAIGNS,
  INITIAL_NEXUS_CREATIVE_ASSETS,
  INITIAL_COMMERCE_OFFERS,
  INITIAL_RESEARCH_FINDINGS,
  INITIAL_NEXUS_NOTIFICATIONS,
  INITIAL_NEXUS_CREDENTIALS,
  INITIAL_LAB_EXPERIMENTS,
  INITIAL_UPGRADE_CANDIDATES,
  INITIAL_DISTRIBUTED_SYSTEMS,
} from '../data/nexusControlPlaneData';

interface CreateProjectInput {
  name: string;
  department: string;
  client: string;
  priority: 'High' | 'Medium' | 'Low';
}

interface NexusContextType {
  currentPage: PageId;
  setCurrentPage: (page: PageId) => void;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  novaState: NovaState;
  setNovaState: (state: NovaState) => void;
  isMuted: boolean;
  setIsMuted: React.Dispatch<React.SetStateAction<boolean>>;
  isSpeakerOn: boolean;
  setIsSpeakerOn: React.Dispatch<React.SetStateAction<boolean>>;
  messages: NovaMessage[];
  sendMessage: (text: string) => void;
  quickActions: string[];
  triggerQuickAction: (action: string) => void;
  isMobileNovaOpen: boolean;
  setIsMobileNovaOpen: (open: boolean) => void;
  isNovaDrawerOpen: boolean;
  setIsNovaDrawerOpen: (open: boolean) => void;
  isNewProjectModalOpen: boolean;
  setIsNewProjectModalOpen: (open: boolean) => void;

  // Live Nexus integration (authoritative read model)
  liveStatus: LiveStatus;
  liveAreas: Record<string, any>;
  liveGeneratedAt: string | null;
  liveFreshness: 'LIVE' | 'STALE' | 'UNKNOWN';

  // Authoritative Unified State
  projects: NexusProject[];
  approvals: NexusApproval[];
  campaigns: NexusCampaign[];
  creativeAssets: CreativeAsset[];
  commerceOffers: NexusCommerceOffer[];
  researchFindings: NexusResearchFinding[];
  notifications: NexusNotification[];
  credentials: NexusCredentialState[];
  labExperiments: NexusLabExperiment[];
  upgradeCandidates: NexusUpgradeCandidate[];
  distributedSystems: DistributedSystemNode[];

  // Nova-Parity Selectors
  nexus_get_project: (projectId: string) => NexusProject | undefined;
  nexus_get_project_approvals: (projectId: string) => NexusApproval[];
  pendingApprovalsCount: number;
  unreadNotificationsCount: number;

  // Entity Selection & Navigation
  selectedApprovalId: string | null;
  setSelectedApprovalId: (id: string | null) => void;
  selectedProjectId: string | null;
  setSelectedProjectId: (id: string | null) => void;
  selectedCampaignId: string | null;
  setSelectedCampaignId: (id: string | null) => void;
  selectedAssetId: string | null;
  setSelectedAssetId: (id: string | null) => void;
  selectedOfferId: string | null;
  setSelectedOfferId: (id: string | null) => void;
  navigateToObject: (
    page: PageId,
    entityId?: string,
    kind?: 'approval' | 'project' | 'campaign' | 'asset' | 'offer'
  ) => void;

  // Authoritative Mutations
  approveDecision: (id: string, note?: string) => void;
  rejectDecision: (id: string, note?: string) => void;
  requestRevisionDecision: (id: string, note: string) => void;
  reAnalyzeDecision: (id: string, note: string) => void;
  clydeDeepDiveDecision: (id: string) => void;
  approveAllLowRiskDecisions: () => void;
  createProject: (input: CreateProjectInput) => NexusProject;
  updateCreativeAssetStatus: (
    assetId: string,
    approvalState: CreativeApprovalState,
    note?: string
  ) => void;
  promoteLabExperiment: (experimentId: string) => void;
  certifyUpgradeCandidate: (candidateId: string) => void;
  updateCredentialState: (
    credentialId: string,
    newState: NexusCredentialState['state']
  ) => void;
  promoteResearchFinding: (findingId: string) => void;
  markNotificationRead: (id: string) => void;
  markAllNotificationsRead: () => void;

  // Legacy Compatibility Views Derived From Authoritative State
  approvalsList: ApprovalItem[];
  setApprovalsList: React.Dispatch<React.SetStateAction<ApprovalItem[]>>;
  addApprovalTicket: (ticket: ApprovalItem) => void;
  isNeedsRayDrawerOpen: boolean;
  setIsNeedsRayDrawerOpen: React.Dispatch<React.SetStateAction<boolean>>;
  needsRayDecisions: NeedsRayDecisionItem[];
  addRayDecision: (decision: NeedsRayDecisionItem) => void;
  xp: number;
  level: number;
  streakDays: number;
  completedQuests: string[];
  completeQuest: (questId: string, xpReward: number) => void;
  claimDailyBonus: () => void;
  hasClaimedDaily: boolean;
  isCommandCenterCompact: boolean;
  setIsCommandCenterCompact: React.Dispatch<React.SetStateAction<boolean>>;
  isZeroScrollMode: boolean;
  setIsZeroScrollMode: React.Dispatch<React.SetStateAction<boolean>>;
}

export const PAGE_NOVA_GREETINGS: Record<PageId, { greeting: string; subtitle: string }> = {
  'command-center': {
    greeting:
      'Nexus Overview ready. Ask about active projects, pending approvals, blocked actions, or verified commerce costs.',
    subtitle: 'Executive Operating Summary · Live Authoritative State',
  },
  approvals: {
    greeting:
      'Approvals Queue active. Review previews, blocked actions, and cost impact before deciding.',
    subtitle: 'Human-in-the-Loop Decision Gate · Ray Davis',
  },
  projects: {
    greeting:
      'Projects view active. Inspect durable project stage progression across Research, Marketing, Creative, Commerce, and Distribution.',
    subtitle: 'First-Class Nexus Projects & Durable Handoffs',
  },
  research: {
    greeting:
      'Research Findings & Recommendations ready. Inspect evidence quality, linked projects, or queue health.',
    subtitle: 'Discovery, Evidence & Promotion Pipeline',
  },
  marketing: {
    greeting:
      'Marketing Strategy & Channel Readiness active. Facebook direct API is NOT CONNECTED; Stage A uses Postiz scheduling upon approval.',
    subtitle: 'Channel Readiness, Schedule & Audience Response',
  },
  campaigns: {
    greeting:
      'Campaigns view active. Inspect hooks, copy, UTM links, Creative assets, and approval/publication states.',
    subtitle: 'First-Class Campaigns & Publication Gates',
  },
  creative: {
    greeting:
      'Creative Asset Library active. Review generated product photos, campaign visuals, videos, and decks synced with Approvals.',
    subtitle: 'Creative Deliverables & Revision State',
  },
  'business-hub': {
    greeting:
      'Commerce & Ventures workspace active. Product Printify base/shipping costs are VERIFIED; Stripe live checkout is BLOCKED pending credential.',
    subtitle: 'Commerce Product Truth, Ventures & Funding',
  },
  finance: {
    greeting:
      'Finance Control active. Verified bank cash is $0.00 (NOT CONNECTED). Printify unit costs are VERIFIED; projected savings are clearly labeled DEMO/ESTIMATED.',
    subtitle: 'Truth-Labeled Economics & Spend Gates',
  },
  'trading-engine': {
    greeting:
      'Trading workspace active. Live state comes from the Trading Core paper store; live trading is never enabled from the Admin.',
    subtitle: 'Deterministic Paper Core & Risk Governance',
  },
  systems: {
    greeting:
      'Systems Health online. Oracle is reserved strictly for Nova/Hermes & essential coordination; Contabo and Mac mini handle heavy workloads.',
    subtitle: 'Distributed Architecture & Recovery Guardrails',
  },
  nova: {
    greeting:
      'Nova Executive Operator online. Every answer is grounded against live Projects, Approvals, Commerce, Trading, and Systems state.',
    subtitle: 'Grounded Operator Interface · Nexus OS',
  },
  clients: {
    greeting:
      'Client Tenants directory active. Filter between PILOT / REAL and DEMO / TEST tenant records.',
    subtitle: 'Tenant Classification & Account Health',
  },
  documents: {
    greeting:
      'Documents repository active. Inspect project specifications, contracts, and evidence artifacts.',
    subtitle: 'Project & Evidence Documents',
  },
  'development-labs': {
    greeting:
      'Development / Labs active. All experiments stay strictly isolated; promotion moves only into Upgrade Control.',
    subtitle: 'Isolated R&D Sandboxes',
  },
  'upgrade-control': {
    greeting:
      'Upgrade Control certification active. Verify security checks, cost impact, and rollback plans before certifying for Systems.',
    subtitle: 'Certification & Rollback Gate',
  },
  settings: {
    greeting:
      'Settings & Credential Registry active. Inspect real CONNECTED vs MISSING CREDENTIAL / NOT_CONNECTED integration states.',
    subtitle: 'Integration Truth & Control Preferences',
  },
  operations: {
    greeting: 'Systems view active.',
    subtitle: 'Infrastructure Health',
  },
  'existing-business': {
    greeting: 'Existing Business Center ready. Every metric carries its truth class; unconnected sources show NOT CONNECTED.',
    subtitle: 'Operating Ventures · Live Authoritative State',
  },
  rea: {
    greeting: 'REA workspace active. Inspect durable REA_EXECUTION jobs, evidence and results. Submit new REA work through Nova.',
    subtitle: 'Reverse Engineering & Analysis · Contabo Harness',
  },
};

const PAGE_QUICK_ACTIONS: Record<PageId, string[]> = {
  'command-center': ['What needs my attention?', 'Status of 6:12 AM Quiet Ritual', 'What is blocked right now?', 'Check Trading R1 status'],
  approvals: ['Summarize pending approvals', 'Explain Stage A vs Stage B', 'What is highest risk?'],
  projects: ['Status of proj_98ef515bccee4b58', 'What is next on active projects?', 'Show blockers'],
  research: ['What did Research recommend?', 'Any unpromoted findings?'],
  marketing: ['Why is Facebook marked NOT CONNECTED?', 'What campaigns are waiting to publish?'],
  campaigns: ['Inspect Stage A campaign', 'Show tracked UTM links'],
  creative: ['What assets await approval?', 'Show Holiday Mug creative assets'],
  'business-hub': ['Verify Printify mug unit economics', 'Why is Stripe checkout blocked?'],
  finance: ['What is verified cash?', 'What spend approvals are pending?'],
  'trading-engine': ['Check Wick Sequence Breakout v1', 'Verify paper-only guardrails'],
  systems: ['Check Oracle workload policy', 'Which services have blockers?'],
  nova: ['What needs my attention right now?', 'Status of The 6:12 AM Quiet Ritual', 'Why is live checkout blocked?', 'Check Trading R1 & Systems health'],
  clients: ['Show pilot vs demo clients'],
  documents: ['List Holiday Mug evidence files'],
  'development-labs': ['Which lab experiments are validated?'],
  'upgrade-control': ['Show pending upgrades'],
  settings: ['List missing credentials'],
  operations: ['Check Systems health'],
  'existing-business': ['Which business has pending approvals?', 'What is the next action?'],
  rea: ['What REA jobs completed?', 'Any REA job blocked?'],
};

function buildGroundedNovaReply(
  query: string,
  state: {
    projects: NexusProject[];
    approvals: NexusApproval[];
    campaigns: NexusCampaign[];
    creativeAssets: CreativeAsset[];
    commerceOffers: NexusCommerceOffer[];
    credentials: NexusCredentialState[];
    distributedSystems: DistributedSystemNode[];
    liveAreas?: Record<string, any>;
  }
): string {
  // Answers come ONLY from the live read model. Decisions and new work go to Nova on Telegram.
  const q = query.toLowerCase();
  const live = state.liveAreas || {};
  const pending = state.approvals.filter(a => a.status === 'PENDING');
  const idMatch = query.match(/proj_[a-z0-9_]+/i)?.[0];
  const project = (idMatch && state.projects.find(p => p.id === idMatch)) || state.projects[0];
  const tail = ' (Read-only Admin view. To decide or start work, message Nova on Telegram.)';
  if (!state.projects.length && !Object.keys(live).length) return 'Live Nexus state is NOT CONNECTED, so I cannot answer from authoritative data.';
  if (q.includes('approv') || q.includes('decision')) {
    if (!pending.length) return 'No approvals are pending in the live read model.' + tail;
    return `${pending.length} approval(s) pending: ` + pending.map(a => `${a.title} [${a.id}] for ${a.projectName}`).join('; ') + '.' + tail;
  }
  if (q.includes('trad')) {
    const t = live.trading || {};
    const v = (t.versions || [])[0];
    if (!v) return 'Trading state is NOT CONNECTED.';
    return `Trading Core: ${v.name} (${v.instrument} ${v.timeframe}), status ${v.status}, ${t.broker} ${t.mode} mode; live trading ${t.liveTradingEnabled === false ? 'locked OFF' : 'UNKNOWN'}. Paper trades: ${t.counts?.trades ?? 'UNKNOWN'}.`;
  }
  if (/\brea\b/.test(q)) {
    const jobs: any[] = live.rea || [];
    if (!jobs.length) return 'No REA jobs in the live read model.';
    return 'Latest REA jobs: ' + jobs.slice(0, 3).map(j => `${j.reaJobId} ${j.status} (${j.workType || 'UNKNOWN'})`).join('; ') + '.';
  }
  if (q.includes('system') || q.includes('health')) {
    return state.distributedSystems.map(s => `${s.name}: ${s.status}${s.blocker ? ` (${s.blocker})` : ''}`).join('; ') || 'Systems state is NOT CONNECTED.';
  }
  if (q.includes('commerce') || q.includes('stripe') || q.includes('checkout') || q.includes('printify') || q.includes('cost')) {
    const o = state.commerceOffers[0];
    if (!o) return 'Commerce state is NOT CONNECTED.';
    return `${o.title}: base cost $${o.productTruth.baseCost ?? 'UNKNOWN'} [${o.productTruth.baseCostTruth}], staged price $${o.productTruth.stagedPrice ?? 'UNKNOWN'} [${o.productTruth.stagedPriceTruth}], mode ${o.interestTest.mode}, live checkout ${o.liveSales.checkoutStatus}.`;
  }
  if (project) {
    const pa = state.approvals.filter(a => a.projectId === project.id && a.status === 'PENDING');
    return `${project.name} [${project.id}]: ${project.currentDepartment} · ${project.stage}. Next: ${project.nextAction}.` +
      (project.blocker ? ` Blocker: ${project.blocker}.` : '') + ` Pending approvals: ${pa.length}.` + tail;
  }
  return 'No matching live state found.' + tail;
}

const NexusContext = createContext<NexusContextType | undefined>(undefined);

export const NexusProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentPage, setCurrentPage] = useState<PageId>('command-center');
  const [searchQuery, setSearchQuery] = useState('');
  const [novaState, setNovaState] = useState<NovaState>('listening');
  const [isMuted, setIsMuted] = useState(false);
  const [isSpeakerOn, setIsSpeakerOn] = useState(true);
  const [isMobileNovaOpen, setIsMobileNovaOpen] = useState(false);
  const [isNovaDrawerOpen, setIsNovaDrawerOpen] = useState(false);
  const [isNewProjectModalOpen, setIsNewProjectModalOpen] = useState(false);

  // Authoritative unified state
  const [projects, setProjects] = useState<NexusProject[]>([]);
  const [approvals, setApprovals] = useState<NexusApproval[]>([]);
  const [campaigns, setCampaigns] = useState<NexusCampaign[]>([]);
  const [creativeAssets, setCreativeAssets] = useState<CreativeAsset[]>([]);
  const [commerceOffers, setCommerceOffers] = useState<NexusCommerceOffer[]>([]);
  const [researchFindings, setResearchFindings] = useState<NexusResearchFinding[]>([]);
  const [notifications, setNotifications] = useState<NexusNotification[]>([]);
  const [credentials, setCredentials] = useState<NexusCredentialState[]>([]);
  const [labExperiments, setLabExperiments] = useState<NexusLabExperiment[]>([]);
  const [upgradeCandidates, setUpgradeCandidates] = useState<NexusUpgradeCandidate[]>([]);
  const [distributedSystems, setDistributedSystems] = useState<DistributedSystemNode[]>([]);

  // Selected entity pointers for seamless cross-page drilldown
  const [selectedApprovalId, setSelectedApprovalId] = useState<string | null>(null);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);
  const [selectedOfferId, setSelectedOfferId] = useState<string | null>(null);

  // Legacy states retained for compatibility
  const [approvalsList, setApprovalsList] = useState<ApprovalItem[]>([]);
  const [isNeedsRayDrawerOpen, setIsNeedsRayDrawerOpen] = useState(false);
  const [xp, setXp] = useState(2450);
  const [level, setLevel] = useState(7);
  const [streakDays, setStreakDays] = useState(14);
  const [hasClaimedDaily, setHasClaimedDaily] = useState(false);
  const [completedQuests, setCompletedQuests] = useState<string[]>(['quest-1']);
  const [isCommandCenterCompact, setIsCommandCenterCompact] = useState<boolean>(true);
  const [isZeroScrollMode, setIsZeroScrollMode] = useState<boolean>(false);

  const [messagesByPage, setMessagesByPage] = useState<Record<string, NovaMessage[]>>({
    nova: [
      {
        id: 'init-nova-1',
        sender: 'nova',
        text: 'Hello Ray. Loading authoritative Nexus state… Answers here are grounded only in the live read model; decisions and new objectives go to Nova on Telegram.',
        timestamp: 'Now',
      },
    ],
  });


  // ---- Live Nexus state (authoritative read model; refreshed every minute) ----
  const [liveStatus, setLiveStatus] = useState<LiveStatus>('loading');
  const [liveAreas, setLiveAreas] = useState<Record<string, any>>({});
  const [liveGeneratedAt, setLiveGeneratedAt] = useState<string | null>(null);
  const [liveFreshness, setLiveFreshness] = useState<'LIVE' | 'STALE' | 'UNKNOWN'>('UNKNOWN');
  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      const r = await loadLiveSnapshot().catch(() => ({ status: 'unavailable' as LiveStatus, snapshot: undefined }));
      if (cancelled) return;
      if (r.status === 'unauthenticated') { redirectToLogin(); return; }
      setLiveStatus(r.status);
      if (r.status !== 'ready' || !r.snapshot) return;
      const a = r.snapshot.areas || {};
      setLiveAreas(a);
      setLiveGeneratedAt(r.snapshot.generated_at);
      setLiveFreshness(r.snapshot.freshness);
      setProjects(mapProjects(a));
      setApprovals(mapApprovals(a));
      setCreativeAssets(mapCreative(a));
      setCommerceOffers(mapCommerce(a));
      setResearchFindings(mapResearch(a));
      setDistributedSystems(mapSystems(a, r.snapshot.generated_at));
      setNotifications(prev => {
        const readIds = new Set(prev.filter(n => n.read).map(n => n.id));
        return mapNotifications(a).map(n => ({ ...n, read: readIds.has(n.id) }));
      });
      setSelectedOfferId(cur => cur ?? (a.commerce?.[0]?.id ?? null));
      setSelectedAssetId(cur => cur ?? (a.creative?.[0]?.id ?? null));
      setSelectedApprovalId(cur => cur ?? (a.approvals?.find((x: any) => x.status === 'PENDING')?.id ?? a.approvals?.[0]?.id ?? null));
    };
    tick();
    const t = window.setInterval(tick, LIVE_REFRESH_MS);
    return () => { cancelled = true; window.clearInterval(t); };
  }, []);

  // Governed actions: the Admin never mutates Nexus state locally. Decisions and new work
  // go through Nova (Telegram) so approvals stay single-source and auditable.
  const governed = (what: string, command?: string) =>
    pushNotification({
      type: 'APPROVAL_REQUIRED',
      title: `${what} is governed by Nova`,
      detail: command ? `Send to Nova on Telegram: ${command}` : 'Send this to Nova on Telegram; the Admin is read-only for decisions.',
      targetPage: 'approvals',
      truthClass: 'VERIFIED',
    });
  const approvalCommand = (id: string) => (liveAreas.approvals || []).find((x: any) => x.id === id)?.approvalCommand as string | undefined;

  // Nova-parity selectors
  const nexus_get_project = (projectId: string) => projects.find(p => p.id === projectId);
  const nexus_get_project_approvals = (projectId: string) =>
    approvals.filter(a => a.projectId === projectId);

  const pendingApprovalsCount = useMemo(
    () => approvals.filter(a => a.status === 'PENDING').length,
    [approvals]
  );

  const unreadNotificationsCount = useMemo(
    () => notifications.filter(n => !n.read).length,
    [notifications]
  );

  const pushNotification = (notif: Omit<NexusNotification, 'id' | 'timestamp' | 'read'>) => {
    setNotifications(prev => [
      {
        ...notif,
        id: `notif-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
        timestamp: 'Just now',
        read: false,
      },
      ...prev,
    ]);
  };

  const navigateToObject = (
    page: PageId,
    entityId?: string,
    kind?: 'approval' | 'project' | 'campaign' | 'asset' | 'offer'
  ) => {
    if (entityId) {
      if (kind === 'approval' || page === 'approvals') setSelectedApprovalId(entityId);
      if (kind === 'project' || page === 'projects') setSelectedProjectId(entityId);
      if (kind === 'campaign' || page === 'campaigns') setSelectedCampaignId(entityId);
      if (kind === 'asset' || page === 'creative') setSelectedAssetId(entityId);
      if (kind === 'offer' || page === 'business-hub') setSelectedOfferId(entityId);
    }
    setCurrentPage(page);
  };

  // Atomic Approval Mutations (updates Approvals + Parent Project + Campaign + Asset + Notifications + Nova)
  const approveDecision = (id: string, note?: string) => {
    const item = approvals.find(a => a.id === id);
    if (!item) return;

    setApprovals(prev =>
      prev.map(a =>
        a.id === id
          ? {
              ...a,
              status: 'APPROVED',
              decisionTimestamp: 'Just now',
              decisionBy: 'Ray Davis',
              decisionNote: note || 'Approved by Ray Davis.',
            }
          : a
      )
    );

    // Sync linked entity if applicable
    if (item.linkedEntity?.kind === 'campaign') {
      setCampaigns(prev =>
        prev.map(c =>
          c.id === item.linkedEntity?.id
            ? {
                ...c,
                approvalStatus: 'APPROVED',
                publicationStatus: c.channelConnectionState === 'NOT_CONNECTED' ? 'SCHEDULED' : 'PUBLISHED',
                resultsSummary:
                  c.channelConnectionState === 'NOT_CONNECTED'
                    ? 'Stage A approved; queued in Postiz scheduler (direct Facebook API not connected).'
                    : 'Approved and active.',
              }
            : c
        )
      );
    }

    if (item.linkedEntity?.kind === 'asset') {
      setCreativeAssets(prev =>
        prev.map(ast =>
          ast.id === item.linkedEntity?.id
            ? { ...ast, approval_state: 'APPROVED', current_stage: 'APPROVED' }
            : ast
        )
      );
    }

    if (item.linkedEntity?.kind === 'experiment') {
      setLabExperiments(prev =>
        prev.map(exp =>
          exp.id === item.linkedEntity?.id ? { ...exp, status: 'PROMOTED_TO_UPGRADE_CONTROL' } : exp
        )
      );
    }

    if (item.linkedEntity?.kind === 'upgrade') {
      setUpgradeCandidates(prev =>
        prev.map(upg =>
          upg.id === item.linkedEntity?.id ? { ...upg, status: 'CERTIFIED' } : upg
        )
      );
    }

    // Update parent project stage & activity log cleanly (durable handoff continuation)
    setProjects(prev =>
      prev.map(p => {
        if (p.id !== item.projectId) return p;
        const remainingPending = approvals.filter(
          a => a.projectId === p.id && a.id !== id && a.status === 'PENDING'
        );
        return {
          ...p,
          status: 'ACTIVE',
          stage:
            item.id === 'apr_holiday_stage_a'
              ? 'STAGE_A_APPROVED_READY_FOR_DISTRIBUTION'
              : p.stage,
          nextAction:
            remainingPending.length > 0
              ? `Next pending gate: ${remainingPending[0].title}`
              : item.nextAction,
          lastActivity: `Just now · Ray approved ${item.title}`,
          activityLog: [
            {
              id: `act-${Date.now()}`,
              timestamp: 'Just now',
              department: item.department,
              event: `Ray approved "${item.title}". ${item.nextAction}`,
              truthClass: 'VERIFIED',
            },
            ...p.activityLog,
          ],
        };
      })
    );

    pushNotification({
      type: 'PROJECT_CONTINUED',
      title: `Approved: ${item.title}`,
      detail: `${item.projectName} · ${item.nextAction}`,
      targetPage: 'projects',
      targetEntityId: item.projectId,
      projectId: item.projectId,
      truthClass: 'VERIFIED',
    });
  };

  const rejectDecision = (id: string, note?: string) => {
    const item = approvals.find(a => a.id === id);
    if (!item) return;

    setApprovals(prev =>
      prev.map(a =>
        a.id === id
          ? {
              ...a,
              status: 'REJECTED',
              decisionTimestamp: 'Just now',
              decisionBy: 'Ray Davis',
              decisionNote: note || 'Rejected by Ray Davis.',
            }
          : a
      )
    );

    if (item.linkedEntity?.kind === 'asset') {
      setCreativeAssets(prev =>
        prev.map(ast =>
          ast.id === item.linkedEntity?.id
            ? { ...ast, approval_state: 'IN_REVISION', current_stage: 'REJECTED_WITH_REPAIR' }
            : ast
        )
      );
    }

    setProjects(prev =>
      prev.map(p =>
        p.id === item.projectId
          ? {
              ...p,
              lastActivity: `Just now · Ray rejected "${item.title}"`,
              activityLog: [
                {
                  id: `act-${Date.now()}`,
                  timestamp: 'Just now',
                  department: item.department,
                  event: `Ray rejected "${item.title}".${note ? ` Reason: ${note}` : ''}`,
                  truthClass: 'VERIFIED',
                },
                ...p.activityLog,
              ],
            }
          : p
      )
    );

    pushNotification({
      type: 'WORK_FAILED',
      title: `Rejected: ${item.title}`,
      detail: note || `Action paused on ${item.projectName}.`,
      targetPage: 'approvals',
      targetEntityId: item.id,
      projectId: item.projectId,
    });
  };

  const requestRevisionDecision = (id: string, note: string) => {
    const item = approvals.find(a => a.id === id);
    if (!item) return;

    setApprovals(prev =>
      prev.map(a =>
        a.id === id
          ? {
              ...a,
              status: 'REVISION_REQUESTED',
              decisionTimestamp: 'Just now',
              decisionBy: 'Ray Davis',
              decisionNote: note,
            }
          : a
      )
    );

    if (item.linkedEntity?.kind === 'asset') {
      setCreativeAssets(prev =>
        prev.map(ast =>
          ast.id === item.linkedEntity?.id
            ? { ...ast, approval_state: 'IN_REVISION', current_stage: 'REVISION' }
            : ast
        )
      );
    }

    if (item.linkedEntity?.kind === 'campaign') {
      setCampaigns(prev =>
        prev.map(c =>
          c.id === item.linkedEntity?.id ? { ...c, approvalStatus: 'REVISION_REQUESTED' } : c
        )
      );
    }

    setProjects(prev =>
      prev.map(p =>
        p.id === item.projectId
          ? {
              ...p,
              lastActivity: `Just now · Revision requested on ${item.title}`,
              activityLog: [
                {
                  id: `act-${Date.now()}`,
                  timestamp: 'Just now',
                  department: item.department,
                  event: `Ray requested revision on "${item.title}": "${note}"`,
                  truthClass: 'VERIFIED',
                },
                ...p.activityLog,
              ],
            }
          : p
      )
    );

    pushNotification({
      type: 'APPROVAL_REQUIRED',
      title: `Revision requested: ${item.title}`,
      detail: note,
      targetPage: 'approvals',
      targetEntityId: item.id,
      projectId: item.projectId,
    });
  };

  const approveAllLowRiskDecisions = () => {
    const lowRisk = approvals.filter(a => a.status === 'PENDING' && a.riskLevel === 'LOW');
    lowRisk.forEach(item => approveDecision(item.id, 'Batch approved (Low Risk).'));
  };

  const createProjectDraft = (input: CreateProjectInput): NexusProject => {
    const id = `proj_${Math.random().toString(16).slice(2, 14)}`;
    const dept = (input.department as NexusProject['currentDepartment']) || 'Marketing';
    const newProj: NexusProject = {
      id,
      name: input.name.trim(),
      clientOrTrack: input.client.includes('GoClear') ? 'CLIENT_PILOT' : 'NEXUS_VENTURE',
      status: 'ACTIVE',
      currentDepartment: dept,
      stage: 'INITIALIZED',
      summary: `Created via Control Center (${input.priority} priority) for ${input.client}.`,
      nextAction: `${dept} builds initial execution packet.`,
      blocker: null,
      lastActivity: 'Just now · Project created by Ray',
      truthClass: 'VERIFIED',
      linkedApprovalIds: [],
      linkedCampaignIds: [],
      linkedAssetIds: [],
      workflowSteps: [
        { stage: 'Research', status: dept === 'Research' ? 'ACTIVE' : 'COMPLETE', owner: 'Research', summary: 'Initialized project intake.' },
        { stage: 'Opportunity / Project', status: 'COMPLETE', owner: 'Ray Davis', summary: `Created for ${input.client}.` },
        { stage: 'Marketing', status: dept === 'Marketing' ? 'ACTIVE' : 'PENDING', owner: 'Marketing', summary: 'Awaiting brief.' },
        { stage: 'Creative', status: dept === 'Creative' ? 'ACTIVE' : 'PENDING', owner: 'Creative', summary: 'Awaiting specs.' },
        { stage: 'Commerce', status: 'PENDING', owner: 'Commerce', summary: 'Not started.' },
        { stage: 'Distribution', status: 'PENDING', owner: 'Distribution', summary: 'Not started.' },
        { stage: 'Metrics', status: 'PENDING', owner: 'Analytics', summary: 'Not started.' },
        { stage: 'Analysis', status: 'PENDING', owner: 'Nova', summary: 'Not started.' },
        { stage: 'Next Action', status: 'PENDING', owner: dept, summary: `Begin ${dept} execution.` },
      ],
      evidence: [],
      activityLog: [
        {
          id: `act-${Date.now()}`,
          timestamp: 'Just now',
          department: dept,
          event: `Project created (${input.priority} priority).`,
          truthClass: 'VERIFIED',
        },
      ],
    };

    return newProj;
    pushNotification({
      type: 'PROJECT_CONTINUED',
      title: `New project created: ${newProj.name}`,
      detail: `Started in ${dept} (${input.priority} priority).`,
      targetPage: 'projects',
      targetEntityId: id,
      projectId: id,
      truthClass: 'VERIFIED',
    });
    return newProj;
  };

  const updateCreativeAssetStatus = (
    assetId: string,
    approvalState: CreativeApprovalState,
    note?: string
  ) => {
    setCreativeAssets(prev =>
      prev.map(a =>
        a.id === assetId
          ? {
              ...a,
              approval_state: approvalState,
              current_stage:
                approvalState === 'APPROVED'
                  ? 'APPROVED'
                  : approvalState === 'IN_REVISION'
                  ? 'REVISION'
                  : 'REVIEW',
              last_revised: 'Just now',
            }
          : a
      )
    );

    const linkedApproval = approvals.find(
      ap => ap.linkedEntity?.kind === 'asset' && ap.linkedEntity.id === assetId
    );
    if (linkedApproval) {
      if (approvalState === 'APPROVED') approveDecision(linkedApproval.id, note);
      if (approvalState === 'IN_REVISION')
        requestRevisionDecision(linkedApproval.id, note || 'Revision requested from Creative Library.');
    }
  };

  const promoteLabExperiment = (experimentId: string) => {
    const exp = labExperiments.find(e => e.id === experimentId);
    if (!exp) return;

    setLabExperiments(prev =>
      prev.map(e =>
        e.id === experimentId ? { ...e, status: 'PROMOTED_TO_UPGRADE_CONTROL' } : e
      )
    );

    const existingUpg = upgradeCandidates.find(u => u.id === `upg-${experimentId}`);
    if (!existingUpg) {
      setUpgradeCandidates(prev => [
        {
          id: `upg-${experimentId}`,
          name: exp.name,
          fromVersion: 'Sandbox',
          toVersion: 'Candidate v1.0',
          targetNode: 'Mac mini / Contabo (Not Oracle)',
          securityReview: 'PENDING',
          costImpact: '$0.00',
          rollbackPlan: 'Revert manifest & restart launchd worker.',
          status: 'HUMAN_REVIEW',
          truthClass: 'PROPOSED',
        },
        ...prev,
      ]);
    }

    pushNotification({
      type: 'WORK_COMPLETED',
      title: `Lab promoted to Upgrade Control: ${exp.name}`,
      detail: 'Strict sandbox boundary respected; requires Upgrade Control certification before Systems rollout.',
      targetPage: 'upgrade-control',
      truthClass: 'PROPOSED',
    });
  };

  const certifyUpgradeCandidate = (candidateId: string) => {
    setUpgradeCandidates(prev =>
      prev.map(u => (u.id === candidateId ? { ...u, status: 'CERTIFIED', securityReview: 'PASSED' } : u))
    );
    const upg = upgradeCandidates.find(u => u.id === candidateId);
    if (upg?.linkedApprovalId) {
      approveDecision(upg.linkedApprovalId, 'Certified in Upgrade Control.');
    }
  };

  const updateCredentialState = (
    credentialId: string,
    newState: NexusCredentialState['state']
  ) => {
    setCredentials(prev =>
      prev.map(c =>
        c.id === credentialId
          ? {
              ...c,
              state: newState,
              truthClass:
                newState === 'CONNECTED'
                  ? 'VERIFIED'
                  : newState === 'SANDBOX / PAPER'
                  ? 'ESTIMATED'
                  : 'NOT_CONNECTED',
              lastVerified: 'Updated just now',
            }
          : c
      )
    );

    if (credentialId === 'cred-stripe' && newState !== 'MISSING CREDENTIAL' && newState !== 'NOT_CONNECTED') {
      setDistributedSystems(prev =>
        prev.map(s =>
          s.id === 'sys-mkt-comm'
            ? {
                ...s,
                status: 'HEALTHY',
                truthClass: 'VERIFIED',
                blocker: undefined,
                activeServices: ['Printify Draft Sync (Connected)', 'Stripe Sandbox Verified'],
              }
            : s
        )
      );
    }
  };

  const promoteResearchFinding = (findingId: string) => {
    const finding = researchFindings.find(f => f.id === findingId);
    if (!finding || finding.promotedToProject) return;

    const created = createProject({
      name: finding.title,
      department: finding.departmentDestination,
      client: 'Nexus Ventures',
      priority: 'Medium',
    });

    setResearchFindings(prev =>
      prev.map(f =>
        f.id === findingId
          ? {
              ...f,
              promotedToProject: true,
              linkedProjectId: created.id,
              linkedProjectName: created.name,
            }
          : f
      )
    );
  };

  const markNotificationRead = (id: string) => {
    setNotifications(prev => prev.map(n => (n.id === id ? { ...n, read: true } : n)));
  };

  const markAllNotificationsRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  };

  // Compatibility bridge so legacy consumers reading needsRayDecisions see live authoritative approvals
  const needsRayDecisions: NeedsRayDecisionItem[] = useMemo(
    () =>
      approvals.map(a => ({
        id: a.id,
        department:
          a.department === 'Commerce' || a.department === 'Distribution'
            ? 'Business Hub'
            : (a.department as NeedsRayDecisionItem['department']),
        title: a.title,
        subtitle: `${a.projectName} · ${a.type}`,
        whatNexusIsAsking: a.whatIsBeingApproved,
        plainEnglishExplanation: a.plainEnglishExplanation,
        financialImpact: a.costImpact,
        riskLevel: a.riskLevel,
        status:
          a.status === 'REVISION_REQUESTED'
            ? 'RE_ANALYSIS_REQUESTED'
            : a.status,
        timestamp: a.createdAt,
        decisionTimestamp: a.decisionTimestamp,
        decisionNote: a.decisionNote,
        decisionBy: a.decisionBy,
        nextAutonomousStep: a.nextAction,
        urgency: a.priority === 'HIGH' ? 'HIGH' : 'NORMAL',
        notebookRef: a.notebookRef,
      })),
    [approvals]
  );

  const addApprovalTicket = (ticket: ApprovalItem) => {
    setApprovalsList(prev => [ticket, ...prev]);
  };

  const addRayDecision = (decision: NeedsRayDecisionItem) => {
    const newApproval: NexusApproval = {
      id: decision.id,
      projectId: selectedProjectId || 'proj_98ef515bccee4b58',
      projectName: 'Executive Request',
      department: 'Finance',
      type: 'Other',
      status: 'PENDING',
      priority: decision.urgency === 'HIGH' ? 'HIGH' : 'MEDIUM',
      riskLevel: decision.riskLevel,
      title: decision.title,
      subtitle: decision.subtitle,
      reason: decision.whatNexusIsAsking,
      whatIsBeingApproved: decision.whatNexusIsAsking,
      plainEnglishExplanation: decision.plainEnglishExplanation,
      costImpact: decision.financialImpact,
      blockedAction: 'Awaiting Ray decision.',
      nextAction: decision.nextAutonomousStep,
      createdAt: decision.timestamp || 'Just now',
      preview: {
        kind: 'finance',
        headline: decision.title,
        body: decision.plainEnglishExplanation,
        facts: [{ label: 'Impact', value: decision.financialImpact, truthClass: 'PROPOSED' }],
      },
    };
    setApprovals(prev => [newApproval, ...prev]);
  };

  const completeQuest = (_questId: string, _xpReward: number) => {
    setCompletedQuests(prev => [...prev, _questId]);
  };

  const claimDailyBonus = () => {
    setHasClaimedDaily(true);
    setXp(x => x + 50);
    setStreakDays(s => s + 1);
  };

  // Keep page awareness subtle
  useEffect(() => {
    setNovaState('thinking');
    const t = setTimeout(() => setNovaState('listening'), 350);
    return () => clearTimeout(t);
  }, [currentPage]);

  const messages = useMemo(() => {
    const key = currentPage;
    if (messagesByPage[key]) return messagesByPage[key];
    return [
      {
        id: `greet-${key}`,
        sender: 'nova' as const,
        text: PAGE_NOVA_GREETINGS[key]?.greeting || 'Nova ready.',
        timestamp: 'Now',
      },
    ];
  }, [messagesByPage, currentPage]);

  const sendMessage = (text: string) => {
    if (!text.trim()) return;
    const key = currentPage;
    const userMsg: NovaMessage = {
      id: `usr-${Date.now()}`,
      sender: 'user',
      text,
      timestamp: 'Just now',
    };

    const replyText = buildGroundedNovaReply(text, {
      projects,
      approvals,
      campaigns,
      creativeAssets,
      commerceOffers,
      credentials,
      distributedSystems,
      liveAreas,
    });

    setMessagesByPage(prev => ({
      ...prev,
      [key]: [...(prev[key] || messages), userMsg],
    }));
    setNovaState('thinking');

    setTimeout(() => {
      setNovaState('speaking');
      const novaMsg: NovaMessage = {
        id: `nova-${Date.now()}`,
        sender: 'nova',
        text: replyText,
        timestamp: 'Just now',
      };
      setMessagesByPage(prev => ({
        ...prev,
        [key]: [...(prev[key] || []), novaMsg],
      }));
      setTimeout(() => setNovaState('listening'), 1200);
    }, 300);
  };

  const triggerQuickAction = (action: string) => {
    sendMessage(action);
  };

  return (
    <NexusContext.Provider
      value={{
        liveStatus,
        liveAreas,
        liveGeneratedAt,
        liveFreshness,
        currentPage,
        setCurrentPage,
        searchQuery,
        setSearchQuery,
        novaState,
        setNovaState,
        isMuted,
        setIsMuted,
        isSpeakerOn,
        setIsSpeakerOn,
        messages,
        sendMessage,
        quickActions: PAGE_QUICK_ACTIONS[currentPage] || PAGE_QUICK_ACTIONS['command-center'],
        triggerQuickAction,
        isMobileNovaOpen,
        setIsMobileNovaOpen,
        isNovaDrawerOpen,
        setIsNovaDrawerOpen,
        isNewProjectModalOpen,
        setIsNewProjectModalOpen,

        projects,
        approvals,
        campaigns,
        creativeAssets,
        commerceOffers,
        researchFindings,
        notifications,
        credentials,
        labExperiments,
        upgradeCandidates,
        distributedSystems,

        nexus_get_project,
        nexus_get_project_approvals,
        pendingApprovalsCount,
        unreadNotificationsCount,

        selectedApprovalId,
        setSelectedApprovalId,
        selectedProjectId,
        setSelectedProjectId,
        selectedCampaignId,
        setSelectedCampaignId,
        selectedAssetId,
        setSelectedAssetId,
        selectedOfferId,
        setSelectedOfferId,
        navigateToObject,

        approveDecision: (id: string) => governed('Approval', approvalCommand(id)),
        rejectDecision: (id: string) => governed('Rejection', approvalCommand(id)?.replace(/^approve/i, 'reject')),
        requestRevisionDecision: (id: string) => governed('Revision request'),
        reAnalyzeDecision: (id: string) => governed('Re-analysis'),
        clydeDeepDiveDecision: id => sendMessage(`Check decision ${id}`),
        approveAllLowRiskDecisions: () => governed('Batch approval'),
        createProject: (input: CreateProjectInput) => { governed(`New objective "${input.name}"`, `Nova, start a project: ${input.name}`); return { ...createProjectDraft(input) }; },
        updateCreativeAssetStatus: () => governed('Creative decision'),
        promoteLabExperiment: () => governed('Lab promotion'),
        certifyUpgradeCandidate: () => governed('Upgrade certification'),
        updateCredentialState: () => governed('Credential change'),
        promoteResearchFinding: (id: string) => governed('Research promotion', `Nova, create a directive from research ${id}`),
        markNotificationRead,
        markAllNotificationsRead,

        approvalsList,
        setApprovalsList,
        addApprovalTicket,
        isNeedsRayDrawerOpen,
        setIsNeedsRayDrawerOpen,
        needsRayDecisions,
        addRayDecision,
        xp,
        level,
        streakDays,
        completedQuests,
        completeQuest,
        claimDailyBonus,
        hasClaimedDaily,
        isCommandCenterCompact,
        setIsCommandCenterCompact,
        isZeroScrollMode,
        setIsZeroScrollMode,
      }}
    >
      {children}
    </NexusContext.Provider>
  );
};

export const useNexus = () => {
  const ctx = useContext(NexusContext);
  if (!ctx) throw new Error('useNexus must be used within NexusProvider');
  return ctx;
};
