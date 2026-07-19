import React, { useEffect, useRef, useState, useCallback } from 'react';
import { hermesStore } from '../lib/hermesChatStore';
import { recordActivity } from '../lib/hermesActivityJournal';
import { isSupabaseConfigured } from '../lib/supabaseClient';
import { getCapabilityBadge } from '../lib/hermesBrainPipeline';
import { runHermesConversation, seedHermesCanonicalAdvisoryContext } from '../lib/hermes/hermesConversationEngine';
import { buildHermesOperatingContext } from '../lib/hermes/hermesOperatingContext';
import { normalizeHermesWorkroomResponse, toHermesChatMessage } from '../lib/hermes/hermesWorkroomResponse';
import HermesMessageBubble from './HermesMessageBubble';

const welcome = { id: 'welcome', role: 'hermes', text: 'I\'m Hermes, your CEO advisor. I can read live Supabase data and use a live model when the question warrants it. Web search is not configured yet. Ask me about approvals, research, clients, opportunities, or any operating question.' };

export default function HermesChatPanel({ activeSpecialist = 'Hermes CEO Advisor', activePage = null, visibleItems = [], selectedItem = null, availableActions = [], onPlanCreated, onReviewCreated, onSpecialistRequested }) {
  const [messages, setMessages] = useState(() => {
    const stored = hermesStore.getMessages();
    if (stored.length > 0) {
      const normalized = stored.map((m, i) => {
        if (m.role === 'hermes' && m.workroomResponse) {
          return toHermesChatMessage(normalizeHermesWorkroomResponse(m.workroomResponse, { messageId: m.workroomResponse.messageId || `stored-${i}` }));
        }
        return { id: `stored-${i}`, role: m.role === 'user' ? 'ray' : 'hermes', text: m.text };
      });
      const latestAdvisory = [...normalized].reverse().find((message) => message.role === 'hermes' && message.advisoryContext)?.advisoryContext;
      if (latestAdvisory) seedHermesCanonicalAdvisoryContext(latestAdvisory, hermesStore.getSessionId());
      return normalized;
    }
    return [welcome];
  });
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const end = useRef(null);

  useEffect(() => {
    const target = end.current;
    if (target && typeof target.scrollIntoView === 'function') {
      target.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const send = useCallback(async (text = input) => {
    const clean = (text || '').trim();
    if (!clean) return;

    const now = Date.now();
    const userMsg = { id: `${now}-ray`, role: 'ray', text: clean };
    setLoading(true);
    let hermesResponse;

    try {
      const operatingContext = buildHermesOperatingContext();
      const brainResult = runHermesConversation({
        message: clean,
        channel: 'full_workroom',
        actorRole: 'admin',
        pageId: activePage || undefined,
        route: window.location.hash,
        sessionId: hermesStore.getSessionId(),
        pageContext: { pageId: activePage, sectionName: activePage, route: window.location.hash, visibleItems, selectedItem, availableActions, operatingContext },
      });
      hermesResponse = normalizeHermesWorkroomResponse(brainResult, { messageId: `${now}-hermes` });
    } catch (err) {
      console.error('[HermesChatPanel] send error:', err);
      hermesResponse = normalizeHermesWorkroomResponse({
        messageId: `${now}-hermes`,
        role: 'hermes',
        text: 'I hit a local routing error while answering that. Nothing was executed. Try again from the Workroom.',
        mode: 'UNSUPPORTED_OR_BLOCKED',
        intent: 'workroom_send_error',
        responseStrategy: 'SAFE_FALLBACK',
        evidenceState: 'BLOCKED',
        confidence: 0.4,
        createdAt: new Date().toISOString(),
        actions: [],
        memoryUsed: [],
        contextUsed: [],
        warnings: ['send_error'],
      }, { messageId: `${now}-hermes` });
    }

    const hermesMsg = toHermesChatMessage(hermesResponse);
    setMessages(current => {
      const next = [...current, userMsg, hermesMsg];
      hermesStore.saveMessages(next.map(m => ({
        role: m.role === 'ray' ? 'user' : 'hermes',
        text: m.text,
        workroomResponse: m.role === 'hermes' && m.messageId ? normalizeHermesWorkroomResponse(m) : undefined,
      })));
      return next;
    });
    setInput('');
    setLoading(false);
    recordActivity({
      source: 'hermes_message',
      pageId: activePage || 'hermes',
      route: window.location.hash,
      eventType: 'hermes_message',
      title: `Hermes chat: ${clean.slice(0, 80)}`,
      summary: `User asked: ${clean.slice(0, 120)}. Source: ${hermesResponse.evidenceState}.`,
      entities: [],
      status: 'completed',
      importance: 'low',
      dataSource: 'local',
      safetyLevel: 'safe',
    });
  }, [input, activePage, visibleItems, selectedItem, availableActions]);

  const clearHistory = useCallback(() => {
    hermesStore.clearHistory();
    setMessages([welcome]);
  }, []);

  const statusLabel = isSupabaseConfigured ? 'Live Supabase' : 'Local context';
  const badgeLabel = getCapabilityBadge();
  return <section className="nxos-chat-panel">
    <header><div><strong>{activeSpecialist}</strong><small>Ray's private CEO Advisor · {badgeLabel}</small></div><span className="nxos-live"><i /> {loading ? 'Querying...' : statusLabel}</span></header>
    <div className="nxos-chat-log" aria-live="polite">{messages.map((message) => <HermesMessageBubble key={message.id} message={message} onDelegate={(item) => onPlanCreated?.({ id:`plan-${Date.now()}`,prompt:item.text,specialist:activeSpecialist,status:'queued_local_safe' })} onAction={(action, item) => {
      if (action.type === 'DRAFT_RAY_REVIEW') onReviewCreated?.(item);
      if (action.type === 'PREPARE_SPECIALIST_HANDOFF') onSpecialistRequested?.(item);
      if (action.type === 'CREATE_TASK_REQUEST') onPlanCreated?.({ id: action.id, prompt: item.text, specialist: activeSpecialist, status: 'approval_required', actionType: action.type });
    }} />)}<div ref={end} /></div>
    <div className="nxos-chat-compose"><textarea aria-label="Message Hermes" value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send(); } }} placeholder="Ask Hermes about Supabase, research, approvals, or anything…" /><button type="button" className="primary" disabled={loading} onClick={() => send()}>{loading ? 'Loading...' : 'Send'}</button></div>
    <div className="nxos-quick-prompts"><span>Try asking</span>{['what did we do today?', 'give me the CEO version', 'can you check Supabase', 'what approvals are pending'].map((prompt) => <button type="button" key={prompt} onClick={() => send(prompt)}>{prompt}</button>)}</div>
    <div className="nxos-chat-actions"><button type="button" onClick={clearHistory}>Clear conversation</button></div>
  </section>;
}
