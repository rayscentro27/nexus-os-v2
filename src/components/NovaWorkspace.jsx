import React, { useState } from 'react'
import { Bot, ShieldCheck } from 'lucide-react'
import SafeMarkdown from './SafeMarkdown'

const endpoint = import.meta.env.VITE_NEXUS_NOVA_ENDPOINT || 'https://nova.goclearonline.cc/v1/nova/chat'

export default function NovaWorkspace() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [state, setState] = useState('IDLE')
  const [error, setError] = useState('')

  async function send(text = input) {
    const clean = text.trim()
    if (!clean || state === 'THINKING') return
    setError(''); setState('THINKING'); setMessages(current => [...current, { role: 'ray', text: clean }]); setInput('')
    try {
      const response = await fetch(endpoint, { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json', 'X-Nexus-Nova-Session': 'admin-browser' }, body: JSON.stringify({ message: clean }) })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.error || 'nova-unavailable')
      setMessages(current => [...current, { role: 'nova', text: payload.text, model: payload.model }]); setState('IDLE')
    } catch (caught) { setState('ERROR'); setError(caught?.message || 'Nova browser transport is unavailable.'); setMessages(current => current.slice(0, -1)) }
  }

  return <section className="nova-workspace" data-testid="nova-workspace">
    <header className="nova-workspace-header"><div><div className="nxos-eyebrow">Strategic adviser</div><h2>Nova</h2><p>Challenge plans, compare scenarios, and surface what may be missing.</p></div><span className="nxos-live"><i /> Telegram runtime certified</span></header>
    <div className="nova-status-grid"><article><Bot size={20} /><strong>Hermes Nova</strong><span>Same canonical Nova graph; browser memory is channel-scoped.</span><b>Healthy</b></article><article><ShieldCheck size={20} /><strong>Boundary</strong><span>Strategic advice only. No execution authority.</span><b>Preserved</b></article><article><strong>Browser transport</strong><span>Admin-only Cloudflare Access route with bounded local adapter.</span><b>CONNECTED</b></article></div>
    <div className="nova-conversation" aria-label="Nova conversation"><div className="nova-conversation-log" aria-live="polite">{messages.length === 0 && <p className="nxos-muted">Ask Nova for a strategy, critique, scenario, or second opinion.</p>}{messages.map((message, index) => <article className={`nova-message nova-message-${message.role}`} key={`${message.role}-${index}`}><strong>{message.role === 'ray' ? 'Ray' : 'Nova'}</strong><div>{message.role === 'nova' ? <SafeMarkdown>{message.text}</SafeMarkdown> : message.text}</div>{message.model && <small>Model: {message.model}</small>}</article>)}</div><div className="nova-compose"><textarea aria-label="Ask Nova" value={input} onChange={event => setInput(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send() } }} placeholder="Ask Nova for a strategic second opinion…" /><button type="button" className="primary" onClick={() => send()} disabled={state === 'THINKING' || !input.trim()}>{state === 'THINKING' ? 'Thinking…' : 'Send'}</button></div><div className="nova-prompts">{['Strategy', 'Critique', 'Scenario', 'Second Opinion'].map(prompt => <button type="button" key={prompt} onClick={() => setInput(`${prompt}: `)}>{prompt}</button>)}</div>{error && <div className="nova-error" role="status">Nova is unavailable: {error}</div>}</div>
  </section>
}
