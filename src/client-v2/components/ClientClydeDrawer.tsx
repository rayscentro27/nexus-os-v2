import { useEffect, useState } from 'react'
import { askClientAI } from '../../lib/clientAiGateway'
import { supabase } from '../../lib/supabaseClient'

type Message = { question: string; answer: string }

export function ClientClydeDrawer() {
  const [open, setOpen] = useState(false)
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [sessionId] = useState(() => `client-v2-clyde-${globalThis.crypto?.randomUUID?.() || Date.now()}`)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  useEffect(() => {
    if (!supabase) return
    void supabase.from('client_ai_conversations').select('user_message,assistant_message').order('created_at', { ascending: false }).limit(8).then(({ data }) => {
      setMessages((data || []).reverse().map(item => ({ question: item.user_message, answer: item.assistant_message })))
    })
  }, [])
  async function send(event: React.FormEvent) {
    event.preventDefault()
    const text = question.trim()
    if (!text || busy) return
    setBusy(true); setNotice('')
    const result = await askClientAI(text, sessionId)
    if (result.ok) {
      setMessages(current => [...current, { question: text, answer: result.data?.answer || 'Clyde could not answer that safely.' }])
      setQuestion('')
    } else setNotice('Clyde is temporarily unavailable. Please use portal support or try again shortly.')
    setBusy(false)
  }
  return <>
    <button type="button" className="v2-btn v2-btn--primary" data-testid="clyde-open" onClick={() => setOpen(true)}>Ask Clyde</button>
    {open && <div role="dialog" aria-label="Ask Clyde" className="fixed inset-0 z-50 flex items-end justify-end bg-black/40 p-4" data-testid="clyde-drawer">
      <section className="w-full max-w-lg rounded-2xl border border-v2line bg-v2surface p-5 shadow-2xl" aria-live="polite">
        <div className="flex items-center justify-between"><div><p className="text-xs uppercase tracking-widest text-v2muted">CLIENT ADVISOR</p><h2 className="text-xl font-semibold text-v2ink">Clyde</h2></div><button type="button" aria-label="Close Clyde" onClick={() => setOpen(false)}>×</button></div>
        <p className="mt-2 text-sm text-v2muted">Guidance from your own portal state. Advisory only; no funding outcome is guaranteed.</p>
        <div className="mt-4 max-h-72 space-y-3 overflow-y-auto">{messages.slice(-6).map((item, index) => <div key={`${item.question}-${index}`} className="rounded-xl bg-v2bg p-3 text-sm"><b>You</b><p>{item.question}</p><b>Clyde</b><p data-testid="clyde-response">{item.answer}</p></div>)}</div>
        {notice && <p role="alert" className="mt-3 text-sm text-red-700">{notice}</p>}
        <form className="mt-4 flex gap-2" onSubmit={send}><input aria-label="Clyde question" placeholder="Ask about your account, documents, or readiness" className="min-w-0 flex-1 rounded-lg border border-v2line px-3 py-2" value={question} onChange={event => setQuestion(event.target.value)} disabled={busy} /><button className="v2-btn v2-btn--primary" type="submit" disabled={busy || !question.trim()}>{busy ? 'Thinking…' : 'Ask'}</button></form>
      </section>
    </div>}
  </>
}
