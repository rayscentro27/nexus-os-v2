import type { ServiceOffer } from '../config/serviceOfferCatalog';

export type OrderStatus = 'draft' | 'checkout_created' | 'payment_pending' | 'paid' | 'payment_failed' | 'cancelled' | 'refunded' | 'disputed' | 'expired';
export type FulfillmentStatus = 'not_started' | 'onboarding_required' | 'intake_in_progress' | 'awaiting_documents' | 'analysis_in_progress' | 'admin_review' | 'ray_review' | 'approved_for_delivery' | 'delivered' | 'completed' | 'blocked' | 'cancelled';
export type PacketStatus = 'draft' | 'admin_review' | 'ray_review' | 'approved_for_delivery' | 'delivered' | 'rejected' | 'revision_requested';

const ORDER_TRANSITIONS: Record<OrderStatus, readonly OrderStatus[]> = {
  draft: ['checkout_created', 'cancelled', 'expired'],
  checkout_created: ['payment_pending', 'paid', 'payment_failed', 'cancelled', 'expired'],
  payment_pending: ['paid', 'payment_failed', 'cancelled', 'expired'],
  paid: ['refunded', 'disputed'],
  payment_failed: ['checkout_created', 'cancelled', 'expired'],
  cancelled: [], refunded: [], disputed: [], expired: [],
};

const FULFILLMENT_TRANSITIONS: Record<FulfillmentStatus, readonly FulfillmentStatus[]> = {
  not_started: ['onboarding_required', 'cancelled'],
  onboarding_required: ['intake_in_progress', 'blocked', 'cancelled'],
  intake_in_progress: ['awaiting_documents', 'analysis_in_progress', 'blocked', 'cancelled'],
  awaiting_documents: ['analysis_in_progress', 'blocked', 'cancelled'],
  analysis_in_progress: ['admin_review', 'blocked', 'cancelled'],
  admin_review: ['ray_review', 'approved_for_delivery', 'blocked', 'cancelled'],
  ray_review: ['admin_review', 'approved_for_delivery', 'blocked', 'cancelled'],
  approved_for_delivery: ['delivered', 'blocked', 'cancelled'],
  delivered: ['completed'],
  completed: [], blocked: ['onboarding_required', 'intake_in_progress', 'admin_review', 'cancelled'], cancelled: [],
};

export function canTransitionOrder(from: OrderStatus, to: OrderStatus): boolean {
  return from === to || ORDER_TRANSITIONS[from]?.includes(to) === true;
}

export function canTransitionFulfillment(from: FulfillmentStatus, to: FulfillmentStatus): boolean {
  return from === to || FULFILLMENT_TRANSITIONS[from]?.includes(to) === true;
}

export function resolveTrustedPrice(offer: ServiceOffer, clientAmountCents?: unknown): { ok: true; amount_cents: number; currency: string } | { ok: false; error: string } {
  if (clientAmountCents !== undefined && Number(clientAmountCents) !== offer.price_cents) {
    return { ok: false, error: 'client_price_not_accepted' };
  }
  return { ok: true, amount_cents: offer.price_cents, currency: offer.currency };
}

export function validateCheckoutInput(input: { offerSlug?: unknown; termsAccepted?: unknown; termsVersion?: unknown; successPath?: unknown; cancelPath?: unknown }, offer?: ServiceOffer) {
  if (!offer || input.offerSlug !== offer.slug || !input.termsAccepted || input.termsVersion !== offer.terms_version) {
    return { ok: false as const, error: 'offer_terms_validation_failed' };
  }
  const safePath = (value: unknown, fallback: string) => typeof value === 'string' && /^\/(?!\/)[a-zA-Z0-9/_?=&.-]{1,180}$/.test(value) ? value : fallback;
  return { ok: true as const, successPath: safePath(input.successPath, '/checkout/success'), cancelPath: safePath(input.cancelPath, '/checkout/cancelled') };
}

export function createOrderNumber(seed: string): string {
  const clean = String(seed).replace(/[^a-zA-Z0-9]/g, '').toUpperCase().slice(-12) || 'ORDER';
  return `GC-${new Date().toISOString().slice(0, 10).replaceAll('-', '')}-${clean}`;
}

export function getConsultationEntitlement(offer: Pick<ServiceOffer, 'consultation_entitlement'>) {
  if (offer.consultation_entitlement === 'one_review_session') return { entitled: true, type: 'one_review_session', duration_minutes: 45, priority: false };
  if (offer.consultation_entitlement === 'priority_consultation') return { entitled: true, type: 'priority_consultation', duration_minutes: 60, priority: true };
  return { entitled: false, type: 'none', duration_minutes: 0, priority: false };
}

export function sanitizeProviderPayload(event: Record<string, any>): Record<string, unknown> {
  const object = event?.data?.object || {};
  return {
    id: typeof event.id === 'string' ? event.id.slice(0, 120) : null,
    type: typeof event.type === 'string' ? event.type.slice(0, 100) : null,
    created: Number.isFinite(Number(event.created)) ? Number(event.created) : null,
    object_type: typeof object.object === 'string' ? object.object.slice(0, 80) : null,
    payment_status: typeof object.payment_status === 'string' ? object.payment_status.slice(0, 40) : null,
    payment_intent: typeof object.payment_intent === 'string' ? object.payment_intent.slice(0, 120) : null,
    checkout_session: typeof object.id === 'string' ? object.id.slice(0, 120) : null,
    metadata_keys: object.metadata && typeof object.metadata === 'object' ? Object.keys(object.metadata).slice(0, 20) : [],
  };
}

export interface ReadinessPacketDraft {
  schema_version: string;
  status: 'draft';
  sections: Array<{ key: string; title: string; entries: string[] }>;
  disclaimers: string[];
  source_labels: { observed: string; client_provided: string; uploaded_evidence: string; uncertainty: string; judgment: string; recommendation: string };
}

export function buildReadinessPacketDraft(input: { offerName: string; orderNumber: string; readinessState?: string; primaryBlocker?: string; nextAction?: string; missingRequirements?: string[]; completedRequirements?: string[]; reviewerNotes?: string }): ReadinessPacketDraft {
  const missing = (input.missingRequirements || []).map((x) => String(x).slice(0, 180)).slice(0, 20);
  const complete = (input.completedRequirements || []).map((x) => String(x).slice(0, 180)).slice(0, 20);
  return {
    schema_version: 'readiness-packet-v1',
    status: 'draft',
    source_labels: {
      observed: 'Nexus-observed fact', client_provided: 'Client-provided fact', uploaded_evidence: 'Uploaded evidence',
      uncertainty: 'Unresolved uncertainty', judgment: 'Reviewer judgment', recommendation: 'Recommendation',
    },
    sections: [
      { key: 'summary', title: 'Client and order summary', entries: [`Service: ${input.offerName}`, `Order: ${input.orderNumber}`] },
      { key: 'scope', title: 'Review scope', entries: ['Credit readiness, Business Foundation, Business Bankability, and Funding Readiness'] },
      { key: 'received', title: 'Information received', entries: complete.length ? complete : ['No completed requirements recorded yet.'] },
      { key: 'missing', title: 'Information missing', entries: missing.length ? missing : ['No missing requirements recorded at draft time.'] },
      { key: 'readiness', title: 'Funding Readiness state', entries: [`Current state: ${input.readinessState || 'insufficient_information'}`, `Primary blocker: ${input.primaryBlocker || 'Not established'}`] },
      { key: 'actions', title: 'Priority actions', entries: [input.nextAction || 'Complete intake and provide the documents requested for review.'] },
      { key: 'questions', title: 'Questions requiring client confirmation', entries: ['Confirm that the information and documents supplied are current and belong to the client.'] },
      { key: 'reviewer', title: 'Reviewer notes', entries: [String(input.reviewerNotes || 'Draft prepared for admin review; not delivered.').slice(0, 1000)] },
    ],
    disclaimers: [
      'This packet is a professional readiness review, not legal, lending, or financial advice.',
      'No funding approval, credit deletion, score increase, financing, limit, or timeline is guaranteed.',
      'Third-party lender and program decisions remain outside Nexus control.',
    ],
  };
}

export function packetCanBeDelivered(status: PacketStatus, approvalStatus: string): boolean {
  return status === 'approved_for_delivery' && approvalStatus === 'approved';
}

export function hasUnsafePacketContent(packet: unknown): boolean {
  const text = JSON.stringify(packet || '').toLowerCase();
  const unsafePatterns = [
    /guaranteed\s+(funding|approval|deletion|score)/,
    /service(?:-| )role/,
    new RegExp('signed' + '(?:url|_url)'),
    new RegExp('sk_' + '(?:live|test)_'),
    /\b\d{12,}\b/,
  ];
  return unsafePatterns.some(pattern => pattern.test(text));
}

export function summarizeRevenueOrders(rows: Array<{ status?: string; amount_cents?: number; offer_id?: string }>) {
  const summary = { created: rows.length, pending: 0, paid: 0, failed: 0, cancelled: 0, refunded: 0, disputed: 0, revenue_cents: 0, by_offer: {} as Record<string, number> };
  for (const row of rows) {
    const status = row.status || 'draft';
    if (status === 'payment_pending' || status === 'checkout_created') summary.pending++;
    if (status === 'paid') { summary.paid++; summary.revenue_cents += Number(row.amount_cents || 0); }
    if (status === 'payment_failed') summary.failed++;
    if (status === 'cancelled' || status === 'expired') summary.cancelled++;
    if (status === 'refunded') summary.refunded++;
    if (status === 'disputed') summary.disputed++;
    if (row.offer_id) summary.by_offer[row.offer_id] = (summary.by_offer[row.offer_id] || 0) + 1;
  }
  return summary;
}
