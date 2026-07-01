import React, { useEffect, useRef, useState, useCallback } from 'react';
import { buildHermesResponse, hermesQuickPrompts } from '../data/hermesWorkroomData';
import { hermesStore } from '../lib/hermesChatStore';
import { recordActivity } from '../lib/hermesActivityJournal';
import { buildLiveSupabaseContext, buildWebSearchResponse } from '../lib/hermesLiveContext';
import { isSupabaseConfigured } from '../lib/supabaseClient';
import HermesMessageBubble from './HermesMessageBubble';

const welcome = { id: 'welcome', role: 'hermes', text: 'I\'m Hermes, your CEO advisor. I can read live Supabase data when connected, and I use local bundled context as fallback. Web search and live model are not configured yet. Ask me about approvals, research, clients, opportunities, or any operating question.' };

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

    // Get sync response first
    const result = buildHermesResponse(clean, activeSpecialist, activePage, {
      visibleItems,
      selectedItem,
      availableActions,
    });

    const now = Date.now();
    const userMsg = { id: `${now}-ray`, role: 'ray', text: clean };
    let responseText = result.text;
    let liveSource = null;

    // Enrich with live data for Supabase/web queries
    const lower = clean.toLowerCase();
    const isSupabaseQuery = /\b(supabase|database|table|row|live data|can you see|check supabase|approval|research|client|opportunity|offer|health|event|blocker|scheduler)\b/.test(lower);
    const isWebQuery = /\b(search the internet|look this up|research current|web search|what is the latest|what's happening|online|google|find online)\b/.test(lower);

    if (isSupabaseQuery) {
      setLoading(true);
      try {
        const liveCtx = await buildLiveSupabaseContext(clean);
        if (liveCtx.liveData) {
          responseText = liveCtx.text;
          liveSource = liveCtx.source;
        }
        // If not live, keep the sync response (which already has honest fallback)
      } catch (e) {
        // Keep sync response on error
      }
      setLoading(false);
    }

    if (isWebQuery) {
      setLoading(true);
      try {
        const webResult = await buildWebSearchResponse(clean);
        responseText = webResult.text;
        liveSource = webResult.source;
      } catch (e) {
        // Keep sync response on error
      }
      setLoading(false);
    }

    const hermesMsg = { id: `${now}-hermes`, role: 'hermes', text: responseText, source: liveSource || result.source };
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

  const statusLabel = isSupabaseConfigured ? 'Live Supabase + local context' : 'Local context';
  return <section className="nxos-chat-panel">
    <header><div><strong>{activeSpecialist}</strong><small>Ray's private CEO Advisor · {statusLabel}</small></div><span className="nxos-live"><i /> {loading ? 'Querying...' : statusLabel}</span></header>
    <div className="nxos-chat-log" aria-live="polite">{messages.map((message) => <HermesMessageBubble key={message.id} message={message} onDelegate={(item) => onPlanCreated?.({ id:`plan-${Date.now()}`,prompt:item.text,specialist:activeSpecialist,status:'queued_local_safe' })} onReview={onReviewCreated} onSpecialist={onSpecialistRequested} />)}<div ref={end} /></div>
    <div className="nxos-chat-compose"><textarea aria-label="Message Hermes" value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send(); } }} placeholder="Ask Hermes about Supabase, research, approvals, or anything…" /><button type="button" className="primary" disabled={loading} onClick={() => send()}>{loading ? 'Loading...' : 'Send'}</button></div>
    <div className="nxos-quick-prompts"><span>Try asking</span>{['can you check Supabase', 'what approvals are pending', 'can you search the internet', 'how do we make money today'].map((prompt) => <button type="button" key={prompt} onClick={() => send(prompt)}>{prompt}</button>)}</div>
    <div className="nxos-chat-actions"><button type="button" onClick={clearHistory}>Clear conversation</button></div>
  </section>;
}
