import React, { useEffect, useRef, useState } from 'react'
import VoicePushToTalk from '../admin/VoicePushToTalk'

const AGENTS = {
  hermes: { label: 'Nexus / Hermes', role: 'Operator · COO · Chief of Staff' },
  nova: { label: 'Nova', role: 'Strategic Adviser · Critic' },
  alpha: { label: 'Alpha', role: 'Research · Evidence · Intelligence' },
}

export default function NexusUniversalComposer({ agent = 'hermes', onAgentChange, onSend, disabled = false, context = null, placeholder = 'Ask Nexus anything…' }) {
  const [text, setText] = useState('')
  const [voiceNotice, setVoiceNotice] = useState('')
  const [activeContext, setActiveContext] = useState(context)
  const textRef = useRef(null)
  const selected = AGENTS[agent] || AGENTS.hermes

  useEffect(() => { textRef.current?.focus?.() }, [agent])

  function submit(event) {
    event?.preventDefault?.()
    const clean = text.trim()
    if (!clean || disabled) return
    onSend(clean)
    setText('')
    setVoiceNotice('')
  }

  return <form className="nx2-composer" onSubmit={submit} data-testid="universal-agent-composer">
    <div className="nx2-composer-head">
      <label className="nx2-agent-select-label" htmlFor="nx2-agent-selector">Talk to</label>
      <select id="nx2-agent-selector" className="nx2-agent-select" value={agent} onChange={event => onAgentChange?.(event.target.value)} disabled={disabled} aria-label="Select agent">
        {Object.entries(AGENTS).map(([id, item]) => <option value={id} key={id}>{item.label} — {item.role}</option>)}
      </select>
      {activeContext && <span className="nx2-context-chip">Context: {activeContext} <button type="button" aria-label="Remove context" onClick={() => { setActiveContext(null); setVoiceNotice('Context removed for this composer.') }}>×</button></span>}
    </div>
    <textarea ref={textRef} value={text} onChange={event => setText(event.target.value)} placeholder={placeholder} aria-label={`Message ${selected.label}`} rows={2} disabled={disabled} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); submit(event) } }} />
    {voiceNotice && <div className="nx2-composer-notice" role="status">{voiceNotice}</div>}
    <div className="nx2-composer-actions">
      <div className="nx2-composer-tools">
        <button type="button" className="nx2-icon-button" aria-label="Attach file" onClick={() => setVoiceNotice('Attachments are bound to the selected agent and conversation.')}>⌕</button>
        <VoicePushToTalk disabled={disabled} sendLabel={`Use transcript in ${selected.label}`} onTranscript={transcript => { setText(transcript); setVoiceNotice('Transcript ready. Review it, then press Send.'); textRef.current?.focus?.() }} />
      </div>
      <button className="nx2-send-button" type="submit" disabled={disabled || !text.trim()}>Send ↑</button>
    </div>
  </form>
}
