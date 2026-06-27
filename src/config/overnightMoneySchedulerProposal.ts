/**
 * Nexus OS v2 — Overnight Money Run scheduler PROPOSAL (inactive by default).
 *
 * This proposes (does NOT activate) a recurring overnight run of the all-night money runner. No cron,
 * launchd, systemd, or daemon is created. Activation is a separate, explicitly Ray-approved step.
 * Pure / deterministic. No I/O.
 */

export type SchedulerApprovalStatus = 'awaiting_ray_approval' | 'ray_approved';
export type SchedulerActivationStatus = 'not_enabled';

export interface OvernightMoneySchedulerProposal {
  proposal_id: string;
  title: string;
  description: string;
  command: string;
  dry_run: true;
  cycles: number;
  interval_minutes: number;
  proposed_start_time: string;
  recurrence: string;
  timing_mode: string;
  expected_outputs: string[];
  safety_checks: string[];
  approval_required: true;
  approval_status: SchedulerApprovalStatus;
  activation_status: SchedulerActivationStatus;
  risk_level: 'medium';
  blocked_actions: string[];
  created_at: string;
  updated_at: string;
}

export const OVERNIGHT_MONEY_SCHEDULER_PROPOSAL: OvernightMoneySchedulerProposal = {
  proposal_id: 'overnight_money_run_v1',
  title: 'Overnight Money Opportunity Run',
  description:
    'Proposes a nightly dry-run of the all-night money runner that researches, scores, and drafts money opportunities, then builds a rolling morning agenda and runs the safety verifier. Activation is NOT included — this is a proposal only.',
  command:
    'python3 scripts/night_run/run_all_night_internal_tests.py --dry-run --cycles 8 --interval-minutes 45 --json',
  dry_run: true,
  cycles: 8,
  interval_minutes: 45,
  proposed_start_time: '22:00 local',
  recurrence: 'daily',
  timing_mode: 'proposed_only_not_installed',
  expected_outputs: [
    'reports/runtime/overnight_money_cycle_history_latest.jsonl',
    'reports/manual_publish/all_night_money_run_summary_latest.md',
    'reports/manual_publish/rolling_morning_money_agenda_latest.md',
    'reports/manual_publish/hermes_rolling_money_morning_brief_latest.md',
    'reports/manual_publish/no_external_execution_verification_latest.md',
  ],
  safety_checks: [
    'python3 scripts/safety/verify_no_external_execution.py --dry-run --json',
  ],
  approval_required: true,
  approval_status: 'awaiting_ray_approval',
  activation_status: 'not_enabled',
  risk_level: 'medium',
  blocked_actions: [
    'install cron / launchd / systemd',
    'create a daemon',
    'publish / send / post / upload / deploy',
    'spend money / charge clients / activate payment links',
    'contact clients / activate partner links externally',
    'connect live Client Vault / use raw client data',
    'run external AI on private client data / scrape / live trading',
  ],
  created_at: '2026-06-27T00:00:00.000Z',
  updated_at: '2026-06-27T00:00:00.000Z',
};
