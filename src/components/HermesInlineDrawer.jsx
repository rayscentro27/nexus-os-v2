import React, { useRef, useState, useEffect, useCallback } from 'react';
import { hermesStore } from '../lib/hermesChatStore';
import { recordActivity } from '../lib/hermesActivityJournal';
import { handleHermesMessage, getCapabilityBadge } from '../lib/hermesBrainPipeline';
import { isSafeHermesUiAction } from '../lib/hermesUiActions';

export default function HermesInlineDrawer({ open, onClose, onOpenWorkroom, initialPrompt = '', activePage = null, visibleItems = [], selectedItem = null, availableActions = [] }) {
  const [messages, setMessages] = useState(() => {
    const stored = hermesStore.getMessages();
    if (stored.length > 0) return stored.map((m, i) => ({ id: `stored-${i}`, role: m.role === 'user' ? 'ray' : 'hermes', text: m.text }));
    return [{ id: 'welcome', role: 'hermes', text: 'I\'m here, Ray. I can read live Supabase data and use a live model when the question warrants it. What do you need?' }];
  });
  const [input, setInput] = useState(initialPrompt);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => { if (open) setTimeout(() => inputRef.current?.focus(), 30); }, [open]);
  useEffect(() => { if (initialPrompt) setInput(initialPrompt); }, [initialPrompt]);

  const send = useCallback(async () => {
    const clean = input.trim(); if (!clean) return;

    let responseText = '';
    let source = 'local';
    let uiActions = [];

    try {
      // ── Use unified brain pipeline — single entry point ──
      const brainResult = await handleHermesMessage({
        message: clean,
        surface: 'inline_drawer',
        pageId: activePage || undefined,
        route: window.location.hash,
        sessionId: hermesStore.getSessionId(),
        currentPageContext: { pageId: activePage, sectionName: activePage, route: window.location.hash, visibleItems, selectedItem, availableActions },
      });
      responseText = brainResult.text;
      source = brainResult.sourceMode;
      uiActions = brainResult.uiActions || [];

      if (!responseText) {
        responseText = 'I am not sure how to answer that. Can you tell me which page or section you are asking about?';
        source = 'local';
      }
    } catch (err) {
      console.error('[HermesInlineDrawer] send error:', err);
      responseText = 'I hit a local routing error. I did not execute anything. Try again or open the full Hermes Workroom.';
      source = 'error_fallback';
    }

    const userMsg = { role: 'ray', text: clean };
    const hermesMsg = { role: 'hermes', text: responseText, source, uiActions };
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
      title: `Hermes inline: ${clean.slice(0, 80)}`,
      summary: `User asked: ${clean.slice(0, 120)}. Source: ${source}.`,
      entities: [],
      status: 'completed',
      importance: 'low',
      dataSource: 'local',
      safetyLevel: 'safe',
    });
  }, [input, activePage, visibleItems, selectedItem, availableActions]);

  const clearHistory = useCallback(() => {
    hermesStore.clearHistory();
    setMessages([{ id: 'welcome', role: 'hermes', text: 'I\'m here, Ray. I can read live Supabase data and use a live model when the question warrants it. What do you need?' }]);
  }, []);

  if (!open) return null;
  return <div className="hermes-drawer-backdrop" role="presentation" onMouseDown={e => { if (e.target === e.currentTarget) onClose(); }}><aside className="hermes-inline-drawer" role="dialog" aria-modal="true" aria-label="Ask Hermes inline chat"><header><div><span>✦</span><div><strong>Hermes</strong><small>CEO Advisor · {getCapabilityBadge()}</small></div></div><button type="button" aria-label="Close Hermes chat" onClick={onClose}>×</button></header><div className="hermes-inline-conversation">{messages.map((message,index)=><div className={`inline-message ${message.role}`} key={`${message.role}-${index}`}><strong>{message.role === 'ray' ? 'Ray' : 'Hermes'}</strong><p>{message.text}</p>{message.role === 'hermes' && <div className="hermes-message-actions">{(message.uiActions || []).filter(isSafeHermesUiAction).map((action, actionIndex) => <button type="button" key={`${action.actionType}-${actionIndex}`} onClick={() => { if (action.href) window.location.hash = action.href.replace(/^#\/?/, ''); }}>{action.actionLabel}: {action.title}</button>)}</div>}</div>)}</div><div className="hermes-inline-compose"><textarea ref={inputRef} value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}}} placeholder="Ask Hermes about Supabase, approvals, research..." aria-label="Ask Hermes inline"/><button type="button" disabled={loading} onClick={send}>{loading ? '...' : 'Send'}</button></div><footer><span>Your current department stays open.</span>{onOpenWorkroom && <button type="button" onClick={onOpenWorkroom}>Open full Hermes Workroom</button>}<button type="button" onClick={clearHistory}>Clear conversation</button></footer></aside></div>;
}
