import React, { useEffect, useRef, useState, useCallback } from 'react';
import { hermesStore } from '../lib/hermesChatStore';
import { recordActivity } from '../lib/hermesActivityJournal';
import { isSupabaseConfigured } from '../lib/supabaseClient';
import { getCapabilityBadge } from '../lib/hermesBrainPipeline';
import { runHermesConversation, seedHermesCanonicalAdvisoryContext } from '../lib/hermes/hermesConversationEngine';
import { buildHermesOperatingContext } from '../lib/hermes/hermesOperatingContext';
import { normalizeHermesWorkroomResponse, toHermesChatMessage } from '../lib/hermes/hermesWorkroomResponse';
import { runHermesModelFirstConversation } from '../lib/hermesModelFirst/hermesModelFirstController';
import { answerOperationalQuestion, getBundledOperationalSnapshot, probeHermesModelHealth, probeSupabaseHealth } from '../lib/nexusOperationalTruth';
import HermesMessageBubble from './HermesMessageBubble';

const welcome = { id: 'welcome', role: 'hermes', text: 'I\'m Hermes, your internal Nexus operator and CEO advisor. I report actual Nexus state from connected tools and authoritative records, and I will say when a source is stale, unavailable, simulated, or not checked.' };

function statusText(probe, fallback) {
  if (!probe) return fallback;
  if (probe.state === 'CONNECTED' || probe.state === 'CURRENT') return 'Connected';
  if (probe.state === 'LOCAL_FALLBACK') return 'Local fallback';
  if (probe.state === 'STALE') return 'Stale';
  if (probe.state === 'UNAVAILABLE') return 'Unavailable';
  return 'Not checked';
}

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
  const [liveProbes, setLiveProbes] = useState({ supabase: null, model: null, processRegistry: null });
  const end = useRef(null);

  useEffect(() => {
    let cancelled = false;
    const snapshot = getBundledOperationalSnapshot();
    setLiveProbes(current => ({
      ...current,
      processRegistry: {
        label: 'Process Registry',
        state: snapshot.freshness,
        checkedAt: snapshot.checkedAt,
        source: 'bundled_operations_snapshot',
        detail: snapshot.stale ? 'Bundled process evidence is stale.' : 'Bundled process evidence is current.',
        recordCount: snapshot.processes.length,
      },
    }));
    Promise.all([probeSupabaseHealth(), probeHermesModelHealth()]).then(([supabaseProbe, modelProbe]) => {
      if (!cancelled) setLiveProbes(current => ({ ...current, supabase: supabaseProbe, model: modelProbe }));
    });
    return () => { cancelled = true; };
  }, []);

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
      const operational = answerOperationalQuestion(clean);
      if (operational.handled) {
        hermesResponse = normalizeHermesWorkroomResponse({
          messageId: `${now}-hermes`,
          role: 'hermes',
          text: operational.text,
          mode: 'SYSTEM_STATUS',
          intent: 'operational_truth',
          responseStrategy: 'operational_truth_response',
          evidenceState: operational.provenance.confidence,
          confidence: operational.provenance.confidence === 'CURRENT' ? 0.86 : 0.66,
          createdAt: new Date().toISOString(),
          actions: [],
          memoryUsed: [],
          contextUsed: [operational.provenance.source],
          warnings: operational.provenance.unavailableSources,
        }, { messageId: `${now}-hermes` });
      } else {
        const operatingContext = buildHermesOperatingContext();
        const recentHistory = messages
          .filter((message) => message.role === 'ray' || message.role === 'hermes')
          .slice(-10)
          .map((message) => ({ role: message.role === 'hermes' ? 'assistant' : 'user', content: String(message.text || '').slice(0, 700) }));
        const pageContext = { pageId: activePage, sectionName: activePage, route: window.location.hash, visibleItems, selectedItem, availableActions, operatingContext };
        const modelFirstResult = await runHermesModelFirstConversation({
          message: clean,
          actorRole: 'admin',
          sessionId: hermesStore.getSessionId(),
          recentHistory,
          pageContext,
        });
        const brainResult = modelFirstResult.usedModelFirst && modelFirstResult.response
          ? modelFirstResult.response
          : runHermesConversation({
              message: clean,
              channel: 'full_workroom',
              actorRole: 'admin',
              pageId: activePage || undefined,
              route: window.location.hash,
              sessionId: hermesStore.getSessionId(),
              pageContext,
            });
        hermesResponse = normalizeHermesWorkroomResponse(brainResult, { messageId: `${now}-hermes` });
      }
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
  }, [input, activePage, visibleItems, selectedItem, availableActions, messages]);

  const clearHistory = useCallback(() => {
    hermesStore.clearHistory();
    setMessages([welcome]);
  }, []);

  const badgeLabel = getCapabilityBadge();
  return <section className="nxos-chat-panel">
    <header><div><strong>{activeSpecialist}</strong><small>Ray's private CEO Advisor · {badgeLabel}</small></div><span className="nxos-live"><i /> {loading ? 'Querying...' : 'Truth checked'}</span></header>
    <div className="nxos-health-strip" aria-label="Hermes live capability status">
      <span>Supabase: {statusText(liveProbes.supabase, isSupabaseConfigured ? 'Not checked' : 'Unavailable')}</span>
      <span>Model: {statusText(liveProbes.model, 'Not checked')}</span>
      <span>Process Registry: {statusText(liveProbes.processRegistry, 'Not checked')}</span>
      <span>Last verified: {liveProbes.supabase?.checkedAt || liveProbes.processRegistry?.checkedAt || 'not checked'}</span>
    </div>
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
