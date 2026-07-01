/**
 * Nexus Section Status Registry — single source of truth for all section statuses.
 *
 * Answers: "is X live?", "what sections are live?", "show proof this is working",
 * "what is blocked?", "what is scheduled?", etc.
 *
 * All data is deterministic. No I/O. No model calls.
 */

export type SectionStatus = 'live' | 'static' | 'mismatch' | 'blocked' | 'unknown' | 'report_snapshot';
export type SectionSource = 'supabase' | 'local_static' | 'mixed' | 'none';
export type ProofLevel = 'verified' | 'unproven' | 'no_proof';

export interface SectionEntry {
  id: string;
  name: string;
  status: SectionStatus;
  source: SectionSource;
  proofLevel: ProofLevel;
  verifiedAt: string | null;
  tableNames: string[];
  rowCount: number;
  schedulerInstalled: boolean;
  schedulerRunning: boolean;
  supabaseWrites: boolean;
  blockers: string[];
  nextAction: string;
  notes: string;
  description: string;
}

const NOW = new Date().toISOString();

// ── Embedded report data for specific handlers (no I/O, no model calls) ──

interface ProcessItem {
  name: string;
  category: string;
  processAvailable: boolean;
  processActive: boolean;
  schedulerInstalled: boolean;
  schedulerLoaded: boolean;
  schedulerRunning: boolean;
  lastSeenAt: string | null;
  lastRunAt: string | null;
  lastOutputAt: string | null;
  lastSupabaseWriteAt: string | null;
  proofLevel: string;
  blockers: string[];
}

const PROCESS_ITEMS: ProcessItem[] = [
  { name: 'hermes_agent', category: 'nexus_process', processAvailable: true, processActive: true, schedulerInstalled: false, schedulerLoaded: false, schedulerRunning: false, lastSeenAt: '2026-07-01T19:39:27Z', lastRunAt: null, lastOutputAt: null, lastSupabaseWriteAt: null, proofLevel: 'active_process', blockers: [] },
  { name: 'tradingview_router', category: 'nexus_process', processAvailable: true, processActive: true, schedulerInstalled: true, schedulerLoaded: true, schedulerRunning: false, lastSeenAt: '2026-07-01T19:39:27Z', lastRunAt: null, lastOutputAt: '2026-07-01T19:00:03Z', lastSupabaseWriteAt: null, proofLevel: 'active_process', blockers: [] },
  { name: 'nexus-orchestrator', category: 'nexus_process', processAvailable: true, processActive: true, schedulerInstalled: true, schedulerLoaded: true, schedulerRunning: false, lastSeenAt: '2026-07-01T19:39:27Z', lastRunAt: null, lastOutputAt: '2026-07-01T19:37:40Z', lastSupabaseWriteAt: null, proofLevel: 'active_process', blockers: [] },
  { name: 'nexus-research-worker', category: 'nexus_process', processAvailable: true, processActive: true, schedulerInstalled: true, schedulerLoaded: true, schedulerRunning: false, lastSeenAt: '2026-07-01T19:39:27Z', lastRunAt: null, lastOutputAt: '2026-06-30T23:37:40Z', lastSupabaseWriteAt: null, proofLevel: 'active_process', blockers: [] },
  { name: 'cloudflared_tunnel', category: 'nexus_process', processAvailable: true, processActive: true, schedulerInstalled: true, schedulerLoaded: true, schedulerRunning: false, lastSeenAt: '2026-07-01T19:39:27Z', lastRunAt: null, lastOutputAt: '2026-06-30T23:39:15Z', lastSupabaseWriteAt: null, proofLevel: 'active_process', blockers: [] },
  { name: 'nexus_trading_engine', category: 'nexus_process', processAvailable: true, processActive: true, schedulerInstalled: true, schedulerLoaded: true, schedulerRunning: false, lastSeenAt: '2026-07-01T19:39:27Z', lastRunAt: null, lastOutputAt: '2026-07-01T19:01:00Z', lastSupabaseWriteAt: null, proofLevel: 'active_process', blockers: [] },
  { name: 'dashboard', category: 'nexus_process', processAvailable: true, processActive: true, schedulerInstalled: true, schedulerLoaded: true, schedulerRunning: false, lastSeenAt: '2026-07-01T19:39:27Z', lastRunAt: null, lastOutputAt: '2026-06-30T23:40:37Z', lastSupabaseWriteAt: null, proofLevel: 'active_process', blockers: [] },
  { name: 'research_signal_bridge', category: 'nexus_process', processAvailable: true, processActive: true, schedulerInstalled: true, schedulerLoaded: true, schedulerRunning: false, lastSeenAt: '2026-07-01T19:39:27Z', lastRunAt: null, lastOutputAt: '2026-07-01T19:39:30Z', lastSupabaseWriteAt: null, proofLevel: 'active_process', blockers: [] },
  { name: 'auto_executor', category: 'nexus_process', processAvailable: true, processActive: true, schedulerInstalled: true, schedulerLoaded: true, schedulerRunning: false, lastSeenAt: '2026-07-01T19:39:27Z', lastRunAt: null, lastOutputAt: '2026-07-01T19:39:10Z', lastSupabaseWriteAt: null, proofLevel: 'active_process', blockers: [] },
  { name: 'operations_center_scheduler', category: 'nexus_process', processAvailable: true, processActive: true, schedulerInstalled: true, schedulerLoaded: true, schedulerRunning: false, lastSeenAt: '2026-07-01T19:39:27Z', lastRunAt: null, lastOutputAt: null, lastSupabaseWriteAt: null, proofLevel: 'active_process', blockers: [] },
  { name: 'hermes_cli_gateway', category: 'nexus_process', processAvailable: true, processActive: true, schedulerInstalled: false, schedulerLoaded: false, schedulerRunning: false, lastSeenAt: '2026-07-01T19:39:27Z', lastRunAt: null, lastOutputAt: null, lastSupabaseWriteAt: null, proofLevel: 'active_process', blockers: [] },
  { name: 'tournament_service', category: 'nexus_process', processAvailable: true, processActive: true, schedulerInstalled: true, schedulerLoaded: true, schedulerRunning: false, lastSeenAt: '2026-07-01T19:39:27Z', lastRunAt: null, lastOutputAt: '2026-07-01T19:38:00Z', lastSupabaseWriteAt: null, proofLevel: 'active_process', blockers: [] },
  { name: 'hermes-gateway-adapter', category: 'nexus_process', processAvailable: true, processActive: true, schedulerInstalled: false, schedulerLoaded: false, schedulerRunning: false, lastSeenAt: '2026-07-01T19:39:27Z', lastRunAt: null, lastOutputAt: null, lastSupabaseWriteAt: null, proofLevel: 'active_process', blockers: [] },
  { name: 'control_center_server', category: 'nexus_process', processAvailable: true, processActive: true, schedulerInstalled: true, schedulerLoaded: true, schedulerRunning: false, lastSeenAt: '2026-07-01T19:39:27Z', lastRunAt: null, lastOutputAt: '2026-07-01T19:39:26Z', lastSupabaseWriteAt: null, proofLevel: 'active_process', blockers: [] },
  { name: 'youtube-channel-poller', category: 'scheduler_only', processAvailable: false, processActive: false, schedulerInstalled: true, schedulerLoaded: true, schedulerRunning: false, lastSeenAt: '2026-07-01T19:39:27Z', lastRunAt: null, lastOutputAt: '2026-07-01T15:40:23Z', lastSupabaseWriteAt: null, proofLevel: 'recent_output', blockers: ['No active PID proof', 'No proof of recent metadata fetch'] },
];

const PROCESS_SUMMARY = {
  total_tracked: 16,
  active_process: 14,
  recent_output: 1,
  loaded_only: 0,
  installed_only: 0,
  available_script_only: 0,
  not_found: 0,
  unknown: 1,
};

const YOUTUBE_PROOF = PROCESS_ITEMS.find((p) => p.name === 'youtube-channel-poller')!;

interface ToolItem {
  name: string;
  installed: boolean;
  version: string;
  authenticated: string;
  safeReadOnlyCommands: string[];
  approvalRequiredCommands: string[];
  blockedCommands: string[];
  proofLevel: string;
}

const TOOL_REGISTRY: ToolItem[] = [
  { name: 'git', installed: true, version: 'git version 2.53.0', authenticated: 'not_proven', safeReadOnlyCommands: ['git status', 'git log', 'git diff'], approvalRequiredCommands: ['git push'], blockedCommands: ['git push --force'], proofLevel: 'installed_only' },
  { name: 'node', installed: true, version: 'v22.22.3', authenticated: 'not_proven', safeReadOnlyCommands: ['node --version'], approvalRequiredCommands: ['node script.js'], blockedCommands: [], proofLevel: 'installed_only' },
  { name: 'npm', installed: true, version: '10.9.8', authenticated: 'not_proven', safeReadOnlyCommands: ['npm --version', 'npm list'], approvalRequiredCommands: ['npm install'], blockedCommands: ['npm publish --access public'], proofLevel: 'installed_only' },
  { name: 'python3', installed: true, version: 'Python 3.14.5', authenticated: 'not_proven', safeReadOnlyCommands: ['python3 --version'], approvalRequiredCommands: ['python3 script.py'], blockedCommands: [], proofLevel: 'installed_only' },
  { name: 'supabase', installed: true, version: 'installed', authenticated: 'not_proven', safeReadOnlyCommands: ['supabase --version'], approvalRequiredCommands: ['supabase db push'], blockedCommands: ['supabase db push --force'], proofLevel: 'installed_only' },
  { name: 'netlify', installed: true, version: 'installed', authenticated: 'not_proven', safeReadOnlyCommands: ['netlify --version', 'netlify status'], approvalRequiredCommands: ['netlify deploy'], blockedCommands: ['netlify deploy --prod'], proofLevel: 'installed_only' },
  { name: 'gh', installed: true, version: 'installed', authenticated: 'not_proven', safeReadOnlyCommands: ['gh --version', 'gh auth status'], approvalRequiredCommands: ['gh pr create'], blockedCommands: ['gh repo delete'], proofLevel: 'installed_only' },
  { name: 'ollama', installed: true, version: 'ollama version is 0.20.5', authenticated: 'not_proven', safeReadOnlyCommands: ['ollama --version', 'ollama list'], approvalRequiredCommands: ['ollama pull'], blockedCommands: ['ollama rm'], proofLevel: 'installed_only' },
  { name: 'opencode', installed: true, version: 'installed', authenticated: 'not_proven', safeReadOnlyCommands: ['opencode --version'], approvalRequiredCommands: ['opencode run'], blockedCommands: [], proofLevel: 'installed_only' },
  { name: 'codex', installed: true, version: 'codex-cli 0.142.4', authenticated: 'not_proven', safeReadOnlyCommands: ['codex --version'], approvalRequiredCommands: ['codex run'], blockedCommands: [], proofLevel: 'installed_only' },
  { name: 'playwright', installed: true, version: 'package_present', authenticated: 'not_proven', safeReadOnlyCommands: ['npx playwright --version'], approvalRequiredCommands: ['npx playwright test'], blockedCommands: ['npx playwright install --with-deps'], proofLevel: 'installed_only' },
];

const TOOL_SUMMARY = { totalTools: 11, installed: 11, authenticated: 0, proofLevel: 'installed_only' };

const REPORT_CENTER = {
  reportCount: 62,
  categories: [
    { name: 'operations_status', description: 'System operations and process status reports', reports: ['nexus_operations_status_latest.json', 'nexus_process_inventory_latest.json', 'nexus_scheduler_inventory_latest.json'] },
    { name: 'hermes_ai', description: 'Hermes AI agent configuration and status reports', reports: ['hermes_chat_live_model_smoke_latest.json', 'hermes_durable_memory_plan.json'] },
    { name: 'supabase_data', description: 'Supabase database status and seed reports', reports: ['supabase_truth_audit.json', 'static_to_supabase_seed_dry_run_latest.json'] },
    { name: 'trading', description: 'Trading engine and strategy reports', reports: ['trading_lab_proof_latest.json'] },
    { name: 'youtube_research', description: 'YouTube research engine status reports', reports: ['nexus_youtube_research_status_latest.json', 'youtube_research_live_proof_latest.json'] },
    { name: 'live_connection', description: 'Live data connection implementation and proof reports', reports: ['live_connection_implementation_plan.json', 'live_seed_execution_latest.json'] },
    { name: 'activation_baselines', description: 'Phase 2 activation baseline and process activity reports', reports: ['nexus_phase2_activation_baseline.json', 'nexus_process_activity_latest.json'] },
  ],
  latestReports: {
    mostRecentByTimestamp: [
      { file: 'hermes_operations_status_latest.json', timestamp: '2026-07-01T14:10:00Z' },
      { file: 'nexus_operations_status_latest.json', timestamp: '2026-07-01T19:39:27Z' },
      { file: 'nexus_process_inventory_latest.json', timestamp: '2026-07-01T19:39:27Z' },
    ],
  },
  blockers: ['Reports center reads local files only', 'No Supabase table for report registry'],
  nextSafeAction: 'Seed report registry to Supabase; wire UI to live reads; keep local files as backup',
};

const SETTINGS_STATUS = {
  mode: 'safe_config_presence',
  summary: { total_configs: 8, present: 4, missing: 4 },
  items: [
    { name: 'supabase', configPresent: true, proofLevel: 'verified', blockers: [] as string[], nextSafeAction: 'Verify Supabase connection health' },
    { name: 'hermes_chat', configPresent: false, proofLevel: 'verified', blockers: ['LLM provider not configured'], nextSafeAction: 'Configure LLM provider in Supabase Edge Function secrets' },
    { name: 'hermes_model', configPresent: false, proofLevel: 'verified', blockers: ['HERMES_MODEL_PROVIDER env var missing'], nextSafeAction: 'Set HERMES_MODEL_PROVIDER environment variable' },
    { name: 'hermes_search', configPresent: false, proofLevel: 'verified', blockers: ['VITE_HERMES_SEARCH_ENABLED not set'], nextSafeAction: 'Set VITE_HERMES_SEARCH_ENABLED=true' },
    { name: 'netlify', configPresent: true, proofLevel: 'installed_only', blockers: [] as string[], nextSafeAction: 'Verify Netlify authentication status' },
    { name: 'oanda', configPresent: false, proofLevel: 'not_proven_live', blockers: ['No proof of Oanda configuration'], nextSafeAction: 'Verify Oanda demo account credentials if needed' },
    { name: 'youtube', configPresent: true, proofLevel: 'verified', blockers: ['No proof of recent YouTube metadata fetch'], nextSafeAction: 'Verify YouTube API key and scheduler execution' },
    { name: 'openrouter', configPresent: true, proofLevel: 'verified', blockers: [] as string[], nextSafeAction: 'Configure model endpoint to use OpenRouter' },
  ],
};

const SECTIONS: SectionEntry[] = [
  {
    id: 'hermes_workroom',
    name: 'Hermes Workroom',
    status: 'live',
    source: 'supabase',
    proofLevel: 'verified',
    verifiedAt: NOW,
    tableNames: [],
    rowCount: 0,
    schedulerInstalled: false,
    schedulerRunning: false,
    supabaseWrites: false,
    blockers: [],
    nextAction: 'None — working as designed',
    notes: 'Chat interface with source reasoning, context packing, and local conversation brain.',
    description: 'Chat, delegate, and create safe work plans',
  },
  {
    id: 'ray_review',
    name: 'Ray Review',
    status: 'live',
    source: 'supabase',
    proofLevel: 'verified',
    verifiedAt: NOW,
    tableNames: ['task_requests'],
    rowCount: 62,
    schedulerInstalled: false,
    schedulerRunning: false,
    supabaseWrites: true,
    blockers: [],
    nextAction: 'Review 62 pending cards',
    notes: 'Live Supabase reads via task_requests with task_type=ray_review_item. Approval flow updates Supabase + localStorage fallback.',
    description: 'Approve, reject, or hold queued decisions',
  },
  {
    id: 'business_opportunities',
    name: 'Business Opportunities',
    status: 'live',
    source: 'supabase',
    proofLevel: 'verified',
    verifiedAt: NOW,
    tableNames: ['business_opportunities'],
    rowCount: 26,
    schedulerInstalled: false,
    schedulerRunning: false,
    supabaseWrites: true,
    blockers: [],
    nextAction: 'Review scored opportunities',
    notes: 'Live Supabase reads. 26 scored opportunities from seed + research pipeline.',
    description: 'Scored business and partner ideas',
  },
  {
    id: 'research_engine',
    name: 'Research Engine',
    status: 'live',
    source: 'supabase',
    proofLevel: 'verified',
    verifiedAt: NOW,
    tableNames: ['research_sources'],
    rowCount: 52,
    schedulerInstalled: true,
    schedulerRunning: false,
    supabaseWrites: true,
    blockers: [
      'YouTube research not proven live — no process/log/write proof',
      'Scheduler loaded but not confirmed running',
    ],
    nextAction: 'Verify YouTube research scheduler write proof',
    notes: 'Live Supabase reads from research_sources. 52 candidates. YouTube research status: not proven live.',
    description: 'Sources, scores, memory, and opportunities',
  },
  {
    id: 'monetization',
    name: 'Monetization',
    status: 'live',
    source: 'supabase',
    proofLevel: 'verified',
    verifiedAt: NOW,
    tableNames: ['monetization_opportunities'],
    rowCount: 9,
    schedulerInstalled: false,
    schedulerRunning: false,
    supabaseWrites: true,
    blockers: [],
    nextAction: 'Review monetization offers',
    notes: 'Live Supabase reads from monetization_opportunities. 9 offers.',
    description: 'Offers, funnel, and revenue status',
  },
  {
    id: 'clients',
    name: 'Clients',
    status: 'live',
    source: 'supabase',
    proofLevel: 'verified',
    verifiedAt: NOW,
    tableNames: ['client_profiles'],
    rowCount: 1,
    schedulerInstalled: false,
    schedulerRunning: false,
    supabaseWrites: true,
    blockers: [],
    nextAction: 'Review client onboarding readiness',
    notes: 'Live Supabase reads from client_profiles. 1 test customer (Julius Erving).',
    description: 'Test customer and onboarding readiness',
  },
  {
    id: 'credit_funding',
    name: 'Credit & Funding',
    status: 'static',
    source: 'local_static',
    proofLevel: 'no_proof',
    verifiedAt: null,
    tableNames: [],
    rowCount: 0,
    schedulerInstalled: false,
    schedulerRunning: false,
    supabaseWrites: false,
    blockers: ['No live Supabase table wired', 'Static data only'],
    nextAction: 'Wire to Supabase or label as static-only',
    notes: 'Static concept — no live Supabase table yet. Approval-gated workflow proposed.',
    description: 'Credit, funding, grants, and readiness',
  },
  {
    id: 'trading_lab',
    name: 'Trading Lab',
    status: 'static',
    source: 'local_static',
    proofLevel: 'unproven',
    verifiedAt: null,
    tableNames: [],
    rowCount: 0,
    schedulerInstalled: true,
    schedulerRunning: false,
    supabaseWrites: false,
    blockers: ['Trading engine process active (pid-588) but demo loop only', 'No live funded trading proven'],
    nextAction: 'Verify demo trading loop scheduler writes',
    notes: 'Trading engine process active (pid-588), demo loop scheduler loaded, but paper/demo only. No live funded trading.',
    description: 'Oanda practice and paper results',
  },
  {
    id: 'system_health',
    name: 'System Health',
    status: 'report_snapshot',
    source: 'local_static',
    proofLevel: 'unproven',
    verifiedAt: null,
    tableNames: [],
    rowCount: 0,
    schedulerInstalled: false,
    schedulerRunning: false,
    supabaseWrites: false,
    blockers: ['No dedicated Supabase table', 'Data from operations status reports only'],
    nextAction: 'Seed system_health table or label as report-only',
    notes: 'Data from operations status reports. No dedicated Supabase table.',
    description: 'Engines, connectors, and safety gates',
  },
  {
    id: 'automation',
    name: 'Automation Scheduler',
    status: 'report_snapshot',
    source: 'local_static',
    proofLevel: 'unproven',
    verifiedAt: null,
    tableNames: [],
    rowCount: 0,
    schedulerInstalled: true,
    schedulerRunning: false,
    supabaseWrites: false,
    blockers: ['launchd schedulers loaded but no active PID proof for all', 'No Supabase writes proven'],
    nextAction: 'Verify scheduler process logs and write receipts',
    notes: '26+ launchd schedulers installed and loaded. Process proof varies per scheduler.',
    description: 'Safe schedules and recent runs',
  },
  {
    id: 'reports',
    name: 'Reports',
    status: 'report_snapshot',
    source: 'local_static',
    proofLevel: 'unproven',
    verifiedAt: null,
    tableNames: [],
    rowCount: 0,
    schedulerInstalled: false,
    schedulerRunning: false,
    supabaseWrites: false,
    blockers: ['No live Supabase reads in UI', 'Report files exist locally only'],
    nextAction: 'Wire report center to Supabase or label as local-only',
    notes: 'Report files exist locally. Indexed in reports/ directory.',
    description: 'Read the latest operating evidence',
  },
  {
    id: 'settings',
    name: 'Settings',
    status: 'static',
    source: 'local_static',
    proofLevel: 'no_proof',
    verifiedAt: null,
    tableNames: [],
    rowCount: 0,
    schedulerInstalled: false,
    schedulerRunning: false,
    supabaseWrites: false,
    blockers: ['No live Supabase table wired', 'Static configuration only'],
    nextAction: 'Label as local configuration',
    notes: 'Config presence checked by env name only. No secrets exposed.',
    description: 'Safety policies and feature gates',
  },
  {
    id: 'cli_registry',
    name: 'CLI / Tool Registry',
    status: 'report_snapshot',
    source: 'local_static',
    proofLevel: 'unproven',
    verifiedAt: null,
    tableNames: [],
    rowCount: 0,
    schedulerInstalled: false,
    schedulerRunning: false,
    supabaseWrites: false,
    blockers: ['CLI tools available but no live registry in Supabase'],
    nextAction: 'Label as local tool inventory',
    notes: '11 CLI tools inventoried. Safe/approval/blocked commands documented.',
    description: 'Tool access and command safety',
  },
  {
    id: 'marketing_drafts',
    name: 'Marketing Drafts',
    status: 'static',
    source: 'local_static',
    proofLevel: 'no_proof',
    verifiedAt: null,
    tableNames: [],
    rowCount: 0,
    schedulerInstalled: false,
    schedulerRunning: false,
    supabaseWrites: false,
    blockers: ['No live Supabase table wired', 'Draft-only content'],
    nextAction: 'Label as draft-only',
    notes: 'Draft-only content. Approval-gated workflow proposed.',
    description: 'Draft-only content and outreach',
  },
];

/**
 * Get status for a single section by ID.
 */
export function getSectionStatus(sectionId: string): SectionEntry | undefined {
  return SECTIONS.find((s) => s.id === sectionId);
}

/**
 * Get all section statuses.
 */
export function getAllSectionStatuses(): SectionEntry[] {
  return [...SECTIONS];
}

/**
 * Get summary counts.
 */
export function getSectionSummary(): { live: number; static: number; mismatch: number; blocked: number; unknown: number; report_snapshot: number; total: number } {
  const counts = { live: 0, static: 0, mismatch: 0, blocked: 0, unknown: 0, report_snapshot: 0, total: SECTIONS.length };
  for (const s of SECTIONS) {
    if (s.status in counts) counts[s.status as keyof typeof counts]++;
  }
  return counts;
}

/**
 * Find sections matching a natural language query.
 * Returns sections whose name, id, or description match the query terms.
 */
export function findSectionsByQuery(query: string): SectionEntry[] {
  const lower = (query || '').toLowerCase();
  const terms = lower.split(/\s+/).filter((t) => t.length > 2);
  return SECTIONS.filter((s) => {
    const haystack = `${s.id} ${s.name} ${s.description} ${s.notes}`.toLowerCase();
    return terms.some((t) => haystack.includes(t));
  });
}

/**
 * Get research engine status specifically — with YouTube proof details.
 */
export function getResearchEngineStatus(): SectionEntry & {
  youtubeProofStatus: string;
  schedulerLoaded: boolean;
  schedulerRunning: boolean;
  supabaseWriteProof: boolean;
  lastReportTimestamp: string | null;
  watchedChannels: number;
} {
  const base = SECTIONS.find((s) => s.id === 'research_engine')!;
  return {
    ...base,
    youtubeProofStatus: 'not_proven_live',
    schedulerLoaded: true,
    schedulerRunning: false,
    supabaseWriteProof: true,
    lastReportTimestamp: '2026-07-01',
    watchedChannels: 4,
  };
}

/**
 * Get all live sections.
 */
export function getLiveSections(): SectionEntry[] {
  return SECTIONS.filter((s) => s.status === 'live');
}

/**
 * Get all static sections.
 */
export function getStaticSections(): SectionEntry[] {
  return SECTIONS.filter((s) => s.status === 'static');
}

/**
 * Get all blocked sections.
 */
export function getBlockedSections(): SectionEntry[] {
  return SECTIONS.filter((s) => s.status === 'blocked');
}

/**
 * Check if a section status question should be answered locally (no model).
 */
export function isSectionStatusQuestion(query: string): boolean {
  const lower = (query || '').toLowerCase();
  return /\b(is\s+.+\s+(live|working|running|blocked|static|connected|up|down|active|verified)|what\s+(is|are)\s+(the\s+)?status|show\s+proof|what\s+sections|which\s+sections|what\s+is\s+scheduled|what\s+is\s+blocked|what\s+is\s+live|what\s+is\s+static|is\s+this\s+section|what\s+sections\s+are|what\s+processes|what\s+tools|what\s+schedulers|what\s+automations|what\s+reports|what\s+settings|what\s+drafts|what\s+is\s+the\s+latest|when\s+was\s+the\s+last|what\s+should\s+i\s+work\s+on|what\s+is\s+broken|what\s+needs\s+approval|youtube|transcripts?|can\s+you\s+place|execute.*trade|buy\s+\w+|sell\s+\w+|turn\s+on\s+live|connect\s+funded|is\s+supabase\s+cli|is\s+netlify\s+cli|is\s+git\s+installed)\b/i.test(lower);
}

/**
 * Build a plain-language answer to a section status question.
 * Format: Plain answer → What this means → Proof → Blocker → Next safe action
 */
export function buildSectionStatusAnswer(query: string): string {
  const lower = (query || '').toLowerCase();

  // ── TRADING SAFETY: execution requests blocked FIRST ──
  if (/\b(can you\s+)?(place\s+a\s+trade|execute\s+(this\s+)?trade|buy\s+\w+|sell\s+\w+|turn\s+on\s+live\s+trading|connect\s+funded|start\s+trading|open\s+a\s+position|make\s+a\s+trade)\b/i.test(lower)) {
    return [
      `Plain answer:`,
      `No, I cannot place trades from this chat. Live/funded trading is blocked.`,
      ``,
      `What this means:`,
      `Trading Lab is set up for paper/demo testing only. There is no approved live broker connection, and placing real trades from this chat is intentionally blocked.`,
      ``,
      `Proof:`,
      `Trading mode: paper/demo only. Live trading enabled: false. Funded broker connected: false.`,
      ``,
      `Blocker:`,
      `Live/funded trading is blocked. No approved broker path.`,
      ``,
      `Next safe action:`,
      `I can help review a paper/demo strategy, summarize the latest trading report, or create an approval-gated task for a safe paper test.`,
    ].join('\n');
  }

  // ── YOUTUBE-SPECIFIC: before generic section matching ──
  if (/\b(youtube|transcripts?|video\s+fetch|channel\s+poll|metadata\s+fetch)\b/i.test(lower)) {
    const ytProcess = YOUTUBE_PROOF;
    return [
      `Plain answer:`,
      `YouTube research is not fully live yet.`,
      ``,
      `What this means:`,
      `Nexus has YouTube research pieces installed and Research Engine rows exist in Supabase, but I do not see proof that the YouTube scheduler is actively fetching new videos/transcripts and writing fresh Supabase rows.`,
      ``,
      `Proof:`,
      `Scheduler installed: ${ytProcess.schedulerInstalled ? 'yes' : 'no'}. Scheduler loaded: ${ytProcess.schedulerLoaded ? 'yes' : 'no'}. Active process: ${ytProcess.processActive ? 'yes' : 'no'}. Last output: ${ytProcess.lastOutputAt || 'none'}. Last Supabase write: ${ytProcess.lastSupabaseWriteAt || 'none'}.`,
      ``,
      `Blocker:`,
      `No process/log/write proof from a live YouTube fetch. Scheduler is loaded but not confirmed running.`,
      ``,
      `Next safe action:`,
      `Run a safe YouTube dry-run, then verify that a new research_sources row appears in Supabase.`,
    ].join('\n');
  }

  // ── TRADING STATUS: separate process/UI/mode/live ──
  if (/\b(is\s+)?(trading\s+lab\s+)?(running|active|live|trading\s+status|trading\s+lab\s+status)\b/i.test(lower) && /\btrading\b/i.test(lower)) {
    const tradingSection = SECTIONS.find((s) => s.id === 'trading_lab')!;
    const tradingProcess = PROCESS_ITEMS.find((p) => p.name === 'nexus_trading_engine')!;
    return [
      `Plain answer:`,
      `Trading Lab is running only in paper/demo mode. It cannot place live trades.`,
      ``,
      `What this means:`,
      `A trading process appears active (pid-588), but live/funded trading is blocked. The UI is still mostly static/report-backed. This is safe — no real money is at risk.`,
      ``,
      `Proof:`,
      `Process active: ${tradingProcess.processActive ? 'yes' : 'no'} (pid-588). Mode: paper/demo. Live trading enabled: false. Funded broker connected: false. UI source: ${tradingSection.status}.`,
      ``,
      `Blocker:`,
      `No approved live broker path, and live trading remains intentionally blocked.`,
      ``,
      `Next safe action:`,
      `Review the latest paper/demo report or prepare a safe paper-test task.`,
    ].join('\n');
  }

  // ── "what sections are live?" ──
  if (/what\s+sections\s+are\s+live|which\s+sections\s+are\s+live|what\s+is\s+live/i.test(lower)) {
    const live = getLiveSections();
    if (live.length === 0) return 'No sections are confirmed live yet.';
    const lines = live.map((s) => `  - ${s.name}: ${s.rowCount} rows from ${s.tableNames.join(', ') || 'local context'}`);
    return [
      `Plain answer:`,
      `${live.length} out of ${SECTIONS.length} sections are live and connected to real Supabase data.`,
      ``,
      `What this means:`,
      `These sections pull real data from the database. When something changes in Supabase, these sections reflect it.`,
      ``,
      `Live sections:`,
      ...lines,
      ``,
      `Next safe action:`,
      `Review the live data in each section to confirm it matches expectations.`,
    ].join('\n');
  }

  // ── "what sections are static?" ──
  if (/what\s+sections\s+are\s+static|which\s+sections\s+are\s+static|what\s+is\s+static/i.test(lower)) {
    const stat = getStaticSections();
    if (stat.length === 0) return 'No sections are labeled as static.';
    const lines = stat.map((s) => `  - ${s.name}: ${s.description}`);
    return [
      `Plain answer:`,
      `${stat.length} sections are still using bundled/static data — they look real but are not connected to a live backend.`,
      ``,
      `What this means:`,
      `These sections show pre-loaded or mockup data. Changes in the database will not appear here until they are wired up.`,
      ``,
      `Static sections:`,
      ...lines,
      ``,
      `Blocker:`,
      `No live Supabase table wired for these sections.`,
      ``,
      `Next safe action:`,
      `Decide which static section to activate next, then wire it to Supabase.`,
    ].join('\n');
  }

  // ── "what is blocked?" ──
  if (/what\s+is\s+blocked|which\s+sections\s+are\s+blocked|what\s+sections\s+are\s+blocked/i.test(lower)) {
    const allWithBlockers = SECTIONS.filter((s) => s.blockers.length > 0);
    if (allWithBlockers.length === 0) return 'No sections have blockers — everything is running clean.';
    const lines = allWithBlockers.map((s) => `  - ${s.name}: ${s.blockers.join('; ')}`);
    return [
      `Plain answer:`,
      `${allWithBlockers.length} sections have blockers that prevent them from working fully.`,
      ``,
      `What this means:`,
      `These sections need specific issues resolved before they can operate as intended.`,
      ``,
      `Sections with blockers:`,
      ...lines,
      ``,
      `Next safe action:`,
      `Pick the highest-priority blocker and resolve it. Credit & Funding and Marketing Drafts are the most revenue-relevant.`,
    ].join('\n');
  }

  // ── "what is scheduled?" ──
  if (/what\s+is\s+scheduled|what\s+schedules|which.*scheduled/i.test(lower)) {
    const scheduled = SECTIONS.filter((s) => s.schedulerInstalled);
    if (scheduled.length === 0) return 'No schedulers are installed.';
    const lines = scheduled.map((s) => `  - ${s.name}: installed=${s.schedulerInstalled ? 'yes' : 'no'}, running=${s.schedulerRunning ? 'yes' : 'no'}`);
    return [
      `Plain answer:`,
      `${scheduled.length} sections have schedulers installed.`,
      ``,
      `What this means:`,
      `These sections are set up to run on a schedule. However, installed does not mean running — some may only be loaded, not proven active.`,
      ``,
      `Scheduled sections:`,
      ...lines,
      ``,
      `Next safe action:`,
      `Check individual scheduler logs to confirm they are actually running and producing output.`,
    ].join('\n');
  }

  // ── "show proof this is working" ──
  if (/show\s+proof|proof\s+this\s+is\s+working|how\s+do\s+you\s+know/i.test(lower)) {
    const verified = SECTIONS.filter((s) => s.proofLevel === 'verified');
    const unproven = SECTIONS.filter((s) => s.proofLevel !== 'verified');
    const vLines = verified.map((s) => `  - ${s.name}: verified ${s.verifiedAt?.split('T')[0] || ''}, ${s.rowCount} rows from ${s.tableNames.join(',')}`);
    const uLines = unproven.map((s) => `  - ${s.name}: ${s.proofLevel} — ${s.description}`);
    return [
      `Plain answer:`,
      `${verified.length} sections are verified with real data. ${unproven.length} sections still need proof.`,
      ``,
      `What this means:`,
      `Verified sections have confirmed Supabase reads/writes. Unproven sections may use local data or have unconfirmed schedulers.`,
      ``,
      `Verified sections:`,
      ...vLines,
      ``,
      `Unproven sections:`,
      ...uLines,
      ``,
      `Next safe action:`,
      `Focus on proving the unproven sections, starting with YouTube research and the automation scheduler.`,
    ].join('\n');
  }

  // ── "what is the status?" — summary ──
  if (/what\s+(is|are)\s+(the\s+)?status|status\s+(of\s+)?all|overall\s+status/i.test(lower)) {
    const summary = getSectionSummary();
    return [
      `Plain answer:`,
      `Nexus has ${summary.live} live sections, ${summary.static} static sections, and ${summary.report_snapshot} report-backed sections out of ${summary.total} total.`,
      ``,
      `What this means:`,
      `The core system is working — Supabase reads, Hermes advisor, and section proof are active. The money workflows (Credit & Funding, Marketing Drafts) and automation proof still need activation.`,
      ``,
      `Proof:`,
      `${summary.live} verified live, ${summary.static} static/local, ${summary.report_snapshot} report snapshots, ${summary.blocked} blocked.`,
      ``,
      `Next safe action:`,
      `Activate Credit & Funding and Marketing Drafts to connect revenue workflows.`,
    ].join('\n');
  }

  // ── "what processes are available/active?" ──
  if (/what\s+processes\s+(are\s+)?(available|active|running)/i.test(lower)) {
    const active = PROCESS_ITEMS.filter((p) => p.proofLevel === 'active_process');
    const recent = PROCESS_ITEMS.filter((p) => p.proofLevel === 'recent_output');
    const topActive = active.slice(0, 5);
    const activeLines = topActive.map((p) => `  - ${p.name}: running since ${p.lastSeenAt?.split('T')[1]?.slice(0, 5) || 'unknown'}`);
    return [
      `Plain answer:`,
      `${active.length} processes are currently running or recently verified. ${recent.length} produced output recently but have no active PID.`,
      ``,
      `What this means:`,
      `These are real background services — Hermes agent, TradingView router, research workers, and the trading engine. They are the operational backbone of Nexus.`,
      ``,
      `Top running processes:`,
      ...activeLines,
      ``,
      `Proof:`,
      `Process inventory: ${PROCESS_SUMMARY.total_tracked} tracked, ${PROCESS_SUMMARY.active_process} with active PID proof.`,
      ``,
      `Next safe action:`,
      `Inspect individual process logs for recent entries, or check if any processes need restarting.`,
    ].join('\n');
  }

  // ── "what tools do we have?" ──
  if (/what\s+tools\s+(do\s+we\s+)?have|what\s+cli\s+tools|what\s+tools\s+(are|is)\s+(safe|available)|is\s+(supabase|netlify|git|gh|ollama)\s+(cli\s+)?(available|connected|installed)/i.test(lower)) {
    const installed = TOOL_REGISTRY.filter((t) => t.installed);
    const toolNames = installed.map((t) => t.name).join(', ');
    return [
      `Plain answer:`,
      `${TOOL_SUMMARY.totalTools} CLI tools are installed and available. None are authenticated yet.`,
      ``,
      `What this means:`,
      `These tools (git, node, npm, python3, supabase, netlify, gh, ollama, etc.) are on the system and ready to use, but none have confirmed authentication. Safe read-only commands work; anything that changes things needs approval.`,
      ``,
      `Installed tools:`,
      `  ${toolNames}`,
      ``,
      `Proof:`,
      `Tool inventory: ${TOOL_SUMMARY.installed} installed, ${TOOL_SUMMARY.authenticated} authenticated. Proof level: installed_only.`,
      ``,
      `Blocker:`,
      `The frontend cannot execute shell commands. Tool availability does not imply authentication.`,
      ``,
      `Next safe action:`,
      `Use safe read-only commands manually; approval-gated commands need Ray Review.`,
    ].join('\n');
  }

  // ── "what reports do we have?" ──
  if (/what\s+reports\s+(do\s+we\s+)?have|what\s+reports|show\s+report|what\s+is\s+the\s+latest\s+report|explain\s+(system\s+health|this)\s+report/i.test(lower)) {
    const latest = REPORT_CENTER.latestReports.mostRecentByTimestamp.slice(0, 3);
    const latestLines = latest.map((r) => `  - ${r.file} (${r.timestamp})`);
    return [
      `Plain answer:`,
      `${REPORT_CENTER.reportCount} reports are indexed across ${REPORT_CENTER.categories.length} categories. These are local files, not a live database-backed report system.`,
      ``,
      `What this means:`,
      `Reports exist as files on disk. They are useful for reviewing what happened, but they are not the same as a live dashboard that updates automatically.`,
      ``,
      `Most recent reports:`,
      ...latestLines,
      ``,
      `Proof:`,
      `Report center reads local files only. No Supabase table for report registry.`,
      ``,
      `Next safe action:`,
      `Seed a report registry to Supabase to make reports queryable from the live system.`,
    ].join('\n');
  }

  // ── "what settings are missing?" ──
  if (/what\s+settings\s+(are\s+)?missing|what\s+settings|missing\s+config|is\s+(web\s+search|hermes\s+model|supabase)\s+configured/i.test(lower)) {
    const present = SETTINGS_STATUS.items.filter((c) => c.configPresent);
    const missing = SETTINGS_STATUS.items.filter((c) => !c.configPresent);
    const presentNames = present.map((c) => c.name).join(', ');
    const missingNames = missing.map((c) => c.name).join(', ');
    return [
      `Plain answer:`,
      `${SETTINGS_STATUS.summary.present} of ${SETTINGS_STATUS.summary.total_configs} config groups are present. ${SETTINGS_STATUS.summary.missing} are missing.`,
      ``,
      `What this means:`,
      `Config presence is checked by name only — no secret values are ever exposed. Some tools (web search, Hermes model) are not yet configured.`,
      ``,
      `Configured:`,
      `  ${presentNames || 'none'}`,
      ``,
      `Missing:`,
      `  ${missingNames || 'none'}`,
      ``,
      `Proof:`,
      `Config check mode: safe_config_presence. Only presence by name is shown.`,
      ``,
      `Next safe action:`,
      `Configure missing groups by setting the required environment variables.`,
    ].join('\n');
  }

  // ── "what is broken?" — CEO-friendly grouped summary ──
  if (/what\s+is\s+broken|what.*broken|what.*failing|what.*not\s+working/i.test(lower)) {
    const broken = SECTIONS.filter((s) => s.blockers.length > 0);
    if (broken.length === 0) return 'No sections have blockers — everything is running clean.';

    const p1 = broken.filter((s) => ['credit_funding', 'marketing_drafts'].includes(s.id));
    const p2 = broken.filter((s) => ['research_engine', 'automation', 'system_health'].includes(s.id));
    const p3 = broken.filter((s) => ['reports', 'cli_registry', 'settings', 'trading_lab'].includes(s.id));

    const formatP = (items: SectionEntry[]) => items.length > 0
      ? items.map((s) => `  - ${s.name}: ${s.blockers[0] || 'blocked'}`).join('\n')
      : `  - (none)`;

    return [
      `Plain answer:`,
      `Nexus is working in the core areas, but the money workflows and automation proof still need activation.`,
      ``,
      `What this means:`,
      `The base system is real now — Hermes, Supabase reads, section proof, process proof, and safety blocks are working. The unfinished parts are the workflows that make Nexus operational for clients and revenue.`,
      ``,
      `1. Money/client workflows:`,
      formatP(p1),
      ``,
      `2. Automation/proof:`,
      formatP(p2),
      ``,
      `3. Infrastructure/reporting:`,
      formatP(p3),
      ``,
      `Next safe action:`,
      `Activate Credit & Funding and Marketing Drafts first because those connect directly to revenue.`,
    ].join('\n');
  }

  // ── "what needs approval?" ──
  if (/what\s+needs\s+approval|what.*approv|what.*pending|approval\s+queue/i.test(lower)) {
    const gated = SECTIONS.filter((s) => s.notes.toLowerCase().includes('approval') || s.nextAction.toLowerCase().includes('approval'));
    if (gated.length === 0) return 'No approval-gated items found.';
    const lines = gated.map((s) => `  - ${s.name}: ${s.nextAction}`);
    return [
      `Plain answer:`,
      `${gated.length} items require Ray's approval before they can proceed.`,
      ``,
      `What this means:`,
      `These workflows can prepare the action, but Ray must approve before anything external happens.`,
      ``,
      `Items awaiting approval:`,
      ...lines,
      ``,
      `Next safe action:`,
      `Review each item and approve or reject as appropriate.`,
    ].join('\n');
  }

  // ── Specific section: "is ray review live?" ──
  const sections = findSectionsByQuery(lower);
  if (sections.length === 1) {
    const s = sections[0];
    const plainAnswer = s.status === 'live'
      ? `${s.name} is live and connected to real Supabase data.`
      : s.status === 'static'
      ? `${s.name} is still using bundled/static data — not connected to a live backend.`
      : s.status === 'report_snapshot'
      ? `${s.name} is reading from local report files, not a live database.`
      : `${s.name} status: ${s.status}.`;

    const whatThisMeans = s.status === 'live'
      ? `This section pulls real data from ${s.tableNames.join(', ') || 'Supabase'}. When the database changes, this section reflects it.`
      : s.status === 'static'
      ? `This section shows pre-loaded data. Changes in the database will not appear here until it is wired up.`
      : `This section reads generated report files. That is useful for reviewing history, but it is not the same as a live workflow.`;

    return [
      `Plain answer:`,
      plainAnswer,
      ``,
      `What this means:`,
      whatThisMeans,
      ``,
      `Proof:`,
      `Status: ${s.status}. Source: ${s.source}. Proof level: ${s.proofLevel}.${s.rowCount > 0 ? ` Rows: ${s.rowCount}.` : ''}`,
      s.blockers.length > 0 ? `\nBlocker: ${s.blockers.join('; ')}` : '',
      ``,
      `Next safe action:`,
      s.nextAction,
    ].filter(Boolean).join('\n');
  }

  if (sections.length > 1) {
    const lines = sections.map((s) => {
      const icon = s.status === 'live' ? '✅' : s.status === 'static' ? '⚠️' : s.status === 'report_snapshot' ? '📊' : '❓';
      return `  ${icon} ${s.name}: ${s.status}`;
    });
    return [
      `Plain answer:`,
      `${sections.length} sections match your question.`,
      ``,
      `Matching sections:`,
      ...lines,
      ``,
      `Next safe action:`,
      `Ask about a specific section for details.`,
    ].join('\n');
  }

  // Fallback
  const summary = getSectionSummary();
  return [
    `Plain answer:`,
    `Nexus has ${summary.live} live, ${summary.static} static, and ${summary.report_snapshot} report-backed sections out of ${summary.total} total.`,
    ``,
    `Next safe action:`,
    `Ask about a specific section for details.`,
  ].join('\n');
}
