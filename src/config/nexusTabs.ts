/**
 * Canonical tab status model for Nexus OS v2.
 *
 * Single source of truth for what each tab really is: its data source, the Supabase tables/scripts
 * behind it, any v1 (Mac Mini) process dependency, action capability, required safety gates, and a
 * connection status. The UI reads this to render honest status badges + a per-tab Connection Status
 * panel. Nothing here controls v1 workers — it only describes/observes them.
 *
 * Derived from the audits in docs/operations/ (esp. NEXUS_MACMINI_PROCESS_SCHEDULE_AUDIT.md,
 * NEXUS_V1_TO_V2_MIGRATION_WRAP_PLAN.md, NEXUS_TAB_CONNECTION_MATRIX.md).
 */

export type TabStatus =
  | 'live_connected'          // real v2 tables/scripts, works now
  | 'partial_connected'       // some live data, some not-yet-wired
  | 'manual_cli_backed'       // works via an approved CLI script, no UI submission yet
  | 'v1_available_not_wrapped'// a useful v1 worker exists but v2 doesn't control it yet
  | 'scaffold_only'           // table exists but no workflow/seed yet
  | 'hide_until_ready'        // not real/too risky to show as primary
  | 'deprecated';

export type RiskLevel = 'low' | 'medium' | 'high';

export interface TabConfig {
  id: string;                 // matches Shell NAV key (or a planned id)
  label: string;
  route: string;              // sidebar key
  status: TabStatus;
  statusLabel: string;        // short badge text
  description: string;        // user-facing purpose
  dataSources: string[];
  tables: string[];
  scripts: string[];
  v1Dependencies: string[];
  v2Dependencies: string[];
  actions: string[];          // what the user can safely do here
  hermesCan: string;          // what Hermes may do with this tab
  riskLevel: RiskLevel;
  visible: boolean;
  disabledReason?: string;
  recommendedNextAction: string;
}

const BADGE: Record<TabStatus, string> = {
  live_connected: 'Live',
  partial_connected: 'Partial',
  manual_cli_backed: 'Manual',
  v1_available_not_wrapped: 'Legacy',
  scaffold_only: 'Seed',
  hide_until_ready: 'Hidden',
  deprecated: 'Deprecated',
};

export function badgeFor(status: TabStatus): string {
  return BADGE[status];
}

export const NEXUS_TABS: TabConfig[] = [
  {
    id: 'command', label: 'Command Center', route: 'command', status: 'partial_connected',
    statusLabel: 'Partial', description: 'Hermes advisor + system overview of all tabs.',
    dataSources: ['Hermes Edge Function', 'Supabase counts'], tables: ['approvals', 'agent_jobs', 'ops_incidents', 'creative_campaigns', 'nexus_events'],
    scripts: [], v1Dependencies: [], v2Dependencies: ['hermes-chat Edge Function', 'nexusTabs config'],
    actions: ['chat with Hermes', 'create approval-gated task_request', 'open related tab', 'read safe reports'],
    hermesCan: 'converse, read safe context, propose approval-gated task_requests; never execute risky actions',
    riskLevel: 'low', visible: true,
    recommendedNextAction: 'Surface tab/system status + failing v1 jobs as the overview.',
  },
  {
    id: 'health', label: 'System Health', route: 'health', status: 'live_connected', statusLabel: 'Live',
    description: 'Live component status.', dataSources: ['Supabase'], tables: ['system_health'], scripts: ['nexus:watch'],
    v1Dependencies: [], v2Dependencies: ['system_health table'], actions: ['read component health'],
    hermesCan: 'summarize health in plain English', riskLevel: 'low', visible: true,
    recommendedNextAction: 'None — connected.',
  },
  {
    id: 'jobs', label: 'Agent Jobs', route: 'jobs', status: 'live_connected', statusLabel: 'Live',
    description: 'Agents + bounded job runner.', dataSources: ['Supabase'], tables: ['agent_jobs', 'agent_registry'],
    scripts: ['scripts/nexus_runner.py'], v1Dependencies: [], v2Dependencies: ['agent_jobs table'],
    actions: ['view jobs/agents', 'queue allowlisted dry-run job'], hermesCan: 'report job status; propose jobs via approval',
    riskLevel: 'low', visible: true, recommendedNextAction: 'None — connected.',
  },
  {
    id: 'approvals', label: 'Approvals', route: 'approvals', status: 'live_connected', statusLabel: 'Live',
    description: 'Approve / reject / request changes.', dataSources: ['Supabase (admin RLS)'], tables: ['approvals', 'social_posts'],
    scripts: [], v1Dependencies: [], v2Dependencies: ['admin session (persistSession fix)'],
    actions: ['approve', 'reject', 'request changes', 'queue dry-run publish job'],
    hermesCan: 'list/explain pending approvals; cannot approve via chat (UI only)', riskLevel: 'medium', visible: true,
    recommendedNextAction: 'None — connected. Approve = sign-off record only; never publishes.',
  },
  {
    id: 'goclear', label: 'GoClear / Apex', route: 'goclear', status: 'partial_connected', statusLabel: 'Partial',
    description: 'Funding readiness workspace / $97 revenue hub.', dataSources: ['Supabase'], tables: ['partner_offers', 'client_recommendations', 'monetization_opportunities'],
    scripts: ['nexus:watch'], v1Dependencies: [], v2Dependencies: ['landing page (nexusv20.netlify.app)'],
    actions: ['view offers/recommendations'], hermesCan: 'advise on the $97 readiness funnel (no guarantees)',
    riskLevel: 'low', visible: true, recommendedNextAction: 'Seed offers + wire $97 intake/checkout backend.',
  },
  {
    id: 'opportunities', label: 'Opportunity Lab', route: 'opportunities', status: 'partial_connected', statusLabel: 'Partial',
    description: 'Money ideas, scored.', dataSources: ['Supabase'], tables: ['monetization_opportunities'], scripts: [],
    v1Dependencies: ['monetization-research worker'], v2Dependencies: ['canonical rating model v1'],
    actions: ['view scored opportunities'], hermesCan: 'rank/explain opportunities; propose next test', riskLevel: 'low', visible: true,
    recommendedNextAction: 'Mirror v1 monetization-research output into v2 monetization_opportunities.',
  },
  {
    id: 'intake', label: 'Source Intake & Review', route: 'intake', status: 'manual_cli_backed', statusLabel: 'Manual',
    description: 'Transcripts/sources → deterministic review → destination.', dataSources: ['Supabase + CLI wrapper'],
    tables: ['research_sources', 'intake_events', 'transcript_reviews', 'dispositions'],
    scripts: ['scripts/intake/run_existing_youtube_monitor.py'], v1Dependencies: ['research-engine/collector.py (yt-dlp)'],
    v2Dependencies: ['canonical rating model v1'], actions: ['view captured sources/reviews', '(CLI) run approved dry-run/capture'],
    hermesCan: 'explain a source review + recommended destination', riskLevel: 'medium', visible: true,
    recommendedNextAction: 'Run one approved YouTube capture into v2 tables, then add a URL-submit UI.',
  },
  {
    id: 'creative', label: 'Creative Studio', route: 'creative', status: 'live_connected', statusLabel: 'Live',
    description: 'Campaigns, briefs, design dept, publish packages.', dataSources: ['Supabase'],
    tables: ['creative_campaigns', 'creative_briefs', 'creative_assets', 'creative_scores', 'publish_readiness_packages'],
    scripts: ['nexus:watch'], v1Dependencies: ['content_employee (legacy)'], v2Dependencies: ['creative tables'],
    actions: ['view campaigns/assets/scores', 'review publish packages'], hermesCan: 'critique creative; propose drafts via approval',
    riskLevel: 'low', visible: true, recommendedNextAction: 'None — connected (publishing stays gated).',
  },
  {
    id: 'design', label: 'Design Library', route: 'design', status: 'live_connected', statusLabel: 'Live',
    description: 'Inspiration, patterns, UI quality.', dataSources: ['Supabase'],
    tables: ['design_inspiration_sources', 'design_pattern_registry', 'feature_design_packets', 'ui_quality_reviews'],
    scripts: [], v1Dependencies: [], v2Dependencies: ['design tables'], actions: ['browse inspiration/patterns/reviews'],
    hermesCan: 'reference design patterns', riskLevel: 'low', visible: true, recommendedNextAction: 'None — connected.',
  },
  {
    id: 'trading', label: 'Trading Lab', route: 'trading', status: 'v1_available_not_wrapped', statusLabel: 'Demo/Legacy',
    description: 'Strategy research/testing — display only, no live trading from UI.', dataSources: ['Supabase (read)'],
    tables: ['trading_strategy_candidates', 'trading_risk_rules'], scripts: [],
    v1Dependencies: ['nexus_trading_engine.py', 'auto_executor.py (trade-capable)', 'tournament_service.py'],
    v2Dependencies: [], actions: ['view candidates/risk rules (read-only)'],
    hermesCan: 'discuss strategy research only; never trigger trades', riskLevel: 'high', visible: true,
    disabledReason: 'Live trading / auto_executor are v1 action-capable workers — never raw-exposed in v2 UI.',
    recommendedNextAction: 'Show v1 trading worker status read-only (demo posture); keep execution out of UI.',
  },
  {
    id: 'seo', label: 'SEO / Marketing', route: 'seo', status: 'scaffold_only', statusLabel: 'Seed',
    description: 'Sites + SEO opportunities.', dataSources: ['Supabase'], tables: ['seo_sites', 'seo_opportunities'], scripts: [],
    v1Dependencies: [], v2Dependencies: ['seo tables (empty)'], actions: ['view (empty until seeded)'],
    hermesCan: 'suggest SEO opportunities (public)', riskLevel: 'low', visible: true,
    recommendedNextAction: 'Seed seo_sites/seo_opportunities before showing as primary.',
  },
  {
    id: 'models', label: 'Model Router', route: 'models', status: 'live_connected', statusLabel: 'Live',
    description: 'AI providers + routes.', dataSources: ['Supabase'], tables: ['model_providers', 'model_routes', 'agent_registry'],
    scripts: ['scripts/model_router.py'], v1Dependencies: [], v2Dependencies: ['model tables'],
    actions: ['view providers/routes'], hermesCan: 'explain routing decisions', riskLevel: 'low', visible: true,
    recommendedNextAction: 'None — connected.',
  },
  {
    id: 'integrations', label: 'Integrations', route: 'integrations', status: 'partial_connected', statusLabel: 'Partial',
    description: 'Registered integrations (status only).', dataSources: ['Supabase'], tables: ['model_providers'], scripts: ['nexus:watch'],
    v1Dependencies: ['cloudflared tunnels', 'hermes gateway'], v2Dependencies: [], actions: ['view connection status (names only)'],
    hermesCan: 'report which integrations are connected', riskLevel: 'medium', visible: true,
    recommendedNextAction: 'Status-only; never expose keys. Show env presence by name.',
  },
  {
    id: 'ops', label: 'Ops & Improvements', route: 'ops', status: 'live_connected', statusLabel: 'Live',
    description: 'Self-healing + improvements + legacy fleet status.', dataSources: ['Supabase + read-only fleet'],
    tables: ['ops_incidents', 'improvement_candidates', 'nexus_events'], scripts: ['nexus:watch'],
    v1Dependencies: ['operations_center/scheduler.py', 'cron workers'], v2Dependencies: [],
    actions: ['view incidents/improvements', 'view detected legacy workers (read-only)'],
    hermesCan: 'summarize ops health + failing legacy jobs', riskLevel: 'medium', visible: true,
    recommendedNextAction: 'Surface read-only v1 fleet status (incl. failing jobs).',
  },
  {
    id: 'events', label: 'Events Feed', route: 'events', status: 'live_connected', statusLabel: 'Live',
    description: 'Proof log.', dataSources: ['Supabase'], tables: ['nexus_events'], scripts: [],
    v1Dependencies: [], v2Dependencies: ['nexus_events'], actions: ['read proof events'],
    hermesCan: 'cite proof events', riskLevel: 'low', visible: true, recommendedNextAction: 'None — connected.',
  },
  // ── Planned / not-yet-primary (documented; not in the live sidebar) ──
  {
    id: 'memory', label: 'Memory / Knowledge', route: 'memory', status: 'scaffold_only', statusLabel: 'Coming Soon',
    description: 'Durable lessons / knowledge.', dataSources: ['Supabase'], tables: ['nexus_lessons'], scripts: [],
    v1Dependencies: ['memory_engine.memory_worker (cron)'], v2Dependencies: [], actions: [],
    hermesCan: 'recall safe lessons', riskLevel: 'low', visible: false,
    disabledReason: 'No dedicated tab yet; lessons sparse.', recommendedNextAction: 'Add a Knowledge tab once seeded.',
  },
];

export function tabById(id: string): TabConfig | undefined {
  return NEXUS_TABS.find((t) => t.id === id);
}

// ── Detected v1 (Mac Mini) legacy workers — OBSERVED, never controlled by v2 ──
export interface LegacyWorker {
  name: string;
  kind: 'process' | 'launchd' | 'cron';
  role: string;
  status: 'running' | 'failing' | 'scheduled';
  actionCapable: boolean;     // if true: never expose raw control in the UI
  wrapCandidate: boolean;
  note?: string;
}

export const V1_FLEET: LegacyWorker[] = [
  { name: 'research-engine / youtube-channel-poller', kind: 'launchd', role: 'YouTube/transcript capture (yt-dlp)', status: 'scheduled', actionCapable: false, wrapCandidate: true, note: 'Wrap into v2 (write v2 tables).' },
  { name: 'nexus-research-worker', kind: 'process', role: 'research → signals/opportunities', status: 'running', actionCapable: false, wrapCandidate: true },
  { name: 'mac-mini-worker.js', kind: 'process', role: 'task execution bridge', status: 'running', actionCapable: true, wrapCandidate: false, note: 'Never expose raw control in UI.' },
  { name: 'nexus_trading_engine.py', kind: 'process', role: 'trading engine', status: 'running', actionCapable: true, wrapCandidate: false, note: 'Trade-capable — never raw-exposed.' },
  { name: 'auto_executor.py', kind: 'process', role: 'auto trade executor', status: 'running', actionCapable: true, wrapCandidate: false, note: 'Trade-capable — never raw-exposed.' },
  { name: 'operations_center/scheduler.py', kind: 'process', role: 'v1 ops scheduler', status: 'running', actionCapable: true, wrapCandidate: false, note: 'Do not duplicate with a v2 scheduler.' },
  { name: 'hermes gateway', kind: 'process', role: 'Hermes gateway/adapter', status: 'running', actionCapable: true, wrapCandidate: false },
  { name: 'continuous-ops-daily', kind: 'launchd', role: 'daily ops', status: 'failing', actionCapable: false, wrapCandidate: false, note: 'Last exit 1 — failing (documented, not fixed).' },
  { name: 'cf.hermes.gateway', kind: 'launchd', role: 'cloudflared hermes tunnel', status: 'failing', actionCapable: false, wrapCandidate: false, note: 'Last exit 11 — failing (documented, not fixed).' },
];
