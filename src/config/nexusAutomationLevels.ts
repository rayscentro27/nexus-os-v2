/**
 * Nexus universal automation levels — the three-level model Ray clarified.
 *
 * Core rule: Nexus can work INTERNALLY. Nexus cannot LEAVE THE BUILDING without approval.
 * "Leave the building" = publish, send, contact, trade, spend, deploy, schedule persistent jobs,
 * change production, connect sensitive systems, or expose private/client data externally.
 *
 * Pure / deterministic. No I/O, no external AI. Never weakens publish/send/trade/deploy gates.
 */

export type AutomationLevelId =
  | 'autonomous_internal' // Level 1
  | 'approval_gated' // Level 2
  | 'blocked_high_risk'; // Level 3

export interface AutomationLevel {
  id: AutomationLevelId;
  level_number: 1 | 2 | 3;
  label: string;
  description: string;
  approval_required: boolean;
  ray_review_required: boolean;
  default_state: 'enabled_internal' | 'prepare_only' | 'blocked';
  special_contract_required: boolean;
  rollback_required: boolean;
  allowed_outputs: string[];
  forbidden_outputs: string[];
  requires?: string[];
}

export const AUTOMATION_LEVELS: Record<AutomationLevelId, AutomationLevel> = {
  autonomous_internal: {
    id: 'autonomous_internal',
    level_number: 1,
    label: 'Autonomous Internal Automation',
    description:
      'Allowed after the resource/process/category is approved. No Ray approval needed for each item. Internal-only outputs.',
    approval_required: false,
    ray_review_required: false,
    default_state: 'enabled_internal',
    special_contract_required: false,
    rollback_required: false,
    allowed_outputs: [
      'internal cards',
      'scores',
      'reports',
      'proof events',
      'Hermes prep',
      'department routing',
      'internal recommendations',
    ],
    forbidden_outputs: [
      'publish',
      'send',
      'trade',
      'spend',
      'deploy',
      'scheduler activation',
      'client contact',
    ],
  },
  approval_gated: {
    id: 'approval_gated',
    level_number: 2,
    label: 'Approval-Gated Automation',
    description:
      'Can prepare work automatically, but Ray must approve before execution. Drafts/proposals are fine; execution is gated.',
    approval_required: true,
    ray_review_required: true,
    default_state: 'prepare_only',
    special_contract_required: false,
    rollback_required: true,
    allowed_outputs: [
      'drafts',
      'proposals',
      'campaign packages',
      'scheduler candidates',
      'connector setup recommendations',
      'reports',
      'decision briefs',
    ],
    forbidden_outputs: [
      'external execution',
      'outbound contact',
      'public publishing',
      'live spending',
      'production mutation',
    ],
  },
  blocked_high_risk: {
    id: 'blocked_high_risk',
    level_number: 3,
    label: 'Blocked / High-Risk Automation',
    description:
      'Not allowed unless separately designed, explicitly approved, and protected by its own contract.',
    approval_required: true,
    ray_review_required: true,
    default_state: 'blocked',
    special_contract_required: true,
    rollback_required: true,
    allowed_outputs: [
      'blocked/escalation card only',
      'separate design doc reference',
    ],
    forbidden_outputs: [
      'any direct execution',
      'live trading',
      'broker execution',
      'funded account actions',
      'raw auto_executor exposure',
      'payment/spend actions',
      'production deploys',
      'credential changes',
      'destructive database actions',
      'broad scraping',
      'YouTube media downloads',
      'external AI on sensitive/private/customer data',
    ],
    requires: [
      'separate design doc',
      'explicit Ray approval',
      'proof plan',
      'rollback plan',
      'hard guard tests',
      'safety contract',
    ],
  },
};

export const AUTOMATION_LEVEL_LIST: AutomationLevel[] = [
  AUTOMATION_LEVELS.autonomous_internal,
  AUTOMATION_LEVELS.approval_gated,
  AUTOMATION_LEVELS.blocked_high_risk,
];

export function getAutomationLevel(id: AutomationLevelId): AutomationLevel {
  return AUTOMATION_LEVELS[id];
}

export const AUTOMATION_CORE_RULE =
  'Nexus can work internally. Nexus cannot leave the building without approval.';

/** "Leave the building" actions — any of these forces Level 2 (gated) or Level 3 (blocked). */
export const LEAVE_THE_BUILDING_ACTIONS = [
  'publish',
  'send',
  'contact',
  'trade',
  'spend',
  'deploy',
  'schedule persistent jobs',
  'change production',
  'connect sensitive systems',
  'expose private/client data externally',
] as const;
