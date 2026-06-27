/**
 * Nexus OS v2 — Credit Specialist policy enforcement.
 * Deterministic. Fails closed. No I/O.
 */
import {
  CREDIT_SPECIALIST_MUST_NOT_USE,
} from '../config/creditSpecialistAccessContract';
import { canUseTool, specialistHasNoWebTools, mustUseApprovedKnowledgeOnly } from './nexusAIAccessPolicy';
import type { AITool } from '../config/nexusAIAgentAccessPolicy';

const FORBIDDEN = new Set<string>(CREDIT_SPECIALIST_MUST_NOT_USE);

export function creditSpecialistMayUseTool(tool: AITool): boolean {
  return canUseTool('credit_specialist_ai', tool).allowed;
}

export function creditSpecialistHasNoWebTools(): boolean {
  return specialistHasNoWebTools('credit_specialist_ai');
}

export function creditSpecialistApprovedKnowledgeOnly(): boolean {
  return mustUseApprovedKnowledgeOnly('credit_specialist_ai');
}

/** Validate a requested resource string against the must-not-use list. */
export function creditSpecialistForbidden(resource: string): boolean {
  const r = resource.toLowerCase().replace(/\s+/g, '_');
  if (FORBIDDEN.has(r)) return true;
  return /internet|web|youtube|external_ai|production|scrap/.test(r);
}

/** Knowledge gate: Credit Specialist may only use knowledge flagged usable + approved. */
export function creditSpecialistMayUseKnowledge(k: { approval_status?: string; usable_by_credit_specialist?: boolean }): boolean {
  return k.approval_status === 'approved' && k.usable_by_credit_specialist === true;
}
