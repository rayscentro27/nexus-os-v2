export type DocumentTrack =
  | 'credit_profile'
  | 'business_profile'
  | 'business_funding'
  | 'request_review'
  | 'credit_repair'
  | 'documents'
  | 'general'

export type DocumentCategory =
  | 'credit_report'
  | 'government_id'
  | 'proof_of_address'
  | 'ein_confirmation'
  | 'business_formation'
  | 'business_license'
  | 'bank_statement'
  | 'tax_return'
  | 'profit_and_loss'
  | 'bureau_response'
  | 'dispute_support'
  | 'funding_support'
  | 'review_support'
  | 'unknown'

const categoryKeywords: Array<[DocumentCategory, RegExp]> = [
  ['credit_report', /credit|report|tradeline|score/i],
  ['government_id', /\bid\b|license|passport|government/i],
  ['proof_of_address', /address|utility|lease|mortgage|residence/i],
  ['ein_confirmation', /\bein\b|cp575|147c|irs/i],
  ['business_formation', /formation|article|incorporation|organization|entity/i],
  ['business_license', /business.?license|permit/i],
  ['bank_statement', /bank|statement|checking|deposit/i],
  ['tax_return', /tax|1040|1120|1065|return/i],
  ['profit_and_loss', /profit|loss|p&l|pl statement|income statement/i],
  ['bureau_response', /bureau|experian|equifax|transunion|response|investigation/i],
  ['dispute_support', /dispute|settlement|payment proof|collector|collection|validation/i],
]

export function inferDocumentCategoryFromContext({
  fileName,
  pageContext,
  track,
  suggestedCategory,
}: {
  fileName?: string
  pageContext?: string
  track?: DocumentTrack
  suggestedCategory?: string
}): DocumentCategory {
  const suggested = String(suggestedCategory || '').trim()
  if (suggested) return suggested as DocumentCategory

  const text = `${fileName || ''} ${pageContext || ''} ${track || ''}`
  for (const [category, pattern] of categoryKeywords) {
    if (pattern.test(text)) return category
  }

  if (track === 'credit_profile') return 'credit_report'
  if (track === 'business_profile') return 'ein_confirmation'
  if (track === 'business_funding') return 'bank_statement'
  if (track === 'request_review') return 'review_support'
  if (track === 'credit_repair') return 'dispute_support'
  return 'unknown'
}

export function getNextRecommendedDocument({
  track,
  uploadedDocuments = [],
  missingRequirements = [],
}: {
  track?: DocumentTrack
  uploadedDocuments?: Array<{ category?: string; title?: string; filename?: string }>
  missingRequirements?: string[]
}): string {
  const uploaded = uploadedDocuments.map(doc => `${doc.category || ''} ${doc.title || ''} ${doc.filename || ''}`.toLowerCase()).join(' ')
  const missing = missingRequirements.join(' ').toLowerCase()
  const has = (key: string) => uploaded.includes(key) || !missing.includes(key)

  if (track === 'credit_profile') {
    if (!uploaded.includes('credit')) return 'Credit Report'
    if (!uploaded.includes('dispute')) return 'Dispute Support or Evidence'
    return 'Bureau Response'
  }
  if (track === 'business_profile') {
    if (!has('ein')) return 'EIN Confirmation'
    if (!has('formation')) return 'Business Formation Docs'
    if (!has('license')) return 'Business License'
    if (!has('address')) return 'Proof of Business Address'
    return 'Business Bank Statement'
  }
  if (track === 'business_funding') {
    if (!has('bank')) return 'Bank Statement'
    if (!has('tax')) return 'Tax Return'
    if (!has('profit')) return 'Profit & Loss Statement'
    if (!has('license')) return 'Business License'
    return 'Funding Support Document'
  }
  if (track === 'request_review') return uploaded.includes('credit') ? 'Most Relevant Support Document' : 'Credit Report'
  if (track === 'credit_repair') return uploaded.includes('credit') ? 'Dispute Support Evidence' : 'Credit Report'
  return 'Most Relevant Support Document'
}

export function getDocumentUsageLabels(category?: string): string[] {
  const value = String(category || '').toLowerCase()
  if (/credit_report|bureau_response/.test(value)) return ['Credit Profile', 'Credit Repair', 'Business Funding', 'Documents Vault']
  if (/dispute/.test(value)) return ['Credit Repair', 'Request Review', 'Documents Vault']
  if (/ein|formation|license|address|government_id/.test(value)) return ['Business Profile', 'Business Funding', 'Documents Vault']
  if (/bank|tax|profit|funding/.test(value)) return ['Business Funding', 'Request Review', 'Documents Vault']
  if (/review/.test(value)) return ['Request Review', 'Documents Vault']
  return ['Documents Vault']
}

export const DOCUMENT_CLASSIFICATION_DISCLOSURE = 'Suggested category based on upload context. GoClear will verify.'
