import { supabase, isSupabaseConfigured } from './supabaseClient'
import { type ResolvedClientContext } from './clientAuthContext'
import {
  type DisputeReason,
  type LetterOption,
  getDisputeOptions,
  summarizeOutcome,
} from './disputeStrategyKnowledge'
import {
  createDisputeItem,
  createDisputeLetterDraft,
  createDocuPostSendRequest as createLegacyDocuPostSendRequest,
  clientApproveLetter as approveLegacyClientLetter,
  specialistApproveLetter,
  approveLetterForSpecialistReview,
} from './creditRepairWorkflow'

export type CreditRepairCaseStatus =
  | 'intake'
  | 'report_uploaded'
  | 'item_review'
  | 'strategy_review'
  | 'client_approval'
  | 'letters_sent'
  | 'waiting_for_response'
  | 'next_round'
  | 'completed'

export type CreditRepairCase = {
  id: string
  tenant_id: string
  client_id: string
  status: CreditRepairCaseStatus
  case_goal?: string | null
  current_round: number
}

export type CreditReportItem = {
  id: string
  tenant_id: string
  client_id: string
  case_id?: string | null
  bureau: string
  furnisher_name?: string | null
  account_name?: string | null
  account_number_masked?: string | null
  item_type: string
  reported_status?: string | null
  raw_notes?: string | null
  client_wants_challenged?: boolean
}

export type DisputeOutcomeInput = {
  caseId?: string
  reportItemId?: string
  strategyId?: string
  letterOptionId?: string
  roundNumber?: number
  responseResult: string
  bureauOrFurnisher?: string
  notes?: string
}

const ACTIVE_CASE_STATUSES = [
  'intake',
  'report_uploaded',
  'item_review',
  'strategy_review',
  'client_approval',
  'letters_sent',
  'waiting_for_response',
  'next_round',
]

function fallbackCase(ctx: ResolvedClientContext): CreditRepairCase {
  return {
    id: `local_case_${ctx.clientId}`,
    tenant_id: ctx.tenantId,
    client_id: ctx.clientId,
    status: 'intake',
    case_goal: 'Challenge negative items, pursue correction/removal when supportable, and track outcomes.',
    current_round: 1,
  }
}

function requireDb() {
  return Boolean(isSupabaseConfigured && supabase)
}

function sanitizeMask(value = '') {
  const digits = String(value).replace(/\D/g, '')
  if (!digits) return ''
  return `****${digits.slice(-4)}`
}

export async function getOrCreateCreditRepairCase(ctx: ResolvedClientContext): Promise<CreditRepairCase> {
  if (!requireDb()) return fallbackCase(ctx)
  const existing = await supabase!
    .from('credit_repair_cases')
    .select('*')
    .eq('client_id', ctx.clientId)
    .in('status', ACTIVE_CASE_STATUSES)
    .order('created_at', { ascending: false })
    .limit(1)
    .maybeSingle()

  if (existing.data) return existing.data as CreditRepairCase

  const insert = await supabase!
    .from('credit_repair_cases')
    .insert({
      tenant_id: ctx.tenantId,
      client_id: ctx.clientId,
      status: 'intake',
      case_goal: 'Challenge negative items, prepare dispute options, and track bureau/furnisher responses.',
      current_round: 1,
    })
    .select('*')
    .single()

  if (insert.data) return insert.data as CreditRepairCase
  return fallbackCase(ctx)
}

export async function getOrCreateCreditRepairCaseForDocument(input: {
  clientId: string
  tenantId: string
  documentId?: string
  source?: string
  createdBy?: string
}) {
  if (!requireDb()) return { ok: false, error: 'Supabase not configured' }
  if (!input.clientId || !input.tenantId) return { ok: false, error: 'Client and tenant are required' }

  const existing = await supabase!
    .from('credit_repair_cases')
    .select('*')
    .eq('client_id', input.clientId)
    .in('status', ACTIVE_CASE_STATUSES)
    .order('created_at', { ascending: false })
    .limit(1)
    .maybeSingle()

  if (existing.data) return { ok: true, case: existing.data as CreditRepairCase, openedExisting: true }
  if (existing.error) return { ok: false, error: existing.error.message }

  const insert = await supabase!
    .from('credit_repair_cases')
    .insert({
      tenant_id: input.tenantId,
      client_id: input.clientId,
      status: 'report_uploaded',
      case_goal: [
        'Specialist review of uploaded credit report.',
        input.documentId ? `Source document: ${input.documentId}` : '',
        input.source ? `Source: ${input.source}` : '',
        input.createdBy ? `Created by: ${input.createdBy}` : '',
      ].filter(Boolean).join(' '),
      current_round: 1,
    })
    .select('*')
    .single()

  if (insert.error) return { ok: false, error: insert.error.message }
  return { ok: true, case: insert.data as CreditRepairCase, openedExisting: false }
}

export async function listCreditReportItems(ctx: ResolvedClientContext, caseId?: string): Promise<CreditReportItem[]> {
  if (!requireDb() || !caseId || caseId.startsWith('local_case_')) return []
  const res = await supabase!
    .from('credit_report_items')
    .select('*')
    .eq('client_id', ctx.clientId)
    .eq('case_id', caseId)
    .order('created_at', { ascending: false })
  return (res.data || []) as CreditReportItem[]
}

export async function createManualReportItem(ctx: ResolvedClientContext, caseId: string, item: Partial<CreditReportItem>) {
  if (!requireDb()) return { ok: false, error: 'Supabase not configured' }
  const payload = {
    tenant_id: ctx.tenantId,
    client_id: ctx.clientId,
    case_id: caseId.startsWith('local_case_') ? null : caseId,
    bureau: item.bureau || 'other',
    furnisher_name: item.furnisher_name || null,
    account_name: item.account_name || null,
    account_number_masked: sanitizeMask(item.account_number_masked || ''),
    item_type: item.item_type || 'other',
    reported_status: item.reported_status || null,
    raw_notes: item.raw_notes || null,
    client_wants_challenged: Boolean(item.client_wants_challenged),
  }
  const { data, error } = await supabase!.from('credit_report_items').insert(payload).select('*').single()
  if (error) return { ok: false, error: error.message }
  return { ok: true, item: data as CreditReportItem }
}

export async function markItemForChallenge(ctx: ResolvedClientContext, itemId: string, wantsChallenged: boolean) {
  if (!requireDb()) return { ok: false, error: 'Supabase not configured' }
  const { error } = await supabase!
    .from('credit_report_items')
    .update({ client_wants_challenged: wantsChallenged, updated_at: new Date().toISOString() })
    .eq('id', itemId)
    .eq('client_id', ctx.clientId)
  return error ? { ok: false, error: error.message } : { ok: true }
}

export async function selectDisputeReason(ctx: ResolvedClientContext, itemId: string, reason: DisputeReason) {
  if (!requireDb()) return { ok: false, error: 'Supabase not configured' }
  const itemRes = await supabase!.from('credit_report_items').select('*').eq('id', itemId).eq('client_id', ctx.clientId).single()
  if (itemRes.error || !itemRes.data) return { ok: false, error: 'Report item not found' }
  const item = itemRes.data as CreditReportItem
  const options = generateDisputeLetterOptions(item, reason, { clientId: ctx.clientId })
  const { data: strategy, error } = await supabase!
    .from('credit_dispute_strategies')
    .insert({
      tenant_id: ctx.tenantId,
      client_id: ctx.clientId,
      case_id: item.case_id || null,
      report_item_id: itemId,
      client_selected_reason: reason,
      strategy_type: options[0]?.optionType || 'bureau_dispute',
      evidence_needed: options[0]?.evidenceNeeded || [],
      specialist_status: reason === 'not_sure' ? 'needs_client_info' : 'needs_review',
    })
    .select('*')
    .single()
  if (error) return { ok: false, error: error.message }
  return { ok: true, strategy, options }
}

export function generateDisputeLetterOptions(item: Partial<CreditReportItem>, reason: DisputeReason, _context?: Record<string, unknown>): LetterOption[] {
  const itemLabel = [
    item.bureau,
    item.furnisher_name || item.account_name,
    item.account_number_masked,
  ].filter(Boolean).join(' / ') || 'the selected credit report item'
  return getDisputeOptions(reason, itemLabel)
}

export async function createLetterDraftFromOption(ctx: ResolvedClientContext, option: LetterOption & { caseId?: string; reportItemId?: string; strategyId?: string; item?: CreditReportItem }) {
  if (!requireDb()) return { ok: false, error: 'Supabase not configured' }
  const item = option.item
  const savedOption = await supabase!
    .from('credit_dispute_letter_options')
    .insert({
      tenant_id: ctx.tenantId,
      client_id: ctx.clientId,
      case_id: option.caseId || item?.case_id || null,
      report_item_id: option.reportItemId || item?.id || null,
      strategy_id: option.strategyId || null,
      option_type: option.optionType,
      title: option.title,
      summary: option.summary,
      recommended: Boolean(option.recommended),
      risk_level: option.riskLevel,
      why_recommended: option.whyRecommended,
      draft_body: option.draftBody,
      status: 'specialist_review',
    })
    .select('*')
    .single()

  if (savedOption.error) return { ok: false, error: savedOption.error.message }

  const legacy = await createDisputeItem({
    tenantId: ctx.tenantId,
    clientId: ctx.clientId,
    bureau: item?.bureau || 'unknown',
    furnisherName: item?.furnisher_name || undefined,
    accountName: item?.account_name || undefined,
    accountNumberMask: item?.account_number_masked || undefined,
    disputeReason: option.title,
    factualBasis: option.summary,
    requestedAction: 'investigate',
  })

  const letter = await createDisputeLetterDraft({
    tenantId: ctx.tenantId,
    clientId: ctx.clientId,
    disputeItemIds: legacy.id ? [legacy.id] : [],
    recipientType: option.optionType.includes('furnisher') || option.optionType.includes('collector') ? 'furnisher' : 'bureau',
    recipientName: item?.bureau || item?.furnisher_name || 'Credit Bureau',
    letterBody: option.draftBody,
  })

  if (!letter.ok || !letter.id) return letter
  await approveLetterForSpecialistReview(letter.id)
  return { ok: true, option: savedOption.data, letterId: letter.id }
}

export async function submitForSpecialistReview(_ctx: ResolvedClientContext, letterOptionId: string) {
  if (!requireDb()) return { ok: false, error: 'Supabase not configured' }
  const { error } = await supabase!.from('credit_dispute_letter_options').update({ status: 'specialist_review', updated_at: new Date().toISOString() }).eq('id', letterOptionId)
  return error ? { ok: false, error: error.message } : { ok: true }
}

export async function approveLetterForClientReview(_ctx: ResolvedClientContext, letterOptionId: string) {
  if (!requireDb()) return { ok: false, error: 'Supabase not configured' }
  const { error } = await supabase!.from('credit_dispute_letter_options').update({ status: 'client_approval', updated_at: new Date().toISOString() }).eq('id', letterOptionId)
  return error ? { ok: false, error: error.message } : { ok: true }
}

export async function clientApproveCaseLetter(ctx: ResolvedClientContext, letterOptionId: string) {
  if (!requireDb()) return { ok: false, error: 'Supabase not configured' }
  const { error } = await supabase!
    .from('credit_dispute_letter_options')
    .update({ status: 'approved', updated_at: new Date().toISOString() })
    .eq('id', letterOptionId)
    .eq('client_id', ctx.clientId)
  return error ? { ok: false, error: error.message } : { ok: true }
}

export async function clientApproveLetter(_ctx: ResolvedClientContext, letterOptionId: string) {
  return clientApproveCaseLetter(_ctx, letterOptionId)
}

export async function createDocuPostSendRequest(ctx: ResolvedClientContext, letterOptionId: string) {
  if (!requireDb()) return { ok: false, error: 'Supabase not configured' }
  const optionRes = await supabase!.from('credit_dispute_letter_options').select('*').eq('id', letterOptionId).eq('client_id', ctx.clientId).single()
  if (optionRes.error || !optionRes.data) return { ok: false, error: 'Letter option not found' }
  if (optionRes.data.status !== 'approved') return { ok: false, error: 'Client approval required before DocuPost send request.' }
  return { ok: false, error: 'Use the linked approved credit_dispute_letters record for the existing approval-gated DocuPost flow.' }
}

export async function clientApproveExistingLetter(letterId: string) {
  return approveLegacyClientLetter(letterId)
}

export async function createExistingDocuPostSendRequest(letterId: string) {
  return createLegacyDocuPostSendRequest(letterId)
}

export async function specialistApproveExistingLetter(letterId: string) {
  return specialistApproveLetter(letterId)
}

export async function recordDisputeOutcome(ctx: ResolvedClientContext, outcome: DisputeOutcomeInput) {
  if (!requireDb()) return { ok: false, error: 'Supabase not configured' }
  const next = recommendNextAction(null, null, outcome)
  const { data, error } = await supabase!
    .from('credit_dispute_outcomes')
    .insert({
      tenant_id: ctx.tenantId,
      client_id: ctx.clientId,
      case_id: outcome.caseId || null,
      report_item_id: outcome.reportItemId || null,
      strategy_id: outcome.strategyId || null,
      letter_option_id: outcome.letterOptionId || null,
      round_number: outcome.roundNumber || 1,
      response_result: outcome.responseResult,
      bureau_or_furnisher: outcome.bureauOrFurnisher || null,
      notes: outcome.notes || null,
      next_recommended_action: next,
    })
    .select('*')
    .single()
  if (error) return { ok: false, error: error.message }
  return { ok: true, outcome: data, nextRecommendedAction: next }
}

export function recommendNextAction(_item: unknown, _strategy: unknown, outcome: { responseResult?: string } | null) {
  return summarizeOutcome(outcome?.responseResult || 'not_sent')
}
