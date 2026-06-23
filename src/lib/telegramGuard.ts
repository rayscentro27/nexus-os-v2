import { supabase } from './supabaseClient';

/**
 * Telegram guard foundation (adapted from v1 lib/telegram_send_guard.py + run_lock.py).
 *
 * DRY-RUN ONLY in this pass — it never sends a real Telegram message. It records the
 * attempt to `telegram_messages` (suppressed=true) and a `nexus_events` row, so the ledger
 * shows intent without any outbound side effect. Real sending requires an explicit
 * server-side sender + allowlist/rate-limit/dedupe added later, gated behind a flag.
 */

const ENABLED = false; // hard off in the foundation pass; never sends.

async function hash(text: string): Promise<string> {
  try {
    const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
    return Array.from(new Uint8Array(buf)).slice(0, 8).map((b) => b.toString(16).padStart(2, '0')).join('');
  } catch {
    return String(text.length);
  }
}

export async function guardedTelegram(opts: {
  purpose: string; body: string; chatLabel?: string;
}): Promise<{ sent: boolean; reason: string }> {
  const messageHash = await hash(`${opts.purpose}|${opts.body}`);
  if (supabase) {
    await supabase.from('telegram_messages').insert({
      purpose: opts.purpose,
      chat_label: opts.chatLabel ?? 'war_room',
      message_hash: messageHash,
      body_preview: opts.body.slice(0, 240),
      status: 'suppressed',
      suppressed: true,
      payload: { dry_run: true, enabled: ENABLED },
    });
    await supabase.from('nexus_events').insert({
      lane: 'communication', source: 'telegram_guard', action: 'telegram_dry_run',
      status: 'info', title: `Telegram (dry-run): ${opts.purpose}`,
      summary: 'Recorded only — no real message sent (guard disabled in foundation pass).',
    });
  }
  return { sent: false, reason: 'dry_run_disabled' };
}
