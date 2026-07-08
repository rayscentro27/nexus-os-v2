import { supabase, isSupabaseConfigured } from './supabaseClient'

export interface ResolvedClientContext {
  authUserId: string
  tenantId: string
  clientId: string
}

export async function resolveClientContextForCurrentUser(): Promise<ResolvedClientContext | null> {
  if (!isSupabaseConfigured || !supabase) return null

  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return null

  const { data: membership, error: membershipError } = await supabase
    .from('tenant_memberships')
    .select('tenant_id, client_id')
    .eq('user_id', user.id)
    .eq('role', 'client')
    .limit(1)
    .maybeSingle()

  if (membershipError || !membership?.tenant_id || !membership?.client_id) {
    const { data: profile } = await supabase
      .from('client_profiles')
      .select('tenant_id, client_id')
      .eq('user_id', user.id)
      .limit(1)
      .maybeSingle()

    if (profile?.tenant_id && profile?.client_id) {
      return { authUserId: user.id, tenantId: profile.tenant_id, clientId: profile.client_id }
    }

    return null
  }

  return { authUserId: user.id, tenantId: membership.tenant_id, clientId: membership.client_id }
}

export async function resolveClientContextForUser(userId: string): Promise<ResolvedClientContext | null> {
  if (!isSupabaseConfigured || !supabase) return null
  if (!userId) return null

  const { data: membership, error: membershipError } = await supabase
    .from('tenant_memberships')
    .select('tenant_id, client_id')
    .eq('user_id', userId)
    .eq('role', 'client')
    .limit(1)
    .maybeSingle()

  if (membershipError || !membership?.tenant_id || !membership?.client_id) {
    const { data: profile } = await supabase
      .from('client_profiles')
      .select('tenant_id, client_id')
      .eq('user_id', userId)
      .limit(1)
      .maybeSingle()

    if (profile?.tenant_id && profile?.client_id) {
      return { authUserId: userId, tenantId: profile.tenant_id, clientId: profile.client_id }
    }

    return null
  }

  return { authUserId: userId, tenantId: membership.tenant_id, clientId: membership.client_id }
}
