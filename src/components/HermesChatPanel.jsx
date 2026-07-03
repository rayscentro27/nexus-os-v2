import React, { useEffect, useRef, useState, useCallback } from 'react';
import { hermesStore } from '../lib/hermesChatStore';
import { recordActivity } from '../lib/hermesActivityJournal';
import { isSupabaseConfigured } from '../lib/supabaseClient';
import { handleHermesMessage, getCapabilityBadge } from '../lib/hermesBrainPipeline';
import HermesMessageBubble from './HermesMessageBubble';

const welcome = { id: 'welcome', role: 'hermes', text: 'I\'m Hermes, your CEO advisor. I can read live Supabase data and use a live model when the question warrants it. Web search is not configured yet. Ask me about approvals, research, clients, opportunities, or any operating question.' };

export default function HermesChatPanel({ activeSpecialist = 'Hermes CEO Advisor', activePage = null, visibleItems = [], selectedItem = null, availableActions = [], onPlanCreated, onReviewCreated, onSpecialistRequested }) {
  const [messages, setMessages] = useState(() => {
    const stored = hermesStore.getMessages();
    if (stored.length > 0) return stored.map((m, i) => ({ id: `stored-${i}`, role: m.role === 'user' ? 'ray' : 'hermes', text: m.text }));
    return [welcome];
  });
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const end = useRef(null);

  useEffect(() => end.current?.scrollIntoView({ behavior: 'smooth' }), [messages]);

  const send = useCallback(async (text = input) => {
    const clean = (text || '').trim();
    if (!clean) return;

    const now = Date.now();
    const userMsg = { id: `${now}-ray`, role: 'ray', text: clean };

    let responseText = '';
    let source = 'local';
    let uiActions = [];

    try {
      // ── Use unified brain pipeline — single entry point ──
      const brainResult = await handleHermesMessage({
        message: clean,
        surface: 'full_workroom',
        pageId: activePage || undefined,
        route: window.location.hash,
        sessionId: hermesStore.getSessionId(),
        currentPageContext: { pageId: activePage, sectionName: activePage, route: window.location.hash, visibleItems, selectedItem, availableActions },
      });
      responseText = brainResult.text;
      source = brainResult.sourceMode;
      uiActions = brainResult.uiActions || [];

      // Ensure we always have an answer
      if (!responseText) {
        responseText = 'I am not sure how to answer that. Can you tell me which page or section you are asking about?';
        source = 'local';
      }
    } catch (err) {
      console.error('[HermesChatPanel] send error:', err);
      responseText = 'I hit a local routing error while answering that. I did not execute anything. Try again or open the full Hermes Workroom.';
      source = 'error_fallback';
    }

    const hermesMsg = {
      id: `${now}-hermes`,
      role: 'hermes',
      text: responseText,
      source,
      uiActions,
    };
    setMessages(current => {
      const next = [...current, userMsg, hermesMsg];
      hermesStore.saveMessages(next.map(m => ({ role: m.role === 'ray' ? 'user' : 'hermes', text: m.text })));
      return next;
    });
    setInput('');
    recordActivity({
      source: 'hermes_message',
      pageId: activePage || 'hermes',
      route: window.location.hash,
      eventType: 'hermes_message',
      title: `Hermes chat: ${clean.slice(0, 80)}`,
      summary: `User asked: ${clean.slice(0, 120)}. Source: ${source}.`,
      entities: [],
      status: 'completed',
      importance: 'low',
      dataSource: 'local',
      safetyLevel: 'safe',
    });
  }, [input, activeSpecialist, activePage, visibleItems, selectedItem, availableActions, onPlanCreated]);

  const clearHistory = useCallback(() => {
    hermesStore.clearHistory();
    setMessages([welcome]);
  }, []);

  const statusLabel = isSupabaseConfigured ? 'Live Supabase' : 'Local context';
  const badgeLabel = getCapabilityBadge();
  return <section className="nxos-chat-panel">
    <header><div><strong>{activeSpecialist}</strong><small>Ray's private CEO Advisor · {badgeLabel}</small></div><span className="nxos-live"><i /> {loading ? 'Querying...' : statusLabel}</span></header>
    <div className="nxos-chat-log" aria-live="polite">{messages.map((message) => <HermesMessageBubble key={message.id} message={message} onDelegate={(item) => onPlanCreated?.({ id:`plan-${Date.now()}`,prompt:item.text,specialist:activeSpecialist,status:'queued_local_safe' })} onReview={onReviewCreated} onSpecialist={onSpecialistRequested} />)}<div ref={end} /></div>
    <div className="nxos-chat-compose"><textarea aria-label="Message Hermes" value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send(); } }} placeholder="Ask Hermes about Supabase, research, approvals, or anything…" /><button type="button" className="primary" disabled={loading} onClick={() => send()}>{loading ? 'Loading...' : 'Send'}</button></div>
    <div className="nxos-quick-prompts"><span>Try asking</span>{['what did we do today?', 'give me the CEO version', 'can you check Supabase', 'what approvals are pending'].map((prompt) => <button type="button" key={prompt} onClick={() => send(prompt)}>{prompt}</button>)}</div>
    <div className="nxos-chat-actions"><button type="button" onClick={clearHistory}>Clear conversation</button></div>
  </section>;
}
