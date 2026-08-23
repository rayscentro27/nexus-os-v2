import React, { useEffect, useMemo, useState } from 'react'
import SafeMarkdown from './SafeMarkdown'
import NexusUniversalComposer from './NexusUniversalComposer'
import HermesAlphaWorkspace from './HermesAlphaWorkspace'
import { respondAsAlpha } from '../hermes/alpha/hermesAlphaConversationEngine'
import { sendThroughCanonicalHermes } from '../lib/hermes/hermesAdminConversationAdapter'

const NOVA_ENDPOINT = import.meta.env.VITE_NEXUS_NOVA_ENDPOINT || 'https://nova.goclearonline.cc/v1/nova/chat'
const AGENT_META = {
  hermes: { name: 'Nexus / Hermes', role: 'Operator · COO · Chief of Staff', tone: 'hermes', placeholder: 'Ask Nexus what matters, what changed, or what needs you…' },
  nova: { name: 'Nova', role: 'Strategic Adviser · Critic', tone: 'nova', placeholder: 'Ask Nova for a strategy critique or second opinion…' },
  alpha: { name: 'Alpha', role: 'Research · Evidence · Intelligence', tone: 'alpha', placeholder: 'Ask Alpha to research, compare, or source a claim…' },
}

function storageKey(agent, id) { return `nexus-experience-chat:${agent}:${id}` }
function newConversation(agent) { return { id: `${agent}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, agent, title: 'New conversation', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), messages: [] } }
function loadConversation(agent, id) { try { const raw = localStorage.getItem(storageKey(agent, id)); return raw ? JSON.parse(raw) : null } catch { return null } }
function saveConversation(conversation) { try { localStorage.setItem(storageKey(conversation.agent, conversation.id), JSON.stringify({ ...conversation, messages: conversation.messages.slice(-60) })) } catch { /* persistence is best-effort */ } }
function listConversations(agent) { try { return Object.keys(localStorage).filter(key => key.startsWith(`nexus-experience-chat:${agent}:`)).map(key => JSON.parse(localStorage.getItem(key))).filter(Boolean).sort((a,b) => String(b.updatedAt).localeCompare(String(a.updatedAt))) } catch { return [] } }
function titleFor(text) { return text.replace(/\s+/g, ' ').trim().slice(0, 48) || 'New conversation' }

export default function NexusAgentConversation({ agent = 'hermes', conversationId = null, onConversationChange, context = null }) {
  const [conversation, setConversation] = useState(() => conversationId ? loadConversation(agent, conversationId) || newConversation(agent) : newConversation(agent))
  const [history, setHistory] = useState(() => listConversations(agent))
  const [thinking, setThinking] = useState(false)
  const meta = AGENT_META[agent] || AGENT_META.hermes

  useEffect(() => {
    const restored = conversationId ? loadConversation(agent, conversationId) : null
    if (restored) setConversation(restored)
    else if (conversation.agent !== agent || (conversationId && conversation.id !== conversationId)) setConversation(newConversation(agent))
  }, [agent, conversationId])
  useEffect(() => { if (conversation.id) { saveConversation(conversation); setHistory(listConversations(agent)) } }, [conversation, agent])

  function openConversation(item) { setConversation(loadConversation(agent, item.id) || item); onConversationChange?.(item.id) }
  function createChat() { const next = newConversation(agent); setConversation(next); onConversationChange?.(next.id) }

  async function send(text) {
    if (!text.trim() || thinking) return
    const now = new Date().toISOString(); const user = { id: `${Date.now()}-user`, role: 'user', text, createdAt: now }
    setConversation(current => ({ ...current, title: current.messages.length ? current.title : titleFor(text), updatedAt: now, messages: [...current.messages, user] }))
    setThinking(true)
    try {
      let response
      if (agent === 'hermes') {
        const recentHistory = conversation.messages.slice(-10).map(message => ({ role: message.role === 'assistant' ? 'assistant' : 'user', content: message.text }))
        const result = await sendThroughCanonicalHermes({ message: text, sessionId: `nexus-${conversation.id}`, pageId: 'agents-hermes', route: window.location.href, recentHistory })
        response = { role: 'assistant', text: result.text, meta: `${result.evidenceState || 'UNKNOWN'} · canonical Hermes`, response: result }
      } else if (agent === 'nova') {
        const result = await fetch(NOVA_ENDPOINT, { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json', 'X-Nexus-Nova-Session': conversation.id }, body: JSON.stringify({ message: text, conversation_id: conversation.id, channel: 'admin_browser' }) })
        const payload = await result.json(); if (!result.ok) throw new Error(payload.error || 'Nova browser transport unavailable')
        response = { role: 'assistant', text: payload.text || 'Nova returned no response.', meta: `${payload.model || 'configured model'} · canonical Nova graph` }
      } else {
        const result = respondAsAlpha(text, 'General Conversation', Date.now())
        response = { role: 'assistant', text: result.text, meta: `${result.provider || 'deterministic_local'} · canonical Alpha route` }
      }
      setConversation(current => ({ ...current, updatedAt: new Date().toISOString(), messages: [...current.messages, response] }))
    } catch (error) {
      setConversation(current => ({ ...current, updatedAt: new Date().toISOString(), messages: [...current.messages, { role: 'error', text: error?.message || 'Agent unavailable.', createdAt: new Date().toISOString() }] }))
    } finally { setThinking(false) }
  }

  if (agent === 'alpha' && false) return <HermesAlphaWorkspace />
  return <section className={`nx2-agent-thread nx2-agent-${meta.tone}`} data-testid={`${agent}-conversation`}>
    <div className="nx2-thread-toolbar"><div><div className="nx2-eyebrow">AGENTS / {agent.toUpperCase()}</div><h2>{meta.name}</h2><p>{meta.role} · <span className="nx2-truth">Separate brain and authority</span></p></div><div className="nx2-thread-actions"><button type="button" onClick={createChat}>+ New Chat</button><button type="button" onClick={() => window.open(window.location.href, '_blank')}>Open in new tab ↗</button></div></div>
    <div className="nx2-thread-layout"><aside className="nx2-chat-history"><div className="nx2-section-label">{meta.name} chats</div>{history.length === 0 && <p className="nx2-muted">No saved chats yet.</p>}{history.map(item => <button type="button" className={`nx2-history-item ${item.id === conversation.id ? 'active' : ''}`} key={item.id} onClick={() => openConversation(item)}><strong>{item.title}</strong><small>{new Date(item.updatedAt).toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}</small><span>{item.messages?.find(message => message.role === 'user')?.text?.slice(0, 54) || 'Empty conversation'}</span></button>)}</aside><main className="nx2-thread-main"><div className="nx2-conversation-log" aria-live="polite">{conversation.messages.length === 0 && <div className="nx2-empty-thread"><div className={`nx2-agent-orb ${meta.tone}`}>{agent === 'hermes' ? 'N' : agent[0].toUpperCase()}</div><h3>Start a conversation with {meta.name}</h3><p>{meta.placeholder}</p><div className="nx2-suggestion-row"><button type="button" onClick={() => send(agent === 'hermes' ? 'What should I focus on today?' : agent === 'nova' ? 'Challenge my current Nexus priorities.' : 'Research what deserves attention next.')}>Try a sample prompt</button></div></div>}{conversation.messages.map(message => <article className={`nx2-message nx2-message-${message.role}`} key={message.id || `${message.role}-${message.text}`}><div className="nx2-message-label">{message.role === 'user' ? 'Ray' : message.role === 'error' ? 'Transport' : meta.name}</div>{message.role === 'assistant' ? <SafeMarkdown>{message.text}</SafeMarkdown> : <p>{message.text}</p>}{message.meta && <small className="nx2-message-meta">{message.meta}</small>}</article>)}{thinking && <div className="nx2-thinking">{meta.name} is thinking…</div>}</div><NexusUniversalComposer agent={agent} onAgentChange={next => onConversationChange?.(conversation.id, next)} onSend={send} disabled={thinking} context={context} placeholder={meta.placeholder} /></main></div>
  </section>
}
