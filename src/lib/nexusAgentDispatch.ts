import { respondAsAlpha } from '../hermes/alpha/hermesAlphaConversationEngine'
import { sendThroughCanonicalHermes } from './hermes/hermesAdminConversationAdapter'
import { containsSensitive } from './dataScopes'
import { supabase } from './supabaseClient'

export type VoiceAgent = 'hermes' | 'nova' | 'alpha'
export const AGENT_THREAD_PREFIX = 'nexus-experience-chat:'
const ACTIVE_THREAD_PREFIX = 'nexus-experience-active-thread:'
const NOVA_POLL_INTERVAL_MS = 1000
const NOVA_POLL_TIMEOUT_MS = 190000

async function sendRemoteNovaCommand({ conversationId, text }: { conversationId: string, text: string }) {
  if (!supabase) throw new Error('Remote Nova transport is not configured.')
  const userMessage = await supabase.from('admin_ai_messages').select('id,created_at').eq('conversation_id', conversationId).eq('role', 'user').eq('content', text).order('created_at', { ascending: false }).limit(1).maybeSingle()
  if (userMessage.error || !userMessage.data) throw new Error(userMessage.error?.message || 'Nova command receipt could not be found.')
  const deadline = Date.now() + NOVA_POLL_TIMEOUT_MS
  while (Date.now() < deadline) {
    await new Promise(resolve => window.setTimeout(resolve, NOVA_POLL_INTERVAL_MS))
    const current = await supabase.from('admin_ai_messages').select('role,content,created_at').eq('conversation_id', conversationId).gt('created_at', userMessage.data.created_at).order('created_at', { ascending: true }).limit(1).maybeSingle()
    if (current.error) throw new Error(`Nova response status unavailable: ${current.error.message}`)
    if (current.data?.role === 'error') throw new Error(current.data.content || 'Nova command failed.')
    if (current.data?.content) return { response: current.data.content, profile: 'nova_nexus', runtime: 'hermes' }
  }
  throw new Error('Nova command timed out while waiting for canonical Hermes.')
}

export function threadStorageKey(agent: VoiceAgent, id: string) { return `${AGENT_THREAD_PREFIX}${agent}:${id}` }
export function activeThreadKey(agent: VoiceAgent) { return `${ACTIVE_THREAD_PREFIX}${agent}` }
export function getActiveThread(agent: VoiceAgent) { try { return localStorage.getItem(activeThreadKey(agent)) } catch { return null } }
export function setActiveThread(agent: VoiceAgent, id: string) { try { localStorage.setItem(activeThreadKey(agent), id) } catch { /* browser policy */ } }
export function loadThread(agent: VoiceAgent, id: string) { try { const raw = localStorage.getItem(threadStorageKey(agent, id)); return raw ? JSON.parse(raw) : null } catch { return null } }
export function saveThread(thread: any) { try { const messages = (thread.messages || []).filter((message: any) => !containsSensitive(String(message.text || ''))); localStorage.setItem(threadStorageKey(thread.agent, thread.id), JSON.stringify({ ...thread, messages: messages.slice(-60) })) } catch { /* best effort */ } }
export function createThread(agent: VoiceAgent, title = 'New conversation') { const now = new Date().toISOString(); return { id: `${agent}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, agent, title, createdAt: now, updatedAt: now, messages: [] } }

export function stripWakePhrase(text: string) { return text.trim().replace(/^[,\s.!?]*(?:hey\s+)?(?:nexus|hermes|nova|alpha)\b[,\s.!?]*/i, '').trim() }
export function routeWakePhrase(text: string): VoiceAgent | null { const match = text.trim().match(/^(?:hey\s+)?(nexus|hermes|nova|alpha)\b/i); if (!match) return null; const name = match[1].toLowerCase(); return name === 'nexus' || name === 'hermes' ? 'hermes' : name as VoiceAgent }
export function isNewThreadCommand(text: string) { return /^(?:start\s+(?:a\s+)?new\s+(?:chat|conversation)|new\s+(?:chat|conversation))\b/i.test(stripWakePhrase(text)) }
export function deriveThreadTitle(text: string) { return stripWakePhrase(text).replace(/^(?:start\s+(?:a\s+)?new\s+(?:chat|conversation)(?:\s+called)?\s*)/i, '').replace(/\s+/g, ' ').trim().slice(0, 48) || 'New conversation' }

export async function sendAgentMessage({ agent, conversationId, text, recentHistory = [] }: { agent: VoiceAgent, conversationId: string, text: string, recentHistory?: Array<{ role: string, content: string }> }) {
  if (agent === 'hermes') {
      const result = await sendThroughCanonicalHermes({ message: text, sessionId: `nexus-${conversationId}`, pageId: 'agents-hermes', route: window.location.href, recentHistory: recentHistory as Array<{ role: 'user' | 'assistant', content: string }> })
    return { role: 'assistant', text: result.text, meta: `${result.evidenceState || 'UNKNOWN'} · canonical Hermes`, response: result }
  }
  if (agent === 'nova') {
    const payload = await sendRemoteNovaCommand({ conversationId, text })
    return { role: 'assistant', text: payload.response || 'Nova returned no response.', meta: `${payload.profile || 'nova_nexus'} · canonical Hermes`, response: payload }
  }
  const result = respondAsAlpha(text, 'General Conversation', Date.now())
  return { role: 'assistant', text: result.text, meta: `${result.provider || 'deterministic_local'} · canonical Alpha route` }
}
