export type EvidenceState = 'PASS_REAL' | 'PARTIAL' | 'UNVALIDATED' | 'GATED' | 'NOT_READY'
export type AuthorityClass = 'READ_ONLY' | 'INTERNAL_WRITE' | 'APPROVAL_GATED_EXTERNAL_ACTION' | 'HUMAN_ONLY' | 'PROHIBITED'

export type ProductOption = {
  model: string; targetCustomer: string; coreValue: string; featureScope: string[]
  tenancyModel: string; aiScope: string; dataAccessModel: string; humanSupportRequired: string
  implementationComplexity: string; costProfile: string; marginRisk: string; privacyRisk: string
  governanceRisk: string; dependencies: string[]; readiness: EvidenceState; knownGaps: string[]
}

export const PRODUCT_OPTIONS: ProductOption[] = [
  { model: 'INTERNAL_OPERATOR_ONLY', targetCustomer: 'Nexus operators', coreValue: 'Internal company operations', featureScope: ['Nexus', 'Nova', 'Alpha'], tenancyModel: 'internal tenant', aiScope: 'internal governed context', dataAccessModel: 'internal RLS scopes', humanSupportRequired: 'operator', implementationComplexity: 'LOW', costProfile: 'INTERNAL', marginRisk: 'NOT_APPLICABLE', privacyRisk: 'LOW', governanceRisk: 'LOW', dependencies: ['canonical goals', 'RLS'], readiness: 'PASS_REAL', knownGaps: [] },
  { model: 'MANAGED_SERVICE', targetCustomer: 'GoClear clients', coreValue: 'Guided readiness service', featureScope: ['portal', 'Clyde', 'support'], tenancyModel: 'tenant per client', aiScope: 'bounded client context', dataAccessModel: 'client-scoped RLS', humanSupportRequired: 'managed support', implementationComplexity: 'MEDIUM', costProfile: 'METERED_PLUS_SUPPORT', marginRisk: 'UNVALIDATED', privacyRisk: 'MEDIUM', governanceRisk: 'MEDIUM', dependencies: ['client portal V2', 'client AI policy', 'support'], readiness: 'PARTIAL', knownGaps: ['commercial validation', 'final visual approval'] },
  { model: 'CLIENT_PORTAL_PLUS_AI', targetCustomer: 'GoClear clients', coreValue: 'Self-service readiness guidance', featureScope: ['portal', 'Clyde', 'documents', 'readiness'], tenancyModel: 'tenant per client', aiScope: 'policy-gated Clyde', dataAccessModel: 'Supabase-first RLS', humanSupportRequired: 'escalation support', implementationComplexity: 'MEDIUM', costProfile: 'USAGE_QUOTA', marginRisk: 'UNVALIDATED', privacyRisk: 'MEDIUM', governanceRisk: 'MEDIUM', dependencies: ['R30A V2', 'R29 client AI'], readiness: 'GATED', knownGaps: ['visual design approval', 'commercial validation'] },
  { model: 'WHITE_LABEL_BUSINESS_OS', targetCustomer: 'Partner businesses', coreValue: 'Rebranded operating system', featureScope: ['multi-tenant platform', 'API', 'white label'], tenancyModel: 'hierarchical tenants', aiScope: 'partner-bounded', dataAccessModel: 'new reviewed boundary required', humanSupportRequired: 'partner support', implementationComplexity: 'HIGH', costProfile: 'HIGH_VARIANCE', marginRisk: 'UNVALIDATED', privacyRisk: 'HIGH', governanceRisk: 'HIGH', dependencies: ['client product', 'contract/legal review', 'support scale'], readiness: 'NOT_READY', knownGaps: ['privacy/legal model', 'tenant hierarchy', 'commercial validation'] },
  { model: 'DEPARTMENT_MODULES', targetCustomer: 'Internal departments', coreValue: 'Reusable governed capabilities', featureScope: ['research', 'funding', 'commerce'], tenancyModel: 'internal scopes', aiScope: 'department authority envelopes', dataAccessModel: 'department-scoped', humanSupportRequired: 'department owner', implementationComplexity: 'MEDIUM', costProfile: 'INTERNAL', marginRisk: 'NOT_APPLICABLE', privacyRisk: 'LOW', governanceRisk: 'MEDIUM', dependencies: ['canonical goal system'], readiness: 'PASS_REAL', knownGaps: [] },
  { model: 'HYBRID', targetCustomer: 'Internal plus managed clients', coreValue: 'Controlled internal and client modules', featureScope: ['internal OS', 'client portal', 'managed service'], tenancyModel: 'separate internal/client tenants', aiScope: 'role-specific', dataAccessModel: 'strict domain boundaries', humanSupportRequired: 'tiered support', implementationComplexity: 'HIGH', costProfile: 'MIXED', marginRisk: 'UNVALIDATED', privacyRisk: 'HIGH', governanceRisk: 'HIGH', dependencies: ['all client proof', 'support scale', 'commercial validation'], readiness: 'GATED', knownGaps: ['product decision', 'design and commercial validation'] },
]

export const CAPABILITY_ENTITLEMENTS = {
  FREE_GUEST: { clientPortal: true, clyde: true, customerService: true, documents: true, fundingExecution: false, admin: false, api: false },
  MANAGED_CLIENT: { clientPortal: true, clyde: true, customerService: true, documents: true, fundingExecution: false, admin: false, api: false },
  INTERNAL_OPERATOR: { clientPortal: false, clyde: false, customerService: false, documents: true, fundingExecution: false, admin: true, api: true },
} as const

export function sameTenantAccess(actorTenantId: string, resourceTenantId: string) { return actorTenantId !== '' && actorTenantId === resourceTenantId }
export function capabilityPolicy(action: string) {
  const lower = action.toLowerCase()
  if (/payment|transfer|live trade|production cutover/.test(lower)) return { authorityClass: 'PROHIBITED' as const, enabled: false, requiresApproval: true }
  if (/invoice|grant application|funding application|signature|email send/.test(lower)) return { authorityClass: 'APPROVAL_GATED_EXTERNAL_ACTION' as const, enabled: false, requiresApproval: true }
  return { authorityClass: 'READ_ONLY' as const, enabled: true, requiresApproval: false }
}

export function provisioningPlan(tenantId: string, plan: keyof typeof CAPABILITY_ENTITLEMENTS) {
  return { tenantId, syntheticOnly: true, status: 'READY_FOR_USE', plan, capabilities: CAPABILITY_ENTITLEMENTS[plan], auditScopeCreated: true, dataBoundaryCreated: true, realCustomerProvisioned: false, externalSideEffect: false }
}

export function readinessMatrix() {
  return {
    INTERNAL_USE: { engineering: 'PASS_REAL', tenant: 'PASS_REAL', security: 'PASS_REAL', privacy: 'PASS_REAL', cost: 'PASS_REAL', governance: 'PASS_REAL', support: 'PASS_REAL', design: 'PASS_REAL', commercialValidation: 'NOT_READY', production: 'PASS_REAL' },
    MANAGED_SERVICE: { engineering: 'PASS_REAL', tenant: 'PASS_REAL', security: 'PASS_REAL', privacy: 'PASS_REAL', cost: 'PARTIAL', governance: 'PASS_REAL', support: 'PARTIAL', design: 'GATED', commercialValidation: 'UNVALIDATED', production: 'GATED' },
    CLIENT_PORTAL_PRODUCT: { engineering: 'PASS_REAL', tenant: 'PASS_REAL', security: 'PASS_REAL', privacy: 'PASS_REAL', cost: 'PARTIAL', governance: 'PASS_REAL', support: 'PASS_REAL', design: 'GATED', commercialValidation: 'UNVALIDATED', production: 'GATED' },
    WHITE_LABEL_PRODUCT: { engineering: 'PARTIAL', tenant: 'NOT_READY', security: 'PARTIAL', privacy: 'NOT_READY', cost: 'UNVALIDATED', governance: 'NOT_READY', support: 'NOT_READY', design: 'UNVALIDATED', commercialValidation: 'UNVALIDATED', production: 'NOT_READY' },
    API_OR_CONNECTOR_PRODUCT: { engineering: 'PARTIAL', tenant: 'PARTIAL', security: 'PARTIAL', privacy: 'PARTIAL', cost: 'UNVALIDATED', governance: 'GATED', support: 'NOT_READY', design: 'UNVALIDATED', commercialValidation: 'UNVALIDATED', production: 'NOT_READY' },
  } as const
}
