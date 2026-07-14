/**
 * Nexus Credit Repair Workflow v1 — Adapter
 *
 * Provides types, data loading, draft letter generation, and approval-gated
 * DocuPost send flow. No automatic sending. No SSN, DOB, or full account numbers.
 */

import { supabase, isSupabaseConfigured } from './supabaseClient';
import { resolveClientContextForCurrentUser, type ResolvedClientContext } from './clientAuthContext';

// ─── Types ───────────────────────────────────────────────────────────────────

export type CreditJourneyStep =
  | 'profile'
  | 'upload_report'
  | 'specialist_review'
  | 'dispute_items'
  | 'draft_letters'
  | 'approve_send'
  | 'track_results';

export type CreditReportReviewStatus =
  | 'pending_review'
  | 'in_review'
  | 'items_identified'
  | 'drafts_ready'
  | 'client_review'
  | 'approved_for_docupost'
  | 'sent_manual'
  | 'waiting_response'
  | 'completed'
  | 'blocked';

export type DisputeItemStatus =
  | 'identified'
  | 'draft_needed'
  | 'draft_ready'
  | 'specialist_review'
  | 'client_review'
  | 'client_approved'
  | 'approved_for_docupost'
  | 'sent_docupost'
  | 'response_received'
  | 'resolved'
  | 'rejected'
  | 'needs_next_round';

export type DisputeItemBureau = 'experian' | 'equifax' | 'transunion' | 'unknown';

export type DisputeItemAction = 'verify' | 'correct' | 'delete' | 'update' | 'investigate';

export type DisputeLetterRecipientType = 'bureau' | 'furnisher';

export type CreditDisputeLetterStatus =
  | 'draft'
  | 'specialist_review'
  | 'ray_review'
  | 'client_review'
  | 'client_approved'
  | 'approved_for_docupost'
  | 'docupost_queued'
  | 'docupost_mailed'
  | 'docupost_delivered'
  | 'response_received'
  | 'archived';

export type DocuPostJobStatus =
  | 'not_sent'
  | 'approval_required'
  | 'approved_to_send'
  | 'docupost_ready'
  | 'queued'
  | 'mailed'
  | 'delivered'
  | 'failed'
  | 'canceled';

export interface CreditReportReview {
  id: string;
  tenant_id: string;
  client_id: string;
  document_id: string | null;
  assigned_specialist: string | null;
  status: CreditReportReviewStatus;
  review_notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreditDisputeItem {
  id: string;
  tenant_id: string;
  client_id: string;
  review_id: string | null;
  bureau: DisputeItemBureau;
  furnisher_name: string | null;
  account_name: string | null;
  account_number_mask: string | null;
  item_type: string | null;
  dispute_reason: string | null;
  factual_basis: string | null;
  requested_action: DisputeItemAction | null;
  evidence_document_ids: string[];
  status: DisputeItemStatus;
  specialist_notes: string | null;
  client_visible: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreditDisputeLetter {
  id: string;
  tenant_id: string;
  client_id: string;
  dispute_item_ids: string[];
  recipient_type: DisputeLetterRecipientType;
  recipient_name: string | null;
  letter_body: string;
  status: CreditDisputeLetterStatus;
  generated_by: string;
  approval_required: boolean;
  client_approved_at: string | null;
  specialist_approved_at: string | null;
  docupost_job_id: string | null;
  sent_at: string | null;
  response_due_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocuPostMailJob {
  id: string;
  tenant_id: string;
  client_id: string;
  letter_id: string | null;
  provider: string;
  provider_job_id: string | null;
  status: DocuPostJobStatus;
  recipient_name: string | null;
  recipient_address: Record<string, string>;
  mail_type: string;
  tracking_number: string | null;
  request_payload: Record<string, unknown>;
  response_payload: Record<string, unknown>;
  error_message: string | null;
  approval_required: boolean;
  approved_by_client: boolean;
  approved_by_specialist: boolean;
  queued_at: string | null;
  mailed_at: string | null;
  delivered_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreditRepairJourneyData {
  reviews: CreditReportReview[];
  disputeItems: CreditDisputeItem[];
  letters: CreditDisputeLetter[];
  mailJobs: DocuPostMailJob[];
  currentStep: CreditJourneyStep;
  stepsCompleted: CreditJourneyStep[];
}

// ─── Data Loading ────────────────────────────────────────────────────────────

export async function loadCreditRepairJourney(ctx?: ResolvedClientContext): Promise<CreditRepairJourneyData> {
  let context = ctx ?? null;
  if (!context) context = await resolveClientContextForCurrentUser();

  const empty: CreditRepairJourneyData = {
    reviews: [], disputeItems: [], letters: [], mailJobs: [],
    currentStep: 'profile', stepsCompleted: [],
  };

  if (!context) return empty;
  if (!isSupabaseConfigured || !supabase) return empty;

  try {
    const [reviewsRes, itemsRes, lettersRes, jobsRes] = await Promise.all([
      supabase.from('credit_report_reviews').select('*').eq('client_id', context.clientId).order('created_at', { ascending: false }),
      supabase.from('credit_dispute_items').select('*').eq('client_id', context.clientId).order('created_at', { ascending: false }),
      supabase.from('credit_dispute_letters').select('*').eq('client_id', context.clientId).order('created_at', { ascending: false }),
      supabase.from('docupost_mail_jobs').select('*').eq('client_id', context.clientId).order('created_at', { ascending: false }),
    ]);

    const reviews = (reviewsRes.data ?? []) as CreditReportReview[];
    const disputeItems = (itemsRes.data ?? []) as CreditDisputeItem[];
    const letters = (lettersRes.data ?? []) as CreditDisputeLetter[];
    const mailJobs = (jobsRes.data ?? []) as DocuPostMailJob[];

    const stepsCompleted: CreditJourneyStep[] = [];
    let currentStep: CreditJourneyStep = 'profile';

    if (reviews.length > 0) {
      stepsCompleted.push('profile');
      currentStep = 'upload_report';
    }
    if (reviews.some(r => r.status !== 'pending_review')) {
      stepsCompleted.push('upload_report');
      currentStep = 'specialist_review';
    }
    if (reviews.some(r => ['items_identified', 'drafts_ready', 'client_review', 'approved_for_docupost', 'completed'].includes(r.status))) {
      stepsCompleted.push('specialist_review');
      currentStep = 'dispute_items';
    }
    if (disputeItems.length > 0) {
      stepsCompleted.push('dispute_items');
      currentStep = 'draft_letters';
    }
    if (letters.length > 0) {
      stepsCompleted.push('draft_letters');
      currentStep = 'approve_send';
    }
    if (letters.some(l => ['docupost_queued', 'docupost_mailed', 'docupost_delivered'].includes(l.status))) {
      stepsCompleted.push('approve_send');
      currentStep = 'track_results';
    }

    return { reviews, disputeItems, letters, mailJobs, currentStep, stepsCompleted };
  } catch {
    return empty;
  }
}

// ─── Credit Report Review ────────────────────────────────────────────────────

export async function createCreditReportReview(
  clientId: string,
  tenantId: string,
  documentId?: string,
): Promise<{ ok: boolean; id?: string; error?: string }> {
  if (!isSupabaseConfigured || !supabase) return { ok: false, error: 'Supabase not configured' };

  const id = crypto.randomUUID();
  const { error } = await supabase.from('credit_report_reviews').insert({
    id,
    tenant_id: tenantId,
    client_id: clientId,
    document_id: documentId ?? null,
    status: 'pending_review',
  });

  if (error) return { ok: false, error: error.message };
  return { ok: true, id };
}

// ─── Dispute Items ───────────────────────────────────────────────────────────

export async function createDisputeItem(input: {
  clientId: string;
  tenantId: string;
  reviewId?: string;
  bureau: string;
  furnisherName?: string;
  accountName?: string;
  accountNumberMask?: string;
  disputeReason: string;
  factualBasis: string;
  requestedAction: DisputeItemAction;
  evidenceDocumentIds?: string[];
}): Promise<{ ok: boolean; id?: string; error?: string }> {
  if (!isSupabaseConfigured || !supabase) return { ok: false, error: 'Supabase not configured' };

  const id = crypto.randomUUID();
  const { error } = await supabase.from('credit_dispute_items').insert({
    id,
    tenant_id: input.tenantId,
    client_id: input.clientId,
    review_id: input.reviewId ?? null,
    bureau: input.bureau,
    furnisher_name: input.furnisherName ?? null,
    account_name: input.accountName ?? null,
    account_number_mask: input.accountNumberMask ?? null,
    dispute_reason: input.disputeReason,
    factual_basis: input.factualBasis,
    requested_action: input.requestedAction,
    evidence_document_ids: input.evidenceDocumentIds ?? [],
    status: 'identified',
  });

  if (error) return { ok: false, error: error.message };
  return { ok: true, id };
}

// ─── Draft Letter Generation ─────────────────────────────────────────────────

export function generateDisputeLetterBody(input: {
  clientName?: string;
  clientAddress?: string;
  recipientName?: string;
  recipientAddress?: string;
  bureau?: string;
  items: Array<{
    furnisherName?: string;
    accountName?: string;
    accountNumberMask?: string;
    disputeReason?: string;
    factualBasis?: string;
    requestedAction?: string;
  }>;
  evidenceLabels?: string[];
}): string {
  const today = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
  const clientName = input.clientName || '[Client Name]';
  const clientAddress = input.clientAddress || '[Client Address]';
  const recipientName = input.recipientName || input.bureau || '[Recipient]';
  const recipientAddress = input.recipientAddress || '[Recipient Address]';

  const itemLines = input.items.map((item, i) => {
    const action = item.requestedAction ? item.requestedAction.charAt(0).toUpperCase() + item.requestedAction.slice(1) : 'Investigate';
    return `  ${i + 1}. ${action} the following account:\n` +
      `     Account: ${item.accountName || '[Account]'} (${item.accountNumberMask || 'XXXX'})\n` +
      `     Furnisher: ${item.furnisherName || '[Furnisher]'}\n` +
      `     Reason: ${item.disputeReason || '[Reason]'}\n` +
      `     Basis: ${item.factualBasis || '[Factual basis]'}`;
  }).join('\n\n');

  const evidenceSection = input.evidenceLabels && input.evidenceLabels.length > 0
    ? `\n\nEnclosed documents:\n${input.evidenceLabels.map((l, i) => `  ${i + 1}. ${l}`).join('\n')}`
    : '';

  return [
    `${clientName}`,
    `${clientAddress}`,
    '',
    today,
    '',
    `${recipientName}`,
    `${recipientAddress}`,
    '',
    'Re: Dispute of Inaccurate Information — Fair Credit Reporting Act (FCRA)',
    '',
    `Dear ${recipientName},`,
    '',
    'I am writing to dispute the following information on my credit report. I believe the following items are inaccurate or incomplete and request investigation under the Fair Credit Reporting Act, 15 U.S.C. § 1681.',
    '',
    'Disputed items:',
    '',
    itemLines,
    '',
    'I have enclosed supporting documentation for your review. Please investigate these items and correct or remove the inaccurate information as required by law.',
    '',
    'Please send me an updated copy of my credit report once the investigation is complete.',
    '',
    'Sincerely,',
    clientName,
    evidenceSection,
  ].join('\n');
}

// ─── Dispute Letters ─────────────────────────────────────────────────────────

export async function createDisputeLetterDraft(input: {
  tenantId: string;
  clientId: string;
  disputeItemIds: string[];
  recipientType: DisputeLetterRecipientType;
  recipientName: string;
  letterBody: string;
}): Promise<{ ok: boolean; id?: string; error?: string }> {
  if (!isSupabaseConfigured || !supabase) return { ok: false, error: 'Supabase not configured' };

  const id = crypto.randomUUID();
  const { error } = await supabase.from('credit_dispute_letters').insert({
    id,
    tenant_id: input.tenantId,
    client_id: input.clientId,
    dispute_item_ids: input.disputeItemIds,
    recipient_type: input.recipientType,
    recipient_name: input.recipientName,
    letter_body: input.letterBody,
    status: 'draft',
    generated_by: 'nexus_draft_engine',
    approval_required: true,
  });

  if (error) return { ok: false, error: error.message };
  return { ok: true, id };
}

export async function approveLetterForSpecialistReview(letterId: string): Promise<{ ok: boolean; error?: string }> {
  if (!isSupabaseConfigured || !supabase) return { ok: false, error: 'Supabase not configured' };

  const { error } = await supabase.from('credit_dispute_letters').update({
    status: 'specialist_review',
    updated_at: new Date().toISOString(),
  }).eq('id', letterId);

  if (error) return { ok: false, error: error.message };
  return { ok: true };
}

export async function specialistApproveLetter(letterId: string): Promise<{ ok: boolean; error?: string }> {
  if (!isSupabaseConfigured || !supabase) return { ok: false, error: 'Supabase not configured' };

  const { error } = await supabase.from('credit_dispute_letters').update({
    status: 'client_review',
    specialist_approved_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  }).eq('id', letterId);

  if (error) return { ok: false, error: error.message };
  return { ok: true };
}

export async function clientApproveLetter(letterId: string): Promise<{ ok: boolean; error?: string }> {
  if (!isSupabaseConfigured || !supabase) return { ok: false, error: 'Supabase not configured' };

  const { error } = await supabase.from('credit_dispute_letters').update({
    status: 'client_approved',
    client_approved_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  }).eq('id', letterId);

  if (error) return { ok: false, error: error.message };
  return { ok: true };
}

// ─── DocuPost Send Flow ──────────────────────────────────────────────────────

export async function createDocuPostSendRequest(letterId: string): Promise<{ ok: boolean; jobId?: string; error?: string }> {
  if (!isSupabaseConfigured || !supabase) return { ok: false, error: 'Supabase not configured' };

  const letterRes = await supabase.from('credit_dispute_letters').select('*').eq('id', letterId).single();
  if (letterRes.error || !letterRes.data) return { ok: false, error: 'Letter not found' };

  const letter = letterRes.data as CreditDisputeLetter;
  const jobId = crypto.randomUUID();

  const { error: jobError } = await supabase.from('docupost_mail_jobs').insert({
    id: jobId,
    tenant_id: letter.tenant_id,
    client_id: letter.client_id,
    letter_id: letterId,
    provider: 'docupost',
    status: 'approval_required',
    recipient_name: letter.recipient_name,
    recipient_address: {},
    mail_type: 'certified',
    approval_required: true,
    approved_by_client: false,
    approved_by_specialist: false,
  });

  if (jobError) return { ok: false, error: jobError.message };

  await supabase.from('credit_dispute_letters').update({
    status: 'approved_for_docupost',
    docupost_job_id: jobId,
    updated_at: new Date().toISOString(),
  }).eq('id', letterId);

  return { ok: true, jobId };
}

export async function approveMailJobForSend(jobId: string, approvedBy: 'client' | 'specialist'): Promise<{ ok: boolean; error?: string }> {
  if (!isSupabaseConfigured || !supabase) return { ok: false, error: 'Supabase not configured' };

  const update: Record<string, unknown> = { updated_at: new Date().toISOString() };
  if (approvedBy === 'client') update.approved_by_client = true;
  if (approvedBy === 'specialist') update.approved_by_specialist = true;

  const { data: job, error: fetchError } = await supabase.from('docupost_mail_jobs').select('*').eq('id', jobId).single();
  if (fetchError || !job) return { ok: false, error: 'Job not found' };

  const bothApproved = approvedBy === 'client' ? job.approved_by_specialist : job.approved_by_client;
  if (bothApproved) {
    update.status = 'approved_to_send';
  }

  const { error } = await supabase.from('docupost_mail_jobs').update(update).eq('id', jobId);
  if (error) return { ok: false, error: error.message };
  return { ok: true };
}

export async function markMailJobSent(jobId: string, trackingNumber: string): Promise<{ ok: boolean; error?: string }> {
  if (!isSupabaseConfigured || !supabase) return { ok: false, error: 'Supabase not configured' };

  const { error } = await supabase.from('docupost_mail_jobs').update({
    status: 'mailed',
    tracking_number: trackingNumber,
    mailed_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  }).eq('id', jobId);

  if (error) return { ok: false, error: error.message };

  const { data: job } = await supabase.from('docupost_mail_jobs').select('letter_id').eq('id', jobId).single();
  if (job?.letter_id) {
    await supabase.from('credit_dispute_letters').update({
      status: 'docupost_mailed',
      sent_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }).eq('id', job.letter_id);
  }

  return { ok: true };
}

// ─── Parser Results (Admin Workbench) ─────────────────────────────────────

export interface ParserResultSummary {
  id: string;
  documentId: string | null;
  sourceFileName: string | null;
  parserVersion: string | null;
  extractionMode: string | null;
  extractionSuccess: boolean;
  textLength: number;
  confidence: string | null;
  accounts: Array<Record<string, unknown>>;
  accountsCount: number;
  inquiries: Array<Record<string, unknown>>;
  inquiriesCount: number;
  reviewCandidates: Array<Record<string, unknown>>;
  reviewCandidatesCount: number;
  negativeCandidatesCount: number;
  personalInfoVariations: Array<Record<string, unknown>>;
  structuredItemDrafts: Array<Record<string, unknown>>;
  structuredItemDraftsCount: number;
  recommendedActions: Array<Record<string, unknown>>;
  recommendedActionsCount: number;
  disputeSuggestionsCount: number;
  utilizationSummary: Record<string, unknown>;
  bureausDetected: string[];
  warnings: Array<{ code: string; message: string; severity: string }>;
  letterPreview: string | null;
  status: string;
  needsSpecialistReview: boolean;
  createdAt: string;
}

export async function loadParserResultForDocument(documentId: string): Promise<ParserResultSummary | null> {
  if (!isSupabaseConfigured || !supabase) return null;
  try {
    const { data, error } = await supabase
      .from('credit_report_parser_results')
      .select('*')
      .eq('document_id', documentId)
      .eq('extraction_success', true)
      .order('created_at', { ascending: false })
      .limit(1)
      .maybeSingle();
    if (error || !data) return null;
    return summarizeParserResult(data);
  } catch {
    return null;
  }
}

export async function loadParserResultsForDocumentIds(documentIds: string[]): Promise<Record<string, ParserResultSummary>> {
  if (!isSupabaseConfigured || !supabase || documentIds.length === 0) return {};
  try {
    const { data, error } = await supabase
      .from('credit_report_parser_results')
      .select('*')
      .in('document_id', documentIds)
      .eq('extraction_success', true)
      .order('created_at', { ascending: false });
    if (error || !data) return {};
    const map: Record<string, ParserResultSummary> = {};
    for (const row of data as Record<string, unknown>[]) {
      const docId = row.document_id as string;
      if (docId && !map[docId]) {
        map[docId] = summarizeParserResult(row);
      }
    }
    return map;
  } catch {
    return {};
  }
}

function parseJsonbField(value: unknown): unknown {
  // Handle double-encoded jsonb: worker sent json.dumps() string instead of raw object
  if (typeof value === 'string' && value.length > 0) {
    try {
      const parsed = JSON.parse(value);
      return parsed;
    } catch {
      return value;
    }
  }
  return value;
}

function summarizeParserResult(row: Record<string, unknown>): ParserResultSummary {
  const accountsRaw = parseJsonbField(row.accounts);
  const inquiriesRaw = parseJsonbField(row.inquiries);
  const negativeRaw = parseJsonbField(row.negative_candidates);
  const draftsRaw = parseJsonbField(row.structured_item_drafts);
  const suggestionsRaw = parseJsonbField(row.dispute_strategy_suggestions);
  const warningsRaw = parseJsonbField(row.warnings);
  const bureausRaw = parseJsonbField(row.bureaus_detected);
  const utilizationRaw = parseJsonbField(row.utilization_summary);
  const personalRaw = parseJsonbField(row.personal_info_variations);

  const accounts = Array.isArray(accountsRaw) ? accountsRaw : [];
  const inquiries = Array.isArray(inquiriesRaw) ? inquiriesRaw : [];
  const negativeCandidates = Array.isArray(negativeRaw) ? negativeRaw : [];
  const structuredDrafts = Array.isArray(draftsRaw) ? draftsRaw : [];
  const suggestions = Array.isArray(suggestionsRaw) ? suggestionsRaw : [];
  const warnings = Array.isArray(warningsRaw) ? warningsRaw : [];
  const bureaus = Array.isArray(bureausRaw) ? bureausRaw : [];
  const utilization = (utilizationRaw && typeof utilizationRaw === 'object' && !Array.isArray(utilizationRaw)) ? utilizationRaw as Record<string, unknown> : {};
  const personalInfoVariations = Array.isArray(personalRaw) ? personalRaw : [];

  return {
    id: row.id as string,
    documentId: row.document_id as string | null,
    sourceFileName: row.source_file_name as string | null,
    parserVersion: row.parser_version as string | null,
    extractionMode: row.extraction_mode as string | null,
    extractionSuccess: Boolean(row.extraction_success),
    textLength: (row.text_length as number) || 0,
    confidence: row.confidence as string | null,
    accounts: accounts as Array<Record<string, unknown>>,
    accountsCount: accounts.length,
    inquiries: inquiries as Array<Record<string, unknown>>,
    inquiriesCount: inquiries.length,
    reviewCandidates: negativeCandidates as Array<Record<string, unknown>>,
    reviewCandidatesCount: negativeCandidates.length,
    negativeCandidatesCount: negativeCandidates.length,
    personalInfoVariations: personalInfoVariations as Array<Record<string, unknown>>,
    structuredItemDrafts: structuredDrafts as Array<Record<string, unknown>>,
    structuredItemDraftsCount: structuredDrafts.length,
    recommendedActions: suggestions as Array<Record<string, unknown>>,
    recommendedActionsCount: suggestions.length,
    disputeSuggestionsCount: suggestions.length,
    utilizationSummary: utilization,
    bureausDetected: bureaus as string[],
    warnings: warnings as ParserResultSummary['warnings'],
    letterPreview: row.letter_preview as string | null,
    status: (row.status as string) || 'suggested_extraction',
    needsSpecialistReview: Boolean(row.needs_specialist_review),
    createdAt: (row.created_at as string) || '',
  };
}

export interface CreditSystemReviewSummary {
  id: string; documentId: string; parserResultId: string | null; status: string; clientVisible: boolean;
  summary: Record<string, unknown>; fundingImpactItems: Array<Record<string, unknown>>; utilizationActions: Array<Record<string, unknown>>;
  reportItemReviews: Array<Record<string, unknown>>; inquiryReviews: Array<Record<string, unknown>>; personalInfoReviews: Array<Record<string, unknown>>;
  evidenceNeeded: Array<Record<string, unknown>>; specialistExceptions: Array<Record<string, unknown>>; noActionItems: Array<Record<string, unknown>>;
  recommendedNextSteps: string[]; confidenceSummary: Record<string, unknown>; tier1Impact: Record<string, unknown>; tier2Impact: Record<string, unknown>;
}

const arrayField = (value: unknown) => { const parsed = parseJsonbField(value); return Array.isArray(parsed) ? parsed as Array<Record<string, unknown>> : [] }
const objectField = (value: unknown) => { const parsed = parseJsonbField(value); return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed as Record<string, unknown> : {} }
function summarizeSystemReview(row: Record<string, unknown>): CreditSystemReviewSummary {
  return { id: row.id as string, documentId: row.document_id as string, parserResultId: row.parser_result_id as string | null, status: String(row.status || 'pending_review'), clientVisible: Boolean(row.client_visible), summary: objectField(row.summary), fundingImpactItems: arrayField(row.funding_impact_items), utilizationActions: arrayField(row.utilization_actions), reportItemReviews: arrayField(row.report_item_reviews), inquiryReviews: arrayField(row.inquiry_reviews), personalInfoReviews: arrayField(row.personal_info_reviews), evidenceNeeded: arrayField(row.evidence_needed), specialistExceptions: arrayField(row.specialist_exceptions), noActionItems: arrayField(row.no_action_items), recommendedNextSteps: arrayField(row.recommended_next_steps).map(String), confidenceSummary: objectField(row.confidence_summary), tier1Impact: objectField(row.tier_1_impact), tier2Impact: objectField(row.tier_2_impact) }
}
export async function loadSystemReviewForDocument(documentId: string): Promise<CreditSystemReviewSummary | null> {
  if (!isSupabaseConfigured || !supabase) return null;
  const { data, error } = await supabase.from('credit_report_system_reviews').select('*').eq('document_id', documentId).order('created_at', { ascending: false }).limit(1).maybeSingle();
  return error || !data ? null : summarizeSystemReview(data as Record<string, unknown>);
}
const ACTIVE_ANALYSIS_STATUSES = ['queued','processing'];
const CURRENT_PARSER_VERSION = 'live-0.1.0';
export async function queueCreditReportAnalysis(input: { tenantId: string; clientId: string; documentId: string }) {
  if (!isSupabaseConfigured || !supabase) return { ok: false, error: 'Supabase is not configured.' };
  const { data: active } = await supabase.from('credit_analysis_jobs').select('id,status').eq('document_id', input.documentId).eq('analysis_type','three_bureau_credit_report').eq('parser_version',CURRENT_PARSER_VERSION).in('status', ACTIVE_ANALYSIS_STATUSES).limit(1).maybeSingle();
  if (active) return { ok: true, job: active, duplicatePrevented: true };
  const { data: complete } = await supabase.from('credit_analysis_jobs').select('id,status').eq('document_id',input.documentId).eq('analysis_type','three_bureau_credit_report').eq('parser_version',CURRENT_PARSER_VERSION).eq('status','complete').is('superseded_by_job_id',null).limit(1).maybeSingle();
  if (complete) return { ok:true, job:complete, duplicatePrevented:true, completedVersionExists:true };
  const { data, error } = await supabase.from('credit_analysis_jobs').insert({ tenant_id: input.tenantId, client_id: input.clientId, document_id: input.documentId, status: 'queued', analysis_type:'three_bureau_credit_report', parser_version:CURRENT_PARSER_VERSION, ruleset_version:'canonical-v1', idempotency_key:`${input.documentId}:three_bureau_credit_report:${CURRENT_PARSER_VERSION}`, requested_reason:'admin recovery queue action' }).select('id,status').single();
  return error ? { ok: false, error: error.message } : { ok: true, job: data, duplicatePrevented: false };
}
export async function requestCreditAnalysisRerun(documentId:string,reason:string){
  if(!isSupabaseConfigured||!supabase)return {ok:false,error:'Supabase is not configured.'};
  if(reason.trim().length<5)return {ok:false,error:'A rerun reason is required.'};
  const {data,error}=await supabase.rpc('request_credit_analysis_rerun',{p_document_id:documentId,p_reason:reason.trim()});
  return error?{ok:false,error:error.message}:{ok:true,jobId:data};
}
export async function loadLatestAnalysisJob(documentId: string) {
  if (!isSupabaseConfigured || !supabase) return null;
  const { data } = await supabase.from('credit_analysis_jobs').select('id,status,failure_code,failure_message,parser_version,worker_version,ruleset_version,attempt_count,max_attempts,claimed_at,started_at,completed_at,created_at,updated_at').eq('document_id', documentId).order('created_at', { ascending: false }).limit(1).maybeSingle();
  return data || null;
}

// ─── Pending Credit Report Reviews (Admin Queue Bridge) ─────────────────────

export interface PendingCreditReportReview {
  reviewId: string;
  documentId: string;
  clientId: string;
  tenantId: string;
  clientName: string | null;
  clientEmail: string | null;
  fileName: string;
  category: string | null;
  suggestedCategory: string | null;
  status: string;
  goclearReviewStatus: string | null;
  uploadedAt: string;
  source: string | null;
  reviewStatusLabel: string;
  parserStatus: 'not_parsed' | 'suggested_extraction_available' | 'ocr_required' | 'needs_specialist_review';
  nextActionLabel: string;
  documentStatus: string;
  analysisStatus: string;
  strategyStatus: string;
  clientActionStatus: string;
  exceptionReviewStatus: string;
  mailStatus: string;
  analysisJobStatus: string | null;
  parserVersion: string | null;
  canonicalAccountsCount: number;
  unmatchedTradelinesCount: number;
  discrepanciesCount: number;
  exceptionCount: number;
  accountsParsed: number;
  inquiriesCount: number;
  bureauCount: number;
}

function isCreditReportDocument(doc: Record<string, unknown>): boolean {
  const text = [
    doc.category,
    doc.suggested_category,
    doc.document_type,
    doc.source,
    doc.title,
    doc.file_name,
  ].filter(Boolean).map(String).join(' ').toLowerCase();
  return text.includes('credit') && (text.includes('report') || text.includes('tradeline') || text.includes('bureau'));
}

export async function loadPendingCreditReportReviews(): Promise<PendingCreditReportReview[]> {
  if (!isSupabaseConfigured || !supabase) return [];

  try {
    const { data: docs, error } = await supabase
      .from('client_documents')
      .select('*')
      .eq('client_visible', true)
      .order('created_at', { ascending: false });

    if (error || !docs) return [];

    const creditReportDocs = docs.filter((doc: Record<string, unknown>) => isCreditReportDocument(doc));

    if (creditReportDocs.length === 0) return [];

    const clientIds = [...new Set(creditReportDocs.map((d: Record<string, unknown>) => d.client_id).filter(Boolean))];
    let clientMap: Record<string, { name: string | null; email: string | null }> = {};

    if (clientIds.length > 0) {
      try {
        const { data: profiles } = await supabase
          .from('client_profiles')
          .select('id, full_name, business_name, email')
          .in('id', clientIds);

        if (profiles) {
          for (const p of profiles as Record<string, unknown>[]) {
            clientMap[p.id as string] = {
              name: (p.full_name as string) || (p.business_name as string) || null,
              email: (p.email as string) || null,
            };
          }
        }
      } catch {
        // RLS or schema may prevent join — show unknown client
      }
    }

    const documentIds=creditReportDocs.map((d:Record<string,unknown>)=>String(d.id));
    const [workflowRes,jobRes,parserRes,canonicalRes,unmatchedRes,discrepancyRes]=await Promise.all([
      supabase.from('credit_document_workflows').select('*').in('document_id',documentIds),
      supabase.from('credit_analysis_jobs').select('document_id,status,parser_version,created_at').in('document_id',documentIds).order('created_at',{ascending:false}),
      supabase.from('credit_report_parser_results').select('document_id,parser_version,accounts,inquiries,bureaus_detected,needs_specialist_review,created_at').in('document_id',documentIds).eq('extraction_success',true).order('created_at',{ascending:false}),
      supabase.from('credit_canonical_accounts').select('document_id,id').in('document_id',documentIds),
      supabase.from('credit_unmatched_tradelines').select('document_id,id,exception_required').in('document_id',documentIds),
      supabase.from('credit_report_discrepancies').select('document_id,id,exception_review_required').in('document_id',documentIds),
    ]);
    const firstMap=(rows:any[]|null,key:string)=>{const m:Record<string,any>={};for(const row of rows||[])if(!m[row[key]])m[row[key]]=row;return m};
    const countMap=(rows:any[]|null,key:string)=>{const m:Record<string,number>={};for(const row of rows||[])m[row[key]]=(m[row[key]]||0)+1;return m};
    const workflows=firstMap(workflowRes.data,'document_id'), jobs=firstMap(jobRes.data,'document_id'), parsers=firstMap(parserRes.data,'document_id');
    const canonicalCounts=countMap(canonicalRes.data,'document_id'), unmatchedCounts=countMap(unmatchedRes.data,'document_id'), discrepancyCounts=countMap(discrepancyRes.data,'document_id');
    return creditReportDocs.map((doc: Record<string, unknown>) => {
      const clientId = doc.client_id as string || 'unknown';
      const client = clientMap[clientId] || { name: null, email: null };
      const fileName = (doc.title as string) || (doc.file_name as string) || 'Untitled document';
      const status = (doc.status as string) || 'pending_review';
      const workflow=workflows[String(doc.id)]||{};const job=jobs[String(doc.id)]||null;const parser=parsers[String(doc.id)]||null;
      const exceptionReviewStatus=String(workflow.exception_review_status||((doc.goclear_review_status==='pending_review')?'required':'not_required'));
      const goclearReviewStatus = exceptionReviewStatus;

      let parserStatus: PendingCreditReportReview['parserStatus'] = exceptionReviewStatus==='required'?'needs_specialist_review':'not_parsed';
      if (fileName.toLowerCase().includes('ocr')) parserStatus = 'ocr_required';
      else if (parser) parserStatus = 'suggested_extraction_available';

      let nextActionLabel = workflow.analysis_status==='complete'?'Inspect completed analysis':'Analysis queues automatically';
      if (parserStatus === 'ocr_required') nextActionLabel = 'Manual review or backend OCR worker';
      else if (status === 'pending_review') nextActionLabel = 'Run parser preview or manual review';

      return {
        reviewId: doc.id as string,
        documentId: doc.id as string,
        clientId,
        tenantId: (doc.tenant_id as string) || 'tenant_default',
        clientName: client.name,
        clientEmail: client.email,
        fileName,
        category: (doc.category as string) || null,
        suggestedCategory: (doc.suggested_category as string) || null,
        status,
        goclearReviewStatus,
        uploadedAt: (doc.created_at as string) || '',
        source: (doc.source as string) || null,
        reviewStatusLabel: exceptionReviewStatus==='required'?'Pending GoClear Review':workflow.analysis_status==='complete'?'Analysis Complete':String(workflow.analysis_status||job?.status||'waiting_for_analysis').replace(/_/g,' '),
        parserStatus,
        nextActionLabel,
        documentStatus:String(workflow.document_status||'uploaded'),analysisStatus:String(workflow.analysis_status||job?.status||'not_queued'),strategyStatus:String(workflow.strategy_status||'not_started'),clientActionStatus:String(workflow.client_action_status||'not_ready'),exceptionReviewStatus,mailStatus:String(workflow.mail_status||'not_requested'),analysisJobStatus:job?.status||null,parserVersion:parser?.parser_version||job?.parser_version||null,canonicalAccountsCount:canonicalCounts[String(doc.id)]||0,unmatchedTradelinesCount:unmatchedCounts[String(doc.id)]||0,discrepanciesCount:discrepancyCounts[String(doc.id)]||0,exceptionCount:exceptionReviewStatus==='required'?1:0,accountsParsed:Array.isArray(parser?.accounts)?parser.accounts.length:0,inquiriesCount:Array.isArray(parser?.inquiries)?parser.inquiries.length:0,bureauCount:Array.isArray(parser?.bureaus_detected)?parser.bureaus_detected.length:0,
      };
    });
  } catch {
    return [];
  }
}

// ─── Status Helpers ──────────────────────────────────────────────────────────

const JOURNEY_STEP_LABELS: Record<CreditJourneyStep, string> = {
  profile: 'Profile Complete',
  upload_report: 'Upload Credit Report',
  specialist_review: 'Specialist Review',
  dispute_items: 'Dispute Items',
  draft_letters: 'Draft Letters',
  approve_send: 'Approve & Send',
  track_results: 'Track Results',
};

export function getJourneyStepLabel(step: CreditJourneyStep): string {
  return JOURNEY_STEP_LABELS[step];
}

const LETTER_STATUS_LABELS: Record<CreditDisputeLetterStatus, string> = {
  draft: 'Draft',
  specialist_review: 'Specialist Review',
  ray_review: 'Ray Review',
  client_review: 'Client Review',
  client_approved: 'Client Approved',
  approved_for_docupost: 'Approved for DocuPost',
  docupost_queued: 'DocuPost Queued',
  docupost_mailed: 'Mailed',
  docupost_delivered: 'Delivered',
  response_received: 'Response Received',
  archived: 'Archived',
};

export function getLetterStatusLabel(status: CreditDisputeLetterStatus): string {
  return LETTER_STATUS_LABELS[status];
}

const MAIL_JOB_STATUS_LABELS: Record<DocuPostJobStatus, string> = {
  not_sent: 'Not Sent',
  approval_required: 'Awaiting Approval',
  approved_to_send: 'Approved to Send',
  docupost_ready: 'DocuPost Ready',
  queued: 'Queued',
  mailed: 'Mailed',
  delivered: 'Delivered',
  failed: 'Failed',
  canceled: 'Canceled',
};

export function getMailJobStatusLabel(status: DocuPostJobStatus): string {
  return MAIL_JOB_STATUS_LABELS[status];
}
