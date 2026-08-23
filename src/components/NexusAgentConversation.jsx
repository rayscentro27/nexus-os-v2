import React, { useEffect, useMemo, useRef, useState } from 'react'
import SafeMarkdown from './SafeMarkdown'
import NexusUniversalComposer from './NexusUniversalComposer'
import { containsSensitive } from '../lib/dataScopes'
import { sendAgentMessage, setActiveThread } from '../lib/nexusAgentDispatch'

const NOVA_ENDPOINT = import.meta.env.VITE_NEXUS_NOVA_ENDPOINT || 'https://nova.goclearonline.cc/v1/nova/chat'
const AGENT_META = {
  hermes: { name: 'Nexus / Hermes', role: 'Operator · COO · Chief of Staff', tone: 'hermes', placeholder: 'Ask Nexus what matters, what changed, or what needs you…' },
  nova: { name: 'Nova', role: 'Strategic Adviser · Critic', tone: 'nova', placeholder: 'Ask Nova for a strategy critique or second opinion…' },
  alpha: { name: 'Alpha', role: 'Research · Evidence · Intelligence', tone: 'alpha', placeholder: 'Ask Alpha to research, compare, or source a claim…' },
}

function storageKey(agent, id) { return `nexus-experience-chat:${agent}:${id}` }
function newConversation(agent) { const now = new Date().toISOString(); return { id: `${agent}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, agent, title: 'New conversation', createdAt: now, updatedAt: now, messages: [] } }
function loadConversation(agent, id) { try { const raw = localStorage.getItem(storageKey(agent, id)); return raw ? JSON.parse(raw) : null } catch { return null } }
function saveConversation(conversation) { try { const safeMessages = (conversation.messages || []).filter(message => !containsSensitive(String(message.text || ''))); localStorage.setItem(storageKey(conversation.agent, conversation.id), JSON.stringify({ ...conversation, messages: safeMessages.slice(-60) })) } catch { /* best effort */ } }
function listConversations() {
  try { return Object.keys(localStorage).filter(key => key.startsWith('nexus-experience-chat:')).map(key => { try { return JSON.parse(localStorage.getItem(key)) } catch { return null } }).filter(item => item && item.agent && !item.archived).sort((a, b) => String(b.updatedAt).localeCompare(String(a.updatedAt))) } catch { return [] }
}
function titleFor(text) { return text.replace(/\s+/g, ' ').trim().slice(0, 48) || 'New conversation' }
function previewFor(item) { return item.messages?.find(message => message.role === 'user')?.text?.slice(0, 70) || 'Empty conversation' }
function groupFor(value) { const age = Date.now() - new Date(value || Date.now()).getTime(); if (age < 86400000) return 'Today'; if (age < 172800000) return 'Yesterday'; if (age < 604800000) return 'Previous 7 days'; if (age < 2592000000) return 'Previous 30 days'; return 'Older' }

export default function NexusAgentConversation({ agent = 'hermes', conversationId = null, initialPrompt = '', onConversationChange, context = null }) {
  const [conversation, setConversation] = useState(() => conversationId ? loadConversation(agent, conversationId) || newConversation(agent) : newConversation(agent))
  const [history, setHistory] = useState(() => listConversations())
  const [chatFilter, setChatFilter] = useState(agent)
  const [search, setSearch] = useState('')
  const [thinking, setThinking] = useState(false)
  const [railOpen, setRailOpen] = useState(false)
  const logRef = useRef(null)
  const initialPromptRef = useRef('')
  const meta = AGENT_META[agent] || AGENT_META.hermes

  useEffect(() => {
    const restored = conversationId ? loadConversation(agent, conversationId) : null
    if (restored) setConversation(restored)
    else if (conversation.agent !== agent || (conversationId && conversation.id !== conversationId)) setConversation(newConversation(agent))
    if (conversationId) setActiveThread(agent, conversationId)
    setChatFilter(agent)
    setHistory(listConversations())
  }, [agent, conversationId])
  useEffect(() => { if (conversation.id) { saveConversation(conversation); setHistory(listConversations()) } }, [conversation])
  useEffect(() => { const onVoiceThreadUpdate = event => { const detail = event.detail || {}; if (detail.agent === agent && detail.conversationId === conversation.id) { const next = loadConversation(agent, conversation.id); if (next) setConversation(next); setHistory(listConversations()) } }; window.addEventListener('nexus:voice-thread-update', onVoiceThreadUpdate); return () => window.removeEventListener('nexus:voice-thread-update', onVoiceThreadUpdate) }, [agent, conversation.id])
  useEffect(() => { if (logRef.current && !thinking) logRef.current.scrollTop = logRef.current.scrollHeight }, [conversation.messages.length, thinking])

  function openConversation(item) { setActiveThread(item.agent, item.id); setConversation(loadConversation(item.agent, item.id) || item); setRailOpen(false); onConversationChange?.(item.id, item.agent) }
  function createChat() { const next = newConversation(agent); setActiveThread(agent, next.id); setConversation(next); setRailOpen(false); onConversationChange?.(next.id, agent) }
  function renameConversation(item) { const nextTitle = window.prompt('Rename conversation', item.title || 'Conversation')?.trim(); if (!nextTitle) return; const next = { ...item, title: nextTitle, updatedAt: new Date().toISOString() }; saveConversation(next); setHistory(listConversations()); if (item.id === conversation.id) setConversation(next) }
  function archiveConversation(item) { saveConversation({ ...item, archived: true, updatedAt: new Date().toISOString() }); setHistory(listConversations()); if (item.id === conversation.id) createChat() }
  function openInNewTab(item) { window.open(`/admin/agents/${item.agent}/chat/${item.id}`, '_blank', 'noopener,noreferrer') }

  async function send(text) {
    if (!text.trim() || thinking) return
    const now = new Date().toISOString(); const user = { id: `${Date.now()}-user`, role: 'user', text, createdAt: now }
    setConversation(current => ({ ...current, title: current.messages.length ? current.title : titleFor(text), updatedAt: now, messages: [...current.messages, user] })); setThinking(true)
    try {
      const recentHistory = conversation.messages.slice(-10).map(message => ({ role: message.role === 'assistant' ? 'assistant' : 'user', content: message.text }))
      const response = await sendAgentMessage({ agent, conversationId: conversation.id, text, recentHistory })
      setConversation(current => ({ ...current, updatedAt: new Date().toISOString(), messages: [...current.messages, response] }))
    } catch (error) { setConversation(current => ({ ...current, updatedAt: new Date().toISOString(), messages: [...current.messages, { role: 'error', text: error?.message || 'Agent unavailable.', createdAt: new Date().toISOString() }] })) } finally { setThinking(false) }
  }
  useEffect(() => { if (initialPrompt && initialPromptRef.current !== initialPrompt && conversation.messages.length === 0) { initialPromptRef.current = initialPrompt; void send(initialPrompt) } }, [initialPrompt])

  const visibleChats = useMemo(() => history.filter(item => (chatFilter === 'all' || item.agent === chatFilter) && `${item.title} ${previewFor(item)}`.toLowerCase().includes(search.toLowerCase())), [history, chatFilter, search])
  const groupedChats = useMemo(() => visibleChats.reduce((groups, item) => { const group = groupFor(item.updatedAt); (groups[group] ||= []).push(item); return groups }, {}), [visibleChats])
  const filters = [['hermes', 'Nexus / Hermes'], ['nova', 'Nova'], ['alpha', 'Alpha'], ['all', 'All Chats']]

  return <section className={`nx2-agent-thread nx2-agent-${meta.tone}`} data-testid={`${agent}-conversation`}>
    <div className="nx2-thread-toolbar"><div><div className="nx2-eyebrow">AGENTS / {agent.toUpperCase()}</div><h2>{meta.name}</h2><p>{meta.role} · <span className="nx2-truth">Separate brain and authority</span></p></div><div className="nx2-thread-actions"><button type="button" className="nx2-mobile-chats" onClick={() => setRailOpen(value => !value)}>Chats</button><button type="button" onClick={createChat}>+ New Chat</button><button type="button" onClick={() => window.open(window.location.href, '_blank', 'noopener,noreferrer')}>Open in new tab ↗</button></div></div>
    <div className="nx2-thread-layout">
      <aside className={`nx2-thread-rail ${railOpen ? 'open' : ''}`} data-testid="nx2-thread-rail" aria-label="Conversation threads"><div className="nx2-thread-rail-head"><strong>Chats</strong><button type="button" onClick={createChat} aria-label="Start a new chat">＋</button></div><input className="nx2-chat-search" value={search} onChange={event => setSearch(event.target.value)} placeholder="Search chats" aria-label="Search chats" /><div className="nx2-chat-filters" role="tablist" aria-label="Chat agents">{filters.map(([value, label]) => <button type="button" role="tab" aria-selected={chatFilter === value} className={chatFilter === value ? 'active' : ''} key={value} onClick={() => setChatFilter(value)}>{label}</button>)}</div><div className="nx2-thread-list">{Object.keys(groupedChats).map(group => <div className="nx2-thread-group" key={group}><div className="nx2-section-label">{group}</div>{groupedChats[group].map(item => <div className={`nx2-history-item ${item.id === conversation.id && item.agent === agent ? 'active' : ''}`} key={`${item.agent}-${item.id}`}><button type="button" className="nx2-history-open" onClick={() => openConversation(item)}><strong>{item.title}</strong><small>{AGENT_META[item.agent]?.name} · {new Date(item.updatedAt).toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}</small><span>{previewFor(item)}</span></button><details className="nx2-history-menu"><summary aria-label={`Actions for ${item.title}`}>•••</summary><div><button type="button" onClick={() => renameConversation(item)}>Rename</button><button type="button" onClick={() => openInNewTab(item)}>Open in new tab</button><button type="button" onClick={() => archiveConversation(item)}>Archive</button></div></details></div>)}</div>)}{visibleChats.length === 0 && <p className="nx2-muted">No saved chats yet.</p>}</div></aside>
      <main className="nx2-thread-main"><div className="nx2-thread-current-header"><span className={`nx2-agent-dot ${meta.tone}`}>{agent === 'alpha' ? 'A' : 'N'}</span><div><strong>{meta.name}</strong><small>{meta.role}</small></div><span className="nx2-thread-truth">Conversation · {conversation.id}</span></div><div ref={logRef} className="nx2-conversation-log" data-testid="nx2-conversation-log" aria-live="polite">{conversation.messages.length === 0 && <div className="nx2-empty-thread"><div className={`nx2-agent-orb ${meta.tone}`}>{agent === 'hermes' ? 'N' : agent[0].toUpperCase()}</div><h3>Start a conversation with {meta.name}</h3><p>{meta.placeholder}</p><div className="nx2-suggestion-row"><button type="button" onClick={() => send(agent === 'hermes' ? 'What should I focus on today?' : agent === 'nova' ? 'Challenge my current Nexus priorities.' : 'Research what deserves attention next.')}>Try a sample prompt</button></div></div>}{conversation.messages.map(message => <article className={`nx2-message nx2-message-${message.role}`} key={message.id || `${message.role}-${message.text}`}><div className="nx2-message-label">{message.role === 'user' ? 'Ray' : message.role === 'error' ? 'Transport' : meta.name}</div>{message.role === 'assistant' ? <SafeMarkdown>{message.text}</SafeMarkdown> : <p>{message.text}</p>}{message.meta && <small className="nx2-message-meta">{message.meta}</small>}</article>)}{thinking && <div className="nx2-thinking">{meta.name} is thinking…</div>}</div><div className="nx2-composer-wrap" data-testid="nx2-composer"><NexusUniversalComposer agent={agent} onAgentChange={next => onConversationChange?.(conversation.id, next)} onSend={send} disabled={thinking} context={context} placeholder={meta.placeholder} /></div></main>
    </div>
  </section>
}
