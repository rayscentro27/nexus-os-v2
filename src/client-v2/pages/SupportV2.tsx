import { useState } from 'react'
import { askClientAI } from '../../lib/clientAiGateway'
import { V2_ROUTE_CONTRACTS } from '../routeContracts'

/** Structural Customer Service surface; final visual composition is design-gated. */
export function SupportV2() {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const contract = V2_ROUTE_CONTRACTS['/client-v2/support']

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    const message = question.trim()
    if (!message || busy) return
    setBusy(true)
    setError('')
    const result = await askClientAI(message, 'client-v2-support', 'customer_service')
    if (result.ok) {
      setAnswer(String(result.data?.answer || 'Customer Service could not provide a safe status answer.'))
      setQuestion('')
    } else {
      setError('Customer Service is temporarily unavailable. Please try again shortly.')
    }
    setBusy(false)
  }

  return (
    <section data-testid="support-v2" data-real-backend-connected="YES" aria-labelledby="support-v2-title">
      <h1 id="support-v2-title">Support</h1>
      <p>{contract.purpose}. Status answers use your authenticated client context.</p>
      <form onSubmit={submit}>
        <label htmlFor="support-question">How can we help?</label>
        <textarea id="support-question" value={question} onChange={(event) => setQuestion(event.target.value)} disabled={busy} />
        <button type="submit" disabled={busy || !question.trim()}>{busy ? 'Checking…' : 'Ask Customer Service'}</button>
      </form>
      {error && <p role="alert">{error}</p>}
      {answer && <p role="status" data-testid="support-response">{answer}</p>}
    </section>
  )
}
