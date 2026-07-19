/** Hermes chat persistence — keeps conversation across tab/screen navigation and reloads.
 *  localStorage only; bounded; sensitive-looking messages are NOT persisted (firewall belt). */
import { containsSensitive } from './dataScopes';
import { resetConversationState } from './hermesConversationState';
import { normalizeHermesWorkroomResponse, type HermesWorkroomResponse } from './hermes/hermesWorkroomResponse';

const MSG_KEY = 'nexus_hermes_chat_history';
const MODE_KEY = 'nexus_hermes_mode';
const SESSION_KEY = 'nexus_hermes_session_id';
const MAX = 50;
const CHAT_SCHEMA_VERSION = 2;

export interface StoredMsg { role: 'user' | 'hermes'; text: string; meta?: string; workroomResponse?: HermesWorkroomResponse }
interface StoredMessageEnvelope { schemaVersion: number; messages: StoredMsg[]; migratedAt?: string }

function safe(): Storage | null {
  try { return typeof window !== 'undefined' ? window.localStorage : null; } catch { return null; }
}

export function loadMessages(): StoredMsg[] | null {
  const ls = safe(); if (!ls) return null;
  try {
    const raw = ls.getItem(MSG_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    const source = Array.isArray(parsed)
      ? parsed
      : parsed && typeof parsed === 'object' && Array.isArray((parsed as StoredMessageEnvelope).messages)
        ? (parsed as StoredMessageEnvelope).messages
        : null;
    if (!source) return null;
    const normalized = source.map(normalizeStoredMessage).filter((item): item is StoredMsg => Boolean(item)).slice(-MAX);
    if (Array.isArray(parsed) || (parsed as StoredMessageEnvelope).schemaVersion !== CHAT_SCHEMA_VERSION) {
      saveMessages(normalized);
    }
    return normalized;
  } catch { return null; }
}

function normalizeStoredMessage(raw: unknown): StoredMsg | null {
  if (!raw || typeof raw !== 'object') return null;
  const candidate = raw as Partial<StoredMsg> & { role?: unknown; text?: unknown; workroomResponse?: unknown };
  const rawRole = String(candidate.role || '');
  const role = rawRole === 'user' || rawRole === 'ray' ? 'user' : rawRole === 'hermes' ? 'hermes' : null;
  const text = typeof candidate.text === 'string' ? candidate.text : '';
  if (!role || !text || containsSensitive(text)) return null;
  const normalized: StoredMsg = { role, text };
  if (role === 'hermes' && candidate.workroomResponse && typeof candidate.workroomResponse === 'object') {
    normalized.workroomResponse = normalizeHermesWorkroomResponse(candidate.workroomResponse as Partial<HermesWorkroomResponse>);
  }
  return JSON.parse(JSON.stringify(normalized)) as StoredMsg;
}

export function saveMessages(messages: StoredMsg[]): void {
  const ls = safe(); if (!ls) return;
  try {
    // Drop anything that trips the firewall before it ever touches storage.
    const clean = messages.map(normalizeStoredMessage).filter((m): m is StoredMsg => Boolean(m)).slice(-MAX);
    const envelope: StoredMessageEnvelope = { schemaVersion: CHAT_SCHEMA_VERSION, messages: clean };
    ls.setItem(MSG_KEY, JSON.stringify(envelope));
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
  resetConversationState();
}

export function getChatSessionId(): string {
  const ls = safe();
  if (!ls) return 'default';
  const existing = ls.getItem(SESSION_KEY);
  if (existing) return existing;
  const created = `hermes-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  try { ls.setItem(SESSION_KEY, created); } catch { return 'default'; }
  return created;
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
  getSessionId: getChatSessionId,
};
