/** Hermes chat persistence — keeps conversation across tab/screen navigation and reloads.
 *  localStorage only; bounded; sensitive-looking messages are NOT persisted (firewall belt). */
import { containsSensitive } from './dataScopes';

const MSG_KEY = 'nexus_hermes_chat_history';
const MODE_KEY = 'nexus_hermes_mode';
const MAX = 50;

export interface StoredMsg { role: 'user' | 'hermes'; text: string; meta?: string }

function safe(): Storage | null {
  try { return typeof window !== 'undefined' ? window.localStorage : null; } catch { return null; }
}

export function loadMessages(): StoredMsg[] | null {
  const ls = safe(); if (!ls) return null;
  try {
    const raw = ls.getItem(MSG_KEY);
    if (!raw) return null;
    const arr = JSON.parse(raw);
    return Array.isArray(arr) ? arr.slice(-MAX) : null;
  } catch { return null; }
}

export function saveMessages(messages: StoredMsg[]): void {
  const ls = safe(); if (!ls) return;
  try {
    // Drop anything that trips the firewall before it ever touches storage.
    const clean = messages.filter((m) => m.text && !containsSensitive(m.text)).slice(-MAX);
    ls.setItem(MSG_KEY, JSON.stringify(clean));
  } catch { /* quota / disabled — ignore */ }
}

export function loadMode(): string | null {
  const ls = safe(); return ls ? ls.getItem(MODE_KEY) : null;
}

export function saveMode(mode: string): void {
  const ls = safe(); if (ls) try { ls.setItem(MODE_KEY, mode); } catch { /* ignore */ }
}

export function clearChat(): void {
  const ls = safe(); if (ls) try { ls.removeItem(MSG_KEY); } catch { /* ignore */ }
}

/** Reusable universal Hermes-state API (used by Command Center + any tab). Persistence is
 *  localStorage-backed; the chosen model (vs. a context provider) is documented in
 *  NEXUS_HERMES_CHAT_PERSISTENCE.md. */
export const hermesStore = {
  getMessages: (): StoredMsg[] => loadMessages() ?? [],
  saveMessages: (msgs: StoredMsg[]): void => { saveMessages(msgs); },
  addMessage: (m: StoredMsg): StoredMsg[] => { const next = [...(loadMessages() ?? []), m]; saveMessages(next); return next.slice(-MAX); },
  clearHistory: clearChat,
  setMode: saveMode,
  getMode: loadMode,
};
