/**
 * Nexus OS v2 — AI access policy enforcement.
 *
 * The single source of truth for "can this AI role use this tool / read this data category / emit
 * this client-facing output". Deterministic. No I/O. Fails closed.
 */
import {
  AI_DEPARTMENT_ROLES,
  type AIDepartmentRole,
} from '../config/nexusAIDepartmentRoles';
import {
  AI_TOOL_ACCESS,
  INTERNET_TOOLS,
  type AITool,
} from '../config/nexusAIAgentAccessPolicy';
import {
  getDataCategory,
  isPrivateClientData,
  type ClientDataCategory,
} from '../config/nexusClientDataSensitivityPolicy';

export interface AccessDecision {
  allowed: boolean;
  reason: string;
}

/** May this role use this tool? */
export function canUseTool(role: AIDepartmentRole, tool: AITool): AccessDecision {
  const access = AI_TOOL_ACCESS[role];
  if (access.blocked_tools.includes(tool)) return { allowed: false, reason: `${role} is blocked from tool ${tool}.` };
  if (access.allowed_tools.includes(tool)) return { allowed: true, reason: `${role} may use ${tool}.` };
  return { allowed: false, reason: `${role} has no grant for ${tool} (deny by default).` };
}

/** May this role read this client data category? Private data is vault-only and never for internet roles. */
export function canAccessData(role: AIDepartmentRole, category: ClientDataCategory): AccessDecision {
  const def = getDataCategory(category);
  const roleDef = AI_DEPARTMENT_ROLES[role];
  if (!def) return { allowed: false, reason: `Unknown data category ${category}.` };

  // Sanitized / aggregate / internal-summary categories.
  if (!def.vault_only) {
    if (def.hermes_allowed) return { allowed: true, reason: `${category} is sanitized/aggregate — readable.` };
    return { allowed: roleDef.supabase_system_reports_allowed, reason: `${category} is internal summary.` };
  }

  // Private vault-only data.
  if (!roleDef.vault_adapter_allowed) {
    return { allowed: false, reason: `${role} has no vault adapter access; ${category} is private vault-only data.` };
  }
  // Even with vault access, a role flagged raw_client_data_allowed=false reads only via adapter (allowed),
  // but Hermes (no vault access) and internet roles are already denied above.
  return { allowed: true, reason: `${role} may read ${category} ONLY through the Client Vault adapter.` };
}

/** Hermes must never touch raw/private client data. */
export function hermesCanAccess(category: ClientDataCategory): AccessDecision {
  return canAccessData('hermes_ceo_advisor', category);
}

/** Internet-enabled tools must never reach Client Vault data. */
export function internetToolCanAccessVault(): AccessDecision {
  return { allowed: false, reason: 'Internet-enabled tools can never access Client Vault data (hard separation).' };
}

export function isInternetTool(tool: AITool): boolean {
  return INTERNET_TOOLS.includes(tool);
}

/** Specialist AIs must be Supabase-only (no internet/web). */
export function specialistHasNoWebTools(role: AIDepartmentRole): boolean {
  const access = AI_TOOL_ACCESS[role];
  return INTERNET_TOOLS.every((t) => !access.allowed_tools.includes(t));
}

/** Credit/Funding/Business specialists + Client Chat must use approved knowledge only. */
export function mustUseApprovedKnowledgeOnly(role: AIDepartmentRole): boolean {
  return AI_DEPARTMENT_ROLES[role].approved_knowledge_only;
}

/** Client-facing output is always blocked or approval-gated — never auto-emitted. */
export function clientFacingOutputDisposition(role: AIDepartmentRole): 'blocked' | 'approval_gated' {
  return AI_DEPARTMENT_ROLES[role].client_facing_output;
}

export interface AccessViolation {
  rule: string;
  role?: AIDepartmentRole;
  detail: string;
}

/** Run the full invariant set. Returns [] when the access model is intact. */
export function verifyAccessInvariants(): AccessViolation[] {
  const v: AccessViolation[] = [];

  // 1. Hermes cannot access any private client data category.
  for (const cat of ['raw_credit_report', 'smartcredit_file', 'bank_statement', 'raw_letter', 'ssn', 'dob', 'account_number'] as ClientDataCategory[]) {
    if (hermesCanAccess(cat).allowed) v.push({ rule: 'hermes_no_raw_client_data', role: 'hermes_ceo_advisor', detail: `Hermes could access ${cat}` });
  }

  // 2. Internet-enabled roles must NOT have vault access.
  for (const role of Object.keys(AI_TOOL_ACCESS) as AIDepartmentRole[]) {
    const access = AI_TOOL_ACCESS[role];
    const hasInternet = INTERNET_TOOLS.some((t) => access.allowed_tools.includes(t));
    const hasVault = access.allowed_tools.includes('client_vault_adapter');
    if (hasInternet && hasVault) v.push({ rule: 'internet_and_vault_separation', role, detail: `${role} has both internet and vault access` });
  }

  // 3. Specialists must have no web tools.
  for (const role of ['credit_specialist_ai', 'funding_specialist_ai', 'business_setup_specialist_ai'] as AIDepartmentRole[]) {
    if (!specialistHasNoWebTools(role)) v.push({ rule: 'specialist_supabase_only', role, detail: `${role} has web tools` });
  }

  // 4. Researcher AI must not access client PII.
  if (canAccessData('researcher_ai', 'raw_credit_report').allowed || canAccessData('researcher_ai', 'ssn').allowed) {
    v.push({ rule: 'researcher_no_client_pii', role: 'researcher_ai', detail: 'Researcher could access client PII' });
  }

  // 5. Every role's client-facing output must be blocked or approval-gated (never auto).
  for (const role of Object.keys(AI_DEPARTMENT_ROLES) as AIDepartmentRole[]) {
    const d = clientFacingOutputDisposition(role);
    if (d !== 'blocked' && d !== 'approval_gated') v.push({ rule: 'client_facing_gated', role, detail: `${role} client-facing output not gated` });
  }

  // 6. Specialists + client chat must require approved knowledge only.
  for (const role of ['credit_specialist_ai', 'funding_specialist_ai', 'business_setup_specialist_ai', 'client_chat_ai'] as AIDepartmentRole[]) {
    if (!mustUseApprovedKnowledgeOnly(role)) v.push({ rule: 'approved_knowledge_only', role, detail: `${role} not restricted to approved knowledge` });
  }

  return v;
}

export { isPrivateClientData };
