import { createManualReportItem, selectDisputeReason, type CreditReportItem } from './creditRepairCaseEngine'
import { type ResolvedClientContext } from './clientAuthContext'
import { type DisputeReason } from './disputeStrategyKnowledge'
import { convertParsedItemsToCaseDrafts, parseCreditReportText } from './creditReportParser'
import { type CreditReportCaseItemDraft, type CreditReportParseResult } from './creditReportParserTypes'

export interface ConfirmParserItemResult {
  ok: boolean
  item?: CreditReportItem
  error?: string
}

export async function confirmParserItemAsCaseItem(
  context: ResolvedClientContext,
  caseId: string,
  parserItem: Record<string, unknown>,
  opts?: { notes?: string; overrideFields?: Partial<CreditReportCaseItemDraft> },
): Promise<ConfirmParserItemResult> {
  try {
    const bureau = (opts?.overrideFields?.bureau as string) || (parserItem.bureau as string) || 'unknown'
    const itemType = (opts?.overrideFields?.item_type as string) || (parserItem.item_type as string) || 'collection'
    const furnisherName = opts?.overrideFields?.furnisher_name || (parserItem.furnisher_name as string) || undefined
    const accountName = opts?.overrideFields?.account_name || (parserItem.account_name as string) || undefined
    const accountNumberMasked = opts?.overrideFields?.account_number_masked || (parserItem.account_number_masked as string) || undefined
    const reportedStatus = opts?.overrideFields?.reported_status || (parserItem.reported_status as string) || undefined

    const rawNotes = [
      'Source: parser_suggested → specialist_confirmed.',
      opts?.notes || '',
      (parserItem.raw_notes as string) || '',
    ].filter(Boolean).join('\n')

    const result = await createManualReportItem(context, caseId, {
      bureau,
      furnisher_name: furnisherName,
      account_name: accountName,
      account_number_masked: accountNumberMasked,
      item_type: itemType,
      reported_status: reportedStatus,
      raw_notes: rawNotes,
      client_wants_challenged: false,
    })

    if (result.ok && result.item) return { ok: true, item: result.item }
    return { ok: false, error: result.error || 'Failed to create case item from parser result.' }
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : 'Unknown error creating parser item.' }
  }
}

export function buildCaseItemDraftsFromParseResult(parseResult: CreditReportParseResult): CreditReportCaseItemDraft[] {
  return convertParsedItemsToCaseDrafts(parseResult)
}

export function buildCaseItemDraftsFromText(rawText: string, sourceFileName: string): CreditReportCaseItemDraft[] {
  return buildCaseItemDraftsFromParseResult(parseCreditReportText(rawText, { sourceFileName }))
}

export async function createConfirmedReportItemsFromDrafts(
  context: ResolvedClientContext,
  caseId: string,
  confirmedDrafts: CreditReportCaseItemDraft[],
) {
  const created: CreditReportItem[] = []
  const errors: string[] = []
  for (const draft of confirmedDrafts) {
    const result = await createManualReportItem(context, caseId, {
      bureau: draft.bureau,
      furnisher_name: draft.furnisher_name || undefined,
      account_name: draft.account_name || undefined,
      account_number_masked: draft.account_number_masked || undefined,
      item_type: draft.item_type,
      reported_status: draft.reported_status || undefined,
      raw_notes: [
        'Source: parser_confirmed / specialist_confirmed.',
        draft.raw_notes || '',
      ].filter(Boolean).join('\n'),
      client_wants_challenged: false,
    })
    if (result.ok && result.item) created.push(result.item)
    if (!result.ok && result.error) errors.push(result.error)
  }
  return { ok: errors.length === 0, created, errors }
}

export async function createDisputeOptionsForConfirmedItem(
  context: ResolvedClientContext,
  itemId: string,
  reason: DisputeReason,
) {
  return selectDisputeReason(context, itemId, reason)
}
