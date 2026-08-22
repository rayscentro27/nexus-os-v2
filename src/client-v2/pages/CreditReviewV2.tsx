import { Info, ShieldCheck } from 'lucide-react'
import type { V2ViewData } from '../types/v2-models'
import { navigateV2 } from '../utils/navigate'
import { PageHeaderV2 } from '../layouts/PageHeaderV2'
import { CardV2, SectionHeaderV2, StatusBadgeV2, ProgressRingV2 } from '../components/primitives'
import { HermesPanelV2 } from '../components/HermesPanelV2'
import InlineDocumentUpload from '../../components/client/InlineDocumentUpload'

const reqTone = (status: string): 'emerald' | 'amber' | 'brand' | 'red' =>
  status === 'complete'
    ? 'emerald'
    : status === 'processing'
      ? 'brand'
      : status === 'attention'
        ? 'red'
        : 'amber'

export function CreditReviewV2({ data }: { data: V2ViewData }) {
  const { scores, readiness, flow, hermes } = data
  const creditStage = readiness.stages.credit
  const requirements = creditStage?.requirements || []
  const creditStatus = flow.creditProfileStatus

  return (
    <div className="v2-fade-in space-y-4">
      <PageHeaderV2
        eyebrow="Journey · Step 1 of 5"
        title="Credit Review"
        subtitle="Your credit snapshot powers the readiness score. Nexus Readiness Score is an educational measure, not a FICO score or lender decision."
        actions={
          <button type="button" className="v2-btn v2-btn--primary v2-btn--sm" onClick={() => navigateV2('/client-v2/credit-improvement')}>
            Continue to Credit Improvement <span className="text-xs">→</span>
          </button>
        }
      />

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_300px] gap-4">
        <div className="space-y-4 min-w-0">
          <CardV2 variant="feature">
            <div className="flex items-center gap-5 flex-wrap">
              <ProgressRingV2 score={scores.credit} size={78} stroke={8} label="credit" />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-v2xl font-bold text-v2ink">Credit readiness</span>
                  <StatusBadgeV2 tone={scores.credit >= 80 ? 'emerald' : scores.credit >= 60 ? 'brand' : 'amber'} dot>
                    {scores.credit >= 80 ? 'Strong' : scores.credit >= 60 ? 'Building' : 'Needs attention'}
                  </StatusBadgeV2>
                </div>
                <p className="mt-1 text-[12.5px] text-v2muted leading-relaxed">{creditStatus?.nextBestAction}</p>
              </div>
              <div className="v2-divider w-full" />
              <div className="flex items-start gap-2 w-full">
                <span className="w-6 h-6 rounded-lg bg-v2amber-tint text-v2amber-deep flex items-center justify-center shrink-0">
                  <Info size={13} />
                </span>
                <p className="text-[12px] leading-relaxed text-v2muted">
                  This is an educational readiness reflection of your credit posture — improving it improves your funding-review quality, but never guarantees any approval or deletion result.
                </p>
              </div>
            </div>
          </CardV2>

          <CardV2>
            <SectionHeaderV2 eyebrow="Readiness baseline" title="What your credit score tracks" />
            <ul className="mt-4 space-y-3">
              {requirements.map((req) => (
                <li key={req.label} className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-[13.5px] font-semibold text-v2ink">{req.label}</span>
                      <StatusBadgeV2 tone={reqTone(String(req.status))} dot>
                        {req.status === 'complete' ? 'Complete' : req.status === 'processing' ? 'Processing' : req.status === 'attention' ? 'Attention' : 'Needed'}
                      </StatusBadgeV2>
                    </div>
                    {req.whyItMatters && <p className="mt-0.5 text-[12.5px] leading-relaxed text-v2muted">{req.whyItMatters}</p>}
                  </div>
                </li>
              ))}
              {requirements.length === 0 && <li className="text-[12.5px] text-v2muted">No baseline requirements available yet.</li>}
            </ul>
          </CardV2>
          <CardV2>
            <div className="flex items-center justify-between gap-3"><span className="text-v2base font-semibold text-v2ink">Upload credit report</span><span className="text-[11px] text-v2muted">Secure, client-scoped storage</span></div>
            <InlineDocumentUpload compact category="credit_reports" label="Choose credit report" pageContext="client_v2_credit_review" track="credit_review" requirementKey="credit_report" />
          </CardV2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <CardV2>
              <SectionHeaderV2 eyebrow="Progress" title="Credit profile status" />
              <div className="mt-3 flex items-center gap-3">
                <ProgressRingV2 score={creditStatus?.percentComplete || 0} size={56} stroke={6} />
                <div className="text-[12.5px] text-v2muted leading-relaxed">
                  {creditStatus?.status?.replace(/_/g, ' ')}
                  {creditStatus?.missingItems?.length ? (
                    <ul className="mt-1 space-y-1">
                      {creditStatus.missingItems.slice(0, 3).map((m) => (
                        <li key={m} className="flex items-center gap-1.5">
                          <span className="v2-dot v2-dot--amber" /> {m}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              </div>
            </CardV2>
            <CardV2>
              <SectionHeaderV2 eyebrow="Strategy" title="Items under review" />
              <div className="mt-3 space-y-2">
                {data.creditRepair.negativeItems.slice(0, 4).map((item) => (
                  <div key={item.id} className="flex items-center justify-between gap-2">
                    <span className="text-[12.5px] font-medium text-v2ink truncate">{item.title}</span>
                    <StatusBadgeV2 tone={String(item.status) === 'draft_ready' ? 'brand' : 'amber'}>{String(item.status).replace(/_/g, ' ')}</StatusBadgeV2>
                  </div>
                ))}
                {data.creditRepair.negativeItems.length === 0 && <p className="text-[12.5px] text-v2muted">No report items flagged yet.</p>}
              </div>
            </CardV2>
          </div>
        </div>

        <aside className="space-y-4">
          <CardV2>
            <div className="flex items-start gap-3">
              <span className="w-9 h-9 rounded-lg bg-v2emerald-tint text-[#0E8A65] flex items-center justify-center shrink-0">
                <ShieldCheck size={18} />
              </span>
              <div>
                <div className="text-v2base font-semibold text-v2ink">Readiness guardrail</div>
                <p className="mt-1 text-[12px] leading-relaxed text-v2muted">
                  {readiness.reviewEligible
                    ? 'You are eligible to request a GoClear review.'
                    : 'Readiness review unlocks when the credit and business stages are complete.'}
                </p>
              </div>
            </div>
          </CardV2>
          <HermesPanelV2
            stageLabel="Credit Review"
            nextAction={readiness.nextBestAction || 'Upload your credit report to generate a baseline.'}
            quickActions={hermes.quickActions}
            insights={hermes.messages.filter((m) => m?.priority === 'high').slice(0, 3).map((m) => String(m?.text || '')).filter(Boolean)}
          />
        </aside>
      </div>
    </div>
  )
}
