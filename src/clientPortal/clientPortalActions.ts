// Client Portal Central Action Map
// All portal actions route through here for consistency.

export type PortalAction =
  | 'upload_credit_report'
  | 'upload_proof_of_address'
  | 'upload_documents'
  | 'improve_approval_odds'
  | 'view_credit_profile'
  | 'view_credit_utilization'
  | 'view_documents'
  | 'view_business_setup'
  | 'view_business_bankability'
  | 'view_funding_readiness'
  | 'view_recommendations'
  | 'view_resources'
  | 'request_review'
  | 'view_notifications'
  | 'view_messages'
  | 'view_help'
  | 'sign_out'

const ACTION_ROUTES: Record<PortalAction, string> = {
  upload_credit_report: '/client/documents',
  upload_proof_of_address: '/client/documents',
  upload_documents: '/client/documents',
  improve_approval_odds: '/client/credit-profile',
  view_credit_profile: '/client/credit-profile',
  view_credit_utilization: '/client/credit-profile',
  view_documents: '/client/documents',
  view_business_setup: '/client/business-setup',
  view_business_bankability: '/client/business-bankability',
  view_funding_readiness: '/client/funding-readiness',
  view_recommendations: '/client/recommendations',
  view_resources: '/client/resources',
  request_review: '/client/request-review',
  view_notifications: '/client/resources',
  view_messages: '/client/resources',
  view_help: '/client/resources',
  sign_out: '__sign_out__',
}

export function getRouteForAction(action: PortalAction): string {
  return ACTION_ROUTES[action] || '/client/dashboard'
}

export function handlePortalAction(action: PortalAction, navigate: (path: string) => void, signOut?: () => void) {
  if (action === 'sign_out' && signOut) {
    signOut()
    return
  }
  const route = getRouteForAction(action)
  if (route !== '__sign_out__') {
    navigate(route)
  }
}
