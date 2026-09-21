import { useEffect, useState } from 'react'
import type { ChangeEvent } from 'react'
import type { V2ViewData } from '../types/v2-models'
import { supabase } from '../../lib/supabaseClient'
import { createGoclearReviewRequest, persistClientReport, submitBetaFeedback } from '../../lib/goclearBetaClosure'
import { PageHeaderV2 } from '../layouts/PageHeaderV2'
import { CardV2, SectionHeaderV2, StatusBadgeV2 } from '../components/primitives'
import { ClientClydeDrawer } from '../components/ClientClydeDrawer'

export function ReviewV2({ data }: { data: V2ViewData }) {
  const [reportId, setReportId] = useState<string | null>(null)
  const [workId, setWorkId] = useState<string | null>(null)
  const [feedbackId, setFeedbackId] = useState<string | null>(null)
  const [notes, setNotes] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [scores, setScores] = useState<Record<string, number>>({ offer: 5, funnel: 5, portal: 5, report: 5, next: 5, credit: 5, resources: 5 })

  useEffect(() => {
    if (!data.resolvedClientId) return
    let cancelled = false
    ;(async () => {
      const existing = await supabase?.from('goclear_client_reports').select('id').eq('client_id', data.resolvedClientId).order('created_at', { ascending: false }).limit(1).maybeSingle()
      if (!cancelled && existing?.data?.id) setReportId(existing.data.id)
      if (!existing?.data?.id) {
        const result = await persistClientReport({ readiness: data.readiness })
        if (!cancelled && result.ok) setReportId(result.reportId)
      }
    })()
    return () => { cancelled = true }
  }, [data.resolvedClientId, data.readiness])

  async function requestReview() {
    setBusy(true); setMessage('')
    const result = await createGoclearReviewRequest({ notes, readiness: data.readiness })
    setBusy(false)
    if (!result.ok) { setMessage(`Review request failed: ${result.error}`); return }
    setWorkId(result.workId || null)
    setMessage('Review request submitted to the GoClear review queue.')
  }

  async function submitFeedback() {
    setBusy(true); setMessage('')
    const result = await submitBetaFeedback({ offerClarity: scores.offer, funnelClarity: scores.funnel, portalUsability: scores.portal, reportUsefulness: scores.report, nextStepClarity: scores.next, creditRepairChoiceClarity: scores.credit, affiliateResourceClarity: scores.resources, comments: notes })
    setBusy(false)
    if (!result.ok) { setMessage(`Feedback failed: ${result.error}`); return }
    setFeedbackId(result.feedbackId || null)
    setMessage('Thank you — your beta feedback was saved for triage.')
  }

  const setScore = (key: string) => (event: ChangeEvent<HTMLSelectElement>) => setScores(current => ({ ...current, [key]: Number(event.target.value) }))
  return <div className="v2-fade-in space-y-4 pb-24" style={{ paddingBottom: 140 }}>
    <PageHeaderV2 eyebrow="Journey · Review" title="GoClear Review" subtitle="Your report and review request stay bounded to your client record. Review is guidance, not a funding approval." />
    <CardV2>
      <SectionHeaderV2 eyebrow="Client report" title="Readiness snapshot" right={<StatusBadgeV2 tone={reportId ? 'emerald' : 'amber'} dot>{reportId ? 'Saved' : 'Preparing'}</StatusBadgeV2>} />
      <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-3 text-sm"><div><b>Readiness</b><p>{data.readiness.state.replace(/_/g, ' ')} · {data.scores.overall}/100</p></div><div><b>Priority issue</b><p>{data.readiness.primaryBlocker || 'None identified'}</p></div><div><b>Next step</b><p>{data.readiness.nextBestAction || 'Request review'}</p></div></div>
      <p className="mt-4 text-sm text-v2muted">Missing items: {data.readiness.outstandingRequirements.slice(0, 8).join(' · ') || 'None'}</p>
      <p className="mt-2 text-xs text-v2muted">Report ID: {reportId || 'being saved'} · Credit repair choices remain educational and never require sharing SSN, full account numbers, passwords, PINs, bank credentials, or unredacted reports.</p>
      <div className="mt-4"><ClientClydeDrawer /></div>
    </CardV2>
    <CardV2><SectionHeaderV2 eyebrow="Human review" title="Request GoClear review" />
      <p className="mt-2 text-sm text-v2muted">Submit the current readiness snapshot and any context you want the review team to see.</p><textarea className="mt-3 w-full rounded-lg border border-v2line p-3 text-sm" rows={3} value={notes} onChange={e => setNotes(e.target.value)} placeholder="Optional context for GoClear…" />
      <button type="button" className="v2-btn v2-btn--primary mt-3" disabled={busy || !!workId} onClick={requestReview}>{workId ? 'Review requested' : busy ? 'Submitting…' : 'Submit review request'}</button>{workId && <p className="mt-2 text-xs text-v2muted">Work ID: {workId}</p>}
    </CardV2>
    <CardV2><SectionHeaderV2 eyebrow="Beta feedback" title="Tell us what to improve" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">{[['offer','Offer clarity'],['funnel','Funnel clarity'],['portal','Portal usability'],['report','Report usefulness'],['next','Next-step clarity'],['credit','Credit-repair choice clarity'],['resources','Affiliate/resource clarity']].map(([key,label]) => <label key={key} className="text-sm">{label}<select className="ml-2 rounded border border-v2line p-1" value={scores[key]} onChange={setScore(key)}>{[1,2,3,4,5].map(v => <option key={v} value={v}>{v}</option>)}</select></label>)}</div>
      <button type="button" className="v2-btn v2-btn--ghost mt-4 relative z-40" style={{ marginBottom: 96 }} disabled={busy || !!feedbackId} onClick={submitFeedback}>{feedbackId ? 'Feedback saved' : 'Submit beta feedback'}</button>{feedbackId && <p className="mt-2 text-xs text-v2muted">Feedback ID: {feedbackId}</p>}
    </CardV2>
    {message && <p role="status" className="text-sm text-v2muted">{message}</p>}
  </div>
}
