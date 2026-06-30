import React, { useRef, useState, useEffect, useCallback } from 'react';
import { buildHermesResponse } from '../data/hermesWorkroomData';
import { hermesStore } from '../lib/hermesChatStore';

export default function HermesInlineDrawer({ open, onClose, onOpenWorkroom, initialPrompt = '' }) {
  const [messages, setMessages] = useState(() => {
    const stored = hermesStore.getMessages();
    if (stored.length > 0) return stored.map((m, i) => ({ id: `stored-${i}`, role: m.role === 'user' ? 'ray' : 'hermes', text: m.text }));
    return [{ id: 'welcome', role: 'hermes', text: 'I\'m here, Ray. Stay on this page and talk to me normally—what are you trying to move?' }];
  });
  const [input, setInput] = useState(initialPrompt);
  const inputRef = useRef(null);

  useEffect(() => { if (open) setTimeout(() => inputRef.current?.focus(), 30); }, [open]);
  useEffect(() => { if (initialPrompt) setInput(initialPrompt); }, [initialPrompt]);

  const send = useCallback(() => {
    const clean = input.trim(); if (!clean) return;
    const result = buildHermesResponse(clean);
    const userMsg = { role: 'ray', text: clean };
    const hermesMsg = { role: 'hermes', text: result.text };
    setMessages(current => {
      const next = [...current, userMsg, hermesMsg];
      hermesStore.saveMessages(next.map(m => ({ role: m.role === 'ray' ? 'user' : 'hermes', text: m.text })));
      return next;
    });
    setInput('');
  }, [input]);

  const clearHistory = useCallback(() => {
    hermesStore.clearHistory();
    setMessages([{ id: 'welcome', role: 'hermes', text: 'I\'m here, Ray. Stay on this page and talk to me normally—what are you trying to move?' }]);
  }, []);

  if (!open) return null;
  return <div className="hermes-drawer-backdrop" role="presentation" onMouseDown={e => { if (e.target === e.currentTarget) onClose(); }}><aside className="hermes-inline-drawer" role="dialog" aria-modal="true" aria-label="Ask Hermes inline chat"><header><div><span>✦</span><div><strong>Hermes</strong><small>CEO Advisor · talking with you here</small></div></div><button type="button" aria-label="Close Hermes chat" onClick={onClose}>×</button></header><div className="hermes-inline-conversation">{messages.map((message,index)=><div className={`inline-message ${message.role}`} key={`${message.role}-${index}`}><strong>{message.role === 'ray' ? 'Ray' : 'Hermes'}</strong><p>{message.text}</p></div>)}</div><div className="hermes-inline-compose"><textarea ref={inputRef} value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}}} placeholder="Talk to Hermes like your operating partner…" aria-label="Ask Hermes inline"/><button type="button" onClick={send}>Send</button></div><footer><span>Your current department stays open.</span><button type="button" onClick={onOpenWorkroom}>Open full Hermes Workroom</button><button type="button" onClick={clearHistory}>Clear conversation</button></footer></aside></div>;
}
