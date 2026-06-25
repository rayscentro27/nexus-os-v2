export type NexusDepartment =
  | 'command_center'
  | 'source_intake'
  | 'opportunity_lab'
  | 'design_library'
  | 'creative_studio'
  | 'growth'
  | 'ops_improvements'
  | 'agent_jobs'
  | 'approvals'
  | 'events_feed'
  | 'integrations'
  | 'trading_lab';

export type NexusProjectStatus =
  | 'researching'
  | 'summarized'
  | 'scored'
  | 'needs_review'
  | 'approved'
  | 'scheduled'
  | 'implementing'
  | 'done'
  | 'parked'
  | 'rejected'
  | 'blocked';

export type NexusProjectPriority = 'low' | 'medium' | 'high' | 'urgent';

export interface NexusProject {
  project_id: string;
  title: string;
  department: NexusDepartment;
  owner_tab: string;
  project_type: string;
  status: NexusProjectStatus;
  score: number | null;
  priority: NexusProjectPriority;
  summary: string;
  pros: string[];
  cons: string[];
  recommendation: string;
  proposed_changes: string[];
  proposed_schedule: string;
  next_action: string;
  approval_required: boolean;
  feedback_requested: boolean;
  risk_triggers: string[];
  visual_url: string | null;
  source_url: string | null;
  source_title: string | null;
  data_sources: string[];
  related_process_id: string | null;
  related_task_request_id: string | null;
  related_approval_id: string | null;
  proof_event_id: string | null;
  created_at: string;
  updated_at: string;
  raw?: Record<string, unknown>;
}

export interface DepartmentAction {
  key: string;
  label: string;
  category: 'safe' | 'approval' | 'disabled';
  description: string;
}

export interface DepartmentWorkspaceConfig {
  department: NexusDepartment;
  tabId: string;
  title: string;
  subtitle: string;
  emptyFeed: string;
  actions: DepartmentAction[];
}

export const PROJECT_STATUSES: NexusProjectStatus[] = [
  'researching',
  'summarized',
  'scored',
  'needs_review',
  'approved',
  'scheduled',
  'implementing',
  'done',
  'parked',
  'rejected',
  'blocked',
];

export const DEPARTMENT_WORKSPACES: Record<string, DepartmentWorkspaceConfig> = {
  intake: {
    department: 'source_intake',
    tabId: 'intake',
    title: 'Research Intake Department',
    subtitle: 'Instant source capture, review metadata, and enrichment follow-up.',
    emptyFeed: 'research_sources, intake_events, transcript_reviews, and safe capture requests',
    actions: [
      { key: 'analyze', label: 'Analyze', category: 'safe', description: 'Create safe analysis work for the selected source.' },
      { key: 'report', label: 'Create Report', category: 'safe', description: 'Create an internal report task.' },
      { key: 'opportunity', label: 'Send to Opportunity Lab', category: 'safe', description: 'Route the source as an opportunity candidate.' },
      { key: 'creative', label: 'Send to Creative', category: 'safe', description: 'Route the source as draft creative inspiration.' },
      { key: 'research', label: 'Request More Research', category: 'safe', description: 'Ask for more public/internal research.' },
      { key: 'summary', label: 'Generate Summary', category: 'disabled', description: 'Not connected yet.' },
      { key: 'research_only', label: 'Mark Research Only', category: 'safe', description: 'Keep this as reference material.' },
      { key: 'park', label: 'Park', category: 'safe', description: 'Move it out of active work.' },
    ],
  },
  opportunities: {
    department: 'opportunity_lab',
    tabId: 'opportunities',
    title: 'Revenue / Opportunity Department',
    subtitle: 'Money ideas, service offers, affiliate paths, and smallest tests.',
    emptyFeed: 'monetization_opportunities and source-to-opportunity extraction',
    actions: [
      { key: 'analyze', label: 'Analyze', category: 'safe', description: 'Create an opportunity analysis task.' },
      { key: 'report', label: 'Create Report', category: 'safe', description: 'Draft a monetization report.' },
      { key: 'task', label: 'Create Task', category: 'safe', description: 'Create an internal implementation task.' },
      { key: 'schedule', label: 'Propose Schedule', category: 'safe', description: 'Draft a schedule only.' },
      { key: 'creative', label: 'Send to Creative', category: 'safe', description: 'Route to Creative Studio.' },
      { key: 'approval', label: 'Approve / Queue', category: 'approval', description: 'Only for risky or client-facing next actions.' },
      { key: 'park', label: 'Park', category: 'safe', description: 'Park the opportunity.' },
      { key: 'reject', label: 'Reject', category: 'safe', description: 'Reject as internal disposition.' },
    ],
  },
  design: {
    department: 'design_library',
    tabId: 'design',
    title: 'Design / Asset Department',
    subtitle: 'Reference designs, patterns, packets, reviews, and asset decisions.',
    emptyFeed: 'design inspiration, design pattern registry, feature packets, and UI quality reviews',
    actions: [
      { key: 'creative', label: 'Send to Creative', category: 'safe', description: 'Use as draft creative reference.' },
      { key: 'campaign', label: 'Create Campaign', category: 'safe', description: 'Create an internal campaign task.' },
      { key: 'approve_asset', label: 'Approve Asset', category: 'approval', description: 'Approval record only when required.' },
      { key: 'changes', label: 'Request Changes', category: 'safe', description: 'Create a revision request.' },
      { key: 'deck', label: 'Generate Slide Deck', category: 'disabled', description: 'Not connected yet.' },
      { key: 'park', label: 'Park', category: 'safe', description: 'Park the asset.' },
    ],
  },
  creative: {
    department: 'creative_studio',
    tabId: 'creative',
    title: 'Campaign / Creative Department',
    subtitle: 'Campaigns, briefs, draft assets, social drafts, and readiness packages.',
    emptyFeed: 'creative campaigns, briefs, assets, scores, and publish readiness packages',
    actions: [
      { key: 'draft', label: 'Generate Draft', category: 'safe', description: 'Queue draft creation only.' },
      { key: 'revise', label: 'Revise', category: 'safe', description: 'Create a revision request.' },
      { key: 'social', label: 'Generate Social Draft', category: 'safe', description: 'Create draft social copy only.' },
      { key: 'approval', label: 'Send for Approval', category: 'approval', description: 'Needed before publish/send/client-facing use.' },
      { key: 'design', label: 'Send to Design Library', category: 'safe', description: 'Route as an asset/design reference.' },
      { key: 'park', label: 'Park', category: 'safe', description: 'Park the creative item.' },
    ],
  },
  seo: {
    department: 'growth',
    tabId: 'seo',
    title: 'Growth Department',
    subtitle: 'SEO opportunities, content projects, keywords, and marketing next actions.',
    emptyFeed: 'seo_sites, seo_opportunities, and future marketing scanners',
    actions: [
      { key: 'article', label: 'Create Article Draft', category: 'safe', description: 'Create internal draft task.' },
      { key: 'report', label: 'Create Report', category: 'safe', description: 'Draft a growth report.' },
      { key: 'schedule', label: 'Schedule', category: 'approval', description: 'Scheduler activation requires approval.' },
      { key: 'creative', label: 'Send to Creative', category: 'safe', description: 'Route to Creative Studio.' },
      { key: 'research', label: 'Request More Research', category: 'safe', description: 'Ask for more public research.' },
      { key: 'park', label: 'Park', category: 'safe', description: 'Park the item.' },
    ],
  },
  ops: {
    department: 'ops_improvements',
    tabId: 'ops',
    title: 'System Improvement Department',
    subtitle: 'Incidents, improvement candidates, process health, and implementation plans.',
    emptyFeed: 'ops_incidents, improvement_candidates, process registry refresh, and health scans',
    actions: [
      { key: 'task', label: 'Create Implementation Task', category: 'safe', description: 'Create internal task request.' },
      { key: 'schedule', label: 'Schedule', category: 'approval', description: 'Scheduler activation requires approval.' },
      { key: 'research', label: 'Request More Research', category: 'safe', description: 'Research the fix safely.' },
      { key: 'dry_run', label: 'Dry-run Plan', category: 'safe', description: 'Plan/dry-run only.' },
      { key: 'park', label: 'Park', category: 'safe', description: 'Park the item.' },
    ],
  },
  jobs: {
    department: 'agent_jobs',
    tabId: 'jobs',
    title: 'Automation Workforce Department',
    subtitle: 'Jobs, agents, dry-run work, proof, and process status.',
    emptyFeed: 'agent_jobs, agent_registry, task_requests, and process registry refresh',
    actions: [
      { key: 'dry_run', label: 'Rerun Dry-run', category: 'safe', description: 'Create dry-run work only.' },
      { key: 'task', label: 'Create Task', category: 'safe', description: 'Create internal task request.' },
      { key: 'proof', label: 'View Proof', category: 'safe', description: 'Open linked proof when present.' },
      { key: 'schedule', label: 'Schedule Later', category: 'approval', description: 'Scheduler activation requires approval.' },
      { key: 'park', label: 'Park', category: 'safe', description: 'Park the job review.' },
    ],
  },
};
