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
    canClientUse: true,
    canAdminUse: true,
    requiresApproval: false,
    blocker: 'Manual-first only: credit report/document collection is outside Nexus, portal data is demo/static, and bureau/creditor/collector connectors remain blocked.',
    nextSafeAction: 'Open Readiness Intake and complete one synthetic or consented manual review without uploading documents to Nexus.',
    sourcePath: 'reports/goclear_activation/goclear_launch_readiness_report.md',
  },
  {
    areaKey: 'business_funding',
    displayName: 'Business Funding Workflow',
    status: 'partial',
    canHermesRead: true,
    canClientUse: true,
    canAdminUse: true,
    requiresApproval: false,
    blocker: 'Manual-first only: business details require human verification; no bank, lender, DUNS, EIN, or SOS integrations; affiliate URLs remain inactive.',
    nextSafeAction: 'Use the mounted intake and admin scorecard for a manual review, then hold any funding recommendation for Ray Review.',
    sourcePath: 'reports/goclear_activation/goclear_launch_readiness_report.md',
  },
  {
    areaKey: 'readiness_review_offer',
    displayName: '$97 Credit & Funding Readiness Review',
    status: 'partial',
    canHermesRead: true,
    canClientUse: true,
    canAdminUse: true,
    requiresApproval: true,
    blocker: 'Manual payment confirmation, document collection, Ray Review, and delivery are required. Production Stripe and email delivery are intentionally not active.',
    nextSafeAction: 'Open the mounted intake and run one no-charge synthetic fulfillment rehearsal before accepting a prospect.',
    sourcePath: 'reports/goclear_activation/goclear_launch_readiness_report.md',
  },
  {
    areaKey: 'client_onboarding',
    displayName: 'Client Onboarding',
    status: 'partial',
    canHermesRead: true,
    canClientUse: true,
    canAdminUse: true,
    requiresApproval: false,
    blocker: 'Manual checklist only. Payment confirmation, persistence, document handling, and client delivery are not automated.',
    nextSafeAction: 'Use the manual payment/onboarding checklist and do not record payment as confirmed without Ray verification.',
    sourcePath: 'reports/goclear_activation/goclear_launch_readiness_report.md',
  },
  {
    areaKey: 'client_portal',
    displayName: 'Client Portal',
    status: 'partial',
    canHermesRead: true,
    canClientUse: true,
    canAdminUse: true,
    requiresApproval: false,
    blocker: '9 pages built with real React components, but all driven by static demo data. No live Supabase reads on credit/funding tables.',
    nextSafeAction: 'Use the portal only as a clearly labeled demo/client preview until secure real-client persistence is approved.',
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
    nextSafeAction: 'Keep Nexus payment status unconfirmed; Ray may use a separately approved manual payment method outside this workflow.',
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
    nextSafeAction: 'Use draft copy only and deliver manually after Ray Review; do not configure or send email in this launch step.',
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
    nextSafeAction: 'Keep referral fields as inactive placeholders and show a free/DIY option with any future reviewed recommendation.',
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
    blocker: 'Local client report drafts are available, but persistence and delivery remain manual and Ray Review-gated.',
    nextSafeAction: 'Generate the local draft in Admin Review, review it, and do not deliver until Ray approves the exact output.',
    sourcePath: 'src/lib/readinessReviewReportDraft.ts',
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

export function getReadinessActionMetadata(areaKey: string): { title: string; actionLabel: string; actionType: 'open_report' | 'open_approval' | 'view_source' | 'draft_ray_review' | 'prepare_specialist_handoff' | 'open_intake' | 'open_scorecard' | 'open_report_template' | 'open_checklist' | 'draft_client_report' | 'draft_upgrade_recommendation'; href?: string; source: string } | null {
  const actionMap: Record<string, { title: string; actionLabel: string; actionType: 'open_report' | 'open_approval' | 'view_source' | 'draft_ray_review' | 'prepare_specialist_handoff' | 'open_intake' | 'open_scorecard' | 'open_report_template' | 'open_checklist' | 'draft_client_report' | 'draft_upgrade_recommendation'; href?: string; source: string }> = {
    credit_repair: { title: 'Open credit repair readiness report', actionLabel: 'Open Report', actionType: 'open_report', href: '#reports', source: 'readiness_registry' },
    business_funding: { title: 'Open business funding readiness report', actionLabel: 'Open Report', actionType: 'open_report', href: '#reports', source: 'readiness_registry' },
    readiness_review_offer: { title: 'Open readiness review offer audit', actionLabel: 'Open Audit', actionType: 'open_report', href: '#reports', source: 'readiness_registry' },
    ray_review: { title: 'Open Ray Review queue', actionLabel: 'Open Queue', actionType: 'open_approval', href: '#rayreview', source: 'readiness_registry' },
    specialist_handoff: { title: 'Prepare specialist handoff draft', actionLabel: 'Prepare Draft', actionType: 'prepare_specialist_handoff', source: 'readiness_registry' },
    client_portal: { title: 'Open client portal section', actionLabel: 'Open Portal', actionType: 'view_source', href: '#clients', source: 'readiness_registry' },
    admin_review: { title: 'Open admin review section', actionLabel: 'Open Admin', actionType: 'view_source', href: '#readiness-admin', source: 'readiness_registry' },
    goclear_launch: { title: 'Open GoClear launch readiness report', actionLabel: 'Open Launch Report', actionType: 'open_report', href: '#reports', source: 'readiness_registry' },
    goclear_processes: { title: 'Open GoClear safe process results', actionLabel: 'Open Process Results', actionType: 'open_report', href: '#reports', source: 'readiness_registry' },
    goclear_marketing: { title: 'Open GoClear marketing activation status', actionLabel: 'Open Marketing Status', actionType: 'open_report', href: '#reports', source: 'readiness_registry' },
    readiness_review_intake: { title: 'Open client intake form', actionLabel: 'Open Intake', actionType: 'open_intake', href: '#readiness-intake', source: 'readiness_registry' },
    readiness_review_scorecard: { title: 'Open manual scorecard', actionLabel: 'Open Scorecard', actionType: 'open_scorecard', href: '#readiness-admin', source: 'readiness_registry' },
    readiness_review_client_report: { title: 'Open client report template', actionLabel: 'Open Report Template', actionType: 'open_report_template', href: '#readiness-admin', source: 'readiness_registry' },
    readiness_review_admin_fulfillment: { title: 'Open fulfillment checklist', actionLabel: 'Open Checklist', actionType: 'open_checklist', href: '#readiness-admin', source: 'readiness_registry' },
    readiness_review_upgrade_path: { title: 'Draft upgrade recommendation', actionLabel: 'Draft Upgrade', actionType: 'draft_upgrade_recommendation', source: 'readiness_registry' },
    readiness_review_specialist_handoff: { title: 'Draft specialist handoff from review', actionLabel: 'Draft Handoff', actionType: 'prepare_specialist_handoff', source: 'readiness_registry' },
  };
  return actionMap[areaKey] ?? null;
}

export interface ReadinessWorkflow {
  workflowKey: string;
  displayName: string;
  triggerQuestion: string;
  steps: string[];
  outputArtifact: string;
  approvalRequired: boolean;
  specialistLane: string | null;
}

export const READINESS_WORKFLOWS: ReadinessWorkflow[] = [
  {
    workflowKey: 'readiness_review_intake',
    displayName: 'Client Intake for $97 Review',
    triggerQuestion: 'How do I start a new readiness review?',
    steps: [
      'Confirm payment received',
      'Open intake template',
      'Send intake questions to client',
      'Wait for responses',
      'Collect credit report information',
    ],
    outputArtifact: 'Client intake responses (conversation or form)',
    approvalRequired: false,
    specialistLane: null,
  },
  {
    workflowKey: 'readiness_review_scorecard',
    displayName: 'Manual Scoring for $97 Review',
    triggerQuestion: 'How do I score the client manually?',
    steps: [
      'Open scorecard template',
      'Score each of the 8 sections',
      'Calculate section totals',
      'Apply weights',
      'Sum weighted scores',
      'Match to readiness tier',
      'Check flags',
    ],
    outputArtifact: 'Completed scorecard with overall score and tier',
    approvalRequired: false,
    specialistLane: null,
  },
  {
    workflowKey: 'readiness_review_client_report',
    displayName: 'Client Report for $97 Review',
    triggerQuestion: 'How do I create the client report?',
    steps: [
      'Open client report template',
      'Fill in executive summary',
      'Insert readiness scores',
      'Write credit and funding findings',
      'List top 3 blockers',
      'Draft recommended next steps',
      'Add upgrade recommendation',
      'Add disclaimer',
      'Review via Ray Review',
      'Deliver to client',
    ],
    outputArtifact: 'Client-facing readiness report (draft)',
    approvalRequired: true,
    specialistLane: null,
  },
  {
    workflowKey: 'readiness_review_admin_fulfillment',
    displayName: 'Fulfillment Checklist for $97 Review',
    triggerQuestion: 'What is the fulfillment process?',
    steps: [
      'Confirm payment',
      'Collect intake',
      'Collect credit report',
      'Score client',
      'Draft report',
      'Review via Ray Review',
      'Deliver to client',
      'Offer upgrade',
      'Log completion',
      'Schedule follow-up',
    ],
    outputArtifact: 'Completed fulfillment record',
    approvalRequired: false,
    specialistLane: null,
  },
  {
    workflowKey: 'readiness_review_upgrade_path',
    displayName: 'Upgrade Recommendation from $97 Review',
    triggerQuestion: 'What is the upgrade recommendation?',
    steps: [
      'Check client readiness tier',
      'If Not Ready or Needs Cleanup: recommend $297 assistant',
      'If Almost Ready: recommend $297 to close gaps',
      'If Ready: recommend Monthly Readiness Subscription',
      'Draft recommendation',
      'Review via Ray Review',
      'Deliver to client',
    ],
    outputArtifact: 'Upgrade recommendation (conversation draft)',
    approvalRequired: true,
    specialistLane: null,
  },
  {
    workflowKey: 'readiness_review_specialist_handoff',
    displayName: 'Specialist Handoff from $97 Review',
    triggerQuestion: 'How do I hand off to a specialist from the review?',
    steps: [
      'Review completed readiness report',
      'Identify client needs (credit vs funding)',
      'Prepare specialist handoff draft',
      'Include readiness tier and blockers',
      'Include recommended next steps',
      'Review via Ray Review',
      'Assign to specialist (when live)',
    ],
    outputArtifact: 'Specialist handoff draft',
    approvalRequired: true,
    specialistLane: 'credit' as string,
  },
];

export function getReadinessWorkflow(workflowKey: string): ReadinessWorkflow | undefined {
  return READINESS_WORKFLOWS.find(w => w.workflowKey === workflowKey);
}

export function getReadinessWorkflowSummary(): string {
  return READINESS_WORKFLOWS.map(w => `${w.displayName}: ${w.steps.length} steps, approval ${w.approvalRequired ? 'required' : 'not required'}`).join('\n');
}
