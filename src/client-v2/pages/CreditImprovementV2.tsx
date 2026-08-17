import { CircleCheck, FileIcon, Layers, RefreshCcw, Upload } from 'lucide-react'
import type { V2ViewData } from '../types/v2-models'
import { navigateV2 } from '../utils/navigate'
import { PageHeaderV2 } from '../layouts/PageHeaderV2'
import { CardV2, ProgressRingV2, SectionHeaderV2, StatusBadgeV2 } from '../components/primitives'
import { HermesPanelV2 } from '../components/HermesPanelV2'

const STAGE_STATE: Record<string, { tone: 'emerald' | 'brand' | 'amber' | 'slate'; label: string }> = {
  complete: { tone: 'emerald', label: 'Complete' },
  in_progress: { tone: 'brand', label: 'In progress' },
  pending: { tone: 'slate', label: 'Pending' },
  blocked: { tone: 'amber', label: 'Blocked' },
  upcoming: { tone: 'slate', label: 'Upcoming' },
}

const itemTone = (status: string) => {
  const s = status.toLowerCase()
  if (s === 'draft_ready') return 'brand' as const
  if (/complete|sent|verified|removed/.test(s)) return 'emerald' as const
  if (/needs_documents/.test(s)) return 'amber' as const
  return 'slate' as const
}

export function CreditImprovementV2({ data }: { data: V2ViewData }) {
  const { creditRepair, hermes, readiness } = data
  const stages = creditRepair.workflowStages

  return (
    <div className="v2-fade-in space-y-4">
      <PageHeaderV2
        eyebrow="Journey · Step 2 of 5"
        title="Credit Improvement"
        subtitle="Outsourced credit remediation, verified results, and outreach status. Every letter or dispute step is reviewed by GoClear before anything is sent — nothing is mailed automatically."
        actions={
          <button type="button" className="v2-btn v2-btn--ghost v2-btn--sm" onClick={() => navigateV2('/client-v2/documents')}>
            <Upload size={14} /> Upload requested docs
          </button>
        }
      />

      <div className="v2-card v2-card--solid-navy p-4">
        <div className="flex flex-wrap items-center gap-5">
          <div className="flex items-center gap-4">
            <ProgressRingV2 score={creditRepair.progressPercent} size={78} stroke={8} label="progress" />
            <div>
              <div className="text-v2lg font-semibold text-white">Fulfillment progress</div>
              <div className="text-[12.5px] text-white/60 mt-0.5">{creditRepair.goclearReviewStatus}</div>
            </div>
          </div>
          <div className="flex-1" />
          <StatChip icon={Layers} label="Items under review" value={creditRepair.negativeItemsUnderReview} />
          <StatChip icon={FileIcon} label="Draft letters ready" value={creditRepair.draftLettersReady} />
          <StatChip icon={RefreshCcw} label="GoClear reviews" value={creditRepair.goclearReviewsPending} />
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_300px] gap-4">
        <div className="space-y-4 min-w-0">
          <CardV2>
            <SectionHeaderV2 eyebrow="Fulfillment queue" title="Where your remediation stands" right={<span className="text-[11.5px] text-v2muted">{stages.filter((s) => s.state === 'complete').length}/{stages.length} complete</span>} />
            <ol className="mt-4 space-y-0">
              {stages.map((stage, i) => {
                const cfg = STAGE_STATE[stage.state]
                return (
                  <li key={stage.label} className="relative flex items-start gap-3 pb-4 last:pb-0">
                    {i < stages.length - 1 && <span className="absolute left-[11px] top-7 bottom-0 w-px bg-[#E7ECF5]" />}
                    <span
                      className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 border ${
                        stage.state === 'complete'
                          ? 'bg-v2emerald border-v2emerald text-white'
                          : stage.state === 'blocked'
                            ? 'bg-v2amber-tint border-v2amber text-v2amber-deep'
                            : stage.state === 'in_progress' || stage.state === 'pending'
                              ? 'bg-v2brand-tint border-v2brand/30 text-v2brand'
                              : 'bg-white border-[#D9E1F0] text-[#93A4BF]'
                      }`}
                    >
                      {stage.state === 'complete' ? <CircleCheck size={14} /> : i + 1}
                    </span>
                    <div className="flex items-center justify-between gap-2 min-w-0 flex-1 pt-0.5">
                      <span className={`text-[13px] font-medium ${stage.state === 'upcoming' ? 'text-[#8FA3C3]' : 'text-v2ink'}`}>{stage.label}</span>
                      <StatusBadgeV2 tone={cfg.tone}>{cfg.label}</StatusBadgeV2>
                    </div>
                  </li>
                )
              })}
            </ol>
          </CardV2>

          <CardV2>
            <SectionHeaderV2 eyebrow="Report items" title="Negative items being handled" />
            <ul className="mt-3 divide-y divide-[#EEF2F9]">
              {creditRepair.negativeItems.map((item) => (
                <li key={item.id} className="py-2.5 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-[13px] font-medium text-v2ink truncate">{item.title}</div>
                    <div className="text-[11px] text-v2muted">
                      {String(item.risk_level || '').toUpperCase()} risk
                      {item.goclear_review_status ? ` · GoClear: ${String(item.goclear_review_status).replace(/_/g, ' ')}` : ''}
                    </div>
                  </div>
                  <StatusBadgeV2 tone={itemTone(String(item.status))}>{String(item.status).replace(/_/g, ' ')}</StatusBadgeV2>
                </li>
              ))}
              {creditRepair.negativeItems.length === 0 && <li className="py-3 text-[12.5px] text-v2muted">No open report items.</li>}
            </ul>
          </CardV2>

          <div className="rounded-xl bg-v2amber-tint border border-amber-100 px-3.5 py-3 flex items-start gap-2">
            <span className="w-5 h-5 rounded-full bg-white flex items-center justify-center mt-px">
              <Upload size={12} className="text-v2amber-deep" />
            </span>
            <p className="text-[12.5px] leading-relaxed text-[#8A6420]">{creditRepair.clientGuideRecommendation}</p>
          </div>
        </div>

        <aside className="space-y-4">
          <HermesPanelV2
            stageLabel="Credit Improvement"
            nextAction={readiness.nextBestAction || 'Items are in the GoClear review queue.'}
            quickActions={hermes.quickActions}
            insights={hermes.messages.filter((m) => m?.priority === 'high').slice(0, 3).map((m) => String(m?.text || '')).filter(Boolean)}
          />
        </aside>
      </div>
    </div>
  )
}

function StatChip({ icon: Icon, label, value }: { icon: any; label: string; value: number }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl bg-white/[0.06] border border-white/10 px-4 py-3">
      <span className="w-9 h-9 rounded-xl bg-white/10 flex items-center justify-center">
        <Icon size={17} className="text-[#9DB8FF]" />
      </span>
      <div>
        <div className="text-v2lg font-bold text-white tabular-nums leading-none">{value}</div>
        <div className="text-[11px] text-white/55 mt-1">{label}</div>
      </div>
    </div>
  )
}