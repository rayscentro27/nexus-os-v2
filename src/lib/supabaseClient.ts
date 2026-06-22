import { createClient, type SupabaseClient } from '@supabase/supabase-js';

/**
 * Frontend Supabase client — uses ONLY the anon key + URL (VITE_* vars).
 * The service-role key is never imported here and must never reach the browser.
 *
 * When env is not configured yet, `supabase` is null and the UI shows a setup state
 * instead of fake data (no reports-as-state, no mock numbers).
 */
const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

export const isSupabaseConfigured = Boolean(url && anonKey);

export const supabase: SupabaseClient | null = isSupabaseConfigured
  ? createClient(url as string, anonKey as string, { auth: { persistSession: false } })
  : null;
