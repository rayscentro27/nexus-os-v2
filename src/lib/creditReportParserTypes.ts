export type CreditReportExtractionMode = 'text_pdf' | 'ocr_image_pdf' | 'manual' | 'mixed' | 'failed'

export type CreditReportConfidence = 'low' | 'medium' | 'high'

export type CreditReportFormatGuess =
  | 'three_bureau_tradeline'
  | 'annual_report_style'
  | 'monitoring_export'
  | 'scanned_ocr_text'
  | 'mixed_credit_funding_bundle'
  | 'unknown'

export type ParsedCreditAccount = {
  bureau: string
  furnisherName?: string
  accountName?: string
  accountNumberMasked?: string
  itemType: string
  status?: string
  reportedBalance?: string
  creditLimit?: string
  utilizationPercent?: number
  dateOpened?: string
  dateReported?: string
  paymentStatus?: string
  notes?: string
  negativeCandidateReason?: string
  suggestedDisputeReasons: string[]
  confidence: CreditReportConfidence
}

export type ParsedInquiry = {
  bureau: string
  company: string
  date?: string
  inquiryType?: string
  notes?: string
  confidence: CreditReportConfidence
}

export type ParsedPersonalInfoVariation = {
  field: string
  value: string
  bureau?: string
  concern?: string
  confidence: CreditReportConfidence
}

export type ParserWarning = {
  code: string
  message: string
  severity: 'info' | 'warning' | 'error'
}

export type CreditReportParseResult = {
  parserVersion: string
  sourceFileName: string
  sourceFormatGuess: CreditReportFormatGuess
  extractionMode: CreditReportExtractionMode
  confidence: CreditReportConfidence
  needsSpecialistReview: true
  clientNameGuess?: string
  reportDateGuess?: string
  bureausDetected: string[]
  accounts: ParsedCreditAccount[]
  inquiries: ParsedInquiry[]
  personalInfoVariations: ParsedPersonalInfoVariation[]
  utilizationSummary: {
    revolvingAccounts: number
    highUtilizationAccounts: number
    highestUtilizationPercent?: number
    notes: string[]
  }
  negativeItemCandidates: Array<ParsedCreditAccount | ParsedInquiry | ParsedPersonalInfoVariation>
  documentClassification: {
    suggestedCategory: string
    label: 'Suggested extraction'
    status: 'Needs GoClear specialist review'
    verified: false
  }
  warnings: ParserWarning[]
  rawTextPreview: string
}

export type CreditReportCaseItemDraft = {
  bureau: string
  furnisher_name?: string | null
  account_name?: string | null
  account_number_masked?: string | null
  item_type: string
  reported_balance?: string | null
  date_opened?: string | null
  date_reported?: string | null
  reported_status?: string | null
  raw_notes?: string | null
  suggested_dispute_reasons: string[]
  parser_confidence: CreditReportConfidence
  source: 'parser_suggested'
  needsSpecialistReview: true
}
