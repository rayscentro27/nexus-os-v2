import { useEffect, useState } from 'react'
import '../styles/v2-tailwind.generated.css'
import '../styles/v2-theme.css'
import { useSession } from '../../components/auth'
import { resolveClientContextForCurrentUser } from '../../lib/clientAuthContext'
import { supabase, isSupabaseConfigured } from '../../lib/supabaseClient'
import { useV2ClientData } from '../hooks/useV2ClientData'
import { AppShellV2 } from '../layouts/AppShellV2'
import { DashboardV2 } from './DashboardV2'
import { PlaceholderV2 } from './PlaceholderV2'
import { ROUTE_LABELS, navigateV2 } from '../utils/navigate'

export const normalizePath = (p: string) => {
  if (p === '/client-v2' || p === '/client-v2/') return '/client-v2/dashboard'
  if (p.startsWith('/client-v2/')) return p
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
    if (loading || !user) return
    let cancelled = false
    ;(async () => {
      try {
        const admin = await isUserAdmin(user.id)
        if (cancelled) return
        if (admin) {
          setClientOk(false)
          return
        }
        const ctx = await resolveClientContextForCurrentUser()
        if (!cancelled) setClientOk(!!ctx)
      } catch {
        if (!cancelled) setClientOk(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [user, loading])

  if (loading || clientOk === null) {
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
  const known = Boolean(ROUTE_LABELS[path])
  const safePath = known ? path : '/client-v2/dashboard'
  return (
    <AppShellV2
      profile={data.profile}
      railStages={data.railStages}
      currentPath={safePath}
      isDemo={data.isDemo}
      onNavigate={navigateV2}
    >
      {safePath === '/client-v2/dashboard' ? <DashboardV2 data={data} /> : <PlaceholderV2 path={safePath} />}
    </AppShellV2>
  )
}