// Nexus integration layer for the approved Admin Center (data only — no styling).
// Source of truth: /.netlify/functions/admin-nexus-state (admin-guarded), which serves the
// read model published from authoritative Nexus state (same project reader Nova uses).
import { createClient, type SupabaseClient } from '@supabase/supabase-js';

export type LiveStatus = 'loading' | 'ready' | 'unauthenticated' | 'forbidden' | 'unavailable';

export interface LiveSnapshot {
  areas: Record<string, any>;
  generated_at: string | null;
  age_seconds: number | null;
  freshness: 'LIVE' | 'STALE' | 'UNKNOWN';
}

// Same normalization as the main app (src/lib/supabaseClient.ts) so both resolve the same session key.
const rawUrl = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const url = rawUrl ? (/^https?:\/\//i.test(rawUrl) ? rawUrl : `https://${rawUrl}`) : undefined;
const anon = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;
let client: SupabaseClient | null = null;
export const supabase = (): SupabaseClient | null => {
  if (!client && url && anon) {
    // Same project + default storage key as the main app: /admin/login's session is shared.
    client = createClient(url, anon, { auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: false } });
  }
  return client;
};

const LOCAL_SNAPSHOT = import.meta.env.DEV ? (import.meta.env.VITE_ADMIN_LOCAL_SNAPSHOT as string | undefined) : undefined;

export async function loadLiveSnapshot(): Promise<{ status: LiveStatus; snapshot?: LiveSnapshot; error?: string }> {
  if (LOCAL_SNAPSHOT) {
    // Dev-only visual verification against a real published read model file (never used in production builds).
    const r = await fetch(LOCAL_SNAPSHOT, { cache: 'no-store' });
    if (!r.ok) return { status: 'unavailable', error: `local_snapshot_${r.status}` };
    const areas = await r.json();
    return { status: 'ready', snapshot: { areas, generated_at: areas?.meta?.generated_at ?? null, age_seconds: null, freshness: 'UNKNOWN' } };
  }
  const sb = supabase();
  if (!sb) return { status: 'unavailable', error: 'supabase_not_configured' };
  const { data } = await sb.auth.getSession();
  const token = data.session?.access_token;
  if (!token) return { status: 'unauthenticated' };
  const response = await fetch('/.netlify/functions/admin-nexus-state', {
    headers: { authorization: `Bearer ${token}` },
    cache: 'no-store',
  }).catch(() => null);
  if (!response) return { status: 'unavailable', error: 'network' };
  if (response.status === 401) return { status: 'unauthenticated' };
  if (response.status === 403) return { status: 'forbidden' };
  if (!response.ok) return { status: 'unavailable', error: `http_${response.status}` };
  const body = await response.json();
  return { status: 'ready', snapshot: body as LiveSnapshot };
}

export function redirectToLogin() {
  const next = encodeURIComponent(window.location.pathname + window.location.hash);
  window.location.assign(`/admin/login?next=${next}`);
}

export const LIVE_REFRESH_MS = 60_000;
