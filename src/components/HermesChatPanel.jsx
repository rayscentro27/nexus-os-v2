import React, { useEffect, useRef, useState } from 'react';
import { buildHermesResponse, hermesQuickPrompts } from '../data/hermesWorkroomData';
import HermesMessageBubble from './HermesMessageBubble';

const initial = [{ id: 'welcome', role: 'hermes', text: 'I’m here, Ray. I have the operating picture: the scheduler is running, the approval queue is waiting, and the closest money path is the $97 readiness journey. Talk to me normally—give me a goal, a problem, or a large prompt—and I’ll help shape it, delegate it, and isolate the decisions that need you.' }];

export default function HermesChatPanel({ activeSpecialist = 'Hermes CEO Advisor', onPlanCreated, onReviewCreated, onSpecialistRequested }) {
  const [messages, setMessages] = useState(initial);
  const [input, setInput] = useState('');
  const end = useRef(null);
  useEffect(() => end.current?.scrollIntoView({ behavior: 'smooth' }), [messages]);
  function send(text = input) {
    const clean = text.trim();
    if (!clean) return;
    const result = buildHermesResponse(clean, activeSpecialist);
    const now = Date.now();
    setMessages((current) => [...current, { id: `${now}-ray`, role: 'ray', text: clean }, { id: `${now}-hermes`, role: 'hermes', text: `[${activeSpecialist}] ${result.text}` }]);
    setInput('');
    if (result.queued) onPlanCreated?.({ id: `plan-${now}`, prompt: clean, specialist: result.specialist, status: 'queued_local_safe', createdAt: new Date().toISOString() });
  }
  return <section className="nxos-chat-panel">
    <header><div><strong>{activeSpecialist}</strong><small>Ray’s private CEO Advisor · Advisor mode</small></div><span className="nxos-live"><i /> Context active</span></header>
    <div className="nxos-chat-log" aria-live="polite">{messages.map((message) => <HermesMessageBubble key={message.id} message={message} onDelegate={(item) => onPlanCreated?.({ id:`plan-${Date.now()}`,prompt:item.text,specialist:activeSpecialist,status:'queued_local_safe' })} onReview={onReviewCreated} onSpecialist={onSpecialistRequested} />)}<div ref={end} /></div>
    <div className="nxos-chat-compose"><textarea aria-label="Message Hermes" value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send(); } }} placeholder="Ask Hermes or paste a large operating prompt…" /><button type="button" className="primary" onClick={() => send()}>Send</button></div>
    <div className="nxos-quick-prompts"><span>Conversation starters</span>{hermesQuickPrompts.map((prompt) => <button type="button" key={prompt} onClick={() => send(prompt)}>{prompt}</button>)}</div>
  </section>;
}
