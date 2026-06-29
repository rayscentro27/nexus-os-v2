import React, { useMemo, useState } from 'react'
import { ArrowUp, ShieldCheck, Sparkles } from 'lucide-react'
import { clientGuideQuestionLabels, clientGuideResponses } from '../../data/clientGuideResponses'

function responseFor(text) {
  const q = text.toLowerCase()
  if (/funding.*ready|apply.*funding/.test(q)) return clientGuideResponses.can_i_apply_for_funding_now
  if (/document/.test(q)) return clientGuideResponses.documents_needed
  if (/credit/.test(q)) return clientGuideResponses.how_to_improve_credit
  if (/business profile|duns|domain/.test(q)) return clientGuideResponses.business_profile_next_step
  if (/opportun/.test(q)) return clientGuideResponses.what_opportunity_should_i_focus_on
  if (/review|goclear/.test(q)) return clientGuideResponses.what_goclear_is_reviewing
  if (/next|today|do now/.test(q)) return clientGuideResponses.what_do_i_do_next
  return clientGuideResponses.escalation
}

export function ClientGuidePanel({ compact = false, suggestedKeys }) {
  const keys = useMemo(() => suggestedKeys || ['what_do_i_do_next', 'documents_needed', 'can_i_apply_for_funding_now'], [suggestedKeys])
  const [input, setInput] = useState('')
  const [answer, setAnswer] = useState(clientGuideResponses.what_do_i_do_next)
  function ask(value) {
    if (!value.trim()) return
    setAnswer(responseFor(value))
    setInput('')
  }
  return (
    <section className={`client-guide-panel ${compact ? 'compact' : ''}`}>
      <div className="client-guide-avatar"><Sparkles size={26} /></div>
      <div className="client-guide-body">
        <div className="client-guide-heading"><strong>Nexus Guide</strong><span><ShieldCheck size={14} /> Approved client-safe guidance only</span></div>
        <p>{answer}</p>
        {!compact && <div className="client-guide-chips">{keys.map(key => <button key={key} onClick={() => setAnswer(clientGuideResponses[key])}>{clientGuideQuestionLabels[key]}</button>)}</div>}
        <form onSubmit={event => { event.preventDefault(); ask(input) }} className="client-guide-input">
          <input value={input} onChange={event => setInput(event.target.value)} placeholder="Ask about your approved scores, tasks, documents, or review status…" />
          <button aria-label="Ask Nexus Guide"><ArrowUp size={17} /></button>
        </form>
      </div>
    </section>
  )
}
