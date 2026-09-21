import { supabase, isSupabaseConfigured } from './supabaseClient';
import { persistClydeReceipt } from './goclearBetaClosure';

export async function askClientAI(message: string, sessionId?: string, mode: 'clyde' | 'customer_service' = 'clyde') {
  if (!supabase || !isSupabaseConfigured) return { ok: false, error: 'client_ai_not_configured' } as const;
  const { data, error } = await supabase.functions.invoke('client-ai-gateway', { body: { message, sessionId, mode } });
  if (error) return { ok: false, error: error.message || 'client_ai_unavailable' } as const;
  if (data?.answer) {
    const receipt = await persistClydeReceipt({ question: message, answer: String(data.answer), status: data.decision === 'POLICY_DENY' ? 'policy_denied' : data.decision === 'POLICY_ESCALATE' ? 'escalated' : 'completed', intent: data.intent, model: data.model_tier });
    if (!receipt.ok) return { ok: false, error: `clyde_receipt_failed:${receipt.error}` } as const;
    data.clyde_receipt_id = receipt.receiptId;
  }
  return { ok: true, data } as const;
}
