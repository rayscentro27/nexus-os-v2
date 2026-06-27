/**
 * Nexus OS v2 — Hermes Plain Language Mode.
 *
 * Hermes speaks like a business partner, not a developer log. Builds an executive brief from
 * SANITIZED client signals + system status only — never raw client data. Deterministic. No I/O.
 */
import type { SanitizedClientSignals } from './sanitizedClientSignals';

export interface SystemSnapshot {
  build_passing: boolean;
  automation_levels_ok: boolean;
  high_risk_guards_ok: boolean;
  ai_access_ok: boolean;
  client_vault_status: string; // 'not_connected_by_design'
  failed_processes: string[];
  approvals_pending: number;
}

export interface DepartmentRecommendation {
  department: string;
  recommendation: string;
}

export interface HermesExecutiveBrief {
  whats_working: string[];
  whats_broken: string[];
  do_next: string[];
  makes_money_fastest: string[];
  needs_approval: string[];
  blocked_for_safety: string[];
  can_run_tonight: string[];
  should_not_run_tonight: string[];
  department_recommendations: DepartmentRecommendation[];
  plain_language_summary: string;
}

const DEPARTMENTS = [
  'Automation',
  'Client Workflow',
  'Credit Specialist',
  'Business Setup',
  'Affiliate Revenue',
  'GoClear Monetization',
  'Market Pricing',
  'Online Banking Affiliate',
  'System Health',
  'Approvals',
] as const;

function deptRec(department: string, s: SanitizedClientSignals): string {
  switch (department) {
    case 'Automation':
      return 'Level 1 internal work can run tonight; keep Level 2 actions gated and Level 3 blocked.';
    case 'Client Workflow':
      return `${s.stuck_clients_count} client(s) stuck and ${s.credit_reports_pending_count} waiting on a credit report — follow up to keep momentum.`;
    case 'Credit Specialist':
      return 'Run credit analysis on mock data; keep client-facing output approval-gated and Supabase-only.';
    case 'Business Setup':
      return `${s.business_setup_incomplete_count} client(s) missing business setup items — surface partner vs DIY options.`;
    case 'Affiliate Revenue':
      return `${s.affiliate_opportunity_count} affiliate opportunity(ies) — recommend partners only where a task is missing, always with a DIY option.`;
    case 'GoClear Monetization':
      return 'Validate the readiness review ($97) + monthly tiers; this is the fastest, safest revenue path.';
    case 'Market Pricing':
      return 'Use the internal pricing bands to set a core tier near $97/mo; validate before any launch.';
    case 'Online Banking Affiliate':
      return 'Bluevine looks like the primary online-bank partner; always offer the client’s-own-bank DIY option.';
    case 'System Health':
      return 'Build/watch and all dry-runs are the night-run focus; nothing leaves the building.';
    case 'Approvals':
      return `${s.ray_review_needed_count} item(s) ready for Ray review; approve plans before anything is exposed to clients.`;
    default:
      return 'No action needed.';
  }
}

export function buildHermesExecutiveBrief(signals: SanitizedClientSignals, system: SystemSnapshot): HermesExecutiveBrief {
  const working: string[] = [];
  if (system.build_passing) working.push('Build and watch pass — the system is healthy.');
  if (system.automation_levels_ok) working.push('Automation levels are enforced (internal allowed, execution gated, high-risk blocked).');
  if (system.ai_access_ok) working.push('AI access boundaries hold — Hermes sees sanitized signals only.');
  if (system.high_risk_guards_ok) working.push('High-risk guards are all blocked by default.');
  working.push(`Client Vault is ${system.client_vault_status} (mock adapter only).`);

  const broken = system.failed_processes.length
    ? system.failed_processes.map((p) => `Process failed: ${p}.`)
    : ['Nothing is broken in the safe internal lane.'];

  const doNext = [
    'Validate GoClear subscription pricing against the market bands.',
    `Follow up on ${signals.stuck_clients_count} stuck client(s).`,
    `Review ${signals.ray_review_needed_count} item(s) waiting for Ray approval.`,
    'Confirm the online-bank affiliate primary (Bluevine) and DIY option.',
  ];

  const fastestMoney = [
    'GoClear readiness review ($97) at signup.',
    'Monthly subscription core tier (~$97/mo) for ongoing tracking.',
    'Affiliate recommendations on missing tasks (SmartCredit, online bank, DocuPost).',
    'Funding readiness → commission pipeline for funding-ready clients.',
  ];

  const needsApproval = [
    'Any client-facing recommendation or plan.',
    'Sending messages, mailing letters, charging clients, activating schedulers/connectors.',
    `${system.approvals_pending} pending approval item(s).`,
  ];

  const blocked = [
    'SmartCredit password storage / scraping / auto-login.',
    'Auto-mailing, auto-disputes, auto-filing LLC/EIN, auto-opening accounts, auto-applying for funding.',
    'Live Client Vault connection, second Supabase, external AI on client credit data.',
  ];

  const canRun = [
    'All Level 1 dry-run reports (research, scoring, routing, internal reports, Hermes prep).',
    'Market pricing + online-bank affiliate research (internal/report-only).',
    'Process inventory + night-run readiness + monetization reports.',
  ];

  const shouldNotRun = [
    'Anything that publishes, sends, mails, charges, trades, spends, or contacts.',
    'Any scheduler activation or connector activation.',
  ];

  const summary =
    `Tonight is a safe internal night run. The system is ${system.build_passing ? 'healthy' : 'NOT healthy'}: ` +
    `${signals.stuck_clients_count} clients are stuck, ${signals.ray_review_needed_count} need your approval, and the fastest money is the ` +
    `$97 readiness review plus a ~$97/mo subscription. Everything risky stays blocked; nothing leaves the building without your approval.`;

  return {
    whats_working: working,
    whats_broken: broken,
    do_next: doNext,
    makes_money_fastest: fastestMoney,
    needs_approval: needsApproval,
    blocked_for_safety: blocked,
    can_run_tonight: canRun,
    should_not_run_tonight: shouldNotRun,
    department_recommendations: DEPARTMENTS.map((d) => ({ department: d, recommendation: deptRec(d, signals) })),
    plain_language_summary: summary,
  };
}
