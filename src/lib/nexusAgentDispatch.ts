import { respondAsAlpha } from '../hermes/alpha/hermesAlphaConversationEngine'
import { sendThroughCanonicalHermes } from './hermes/hermesAdminConversationAdapter'
import { containsSensitive } from './dataScopes'

export type VoiceAgent = 'hermes' | 'nova' | 'alpha'
export const AGENT_THREAD_PREFIX = 'nexus-experience-chat:'
const ACTIVE_THREAD_PREFIX = 'nexus-experience-active-thread:'
const NOVA_ENDPOINT = import.meta.env.VITE_NEXUS_NOVA_ENDPOINT || 'https://nova.goclearonline.cc/v1/nova/chat'

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
    const result = await fetch(NOVA_ENDPOINT, { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json', 'X-Nexus-Nova-Session': conversationId }, body: JSON.stringify({ message: text, conversation_id: conversationId, channel: 'admin_browser' }) })
    if (result.redirected || result.url.includes('cloudflareaccess.com')) throw new Error('Nova Access authentication required. Open nova.goclearonline.cc once, complete Ray Admin sign-in, then retry.')
    let payload: any = {}; try { payload = await result.json() } catch { /* handled below */ }
    if (!result.ok) throw new Error(payload.error || (result.status === 302 ? 'Nova Access authentication required' : 'Nova browser transport unavailable'))
    return { role: 'assistant', text: payload.text || 'Nova returned no response.', meta: `${payload.model || 'configured model'} · canonical Nova graph` }
  }
  const result = respondAsAlpha(text, 'General Conversation', Date.now())
  return { role: 'assistant', text: result.text, meta: `${result.provider || 'deterministic_local'} · canonical Alpha route` }
}
