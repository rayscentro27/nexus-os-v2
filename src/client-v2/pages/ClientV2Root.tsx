import { useEffect, useState } from 'react'
import '../styles/v2-tailwind.generated.css'
import '../styles/v2-theme.css'
import { useSession } from '../../components/auth'
import { resolveClientContextForUser } from '../../lib/clientAuthContext'
import { supabase, isSupabaseConfigured } from '../../lib/supabaseClient'
import { useV2ClientData } from '../hooks/useV2ClientData'
import { AppShellV2 } from '../layouts/AppShellV2'
import { DashboardV2 } from './DashboardV2'
import { CreditReviewV2 } from './CreditReviewV2'
import { CreditImprovementV2 } from './CreditImprovementV2'
import { DocumentsV2 } from './DocumentsV2'
import { BusinessFoundationV2 } from './BusinessFoundationV2'
import { FundingReadinessV2 } from './FundingReadinessV2'
import { FundingAccessV2 } from './FundingAccessV2'
import { ResourcesV2 } from './ResourcesV2'
import { BillingV2 } from './BillingV2'
import { PlaceholderV2 } from './PlaceholderV2'
import { RouteContractV2 } from './RouteContractV2'
import type { V2ViewData } from '../types/v2-models'
import { ROUTE_LABELS, navigateV2, mapRouteToV2 } from '../utils/navigate'
import { V2_ROUTE_CONTRACTS } from '../routeContracts'

const IMPLEMENTED_V2_ROUTES = new Set([
  '/client-v2/dashboard',
  '/client-v2/credit-review',
  '/client-v2/credit-improvement',
  '/client-v2/documents',
  '/client-v2/business-foundation',
  '/client-v2/funding-readiness',
  '/client-v2/funding-access',
  '/client-v2/resources',
  '/client-v2/billing',
])

export function renderV2Page(path: string, data: V2ViewData) {
  if (V2_ROUTE_CONTRACTS[path] && !IMPLEMENTED_V2_ROUTES.has(path)) {
    return <RouteContractV2 path={path} data={data} />
  }
  switch (path) {
    case '/client-v2/dashboard':
      return <DashboardV2 data={data} />
    case '/client-v2/credit-review':
      return <CreditReviewV2 data={data} />
    case '/client-v2/credit-improvement':
      return <CreditImprovementV2 data={data} />
    case '/client-v2/documents':
      return <DocumentsV2 data={data} />
    case '/client-v2/business-foundation':
      return <BusinessFoundationV2 data={data} />
    case '/client-v2/funding-readiness':
      return <FundingReadinessV2 data={data} />
    case '/client-v2/funding-access':
      return <FundingAccessV2 data={data} />
    case '/client-v2/resources':
      return <ResourcesV2 data={data} />
    case '/client-v2/billing':
      return <BillingV2 data={data} />
    default:
      return <PlaceholderV2 path={path} />
  }
}

export const normalizePath = (p: string) => {
  if (p === '/client-v2' || p === '/client-v2/') return '/client-v2/dashboard'
  if (p.startsWith('/client-v2/')) return p
  if (p === '/client' || p.startsWith('/client/')) return mapRouteToV2(p)
  return '/client-v2/dashboard'
}

async function isUserAdmin(userId: string): Promise<boolean> {
  if (!isSupabaseConfigured || !supabase) return false
  try {
    const { data: adminRow } = await supabase
      .from('admin_users')
      .select('id')
      .eq('id', userId)
      .maybeSingle()
    if (adminRow) return true
  } catch {}
  try {
    const { data: membership } = await supabase
      .from('tenant_memberships')
      .select('role')
      .eq('user_id', userId)
      .in('role', ['super_admin', 'admin', 'operator'])
      .limit(1)
      .maybeSingle()
    if (membership) return true
  } catch {}
  return false
}

export function ClientV2Gate() {
  const { user, loading } = useSession()
  const [clientOk, setClientOk] = useState<boolean | null>(null)

  useEffect(() => {
    if (loading) return
    if (!user) {
      setClientOk(false)
      return
    }
    let cancelled = false
    ;(async () => {
      for (let attempt = 0; attempt < 3 && !cancelled; attempt += 1) {
        try {
          const admin = await isUserAdmin(user.id)
          if (cancelled) return
          if (admin) { setClientOk(false); return }
          // Resolve membership with the user already authenticated by useSession.
          // Re-reading auth.getUser here can briefly return no user during the
          // post-login session handoff even though the authenticated REST query
          // is valid.
          const ctx = await resolveClientContextForUser(user.id)
          if (ctx) { setClientOk(true); return }
        } catch {}
        await new Promise(resolve => window.setTimeout(resolve, 250))
      }
      if (!cancelled) setClientOk(false)
    })()
    return () => {
      cancelled = true
    }
  }, [user, loading])

  if (loading || (user && clientOk === null)) {
    return (
      <div className="v2-app min-h-screen flex items-center justify-center">
        <div className="text-v2muted text-v2base">Preparing your portal…</div>
      </div>
    )
  }
  if (!user || !clientOk) {
    window.location.assign('/client-v2/login')
    return (
      <div className="v2-app min-h-screen flex items-center justify-center">
        <div className="text-v2muted text-v2base">Redirecting to login…</div>
      </div>
    )
  }
  return <ClientV2Root />
}

export function ClientV2Root() {
  const path = normalizePath(window.location.pathname)
  const data = useV2ClientData(path)
  const known = Boolean(ROUTE_LABELS[path] || V2_ROUTE_CONTRACTS[path])
  const safePath = known ? path : '/client-v2/dashboard'
  return (
    <AppShellV2
      profile={data.profile}
      railStages={data.railStages}
      currentPath={safePath}
      isDemo={data.isDemo}
      onNavigate={navigateV2}
    >
      {renderV2Page(safePath, data)}
    </AppShellV2>
  )
}
