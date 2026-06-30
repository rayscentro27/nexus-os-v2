import React, { useEffect, useRef, useState } from 'react';
import { buildHermesResponse, hermesQuickPrompts } from '../data/hermesWorkroomData';

const initial = [{ id: 'welcome', role: 'hermes', text: 'Hermes is ready. Ask for system status, money actions, blockers, specialist review, or paste a large prompt for delegation.' }];

export default function HermesChatPanel({ activeSpecialist = 'Hermes CEO Advisor', onPlanCreated }) {
  const [messages, setMessages] = useState(initial);
  const [input, setInput] = useState('');
  const end = useRef(null);
  useEffect(() => end.current?.scrollIntoView({ behavior: 'smooth' }), [messages]);
  function send(text = input) {
    const clean = text.trim();
    if (!clean) return;
    const result = buildHermesResponse(clean);
    const now = Date.now();
    setMessages((current) => [...current, { id: `${now}-ray`, role: 'ray', text: clean }, { id: `${now}-hermes`, role: 'hermes', text: `[${activeSpecialist}] ${result.text}` }]);
    setInput('');
    if (result.queued) onPlanCreated?.({ id: `plan-${now}`, prompt: clean, specialist: result.specialist, status: 'queued_local_safe', createdAt: new Date().toISOString() });
  }
  return <section className="nxos-chat-panel">
    <header><div><strong>{activeSpecialist}</strong><small>Local-safe response and delegation planner</small></div><span className="nxos-live"><i /> Responsive</span></header>
    <div className="nxos-quick-prompts">{hermesQuickPrompts.map((prompt) => <button type="button" key={prompt} onClick={() => send(prompt)}>{prompt}</button>)}</div>
    <div className="nxos-chat-log" aria-live="polite">{messages.map((message) => <div key={message.id} className={`nxos-message ${message.role}`}><strong>{message.role === 'ray' ? 'Ray' : 'Hermes'}</strong><p>{message.text}</p></div>)}<div ref={end} /></div>
    <div className="nxos-chat-compose"><textarea aria-label="Message Hermes" value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send(); } }} placeholder="Ask Hermes or paste a large operating prompt…" /><button type="button" className="primary" onClick={() => send()}>Send</button></div>
  </section>;
}
