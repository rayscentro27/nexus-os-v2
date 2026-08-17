import { BookOpen, Compass, ShieldCheck } from 'lucide-react'
import type { V2ViewData } from '../types/v2-models'
import { navigateV2 } from '../utils/navigate'
import { PageHeaderV2 } from '../layouts/PageHeaderV2'
import { CardV2, SectionHeaderV2 } from '../components/primitives'
import { HermesPanelV2 } from '../components/HermesPanelV2'

const PILLARS = [
  { id: 'credit', title: 'Credit', sub: 'readiness baseline', route: '/client-v2/credit-review' },
  { id: 'improvement', title: 'Credit Improvement', sub: 'fulfillment tracking', route: '/client-v2/credit-improvement' },
  { id: 'business', title: 'Business Foundation', sub: 'entity & bankability', route: '/client-v2/business-foundation' },
  { id: 'funding', title: 'Funding Readiness', sub: 'requirement depth', route: '/client-v2/funding-readiness' },
  { id: 'access', title: 'Funding Access', sub: 'review & sequence', route: '/client-v2/funding-access' },
  { id: 'documents', title: 'Documents', sub: 'required set', route: '/client-v2/documents' },
]

export function ResourcesV2({ data }: { data: V2ViewData }) {
  const { flow, readiness } = data
  const actions = flow.nextBestActions || []

  return (
    <div className="v2-fade-in space-y-4">
      <PageHeaderV2 eyebrow="Reference" title="Resources" subtitle="Your Nexus reference space: what the portal tracks, the recommended next actions, and the guardrails that protect your posture." />

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_300px] gap-4">
        <div className="space-y-4 min-w-0">
          <CardV2>
            <SectionHeaderV2 eyebrow="Index" title="Portal map" />
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {PILLARS.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  className="flex items-center gap-3 rounded-xl border border-v2line bg-[#FBFCFE] px-3.5 py-3 text-left hover:border-[#C9D4E6] transition-colors focus:outline-none focus:ring-2 focus:ring-v2brand/30"
                  onClick={() => navigateV2(p.route)}
                >
                  <span className="w-8 h-8 rounded-lg bg-v2brand-tint text-v2brand flex items-center justify-center shrink-0">
                    <BookOpen size={16} />
                  </span>
                  <span className="min-w-0">
                    <span className="block text-[13px] font-semibold text-v2ink">{p.title}</span>
                    <span className="block text-[11.5px] text-v2muted">{p.sub}</span>
                  </span>
                </button>
              ))}
            </div>
          </CardV2>

          <CardV2>
            <SectionHeaderV2 eyebrow="Recommended" title="Next actions across the portal" />
            <ul className="mt-3 space-y-2.5">
              {actions.slice(0, 6).map((a, i) => (
                <li key={i} className="flex items-start gap-3 rounded-xl border border-v2line bg-[#FBFCFE] px-3.5 py-3">
                  <span className="w-6 h-6 rounded-full bg-v2indigo-tint text-v2indigo flex items-center justify-center shrink-0">
                    <Compass size={14} />
                  </span>
                  <div className="min-w-0">
                    <div className="text-[13px] font-semibold text-v2ink">{a?.primaryCTA || a?.title || a?.action || 'Next action'}</div>
                    {(a?.nextBestAction || a?.detail) && (
                      <p className="mt-0.5 text-[12px] leading-relaxed text-v2muted">{a?.nextBestAction || a?.detail}</p>
                    )}
                  </div>
                </li>
              ))}
              {actions.length === 0 && <li className="text-[12.5px] text-v2muted">No pending recommendations right now.</li>}
            </ul>
          </CardV2>
        </div>

        <aside className="space-y-4">
          <CardV2>
            <div className="flex items-start gap-3">
              <span className="w-9 h-9 rounded-lg bg-v2emerald-tint text-[#0E8A65] flex items-center justify-center shrink-0">
                <ShieldCheck size={18} />
              </span>
              <div>
                <div className="text-v2base font-semibold text-v2ink">Guardrails</div>
                <ul className="mt-2 space-y-2">
                  <li className="text-[11.5px] leading-relaxed text-v2muted flex gap-1.5">
                    <span className="v2-dot v2-dot--emerald mt-1" /> Readiness Score is educational guidance, not a FICO score or lender decision.
                  </li>
                  <li className="text-[11.5px] leading-relaxed text-v2muted flex gap-1.5">
                    <span className="v2-dot v2-dot--emerald mt-1" /> No score improvement or deletion result is guaranteed.
                  </li>
                  <li className="text-[11.5px] leading-relaxed text-v2muted flex gap-1.5">
                    <span className="v2-dot v2-dot--emerald mt-1" /> Nothing is mailed or submitted without GoClear + client review.
                  </li>
                  <li className="text-[11.5px] leading-relaxed text-v2muted flex gap-1.5">
                    <span className="v2-dot v2-dot--emerald mt-1" /> Do not apply for funding while readiness is not confirmed.
                  </li>
                </ul>
              </div>
            </div>
          </CardV2>
          <HermesPanelV2
            stageLabel="Resources"
            nextAction={readiness.nextBestAction || 'Ask Hermes about any step in your funding journey.'}
            quickActions={data.hermes.quickActions}
            insights={data.hermes.messages.filter((m) => m?.priority === 'high').slice(0, 3).map((m) => String(m?.text || '')).filter(Boolean)}
          />
        </aside>
      </div>
    </div>
  )
}