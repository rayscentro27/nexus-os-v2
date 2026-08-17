import { FileCheck, Lock, ShieldCheck } from 'lucide-react'
import type { V2ViewData } from '../types/v2-models'
import { navigateV2 } from '../utils/navigate'
import { PageHeaderV2 } from '../layouts/PageHeaderV2'
import { CardV2, SectionHeaderV2, StatusBadgeV2 } from '../components/primitives'
import { HermesPanelV2 } from '../components/HermesPanelV2'

export function FundingAccessV2({ data }: { data: V2ViewData }) {
  const { readiness, flow, hermes } = data
  const eligible = readiness.reviewEligible || readiness.state === 'ready_to_review'
  const fundingStatus = flow.businessFundingStatus

  return (
    <div className="v2-fade-in space-y-4">
      <PageHeaderV2
        eyebrow="Journey · Step 5 of 5"
        title="Funding Access"
        subtitle="Readiness confirmation and the recommended funding sequence. Nexus never recommends submitting an application while readiness is not confirmed."
      />

      <div className={`v2-card ${eligible ? 'v2-card--solid-navy' : ''} p-4`}>
        <div className="flex flex-wrap items-center gap-5">
          <div className={`w-14 h-14 rounded-2xl flex items-center justify-center ${eligible ? 'bg-v2emerald/20 text-[#4CE0B0]' : 'bg-v2amber-tint text-v2amber-deep'}`}>
            {eligible ? <ShieldCheck size={26} /> : <Lock size={24} />}
          </div>
          <div className="min-w-0 flex-1">
            <div className={`text-v2lg font-semibold ${eligible ? 'text-white' : 'text-v2ink'}`}>
              {eligible ? 'Readiness confirmed — you may request a GoClear review' : 'Not ready to apply yet'}
            </div>
            <div className={`mt-1 text-[12.5px] leading-relaxed ${eligible ? 'text-white/60' : 'text-v2muted'}`}>
              {eligible
                ? 'Nexus recommends requesting a review before approaching any lender. GoClear evaluates the full picture and gates recommendations to your fit.'
                : readiness.primaryBlocker
                  ? `Complete "${readiness.primaryBlocker}" to move your readiness forward.`
                  : 'Resolve the outstanding requirements, then request a review.'}
            </div>
          </div>
          <div className="flex gap-2">
            <StatusBadgeV2 tone={eligible ? 'emerald' : 'amber'} dot>{readiness.state.replace(/_/g, ' ')}</StatusBadgeV2>
            {eligible && (
              <button type="button" className="v2-btn v2-btn--emerald v2-btn--sm" onClick={() => navigateV2('/client-v2/documents')}>
                <FileCheck size={14} /> Docs ready for review
              </button>
            )}
          </div>
        </div>
      </div>

      {!eligible && (
        <div className="flex items-start gap-2 rounded-xl bg-v2red-tint border border-red-100 px-3.5 py-3">
          <span className="w-5 h-5 rounded-full bg-white flex items-center justify-center mt-px">
            <Lock size={12} className="text-v2red-deep" />
          </span>
          <p className="text-[12.5px] leading-relaxed text-[#A04A44]">
            Avoid new funding applications while readiness is not confirmed. A rejected or premature application can damage the posture this portal works to protect.
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_300px] gap-4">
        <div className="space-y-4 min-w-0">
          <CardV2>
            <SectionHeaderV2 eyebrow="Sequence" title="Recommended funding sequence" />
            <div className="mt-3 space-y-2.5">
              <SequenceRow index={1} title="Readiness confirmation" body={eligible ? 'Confirmed. Your review eligibility is verified against the current pillar status.' : 'Funding readiness must reach review eligibility before any recommendation.'} done={eligible} />
              <SequenceRow index={2} title="Tier 1 evaluation" body={readiness.tier1.relevance || 'Core credit and business profile posture.'} done={readiness.tier1.status === 'ready_to_review'} />
              <SequenceRow index={3} title="Tier 2 evaluation" body={readiness.tier2.relevance || 'Additional bankability and funding considerations.'} done={readiness.tier2.status === 'ready_to_review'} />
              <SequenceRow index={4} title="GoClear fit review" body={readiness.primaryBlocker ? `Blocked by: ${readiness.primaryBlocker}` : 'Fit review is ready to run with your document set.'} done={eligible && !readiness.primaryBlocker} />
            </div>
          </CardV2>

          <CardV2>
            <SectionHeaderV2 eyebrow="Status" title="What Nexus tracks" />
            <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-3">
              <MiniStat label="Business funding" value={fundingStatus?.percentComplete || 0} detail={fundingStatus?.status?.replace(/_/g, ' ') || 'Pending'} />
              <MiniStat label="Review eligible" value={eligible ? 100 : 0} detail={eligible ? 'Yes' : 'Not yet'} />
              <MiniStat label="Outstanding requirements" value={Math.max(0, 100 - (readiness.outstandingRequirements.length ? Math.min(100, readiness.outstandingRequirements.length * 20) : 100))} detail={eligible ? 'None' : `${readiness.outstandingRequirements.length || '—'} remaining`} />
            </div>
          </CardV2>
        </div>

        <aside className="space-y-4">
          <HermesPanelV2
            stageLabel="Funding Access"
            nextAction={
              eligible
                ? 'Readiness is confirmed. Your GoClear fit review can proceed when you are ready.'
                : readiness.nextBestAction || 'Complete the readiness steps to unlock access.'
            }
            quickActions={hermes.quickActions}
            insights={hermes.messages.filter((m) => m?.priority === 'high').slice(0, 3).map((m) => String(m?.text || '')).filter(Boolean)}
          />
        </aside>
      </div>
    </div>
  )
}

function SequenceRow({ index, title, body, done }: { index: number; title: string; body: string; done: boolean }) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-v2line bg-[#FBFCFE] p-3">
      <span className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-[12px] font-bold ${done ? 'bg-v2emerald text-white' : 'bg-v2brand-tint text-v2brand'}`}>
        {done ? '✓' : index}
      </span>
      <div className="min-w-0">
        <div className="text-[13px] font-semibold text-v2ink">{title}</div>
        <p className="mt-0.5 text-[12px] leading-relaxed text-v2muted">{body}</p>
      </div>
    </div>
  )
}

function MiniStat({ label, value, detail }: { label: string; value: number; detail: string }) {
  return (
    <div className="rounded-xl border border-v2line p-3">
      <div className="text-[11px] font-semibold uppercase tracking-wide text-v2muted">{label}</div>
      <div className="mt-1 flex items-baseline gap-1">
        <span className="text-v2xl font-bold text-v2ink tabular-nums">{value}</span>
        <span className="text-[11px] text-v2muted font-medium">{detail}</span>
      </div>
    </div>
  )
}