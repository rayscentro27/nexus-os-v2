export type ReadinessStatus = 'ready_to_review' | 'almost_ready' | 'action_needed' | 'insufficient_information'
export interface BusinessProfileInput { businessName?: string; entityType?: string; stateRegistrationStatus?: string; einStatus?: string; businessAddress?: string; businessPhone?: string; businessEmail?: string; businessDomain?: string; naicsCode?: string; industry?: string; timeInBusiness?: string; revenueRange?: string; businessBankAccountStatus?: string; ownershipComplete?: boolean; licensesStatus?: string; documents?: string[] }
export interface BusinessReadinessAction { key: string; label: string; action: 'complete_field' | 'upload_document' | 'read_guidance' | 'recommended_resource' | 'request_goclear_help'; route: string }
export interface BusinessFundingReadiness { completenessScore: number; status: ReadinessStatus; tier1Status: ReadinessStatus; tier2Status: ReadinessStatus; missingRequirements: string[]; recommendedActions: BusinessReadinessAction[]; documentRequests: string[]; confidence: 'high' | 'medium' | 'low'; dataSufficiency: number }

export function evaluateBusinessFundingReadiness(profile: BusinessProfileInput): BusinessFundingReadiness {
  const fields: Array<[keyof BusinessProfileInput, string, BusinessReadinessAction]> = [
    ['businessName', 'Business name', { key: 'business_name', label: 'Complete business name', action: 'complete_field', route: '/client/profile' }],
    ['entityType', 'Entity type', { key: 'entity_type', label: 'Complete entity type', action: 'complete_field', route: '/client/profile' }],
    ['stateRegistrationStatus', 'State registration status', { key: 'state_registration', label: 'Review state registration guidance', action: 'read_guidance', route: '/client/business-setup' }],
    ['einStatus', 'EIN status', { key: 'ein_status', label: 'Complete EIN status (never full EIN)', action: 'complete_field', route: '/client/profile' }],
    ['businessAddress', 'Business address', { key: 'business_address', label: 'Complete business address', action: 'complete_field', route: '/client/profile' }],
    ['businessPhone', 'Business phone', { key: 'business_phone', label: 'Complete business phone', action: 'complete_field', route: '/client/profile' }],
    ['businessEmail', 'Business email', { key: 'business_email', label: 'Complete business email', action: 'complete_field', route: '/client/profile' }],
    ['industry', 'Industry', { key: 'industry', label: 'Complete industry and NAICS guidance', action: 'read_guidance', route: '/client/business-setup' }],
    ['timeInBusiness', 'Time in business', { key: 'time_in_business', label: 'Complete time in business', action: 'complete_field', route: '/client/profile' }],
    ['revenueRange', 'Revenue range', { key: 'revenue', label: 'Complete revenue range', action: 'complete_field', route: '/client/profile' }],
    ['businessBankAccountStatus', 'Business bank account status', { key: 'business_bank', label: 'Review business banking readiness', action: 'recommended_resource', route: '/client/business-bankability' }],
  ]
  const missing = fields.filter(([key]) => !profile[key]).map(([, label]) => label)
  const actions = fields.filter(([key]) => !profile[key]).map(([, , action]) => action)
  const documents = profile.documents || []
  const documentRequests = ['business formation document', 'proof of business address', 'business bank statements'].filter(name => !documents.some(doc => doc.toLowerCase().includes(name.split(' ')[0])))
  documentRequests.forEach((label, index) => actions.push({ key: `document_${index}`, label: `Upload ${label}`, action: 'upload_document', route: '/client/documents' }))
  const total = fields.length + 3
  const present = total - missing.length - documentRequests.length
  const score = Math.max(0, Math.round((present / total) * 100))
  const status: ReadinessStatus = present < 4 ? 'insufficient_information' : score >= 85 ? 'ready_to_review' : score >= 65 ? 'almost_ready' : 'action_needed'
  const tier1Status: ReadinessStatus = ['businessName', 'entityType', 'stateRegistrationStatus', 'einStatus', 'businessAddress', 'businessPhone', 'businessEmail', 'industry'].every(key => Boolean(profile[key as keyof BusinessProfileInput])) ? 'ready_to_review' : status === 'insufficient_information' ? status : 'action_needed'
  const tier2Status: ReadinessStatus = tier1Status === 'ready_to_review' && profile.timeInBusiness && profile.revenueRange && profile.businessBankAccountStatus && documentRequests.length === 0 ? 'ready_to_review' : status === 'insufficient_information' ? status : score >= 65 ? 'almost_ready' : 'action_needed'
  return { completenessScore: score, status, tier1Status, tier2Status, missingRequirements: missing, recommendedActions: actions.slice(0, 8), documentRequests, confidence: score >= 80 ? 'high' : score >= 45 ? 'medium' : 'low', dataSufficiency: present }
}
