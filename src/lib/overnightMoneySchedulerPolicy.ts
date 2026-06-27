/**
 * Nexus OS v2 — Overnight Money scheduler policy.
 *
 * Enforces that the scheduler proposal can never self-activate. Deterministic. No I/O. Fails closed.
 */
import {
  OVERNIGHT_MONEY_SCHEDULER_PROPOSAL,
  type OvernightMoneySchedulerProposal,
} from '../config/overnightMoneySchedulerProposal';

export type ProposalCommandCenterStatus =
  | 'proposal_ready'
  | 'awaiting_ray_approval'
  | 'activation_not_enabled'
  | 'dry_run_only'
  | 'safe_internal';

/** Activation is never enabled by this code path. The proposal's activation_status is always
 *  'not_enabled' (typed as such); no code here can flip it. */
export function isActivationEnabled(p: OvernightMoneySchedulerProposal = OVERNIGHT_MONEY_SCHEDULER_PROPOSAL): boolean {
  void p;
  return false;
}

/** A proposal may only be activated later if Ray approved AND a separate activation flow runs. */
export function canActivateNow(): boolean {
  return false; // always false here — activation lives behind a separate approved flow
}

export function proposalStatuses(
  p: OvernightMoneySchedulerProposal = OVERNIGHT_MONEY_SCHEDULER_PROPOSAL,
): ProposalCommandCenterStatus[] {
  const out: ProposalCommandCenterStatus[] = ['proposal_ready'];
  if (p.approval_status === 'awaiting_ray_approval') out.push('awaiting_ray_approval');
  if (p.activation_status === 'not_enabled') out.push('activation_not_enabled');
  if (p.dry_run) out.push('dry_run_only');
  out.push('safe_internal');
  return out;
}

export function proposalSummary(p: OvernightMoneySchedulerProposal = OVERNIGHT_MONEY_SCHEDULER_PROPOSAL) {
  return {
    proposal_id: p.proposal_id,
    title: p.title,
    command: p.command,
    schedule: `${p.recurrence} @ ${p.proposed_start_time}`,
    cycles: p.cycles,
    interval_minutes: p.interval_minutes,
    approval_required: p.approval_required,
    approval_status: p.approval_status,
    activation_status: p.activation_status,
    risk_level: p.risk_level,
    statuses: proposalStatuses(p),
  };
}
