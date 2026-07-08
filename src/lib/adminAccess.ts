import { supabase, isSupabaseConfigured } from '../lib/supabaseClient';

export type AdminAccessSource = 'admin_users' | 'tenant_memberships' | 'none';

export interface AdminAccessResult {
  allowed: boolean;
  source: AdminAccessSource;
  role?: string;
  reason?: string;
}

export async function checkAdminAccess(): Promise<AdminAccessResult> {
  if (!isSupabaseConfigured || !supabase) {
    return { allowed: false, source: 'none', reason: 'Supabase not configured' };
  }

  const { data: { user } } = await supabase.auth.getUser();
  if (!user) {
    return { allowed: false, source: 'none', reason: 'Not authenticated' };
  }

  try {
    const { data: adminRow, error: adminError } = await supabase
      .from('admin_users')
      .select('id, active, role')
      .eq('id', user.id)
      .maybeSingle();

    if (!adminError && adminRow && adminRow.active !== false) {
      return {
        allowed: true,
        source: 'admin_users',
        role: adminRow.role || 'admin',
        reason: 'Active admin_users record',
      };
    }
  } catch {
    // table may not exist; fall through to tenant_memberships
  }

  try {
    const { data: membership, error: membershipError } = await supabase
      .from('tenant_memberships')
      .select('role')
      .eq('user_id', user.id)
      .in('role', ['super_admin', 'admin', 'operator', 'owner'])
      .limit(1)
      .maybeSingle();

    if (!membershipError && membership?.role) {
      return {
        allowed: true,
        source: 'tenant_memberships',
        role: membership.role,
        reason: 'Admin role in tenant_memberships',
      };
    }
  } catch {
    // fall through
  }

  return {
    allowed: false,
    source: 'none',
    reason: 'No admin access found in admin_users or tenant_memberships',
  };
}
