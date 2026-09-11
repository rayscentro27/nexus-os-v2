import { supabase, isSupabaseConfigured } from './supabaseClient';

export async function askClientAI(message: string, sessionId?: string, mode: 'clyde' | 'customer_service' = 'clyde') {
  if (!supabase || !isSupabaseConfigured) return { ok: false, error: 'client_ai_not_configured' } as const;
  const { data, error } = await supabase.functions.invoke('client-ai-gateway', { body: { message, sessionId, mode } });
  if (error) return { ok: false, error: error.message || 'client_ai_unavailable' } as const;
  return { ok: true, data } as const;
}
