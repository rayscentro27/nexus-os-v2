import React, { useEffect, useRef, useState, useCallback } from 'react';
import { buildHermesResponse, hermesQuickPrompts } from '../data/hermesWorkroomData';
import { hermesStore } from '../lib/hermesChatStore';
import { recordActivity } from '../lib/hermesActivityJournal';
import HermesMessageBubble from './HermesMessageBubble';

const welcome = { id: 'welcome', role: 'hermes', text: 'I\'m here, Ray. I have the operating picture: the scheduler is running, the approval queue is waiting, and the closest money path is the $97 readiness journey. Talk to me normally—give me a goal, a problem, or a question—and I\'ll help shape it, answer it, or route it to the right specialist.' };

export default function HermesChatPanel({ activeSpecialist = 'Hermes CEO Advisor', activePage = null, visibleItems = [], selectedItem = null, availableActions = [], onPlanCreated, onReviewCreated, onSpecialistRequested }) {
  const [messages, setMessages] = useState(() => {
    const stored = hermesStore.getMessages();
    if (stored.length > 0) return stored.map((m, i) => ({ id: `stored-${i}`, role: m.role === 'user' ? 'ray' : 'hermes', text: m.text }));
    return [welcome];
  });
  const [input, setInput] = useState('');
  const end = useRef(null);

  useEffect(() => end.current?.scrollIntoView({ behavior: 'smooth' }), [messages]);

  const send = useCallback((text = input) => {
    const clean = (text || '').trim();
    if (!clean) return;
    const result = buildHermesResponse(clean, activeSpecialist, activePage, {
      visibleItems,
      selectedItem,
      availableActions,
    });
    const now = Date.now();
    const userMsg = { id: `${now}-ray`, role: 'ray', text: clean };
    const hermesMsg = { id: `${now}-hermes`, role: 'hermes', text: result.text };
    setMessages(current => {
      const next = [...current, userMsg, hermesMsg];
      hermesStore.saveMessages(next.map(m => ({ role: m.role === 'ray' ? 'user' : 'hermes', text: m.text })));
      return next;
    });
    setInput('');
    if (result.queued) onPlanCreated?.({ id: `plan-${now}`, prompt: clean, specialist: result.specialist, status: 'queued_local_safe', createdAt: new Date().toISOString() });
  }, [input, activeSpecialist, activePage, visibleItems, selectedItem, availableActions, onPlanCreated]);

  const clearHistory = useCallback(() => {
    hermesStore.clearHistory();
    setMessages([welcome]);
  }, []);

  return <section className="nxos-chat-panel">
    <header><div><strong>{activeSpecialist}</strong><small>Ray's private CEO Advisor · Local advisor</small></div><span className="nxos-live"><i /> Local context</span></header>
    <div className="nxos-chat-log" aria-live="polite">{messages.map((message) => <HermesMessageBubble key={message.id} message={message} onDelegate={(item) => onPlanCreated?.({ id:`plan-${Date.now()}`,prompt:item.text,specialist:activeSpecialist,status:'queued_local_safe' })} onReview={onReviewCreated} onSpecialist={onSpecialistRequested} />)}<div ref={end} /></div>
    <div className="nxos-chat-compose"><textarea aria-label="Message Hermes" value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send(); } }} placeholder="Ask Hermes or talk normally…" /><button type="button" className="primary" onClick={() => send()}>Send</button></div>
    <div className="nxos-quick-prompts"><span>Conversation starters</span>{hermesQuickPrompts.map((prompt) => <button type="button" key={prompt} onClick={() => send(prompt)}>{prompt}</button>)}</div>
    <div className="nxos-chat-actions"><button type="button" onClick={clearHistory}>Clear conversation</button></div>
  </section>;
}
