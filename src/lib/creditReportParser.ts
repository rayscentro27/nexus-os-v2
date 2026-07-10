import {
  type CreditReportCaseItemDraft,
  type CreditReportConfidence,
  type CreditReportFormatGuess,
  type CreditReportParseResult,
  type ParsedCreditAccount,
  type ParsedInquiry,
  type ParsedPersonalInfoVariation,
  type ParserWarning,
} from './creditReportParserTypes'

export const CREDIT_REPORT_PARSER_VERSION = 'preview-0.1.0'

const BUREAUS = ['experian', 'equifax', 'transunion'] as const

function cleanText(value: string) {
  return String(value || '').replace(/\s+/g, ' ').trim()
}

function maskAccount(value?: string) {
  const digits = String(value || '').replace(/\D/g, '')
  if (!digits) return value?.includes('*') ? value : undefined
  return `****${digits.slice(-4)}`
}

function moneyAfter(text: string, labels: string[]) {
  for (const label of labels) {
    const match = text.match(new RegExp(`${label}[^$0-9-]*([$]?[0-9][0-9,]*(?:\\.\\d{2})?)`, 'i'))
    if (match?.[1]) return match[1].startsWith('$') ? match[1] : `$${match[1]}`
  }
  return undefined
}

export function detectCreditReportFormat(rawText: string, fileName = ''): CreditReportFormatGuess {
  const haystack = `${fileName} ${rawText}`.toLowerCase()
  if (/mixed|funding|bank statement|profit|loss|ein|business formation/.test(haystack)) return 'mixed_credit_funding_bundle'
  if (/monitoring|score alert|dashboard|credit monitoring/.test(haystack)) return 'monitoring_export'
  if (/annualcreditreport|annual credit report|disclosure/.test(haystack)) return 'annual_report_style'
  if (/3[- ]bureau|three bureau|tradeline/.test(haystack)) return 'three_bureau_tradeline'
  if (/scan|screenshot|ocr/.test(haystack)) return 'scanned_ocr_text'
  return 'unknown'
}

export function extractUtilization(accountText: string) {
  const explicit = accountText.match(/(\d{1,3})\s*%\s*(?:utilization|utilized|used)?/i)
  if (explicit) return Number(explicit[1])
  const balance = moneyAfter(accountText, ['balance', 'reported balance'])
  const limit = moneyAfter(accountText, ['limit', 'credit limit'])
  const balanceNumber = Number(String(balance || '').replace(/[^0-9.]/g, ''))
  const limitNumber = Number(String(limit || '').replace(/[^0-9.]/g, ''))
  if (balanceNumber && limitNumber) return Math.round((balanceNumber / limitNumber) * 100)
  return undefined
}

function inferItemType(text: string): string {
  if (/collection|collector|medical collection/i.test(text)) return 'collection'
  if (/charge[- ]?off/i.test(text)) return 'charge_off'
  if (/late|30 day|60 day|90 day/i.test(text)) return 'late_payment'
  if (/inquiry|hard pull/i.test(text)) return 'inquiry'
  if (/address|name|employer|personal information/i.test(text)) return 'personal_info'
  if (/duplicate/i.test(text)) return 'duplicate_account'
  if (/utilization|credit limit|balance/i.test(text)) return 'utilization'
  return 'other'
}

export function suggestDisputeReasons(item: Partial<ParsedCreditAccount> | Partial<ParsedInquiry> | Partial<ParsedPersonalInfoVariation>): string[] {
  const text = cleanText([
    'itemType' in item ? item.itemType : '',
    'status' in item ? item.status : '',
    'notes' in item ? item.notes : '',
    'concern' in item ? item.concern : '',
    'negativeCandidateReason' in item ? item.negativeCandidateReason : '',
  ].join(' ')).toLowerCase()
  if (/duplicate/.test(text)) return ['duplicate', 'verify_or_validate', 'not_sure']
  if (/balance|utilization/.test(text)) return ['incorrect_balance', 'verify_or_validate', 'not_sure']
  if (/late/.test(text)) return ['late_payment_wrong', 'incorrect_dates', 'not_sure']
  if (/inquiry|unauthorized/.test(text)) return ['unauthorized_inquiry', 'verify_or_validate', 'not_sure']
  if (/personal|address|name|employer/.test(text)) return ['personal_info_error', 'mixed_file', 'not_sure']
  if (/paid|settled/.test(text)) return ['paid_or_settled_wrong', 'incorrect_balance', 'not_sure']
  if (/old|outdated|re-aging|date/.test(text)) return ['outdated', 'incorrect_dates', 'not_sure']
  if (/collection|charge/.test(text)) return ['verify_or_validate', 'not_mine', 'not_sure']
  return ['verify_or_validate', 'not_sure']
}

function detectBureau(line: string, fallback = 'other') {
  const lower = line.toLowerCase()
  return BUREAUS.find(bureau => lower.includes(bureau)) || fallback
}

function parseAccounts(rawText: string): ParsedCreditAccount[] {
  const lines = rawText.split(/\n|(?<=\.)\s+/).map(cleanText).filter(Boolean)
  const candidates = lines.filter(line => /(collection|charge[- ]?off|late|utilization|balance|credit limit|duplicate|settled|paid|tradeline|account)/i.test(line))
  return candidates.slice(0, 30).map((line) => {
    const itemType = inferItemType(line)
    const utilizationPercent = extractUtilization(line)
    const accountNumberMasked = maskAccount(line.match(/(?:account|acct)[^0-9*]*([*Xx\d -]{4,})/i)?.[1])
    const furnisherName = cleanText(line.match(/(?:furnisher|creditor|collector|account)\s*[:\-]\s*([^.;|]+)/i)?.[1] || line.split(/[-|:]/)[0] || '')
    const negativeCandidateReason = [
      itemType !== 'other' ? itemType : '',
      utilizationPercent && utilizationPercent >= 30 ? 'high_utilization' : '',
      /paid|settled/i.test(line) ? 'paid_or_settled_wrong_possible' : '',
      /duplicate/i.test(line) ? 'duplicate_account_possible' : '',
    ].filter(Boolean).join(', ')
    const account: ParsedCreditAccount = {
      bureau: detectBureau(line),
      furnisherName: furnisherName.slice(0, 80) || undefined,
      accountName: furnisherName.slice(0, 80) || undefined,
      accountNumberMasked,
      itemType,
      status: cleanText(line.match(/status\s*[:\-]\s*([^.;|]+)/i)?.[1] || ''),
      reportedBalance: moneyAfter(line, ['balance', 'reported balance']),
      creditLimit: moneyAfter(line, ['limit', 'credit limit']),
      utilizationPercent,
      dateOpened: line.match(/opened\s*[:\-]?\s*([0-9/ -]{6,12})/i)?.[1],
      dateReported: line.match(/reported\s*[:\-]?\s*([0-9/ -]{6,12})/i)?.[1],
      paymentStatus: line.match(/(30|60|90)\s*day\s*late/i)?.[0],
      notes: line,
      negativeCandidateReason: negativeCandidateReason || undefined,
      suggestedDisputeReasons: [],
      confidence: line.length > 30 ? 'medium' : 'low',
    }
    account.suggestedDisputeReasons = suggestDisputeReasons(account)
    return account
  })
}

function parseInquiries(rawText: string): ParsedInquiry[] {
  return rawText.split(/\n|(?<=\.)\s+/).map(cleanText).filter(line => /inquiry|hard pull|permissible purpose/i.test(line)).slice(0, 20).map(line => ({
    bureau: detectBureau(line),
    company: cleanText(line.match(/(?:inquiry|company|creditor)\s*[:\-]\s*([^.;|]+)/i)?.[1] || line.split(/[-|:]/)[0] || 'Inquiry'),
    date: line.match(/(\d{1,2}\/\d{1,2}\/\d{2,4}|\d{4}-\d{2}-\d{2})/)?.[1],
    inquiryType: /hard/i.test(line) ? 'hard' : 'unknown',
    notes: line,
    confidence: 'medium' as CreditReportConfidence,
  }))
}

function parsePersonalInfo(rawText: string): ParsedPersonalInfoVariation[] {
  return rawText.split(/\n|(?<=\.)\s+/).map(cleanText).filter(line => /address|name variation|employer|personal information|old address/i.test(line)).slice(0, 20).map(line => ({
    field: /address/i.test(line) ? 'address' : /employer/i.test(line) ? 'employer' : /name/i.test(line) ? 'name' : 'personal_info',
    value: line.slice(0, 160),
    bureau: detectBureau(line, ''),
    concern: /old|variation|mismatch|incorrect/i.test(line) ? 'possible personal information error' : 'specialist review suggested',
    confidence: 'low' as CreditReportConfidence,
  }))
}

export function inferNegativeItemCandidates(accounts: ParsedCreditAccount[], inquiries: ParsedInquiry[], personalInfo: ParsedPersonalInfoVariation[]) {
  return [
    ...accounts.filter(account => account.negativeCandidateReason || ['collection', 'charge_off', 'late_payment', 'utilization', 'duplicate_account'].includes(account.itemType)),
    ...inquiries,
    ...personalInfo.filter(info => /error|old|variation|mismatch/i.test(info.concern || info.value)),
  ]
}

export function parseCreditReportText(rawText: string, options: { sourceFileName?: string } = {}): CreditReportParseResult {
  const text = String(rawText || '')
  const warnings: ParserWarning[] = [
    {
      code: 'SUGGESTED_EXTRACTION_ONLY',
      message: 'Suggested extraction only. Needs GoClear specialist review and is not verified yet.',
      severity: 'warning',
    },
  ]
  const sourceFileName = options.sourceFileName || 'credit-report-upload'
  if (!cleanText(text)) {
    warnings.push({ code: 'NO_TEXT_EXTRACTED', message: 'No text was extracted. OCR or manual specialist review is required.', severity: 'error' })
  }
  const sourceFormatGuess = detectCreditReportFormat(text, sourceFileName)
  const accounts = parseAccounts(text)
  const inquiries = parseInquiries(text)
  const personalInfoVariations = parsePersonalInfo(text)
  const highUtilizationAccounts = accounts.filter(account => (account.utilizationPercent || 0) >= 30)
  const negativeItemCandidates = inferNegativeItemCandidates(accounts, inquiries, personalInfoVariations)
  const bureausDetected = BUREAUS.filter(bureau => new RegExp(bureau, 'i').test(text))
  const confidence: CreditReportConfidence = cleanText(text).length < 200 ? 'low' : accounts.length >= 3 ? 'medium' : 'low'

  return {
    parserVersion: CREDIT_REPORT_PARSER_VERSION,
    sourceFileName,
    sourceFormatGuess,
    extractionMode: cleanText(text) ? (sourceFormatGuess === 'mixed_credit_funding_bundle' ? 'mixed' : 'text_pdf') : 'failed',
    confidence,
    needsSpecialistReview: true,
    clientNameGuess: text.match(/client\s*:\s*([A-Z][A-Za-z ]{2,80})/i)?.[1]?.trim(),
    reportDateGuess: text.match(/(?:date|report date)\s*:\s*([0-9-\/]{8,12})/i)?.[1],
    bureausDetected,
    accounts,
    inquiries,
    personalInfoVariations,
    utilizationSummary: {
      revolvingAccounts: accounts.filter(account => /utilization|balance|credit limit/i.test(account.notes || '')).length,
      highUtilizationAccounts: highUtilizationAccounts.length,
      highestUtilizationPercent: highUtilizationAccounts.map(a => a.utilizationPercent || 0).sort((a, b) => b - a)[0],
      notes: highUtilizationAccounts.map(account => `${account.accountName || account.furnisherName || 'Account'} at ${account.utilizationPercent}% utilization`),
    },
    negativeItemCandidates,
    documentClassification: {
      suggestedCategory: sourceFormatGuess === 'mixed_credit_funding_bundle' ? 'mixed_credit_funding_bundle' : 'credit_report',
      label: 'Suggested extraction',
      status: 'Needs GoClear specialist review',
      verified: false,
    },
    warnings,
    rawTextPreview: cleanText(text).slice(0, 1200),
  }
}

export function convertParsedItemsToCaseDrafts(parseResult: CreditReportParseResult): CreditReportCaseItemDraft[] {
  return parseResult.negativeItemCandidates
    .filter((item): item is ParsedCreditAccount => 'itemType' in item)
    .map(item => ({
      bureau: item.bureau || 'other',
      furnisher_name: item.furnisherName || null,
      account_name: item.accountName || null,
      account_number_masked: item.accountNumberMasked || null,
      item_type: item.itemType || 'other',
      reported_balance: item.reportedBalance || null,
      date_opened: item.dateOpened || null,
      date_reported: item.dateReported || null,
      reported_status: item.status || item.paymentStatus || null,
      raw_notes: [
        'Suggested extraction - Needs GoClear specialist review - Not verified yet.',
        item.notes || '',
        item.negativeCandidateReason ? `Candidate reason: ${item.negativeCandidateReason}` : '',
      ].filter(Boolean).join('\n'),
      suggested_dispute_reasons: item.suggestedDisputeReasons,
      parser_confidence: item.confidence,
      source: 'parser_suggested',
      needsSpecialistReview: true,
    }))
}
