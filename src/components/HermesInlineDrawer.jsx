import React, { useRef, useState, useEffect, useCallback } from 'react';
import { buildHermesResponse } from '../data/hermesWorkroomData';
import { hermesStore } from '../lib/hermesChatStore';
import { recordActivity } from '../lib/hermesActivityJournal';
import { buildLiveSupabaseContext, buildWebSearchResponse } from '../lib/hermesLiveContext';
import { orchestrateHermes } from '../lib/hermesOrchestrator';

export default function HermesInlineDrawer({ open, onClose, onOpenWorkroom, initialPrompt = '', activePage = null, visibleItems = [], selectedItem = null, availableActions = [] }) {
  const [messages, setMessages] = useState(() => {
    const stored = hermesStore.getMessages();
    if (stored.length > 0) return stored.map((m, i) => ({ id: `stored-${i}`, role: m.role === 'user' ? 'ray' : 'hermes', text: m.text }));
    return [{ id: 'welcome', role: 'hermes', text: 'I\'m here, Ray. I can read live Supabase data and search the web when configured. What do you need?' }];
  });
  const [input, setInput] = useState(initialPrompt);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => { if (open) setTimeout(() => inputRef.current?.focus(), 30); }, [open]);
  useEffect(() => { if (initialPrompt) setInput(initialPrompt); }, [initialPrompt]);

  const send = useCallback(async () => {
    const clean = input.trim(); if (!clean) return;
    const result = buildHermesResponse(clean, undefined, activePage, {
      visibleItems,
      selectedItem,
      availableActions,
    });

    let responseText = result.text;
    let liveSource = null;

    const orchestration = orchestrateHermes(clean, Boolean(activePage));
    const isSupabaseQuery = orchestration.shouldQuerySupabase;
    const isWebQuery = orchestration.shouldQueryWeb;

    if (isSupabaseQuery) {
      setLoading(true);
      try {
        const liveCtx = await buildLiveSupabaseContext(clean);
        if (liveCtx.liveData) {
          responseText = orchestration.routing.intent === 'run_nexus_audit' ? `${responseText}\n\n${liveCtx.text}` : liveCtx.text;
          liveSource = liveCtx.source;
        }
      } catch (e) { /* keep sync response */ }
      setLoading(false);
    }

    if (isWebQuery) {
      setLoading(true);
      try {
        const webResult = await buildWebSearchResponse(clean);
        responseText = webResult.text;
        liveSource = webResult.source;
      } catch (e) { /* keep sync response */ }
      setLoading(false);
    }

    const userMsg = { role: 'ray', text: clean };
    const hermesMsg = { role: 'hermes', text: responseText, source: liveSource || result.source };
    setMessages(current => {
      const next = [...current, userMsg, hermesMsg];
      hermesStore.saveMessages(next.map(m => ({ role: m.role === 'ray' ? 'user' : 'hermes', text: m.text })));
      return next;
    });
    setInput('');
  }, [input, activePage, visibleItems, selectedItem, availableActions]);

  const clearHistory = useCallback(() => {
    hermesStore.clearHistory();
    setMessages([{ id: 'welcome', role: 'hermes', text: 'I\'m here, Ray. I can read live Supabase data and search the web when configured. What do you need?' }]);
  }, []);

  if (!open) return null;
  return <div className="hermes-drawer-backdrop" role="presentation" onMouseDown={e => { if (e.target === e.currentTarget) onClose(); }}><aside className="hermes-inline-drawer" role="dialog" aria-modal="true" aria-label="Ask Hermes inline chat"><header><div><span>✦</span><div><strong>Hermes</strong><small>CEO Advisor · Live context when available</small></div></div><button type="button" aria-label="Close Hermes chat" onClick={onClose}>×</button></header><div className="hermes-inline-conversation">{messages.map((message,index)=><div className={`inline-message ${message.role}`} key={`${message.role}-${index}`}><strong>{message.role === 'ray' ? 'Ray' : 'Hermes'}</strong><p>{message.text}</p></div>)}</div><div className="hermes-inline-compose"><textarea ref={inputRef} value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}}} placeholder="Ask Hermes about Supabase, approvals, research..." aria-label="Ask Hermes inline"/><button type="button" disabled={loading} onClick={send}>{loading ? '...' : 'Send'}</button></div><footer><span>Your current department stays open.</span>{onOpenWorkroom && <button type="button" onClick={onOpenWorkroom}>Open full Hermes Workroom</button>}<button type="button" onClick={clearHistory}>Clear conversation</button></footer></aside></div>;
}
