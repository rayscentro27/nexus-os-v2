/**
 * Hermes provider abstraction (browser side).
 *
 * The real chat/search providers run SERVER-SIDE only (Supabase Edge Functions hold the keys);
 * the browser never contains a chat/search API key. The frontend only knows a boolean flag
 * (VITE_HERMES_CHAT_ENABLED / VITE_HERMES_SEARCH_ENABLED) saying whether the server endpoint is
 * available, and which provider to use is selected server-side by env (env-based, not hardcoded).
 *
 * If no provider is configured, the caller renders a clear "not configured" message — Hermes must
 * never fake current facts. Private data is never sent to a public provider/search.
 */

import { supabase } from './supabaseClient';
import { containsSensitive } from './dataScopes';

const CHAT_ENABLED = (import.meta.env.VITE_HERMES_CHAT_ENABLED as string | undefined) === 'true';
const SEARCH_ENABLED = (import.meta.env.VITE_HERMES_SEARCH_ENABLED as string | undefined) === 'true';

export interface ProviderResult {
  configured: boolean;   // false → caller shows the canonical "not configured" line
  blocked?: boolean;     // true → request was refused by the firewall (do not show not-configured)
  text: string;
}

const NOT_CONFIGURED: ProviderResult = { configured: false, text: '' };

/** Conversational reply from the real chat provider (server-side), or not-configured. */
export async function hermesChat(message: string, mode: string): Promise<ProviderResult> {
  if (!CHAT_ENABLED || !supabase) return NOT_CONFIGURED;
  if (containsSensitive(message))
    return { configured: true, blocked: true, text: "I won't send that to an external model — it looks like private data." };
  try {
    const { data, error } = await supabase.functions.invoke('hermes-chat', { body: { message, mode } });
    if (error || !data || data.configured === false) return NOT_CONFIGURED;
    return { configured: true, text: String(data.reply ?? '') };
  } catch {
    return NOT_CONFIGURED;
  }
}

/** Public web search (server-side) for public questions only, or not-configured. */
export async function publicSearch(query: string): Promise<ProviderResult> {
  if (!SEARCH_ENABLED || !supabase) return NOT_CONFIGURED;
  if (containsSensitive(query))
    return { configured: true, blocked: true, text: "That looks like private data — I won't search public sources for it." };
  try {
    const { data, error } = await supabase.functions.invoke('hermes-search', { body: { query } });
    if (error || !data || data.configured === false) return NOT_CONFIGURED;
    return { configured: true, text: String(data.summary ?? '') };
  } catch {
    return NOT_CONFIGURED;
  }
}

export const CHAT_NOT_CONFIGURED_MSG = 'Hermes chat provider is not configured yet.';
export const SEARCH_NOT_CONFIGURED_MSG = 'Public search is not configured yet, so I cannot verify current information.';
