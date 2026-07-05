/**
 * Nexus OS v2 — Process Receipts
 * Prompt 2: Phase C
 *
 * Receipt model and management for every active process.
 * Receipts provide proof that a process ran, what it did, and what happened.
 */

import { ActivationMode } from './nexusActivationModes';
import { ProcessStatus } from './nexusProcessRegistry';

export interface ProcessReceipt {
  receipt_id: string;
  process_id: string;
  department: string;
  activation_mode: ActivationMode;
  status: ProcessStatus;
  started_at: string;
  completed_at: string;
  last_run_time: string;
  input_source: string;
  output_files: string[];
  supabase_project: string;
  supabase_tables: string[];
  ui_visibility: string;
  alpha_visibility: string;
  nexus_hermes_visibility: string;
  external_action_taken: boolean;
  cost_estimate: string;
  errors: string[];
  score: number;
  recommendation: string;
  ray_review_required: boolean;
  next_action: string;
  recovery_prompt: string;
}

let receiptCounter = 0;

export function generateReceiptId(): string {
  receiptCounter++;
  const ts = Date.now().toString(36);
  const rand = Math.random().toString(36).substring(2, 6);
  return `receipt_${ts}_${rand}_${receiptCounter}`;
}

export function createReceipt(
  processId: string,
  department: string,
  mode: ActivationMode,
  overrides: Partial<ProcessReceipt> = {}
): ProcessReceipt {
  const now = new Date().toISOString();
  return {
    receipt_id: generateReceiptId(),
    process_id: processId,
    department,
    activation_mode: mode,
    status: 'completed',
    started_at: now,
    completed_at: now,
    last_run_time: now,
    input_source: '',
    output_files: [],
    supabase_project: '',
    supabase_tables: [],
    ui_visibility: '',
    alpha_visibility: '',
    nexus_hermes_visibility: '',
    external_action_taken: false,
    cost_estimate: '',
    errors: [],
    score: 0,
    recommendation: '',
    ray_review_required: false,
    next_action: '',
    recovery_prompt: '',
    ...overrides,
  };
}

export function validateReceipt(receipt: ProcessReceipt): { valid: boolean; errors: string[] } {
  const errors: string[] = [];
  if (!receipt.receipt_id) errors.push('receipt_id is required');
  if (!receipt.process_id) errors.push('process_id is required');
  if (!receipt.department) errors.push('department is required');
  if (!['OBSERVE', 'DRY_RUN', 'SANDBOX_TEST', 'APPROVED_LIVE'].includes(receipt.activation_mode)) {
    errors.push('invalid activation_mode');
  }
  if (receipt.external_action_taken && !receipt.ray_review_required) {
    errors.push('external_action_taken requires ray_review_required');
  }
  if (receipt.activation_mode === 'APPROVED_LIVE' && receipt.score < 81) {
    errors.push('APPROVED_LIVE requires score >= 81');
  }
  return { valid: errors.length === 0, errors };
}

export function serializeReceipts(receipts: ProcessReceipt[]): string {
  return JSON.stringify(receipts, null, 2);
}

export function deserializeReceipts(json: string): ProcessReceipt[] {
  try {
    return JSON.parse(json);
  } catch {
    return [];
  }
}
