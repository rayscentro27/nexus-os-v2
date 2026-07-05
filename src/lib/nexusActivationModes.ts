/**
 * Nexus OS v2 — Activation Modes
 * Prompt 2: Phase C
 *
 * Defines the four activation modes and provides type-safe utilities
 * for classifying processes, capabilities, and receipts.
 */

export type ActivationMode = 'OBSERVE' | 'DRY_RUN' | 'SANDBOX_TEST' | 'APPROVED_LIVE';

export interface ActivationModeInfo {
  mode: ActivationMode;
  label: string;
  description: string;
  allowsExternalAction: boolean;
  requiresRayReview: boolean;
}

export const ACTIVATION_MODES: Record<ActivationMode, ActivationModeInfo> = {
  OBSERVE: {
    mode: 'OBSERVE',
    label: 'Observe',
    description: 'Read-only inspection and monitoring',
    allowsExternalAction: false,
    requiresRayReview: false,
  },
  DRY_RUN: {
    mode: 'DRY_RUN',
    label: 'Dry Run',
    description: 'Generate output/report/package without sending, posting, or charging',
    allowsExternalAction: false,
    requiresRayReview: false,
  },
  SANDBOX_TEST: {
    mode: 'SANDBOX_TEST',
    label: 'Sandbox/Test',
    description: 'Use test accounts, synthetic data, demo broker, or staging routes',
    allowsExternalAction: false,
    requiresRayReview: false,
  },
  APPROVED_LIVE: {
    mode: 'APPROVED_LIVE',
    label: 'Approved Live',
    description: 'Production ready with real accounts, data, and Ray approval',
    allowsExternalAction: true,
    requiresRayReview: true,
  },
};

export function getActivationModeInfo(mode: ActivationMode): ActivationModeInfo {
  return ACTIVATION_MODES[mode];
}

export function canRunExternally(mode: ActivationMode): boolean {
  return ACTIVATION_MODES[mode].allowsExternalAction;
}

export function needsRayReview(mode: ActivationMode): boolean {
  return ACTIVATION_MODES[mode].requiresRayReview;
}

export function classifyMode(score: number): ActivationMode {
  if (score >= 81) return 'APPROVED_LIVE';
  if (score >= 61) return 'SANDBOX_TEST';
  if (score >= 41) return 'DRY_RUN';
  return 'OBSERVE';
}
