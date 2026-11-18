// Maps the authoritative Nexus read model into the approved Admin's existing entity shapes.
// Rule: never invent data. Missing values stay null/empty and carry UNKNOWN / NOT_CONNECTED.
import type {
  DistributedSystemNode,
  NexusApproval,
  NexusCommerceOffer,
  NexusNotification,
  NexusNotificationType,
  NexusProject,
  NexusResearchFinding,
} from '../types';
import type { CreativeAsset } from '../data/creativeMarketingData';

const arr = (v: unknown): any[] => (Array.isArray(v) ? v : []);
const str = (v: unknown, fallback = ''): string => (v === null || v === undefined ? fallback : String(v));

export const mapProjects = (a: Record<string, any>): NexusProject[] =>
  arr(a.projects).map(p => ({
    ...p,
    name: str(p.name, p.id),
    stage: str(p.stage, 'UNKNOWN'),
    nextAction: str(p.nextAction, 'UNKNOWN'),
    lastActivity: str(p.lastActivity, 'UNKNOWN'),
    workflowSteps: arr(p.workflowSteps).map(s => ({ ...s, summary: str(s.summary), timestamp: s.timestamp ?? undefined })),
    linkedApprovalIds: arr(p.linkedApprovalIds).filter(Boolean),
    linkedCampaignIds: arr(p.linkedCampaignIds),
    linkedAssetIds: arr(a.creative).filter((c: any) => c.project_id === p.id).map((c: any) => c.id),
    evidence: arr(p.evidence),
    activityLog: arr(p.activityLog).map(x => ({ ...x, timestamp: str(x.timestamp, 'UNKNOWN') })),
  })) as NexusProject[];

export const mapApprovals = (a: Record<string, any>): NexusApproval[] =>
  arr(a.approvals).map(x => ({
    ...x,
    subtitle: str(x.subtitle),
    whatIsBeingApproved: str(x.whatIsBeingApproved),
    createdAt: str(x.createdAt, 'UNKNOWN'),
    notebookRef: x.approvalCommand ? `Approve via Nova/Telegram: ${x.approvalCommand}` : undefined,
    preview: { ...(x.preview || {}), headline: str(x.preview?.headline, x.title), facts: arr(x.preview?.facts),
      body: x.approvalCommand ? `Governed approval. Decide in Telegram with: ${x.approvalCommand}` : undefined },
  })) as NexusApproval[];

export const mapCreative = (a: Record<string, any>): CreativeAsset[] =>
  arr(a.creative).map(c => ({ ...c, last_revised: str(c.last_revised, c.created_at), revisions: arr(c.revisions) })) as CreativeAsset[];

export const mapCommerce = (a: Record<string, any>): NexusCommerceOffer[] => arr(a.commerce) as NexusCommerceOffer[];

export const mapResearch = (a: Record<string, any>): NexusResearchFinding[] =>
  arr(a.research).map(r => ({
    ...r,
    title: str(r.title, r.id),
    source: str(r.source, 'UNKNOWN'),
    recommendation: str(r.recommendation, 'No summary recorded.'),
    discoveredAt: str(r.discoveredAt, 'UNKNOWN'),
    departmentDestination: 'Research',
  })) as NexusResearchFinding[];

const KNOWN_TYPES: NexusNotificationType[] = [
  'APPROVAL_REQUIRED', 'WORK_COMPLETED', 'WORK_FAILED', 'PROJECT_BLOCKED', 'PROJECT_CONTINUED',
  'CREATIVE_CREATED', 'CAMPAIGN_CREATED', 'COMMERCE_OFFER_CREATED',
];

export const mapNotifications = (a: Record<string, any>): NexusNotification[] =>
  arr(a.notifications)
    .map(n => ({
      ...n,
      // REA_* and DIRECTIVE_CREATED map onto the closest existing visual type; the title keeps the real kind.
      type: (KNOWN_TYPES.includes(n.type) ? n.type
        : String(n.type).endsWith('FAILED') ? 'WORK_FAILED'
        : String(n.type).endsWith('COMPLETED') ? 'WORK_COMPLETED' : 'PROJECT_CONTINUED') as NexusNotificationType,
      targetPage: String(n.type).startsWith('REA_') ? 'rea' : n.targetPage || 'projects',
      timestamp: str(n.timestamp, 'UNKNOWN'),
      read: false,
    }))
    .sort((x, y) => (x.timestamp < y.timestamp ? 1 : -1)) as NexusNotification[];

const SYS_STATUS: Record<string, DistributedSystemNode['status']> = {
  ONLINE: 'HEALTHY', UNKNOWN: 'NOT_CONNECTED', DEGRADED: 'DEGRADED', STOPPED: 'BLOCKED', BLOCKED: 'BLOCKED',
};

export const mapSystems = (a: Record<string, any>, generatedAt: string | null): DistributedSystemNode[] =>
  arr(a.systems).map(s => {
    const services = Object.entries(s.services || {}) as [string, string][];
    const down = services.filter(([, v]) => v !== 'RUNNING' && v !== 'ACTIVE');
    return {
      id: s.id,
      name: s.name,
      role: s.role,
      workloadPolicy: s.workloadPolicy,
      status: s.status === 'ONLINE' && down.length ? 'DEGRADED' : SYS_STATUS[s.status] || 'NOT_CONNECTED',
      truthClass: s.truthClass,
      activeServices: services.map(([k, v]) => `${k}: ${v}`),
      blocker: down.length ? down.map(([k, v]) => `${k} ${v}`).join(', ') : undefined,
      lastChecked: generatedAt || 'UNKNOWN',
    };
  });
