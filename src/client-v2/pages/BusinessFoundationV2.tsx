import { Building2, FileText } from 'lucide-react'
import type { V2ViewData } from '../types/v2-models'
import { navigateV2 } from '../utils/navigate'
import { PageHeaderV2 } from '../layouts/PageHeaderV2'
import { CardV2, ProgressRingV2, SectionHeaderV2, StatusBadgeV2 } from '../components/primitives'
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

const reqLabel = (status: string) =>
  status === 'complete' ? 'Complete' : status === 'processing' ? 'Processing' : status === 'attention' ? 'Attention' : 'Needed'

export function BusinessFoundationV2({ data }: { data: V2ViewData }) {
  const { readiness, flow, hermes } = data
  const foundation = readiness.stages.business_foundation?.requirements || []
  const bankability = readiness.stages.business_bankability?.requirements || []
  const bizStatus = flow.businessProfileStatus
  const completed = foundation.filter((r) => r.status === 'complete').length

  return (
    <div className="v2-fade-in space-y-4">
      <PageHeaderV2
        eyebrow="Journey · Step 3 of 5"
        title="Business Foundation"
        subtitle="The entity, banking, and trade-profile milestones Nexus uses to confirm your business is fundable. Completeness improves review quality — it is not a guarantee."
        actions={
          <button type="button" className="v2-btn v2-btn--ghost v2-btn--sm" onClick={() => navigateV2('/client-v2/documents')}>
            <FileText size={14} /> Add business documents
          </button>
        }
      />

      <div className="v2-card v2-card--solid-navy p-4">
        <div className="flex flex-wrap items-center gap-5">
          <ProgressRingV2 score={bizStatus?.percentComplete || readiness.stages.business_foundation.contribution || 0} size={78} stroke={8} label="profile" />
          <div>
            <div className="text-v2lg font-semibold text-white">Business profile readiness</div>
            <div className="text-[12.5px] text-white/60 mt-0.5">{bizStatus?.nextBestAction || 'Complete the remaining foundation milestones.'}</div>
          </div>
          <div className="flex-1" />
          <div className="flex gap-4">
            <Band label="Complete" value={foundation.filter((r) => r.status === 'complete').length} />
            <Band label="Needed" value={foundation.filter((r) => r.status === 'missing').length} />
            <Band label="Funding blockers" value={readiness.tier1.blockers.length + readiness.tier2.blockers.length} />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_300px] gap-4">
        <div className="space-y-4 min-w-0">
          <CardV2>
            <SectionHeaderV2 eyebrow="Foundation" title="Core business milestones" right={<span className="text-[11.5px] text-v2muted">{completed}/{foundation.length} complete</span>} />
            <ul className="mt-3 divide-y divide-[#EEF2F9]">
              {foundation.map((req) => (
                <li key={req.label} className="py-3 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-[13px] font-semibold text-v2ink">{req.label}</div>
                    {req.whyItMatters && <div className="mt-0.5 text-[12px] leading-relaxed text-v2muted">{req.whyItMatters}</div>}
                  </div>
                  <StatusBadgeV2 tone={reqTone(String(req.status))} dot>{reqLabel(String(req.status))}</StatusBadgeV2>
                </li>
              ))}
              {foundation.length === 0 && <li className="py-4 text-[12.5px] text-v2muted">No foundation milestones yet.</li>}
            </ul>
          </CardV2>
          <CardV2>
            <div className="flex items-center justify-between gap-3"><span className="text-v2base font-semibold text-v2ink">Add business document</span><span className="text-[11px] text-v2muted">EIN, formation, or banking evidence</span></div>
            <InlineDocumentUpload compact category="business_formation" label="Choose business document" pageContext="client_v2_business_foundation" track="business_foundation" />
          </CardV2>

          <CardV2>
            <SectionHeaderV2 eyebrow="Bankability" title="Banking & revenue readiness" />
            <ul className="mt-3 divide-y divide-[#EEF2F9]">
              {bankability.map((req) => (
                <li key={req.label} className="py-3 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-[13px] font-semibold text-v2ink">{req.label}</div>
                    {req.whyItMatters && <div className="mt-0.5 text-[12px] leading-relaxed text-v2muted">{req.whyItMatters}</div>}
                  </div>
                  <StatusBadgeV2 tone={reqTone(String(req.status))} dot>{reqLabel(String(req.status))}</StatusBadgeV2>
                </li>
              ))}
              {bankability.length === 0 && <li className="py-4 text-[12.5px] text-v2muted">No banking milestones yet.</li>}
            </ul>
          </CardV2>
        </div>

        <aside className="space-y-4">
          <CardV2>
            <div className="flex items-center gap-2 mb-3">
              <span className="w-8 h-8 rounded-lg bg-v2brand-tint text-v2brand flex items-center justify-center">
                <Building2 size={16} />
              </span>
              <span className="text-v2base font-semibold text-v2ink">Funding posture</span>
            </div>
            <div className="space-y-2.5">
              <div>
                <div className="flex items-center justify-between text-[11.5px] mb-1">
                  <span className="font-medium text-v2muted">Tier 1 readiness</span>
                  <StatusBadgeV2 tone={readiness.tier1.status === 'ready_to_review' ? 'emerald' : readiness.tier1.status === 'insufficient_information' ? 'red' : 'amber'}>
                    {readiness.tier1.status.replace(/_/g, ' ')}
                  </StatusBadgeV2>
                </div>
                {readiness.tier1.blockers.length > 0 && (
                  <ul className="space-y-1">
                    {readiness.tier1.blockers.slice(0, 2).map((b) => (
                      <li key={b} className="text-[11.5px] text-v2muted flex items-start gap-1.5">
                        <span className="v2-dot v2-dot--amber mt-1" /> {b}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div>
                <div className="flex items-center justify-between text-[11.5px] mb-1">
                  <span className="font-medium text-v2muted">Tier 2 readiness</span>
                  <StatusBadgeV2 tone={readiness.tier2.status === 'ready_to_review' ? 'emerald' : readiness.tier2.status === 'insufficient_information' ? 'red' : 'amber'}>
                    {readiness.tier2.status.replace(/_/g, ' ')}
                  </StatusBadgeV2>
                </div>
                {readiness.tier2.blockers.length > 0 && (
                  <ul className="space-y-1">
                    {readiness.tier2.blockers.slice(0, 2).map((b) => (
                      <li key={b} className="text-[11.5px] text-v2muted flex items-start gap-1.5">
                        <span className="v2-dot v2-dot--amber mt-1" /> {b}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </CardV2>
          <HermesPanelV2
            stageLabel="Business Foundation"
            nextAction={readiness.nextBestAction || 'Complete the remaining business milestones.'}
            quickActions={hermes.quickActions}
            insights={hermes.messages.filter((m) => m?.priority === 'high').slice(0, 3).map((m) => String(m?.text || '')).filter(Boolean)}
          />
        </aside>
      </div>
    </div>
  )
}

function Band({ label, value }: { label: string; value: number }) {
  return (
    <div className="text-center rounded-2xl bg-white/[0.06] border border-white/10 px-4 py-2.5 min-w-[92px]">
      <div className="text-v2lg font-bold text-white tabular-nums leading-none">{value}</div>
      <div className="text-[10.5px] font-semibold uppercase tracking-wide text-white/50 mt-1">{label}</div>
    </div>
  )
}
