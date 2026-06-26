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
  | 'proposed'
  | 'paper_demo'
  | 'backtested'
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

export type NexusEnrichmentStatus =
  | 'metadata_saved'
  | 'pending_transcript'
  | 'pending_notebooklm'
  | 'enriched'
  | 'scored'
  | 'needs_review'
  | 'failed';

export type NexusEnrichmentSource =
  | 'deterministic'
  | 'transcript_capture'
  | 'notebooklm'
  | 'manual'
  | 'fallback';

export interface NexusProjectEnrichment {
  enrichment_status: NexusEnrichmentStatus;
  summary: string;
  score: number | null;
  score_label: string;
  category: string;
  destination: string;
  pros: string[];
  cons: string[];
  recommendation: string;
  proposed_schedule: string;
  next_action: string;
  confidence: number | null;
  risk_triggers: string[];
  approval_required: boolean;
  hermes_memory_summary: string;
  source_summary: string;
  enrichment_source: NexusEnrichmentSource;
  enriched_at: string | null;
  reviewed_at: string | null;
  proof_event_id: string | null;
}

export interface NexusDepartmentFeederOutput {
  feeder_id: string;
  department: NexusDepartment;
  project_type: string;
  title: string;
  summary: string;
  score: number | null;
  pros: string[];
  cons: string[];
  recommendation: string;
  proposed_schedule: string;
  next_action: string;
  source_url: string | null;
  source_title: string | null;
  data_sources: string[];
  risk_triggers: string[];
  approval_required: boolean;
  status: NexusProjectStatus;
  proof_event_type: string;
  metadata: Record<string, unknown>;
}

export interface NexusProject {
  project_id: string;
  title: string;
  department: NexusDepartment;
  owner_tab: string;
  project_type: string;
  status: NexusProjectStatus;
  score: number | null;
  score_label: string;
  priority: NexusProjectPriority;
  enrichment_status: NexusEnrichmentStatus;
  enrichment_source: NexusEnrichmentSource;
  confidence: number | null;
  summary: string;
  pros: string[];
  cons: string[];
  recommendation: string;
  proposed_changes: string[];
  proposed_schedule: string;
  next_action: string;
  hermes_memory_summary: string;
  category: string;
  destination: string;
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
  enriched_at: string | null;
  reviewed_at: string | null;
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
  'proposed',
  'paper_demo',
  'backtested',
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
  goclear: {
    department: 'opportunity_lab',
    tabId: 'goclear',
    title: 'GoClear / Apex Revenue Hub',
    subtitle: 'Readiness-review leads, revenue metrics, partner referrals, and safe next actions.',
    emptyFeed: 'goclear_revenue_hub_feeder, partner_offers, client_recommendations, and safe revenue reports',
    actions: [
      { key: 'report', label: 'Create Report', category: 'safe', description: 'Create an internal revenue snapshot.' },
      { key: 'task', label: 'Create Task', category: 'safe', description: 'Create an internal follow-up task.' },
      { key: 'opportunity', label: 'Send to Opportunity Lab', category: 'safe', description: 'Route as monetization review.' },
      { key: 'creative', label: 'Send to Creative', category: 'safe', description: 'Draft creative only.' },
      { key: 'connector', label: 'Configure Connector', category: 'approval', description: 'Revenue/affiliate connectors require approval.' },
      { key: 'park', label: 'Park', category: 'safe', description: 'Park the revenue signal.' },
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
  trading: {
    department: 'trading_lab',
    tabId: 'trading',
    title: 'Demo Research Department',
    subtitle: 'Paper-only strategy research, backtests, risk notes, and proof.',
    emptyFeed: 'Vibe Trading paper reports, backtests, strategy candidates, and paper demo journals',
    actions: [
      { key: 'backtest', label: 'Run Backtest', category: 'disabled', description: 'Not connected yet; adapter only reports safe command templates.' },
      { key: 'report', label: 'Generate Report', category: 'safe', description: 'Create internal paper-only research report task.' },
      { key: 'task', label: 'Create Task', category: 'safe', description: 'Create internal research task.' },
      { key: 'ops', label: 'Send to Ops', category: 'safe', description: 'Route safety/process follow-up to Ops.' },
      { key: 'paper_demo', label: 'Paper Demo Only', category: 'safe', description: 'Mark as paper/demo research only.' },
      { key: 'park', label: 'Park Strategy', category: 'safe', description: 'Park the strategy research card.' },
    ],
  },
  command: {
    department: 'command_center',
    tabId: 'command',
    title: 'Executive Office',
    subtitle: 'Department summary, risk alerts, next decisions, and feeder status.',
    emptyFeed: 'department project cards, approvals, nexus_events, and feeder summaries',
    actions: [
      { key: 'review', label: 'Review Summary', category: 'safe', description: 'Review the executive summary card.' },
      { key: 'decision', label: 'Next Decision', category: 'safe', description: 'Create an internal decision follow-up.' },
      { key: 'schedule', label: 'Schedule Later', category: 'approval', description: 'Scheduler activation requires approval.' },
      { key: 'park', label: 'Park', category: 'safe', description: 'Park the summary.' },
    ],
  },
  approvals: {
    department: 'approvals',
    tabId: 'approvals',
    title: 'Decision Desk',
    subtitle: 'Approval-required work and advisory decision items.',
    emptyFeed: 'approvals and approval-required task_requests',
    actions: [
      { key: 'review', label: 'Review', category: 'safe', description: 'Review approval context.' },
      { key: 'changes', label: 'Request Changes', category: 'safe', description: 'Create advisory change request.' },
      { key: 'approval', label: 'Approve / Reject', category: 'approval', description: 'Human decision only in the Approvals tab.' },
      { key: 'park', label: 'Park', category: 'safe', description: 'Park advisory card.' },
    ],
  },
  events: {
    department: 'events_feed',
    tabId: 'events',
    title: 'Proof / History Ledger',
    subtitle: 'Summaries of proof events and department history.',
    emptyFeed: 'nexus_events and feeder proof rows',
    actions: [
      { key: 'proof', label: 'View Proof', category: 'safe', description: 'Review proof context.' },
      { key: 'report', label: 'Create Report', category: 'safe', description: 'Create internal proof summary.' },
      { key: 'park', label: 'Park', category: 'safe', description: 'Park the ledger item.' },
    ],
  },
  integrations: {
    department: 'integrations',
    tabId: 'integrations',
    title: 'Connections Department',
    subtitle: 'Connector readiness, health, and configuration next actions.',
    emptyFeed: 'integration_registry, system_health, and safe watch reports',
    actions: [
      { key: 'review', label: 'Review Status', category: 'safe', description: 'Review connector status.' },
      { key: 'task', label: 'Create Task', category: 'safe', description: 'Create internal configuration follow-up.' },
      { key: 'approval', label: 'Approve Config', category: 'approval', description: 'Connector enablement requires approval.' },
      { key: 'park', label: 'Park', category: 'safe', description: 'Park connector follow-up.' },
    ],
  },
};
