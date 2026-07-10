import { createManualReportItem, selectDisputeReason, type CreditReportItem } from './creditRepairCaseEngine'
import { type ResolvedClientContext } from './clientAuthContext'
import { type DisputeReason } from './disputeStrategyKnowledge'
import { convertParsedItemsToCaseDrafts, parseCreditReportText } from './creditReportParser'
import { type CreditReportCaseItemDraft, type CreditReportParseResult } from './creditReportParserTypes'

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
