/**
 * Nexus OS v2 — Readiness Registry.
 *
 * Centralized, deterministic status for every credit repair, business funding,
 * and offer-readiness area. Pure config — no I/O, no external calls.
 * Hermes reads this to answer "is X ready?" questions in CEO voice.
 */

export type ReadinessStatus = 'ready' | 'partial' | 'blocked' | 'placeholder' | 'not_configured' | 'unknown';

export interface ReadinessRegistryItem {
  areaKey: string;
  displayName: string;
  status: ReadinessStatus;
  canHermesRead: boolean;
  canClientUse: boolean;
  canAdminUse: boolean;
  requiresApproval: boolean;
  blocker: string | null;
  nextSafeAction: string;
  sourcePath: string;
}

export const READINESS_REGISTRY: ReadinessRegistryItem[] = [
  {
    areaKey: 'credit_repair',
    displayName: 'Credit Repair Workflow',
    status: 'partial',
    canHermesRead: true,
    canClientUse: false,
    canAdminUse: true,
    requiresApproval: false,
    blocker: 'No live client data. Scoring engine exists but runs on static demo data. Document upload disabled. Bureau/creditor/collector connectors blocked.',
    nextSafeAction: 'Apply Supabase migrations and create first test client to wire the scoring engine to real data.',
    sourcePath: 'src/lib/clientWorkflowEngine.ts',
  },
  {
    areaKey: 'business_funding',
    displayName: 'Business Funding Workflow',
    status: 'partial',
    canHermesRead: true,
    canClientUse: false,
    canAdminUse: true,
    requiresApproval: false,
    blocker: 'No live client data. Funding scoring engine exists but runs on static demo data. No bank/DUNS/EIN integrations. All affiliate URLs null.',
    nextSafeAction: 'Apply Supabase migrations and create first test client with business profile data.',
    sourcePath: 'src/lib/clientWorkflowEngine.ts',
  },
  {
    areaKey: 'readiness_review_offer',
    displayName: '$97 Credit & Funding Readiness Review',
    status: 'partial',
    canHermesRead: true,
    canClientUse: false,
    canAdminUse: true,
    requiresApproval: true,
    blocker: 'No live intake flow, no production Stripe, no report generation from real data, no email delivery.',
    nextSafeAction: 'Enable Stripe production mode and build a manual intake conversation flow.',
    sourcePath: 'configs/offer_registry.json',
  },
  {
    areaKey: 'client_onboarding',
    displayName: 'Client Onboarding',
    status: 'placeholder',
    canHermesRead: false,
    canClientUse: false,
    canAdminUse: true,
    requiresApproval: false,
    blocker: 'Onboarding pipeline exists in Python scripts only. Not wired to live UI or database.',
    nextSafeAction: 'Apply Supabase migrations and wire the onboarding flow to the client portal.',
    sourcePath: 'scripts/payments/prepare_payment_to_client_onboarding_flow.py',
  },
  {
    areaKey: 'client_portal',
    displayName: 'Client Portal',
    status: 'partial',
    canHermesRead: false,
    canClientUse: true,
    canAdminUse: true,
    requiresApproval: false,
    blocker: '9 pages built with real React components, but all driven by static demo data. No live Supabase reads on credit/funding tables.',
    nextSafeAction: 'Wire client portal pages to live Supabase reads for credit repair and funding readiness.',
    sourcePath: 'src/pages/client/ClientPortalPages.jsx',
  },
  {
    areaKey: 'admin_review',
    displayName: 'Admin Review',
    status: 'ready',
    canHermesRead: true,
    canClientUse: false,
    canAdminUse: true,
    requiresApproval: false,
    blocker: null,
    nextSafeAction: 'Open admin dashboard and review current status.',
    sourcePath: 'src/admin/NexusAdminUI.jsx',
  },
  {
    areaKey: 'ray_review',
    displayName: 'Ray Review Queue',
    status: 'ready',
    canHermesRead: true,
    canClientUse: false,
    canAdminUse: true,
    requiresApproval: true,
    blocker: null,
    nextSafeAction: 'Open Ray Review and inspect pending items.',
    sourcePath: 'src/lib/rayReviewQueue.ts',
  },
  {
    areaKey: 'specialist_handoff',
    displayName: 'Specialist Handoff',
    status: 'partial',
    canHermesRead: true,
    canClientUse: false,
    canAdminUse: true,
    requiresApproval: true,
    blocker: 'Draft-only. No live specialist agents registered. 11 domains in registry all show "not registered".',
    nextSafeAction: 'Prepare a draft specialist handoff for Ray Review.',
    sourcePath: 'src/lib/hermesOperationalContracts.ts',
  },
  {
    areaKey: 'payments',
    displayName: 'Payment Processing',
    status: 'partial',
    canHermesRead: true,
    canClientUse: false,
    canAdminUse: true,
    requiresApproval: true,
    blocker: 'Stripe test checkout open for $97. Production mode not enabled. No live payment collection.',
    nextSafeAction: 'Enable Stripe production mode for $97 readiness review.',
    sourcePath: 'configs/stripe_product_registry.json',
  },
  {
    areaKey: 'email_followup',
    displayName: 'Email / Follow-up',
    status: 'not_configured',
    canHermesRead: false,
    canClientUse: false,
    canAdminUse: false,
    requiresApproval: true,
    blocker: 'Resend integration not configured. No verified sender/domain. No email sequences.',
    nextSafeAction: 'Configure Resend with a verified sender domain and test email delivery.',
    sourcePath: 'src/lib/hermesCapabilityRegistry.ts',
  },
  {
    areaKey: 'affiliate_links',
    displayName: 'Affiliate / Referral Links',
    status: 'not_configured',
    canHermesRead: true,
    canClientUse: false,
    canAdminUse: true,
    requiresApproval: true,
    blocker: '13 partner programs tracked. All status: not_applied. All affiliate URLs null.',
    nextSafeAction: 'Apply to SmartCredit affiliate program as the first partner.',
    sourcePath: 'src/config/affiliateApprovalStatus.ts',
  },
  {
    areaKey: 'document_uploads',
    displayName: 'Document Uploads',
    status: 'blocked',
    canHermesRead: false,
    canClientUse: false,
    canAdminUse: false,
    requiresApproval: false,
    blocker: 'No private storage. Upload UI disabled with explicit disclaimer. No consent/tenant isolation.',
    nextSafeAction: 'Set up private storage (S3/R2) with consent and tenant isolation.',
    sourcePath: 'configs/connector_registry.json',
  },
  {
    areaKey: 'report_generation',
    displayName: 'Report Generation',
    status: 'partial',
    canHermesRead: true,
    canClientUse: false,
    canAdminUse: true,
    requiresApproval: false,
    blocker: 'Report registry has 13 reports. Python scripts generate local JSON. No client-facing report renderer.',
    nextSafeAction: 'Build a client-facing readiness report template that Hermes can populate.',
    sourcePath: 'src/data/reportRegistry.js',
  },
];

export function getReadinessByArea(areaKey: string): ReadinessRegistryItem | undefined {
  return READINESS_REGISTRY.find(r => r.areaKey === areaKey);
}

export function getReadinessSummary(): string {
  const ready = READINESS_REGISTRY.filter(r => r.status === 'ready').length;
  const partial = READINESS_REGISTRY.filter(r => r.status === 'partial').length;
  const blocked = READINESS_REGISTRY.filter(r => r.status === 'blocked').length;
  const placeholder = READINESS_REGISTRY.filter(r => r.status === 'placeholder').length;
  const notConfigured = READINESS_REGISTRY.filter(r => r.status === 'not_configured').length;
  return `${ready} ready, ${partial} partial, ${blocked} blocked, ${placeholder} placeholder, ${notConfigured} not configured.`;
}

export function getReadinessCeoAnswer(areaKey: string): string {
  const item = getReadinessByArea(areaKey);
  if (!item) return `I do not have a readiness entry for "${areaKey}". Ask me about credit repair, business funding, the $97 readiness review, client onboarding, the client portal, admin review, Ray Review, specialist handoff, payments, email, affiliate links, document uploads, or report generation.`;

  const statusPhrase: Record<ReadinessStatus, string> = {
    ready: 'Ready to use.',
    partial: 'Partially ready — some pieces work, others need to be built or connected.',
    blocked: 'Blocked — a key dependency is missing.',
    placeholder: 'Placeholder only — no live implementation yet.',
    not_configured: 'Not configured — the integration does not exist yet.',
    unknown: 'Status unknown — needs verification.',
  };

  const answer = `**${item.displayName}**: ${statusPhrase[item.status]}`;
  const blocker = item.blocker ? `\n\nWhat is blocking it: ${item.blocker}` : '';
  const next = `\n\nNext step: ${item.nextSafeAction}`;
  return `${answer}${blocker}${next}`;
}

export function getReadinessActionMetadata(areaKey: string): { title: string; actionLabel: string; actionType: 'open_report' | 'open_approval' | 'view_source' | 'draft_ray_review' | 'prepare_specialist_handoff'; href?: string; source: string } | null {
  const actionMap: Record<string, { title: string; actionLabel: string; actionType: 'open_report' | 'open_approval' | 'view_source' | 'draft_ray_review' | 'prepare_specialist_handoff'; href?: string; source: string }> = {
    credit_repair: { title: 'Open credit repair readiness report', actionLabel: 'Open Report', actionType: 'open_report', href: '#reports', source: 'readiness_registry' },
    business_funding: { title: 'Open business funding readiness report', actionLabel: 'Open Report', actionType: 'open_report', href: '#reports', source: 'readiness_registry' },
    readiness_review_offer: { title: 'Open readiness review offer audit', actionLabel: 'Open Audit', actionType: 'open_report', href: '#reports', source: 'readiness_registry' },
    ray_review: { title: 'Open Ray Review queue', actionLabel: 'Open Queue', actionType: 'open_approval', href: '#rayreview', source: 'readiness_registry' },
    specialist_handoff: { title: 'Prepare specialist handoff draft', actionLabel: 'Prepare Draft', actionType: 'prepare_specialist_handoff', source: 'readiness_registry' },
    client_portal: { title: 'Open client portal section', actionLabel: 'Open Portal', actionType: 'view_source', href: '#clients', source: 'readiness_registry' },
    admin_review: { title: 'Open admin review section', actionLabel: 'Open Admin', actionType: 'view_source', href: '#system', source: 'readiness_registry' },
  };
  return actionMap[areaKey] ?? null;
}
