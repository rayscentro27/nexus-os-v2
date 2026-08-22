import { AlertTriangle, CheckCircle2, ShieldAlert } from 'lucide-react'
import type { V2ViewData } from '../types/v2-models'
import { navigateV2 } from '../utils/navigate'
import { PageHeaderV2 } from '../layouts/PageHeaderV2'
import { CardV2, SectionHeaderV2, StatusBadgeV2 } from '../components/primitives'
import { ReadinessArcV2 } from '../components/ReadinessArcV2'
import { NextMoveCardV2 } from '../components/NextMoveCardV2'
import { HermesPanelV2 } from '../components/HermesPanelV2'
import InlineDocumentUpload from '../../components/client/InlineDocumentUpload'

export function FundingReadinessV2({ data }: { data: V2ViewData }) {
  const { readiness, scores, hermes } = data

  return (
    <div className="v2-fade-in space-y-4">
      <PageHeaderV2
        eyebrow="Journey · Step 4 of 5"
        title="Funding Readiness"
        subtitle="Nexus scores your funding posture from the credit, business, and document pillars. This is an educational measure, not a lender decision."
        actions={
          <button type="button" className="v2-btn v2-btn--primary v2-btn--sm" onClick={() => navigateV2('/client-v2/funding-access')}>
            Review funding access →
          </button>
        }
      />

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_300px] gap-4">
        <div className="space-y-4 min-w-0">
          <div className="grid grid-cols-1 md:grid-cols-[220px_minmax(0,1fr)] gap-4">
            <CardV2 variant="feature" className="flex items-center justify-center">
              <ReadinessArcV2 readiness={readiness} credit={scores.credit} business={scores.business} funding={scores.funding} />
            </CardV2>
            <div className="space-y-3">
              <CardV2>
                <div className="flex items-start gap-3">
                  <span className="w-9 h-9 rounded-lg bg-v2emerald-tint text-[#0E8A65] flex items-center justify-center shrink-0">
                    <CheckCircle2 size={18} />
                  </span>
                  <div>
                    <div className="text-v2base font-semibold text-v2ink">Completed requirements</div>
                    <div className="mt-0.5 text-[12px] leading-relaxed text-v2muted">
                      {readiness.completedRequirements.length > 0
                        ? readiness.completedRequirements.slice(0, 6).join(' · ')
                        : 'No verified requirements yet — work through the checklist below.'}
                    </div>
                  </div>
                </div>
              </CardV2>
              <CardV2>
                <div className="flex items-start gap-3">
                  <span className="w-9 h-9 rounded-lg bg-v2amber-tint text-v2amber-deep flex items-center justify-center shrink-0">
                    <AlertTriangle size={18} />
                  </span>
                  <div>
                    <div className="text-v2base font-semibold text-v2ink">Outstanding requirements</div>
                    <div className="mt-0.5 text-[12px] leading-relaxed text-v2muted">
                      {readiness.outstandingRequirements.length > 0
                        ? readiness.outstandingRequirements.slice(0, 6).join(' · ')
                        : 'No outstanding requirements. Request review to confirm readiness.'}
                    </div>
                  </div>
                </div>
              </CardV2>
              <NextMoveCardV2
                action={readiness.nextBestAction || 'Complete the remaining requirements to unlock review.'}
                route={readiness.nextBestActionRoute || '/client-v2/dashboard'}
                outstandingCount={readiness.outstandingRequirements.length}
                waitingOnProvider={readiness.processingDocuments.length > 0}
                providerLabel="GoClear Review Team"
              />
            </div>
          </div>

          <CardV2>
            <SectionHeaderV2 eyebrow="Pillars" title="Pillar breakdown" />
            <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-4">
              <Pillar
                title="Credit"
                status={readiness.stages.credit.status}
                blockers={readiness.stages.credit.requirements.filter((r) => r.status === 'missing' || r.status === 'attention').map((r) => r.label)}
              />
              <Pillar
                title="Business foundation"
                status={readiness.stages.business_foundation.status}
                blockers={readiness.stages.business_foundation.requirements.filter((r) => r.status === 'missing' || r.status === 'attention').map((r) => r.label)}
              />
              <Pillar
                title="Business bankability"
                status={readiness.stages.business_bankability.status}
                blockers={readiness.stages.business_bankability.requirements.filter((r) => r.status === 'missing' || r.status === 'attention').map((r) => r.label)}
              />
            </div>
          </CardV2>

          {readiness.primaryBlocker && (
            <div className="flex items-start gap-2 rounded-xl bg-v2red-tint border border-red-100 px-3.5 py-3">
              <span className="w-5 h-5 rounded-full bg-white flex items-center justify-center mt-px">
                <ShieldAlert size={12} className="text-v2red-deep" />
              </span>
              <p className="text-[12.5px] leading-relaxed text-[#A04A44]">
                <span className="font-semibold">Primary blocker:</span> {readiness.primaryBlocker}
              </p>
            </div>
          )}
          <CardV2>
            <div className="flex items-center justify-between gap-3"><span className="text-v2base font-semibold text-v2ink">Upload readiness evidence</span><span className="text-[11px] text-v2muted">Bank statements or revenue support</span></div>
            <InlineDocumentUpload compact category="banking" label="Choose readiness document" pageContext="client_v2_funding_readiness" track="funding_readiness" />
          </CardV2>
        </div>

        <aside className="space-y-4">
          <HermesPanelV2
            stageLabel="Funding Readiness"
            nextAction={readiness.nextBestAction || 'Your funding posture is being evaluated.'}
            quickActions={hermes.quickActions}
            insights={hermes.messages.filter((m) => m?.priority === 'high').slice(0, 3).map((m) => String(m?.text || '')).filter(Boolean)}
          />
        </aside>
      </div>
    </div>
  )
}

function Pillar({ title, status, blockers }: { title: string; status: string; blockers: string[] }) {
  return (
    <div className="rounded-xl border border-v2line bg-[#FBFCFE] p-3.5">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[13px] font-semibold text-v2ink">{title}</span>
        <StatusBadgeV2 tone={status === 'ready_to_review' ? 'emerald' : status === 'insufficient_information' ? 'red' : 'amber'}>{status.replace(/_/g, ' ')}</StatusBadgeV2>
      </div>
      {blockers.length > 0 ? (
        <ul className="mt-2 space-y-1">
          {blockers.slice(0, 3).map((b) => (
            <li key={b} className="flex items-start gap-1.5 text-[11.5px] text-v2muted">
              <span className="v2-dot v2-dot--amber mt-1" /> {b}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-[11.5px] text-[#0E8A65] font-medium">No blockers in this pillar.</p>
      )}
    </div>
  )
}
