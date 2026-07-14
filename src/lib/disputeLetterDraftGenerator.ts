export type DisputeLetterDraftInput = {
  consumerName: string
  consumerAddress: string
  bureau: string
  bureauAddress?: string
  item: {
    accountName?: string
    furnisherName?: string
    accountNumberMasked?: string
    itemType?: string
    reportedBalance?: string
    creditLimit?: string
    status?: string
    dateOpened?: string
    dateReported?: string
  }
  reason: string
  reasonLabel?: string
  evidenceList?: string[]
  additionalNotes?: string
}

export type DisputeLetterDraftOutput = {
  letterText: string
  date: string
  consumerName: string
  bureau: string
  itemLabel: string
  reason: string
  disclaimer: string
}

const BUREAU_ADDRESSES: Record<string, string> = {
  experian: 'Experian\nP.O. Box 4500\nAllen, TX 75013',
  equifax: 'Equifax Information Services LLC\nP.O. Box 740256\nAtlanta, GA 30374',
  transunion: 'TransUnion LLC\nConsumer Dispute Center\nP.O. Box 2000\nChester, PA 19016',
}

const DISCLAIMER = [
  'Draft preview only. This document requires review and approval before use. Nexus does not guarantee deletion, a credit score change, or a specific reporting outcome.',
  'GoClear review and client approval are required before any mailing request.',
  'Do not include SSN, full DOB, full account numbers, or sensitive identifiers.',
  'All dispute activity must comply with the Fair Credit Reporting Act (FCRA), 15 U.S.C. § 1681.',
].join('\n')

export function generateDisputeLetterDraftPreview(input: DisputeLetterDraftInput): DisputeLetterDraftOutput {
  const today = new Date().toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })

  const consumerName = input.consumerName || '[Consumer Name]'
  const consumerAddress = input.consumerAddress || '[Consumer Address]'
  const bureau = input.bureau || '[Bureau]'
  const bureauAddress = input.bureauAddress || BUREAU_ADDRESSES[bureau.toLowerCase()] || '[Bureau Address]'
  const item = input.item
  const reason = input.reason || 'Verify/validate this item'
  const reasonLabel = input.reasonLabel || reason

  const itemLabel = [
    item.furnisherName || item.accountName || '[Creditor/Furnisher]',
    item.accountNumberMasked || 'XXXX',
  ].filter(Boolean).join(' / ')

  const itemLines: string[] = []
  if (item.accountName) itemLines.push(`  Account: ${item.accountName}`)
  if (item.furnisherName) itemLines.push(`  Furnisher: ${item.furnisherName}`)
  if (item.accountNumberMasked) itemLines.push(`  Account #: ${item.accountNumberMasked}`)
  if (item.itemType) itemLines.push(`  Type: ${item.itemType}`)
  if (item.reportedBalance) itemLines.push(`  Reported Balance: ${item.reportedBalance}`)
  if (item.creditLimit) itemLines.push(`  Credit Limit: ${item.creditLimit}`)
  if (item.status) itemLines.push(`  Status: ${item.status}`)
  if (item.dateOpened) itemLines.push(`  Date Opened: ${item.dateOpened}`)
  if (item.dateReported) itemLines.push(`  Date Reported: ${item.dateReported}`)

  const evidenceSection = input.evidenceList && input.evidenceList.length > 0
    ? `\nEnclosed supporting documents:\n${input.evidenceList.map((e, i) => `  ${i + 1}. ${e}`).join('\n')}`
    : ''

  const additionalNotes = input.additionalNotes
    ? `\n\nAdditional notes:\n${input.additionalNotes}`
    : ''

  const letterText = [
    consumerName,
    consumerAddress,
    '',
    today,
    '',
    bureauAddress,
    '',
    'Re: Request for Investigation / Verification — Fair Credit Reporting Act (FCRA)',
    '',
    `Dear ${bureau} Dispute Department,`,
    '',
    'I am writing to dispute the following information on my credit report. I believe the item listed below is inaccurate, incomplete, or cannot be verified, and I request an investigation under the Fair Credit Reporting Act, 15 U.S.C. § 1681.',
    '',
    'Disputed Item:',
    ...itemLines,
    '',
    `Reason for dispute: ${reasonLabel}.`,
    '',
    'Please investigate this item, contact the furnisher for verification, and correct or remove any information that cannot be accurately verified as required by law.',
    '',
    'If this item is found to be inaccurate or unverifiable, please remove it from my credit report and provide me with an updated copy.',
    '',
    'I have enclosed supporting documentation for your review.',
    '',
    'Sincerely,',
    consumerName,
    evidenceSection,
    additionalNotes,
    '',
    '---',
    DISCLAIMER,
  ].join('\n')

  return {
    letterText,
    date: today,
    consumerName,
    bureau,
    itemLabel,
    reason: reasonLabel,
    disclaimer: DISCLAIMER,
  }
}

export function generateMultipleDraftPreviews(
  items: Array<{ item: DisputeLetterDraftInput['item']; reason: string; bureau: string }>,
  consumerName: string,
  consumerAddress: string,
): DisputeLetterDraftOutput[] {
  return items.map(entry =>
    generateDisputeLetterDraftPreview({
      consumerName,
      consumerAddress,
      bureau: entry.bureau,
      item: entry.item,
      reason: entry.reason,
    })
  )
}
