type NavigateHandler = (path: string) => void

let navigateHandler: NavigateHandler | null = null

export const setV2NavigateHandler = (fn: NavigateHandler | null) => {
  navigateHandler = fn
}

export const navigateV2 = (path: string) => {
  if (navigateHandler) {
    navigateHandler(path)
    return
  }
  if (window.location.pathname === path) return
  window.history.pushState({}, '', path)
  window.dispatchEvent(new PopStateEvent('popstate'))
  window.scrollTo({ top: 0 })
}

const ROUTE_MAP: Array<[string, string]> = [
  ['/client-v2/', '/client-v2/'],
  ['/client/credit-repair-journey', '/client-v2/credit-improvement'],
  ['/client/credit-improvement', '/client-v2/credit-improvement'],
  ['/client/credit-rounds', '/client-v2/credit-improvement'],
  ['/client/credit-profile', '/client-v2/credit-review'],
  ['/client/credit-review', '/client-v2/credit-review'],
  ['/client/business-foundation', '/client-v2/business-foundation'],
  ['/client/business-bankability', '/client-v2/business-foundation'],
  ['/client/business-setup', '/client-v2/business-foundation'],
  ['/client/funding-readiness', '/client-v2/funding-readiness'],
  ['/client/request-review', '/client-v2/funding-access'],
  ['/client/funding-access', '/client-v2/funding-access'],
  ['/client/dashboard', '/client-v2/dashboard'],
  ['/client/documents', '/client-v2/documents'],
  ['/client/resources', '/client-v2/resources'],
  ['/client/messages', '/client-v2/messages'],
  ['/client/billing', '/client-v2/billing'],
]

export const mapRouteToV2 = (route: string): string => {
  if (!route) return '/client-v2/dashboard'
  for (const [oldRoute, v2Route] of ROUTE_MAP) {
    if (route.startsWith(oldRoute)) return v2Route
  }
  return '/client-v2/dashboard'
}

export const ROUTE_LABELS: Record<string, string> = {
  '/client-v2/dashboard': 'Dashboard',
  '/client-v2/credit-review': 'Credit Review',
  '/client-v2/credit-improvement': 'Credit Improvement',
  '/client-v2/business-foundation': 'Business Foundation',
  '/client-v2/funding-readiness': 'Funding Readiness',
  '/client-v2/funding-access': 'Funding Access',
  '/client-v2/documents': 'Documents',
  '/client-v2/resources': 'Resources',
  '/client-v2/messages': 'Messages',
  '/client-v2/billing': 'Billing',
}