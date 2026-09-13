import { CheckCircle2, Circle, FileText, Target, TrendingUp } from 'lucide-react'
import type { V2ViewData } from '../types/v2-models'
import { customerGoalBusinessPlanContext, resolveCustomerGoals } from '../adapters/customerGoalsAdapter'
import { PageHeaderV2 } from '../layouts/PageHeaderV2'
import { BrandWave } from '../components/BrandWave'
import { CardV2, SectionHeaderV2, StatusBadgeV2 } from '../components/primitives'

export function CustomerGoalsV2({ data }: { data: V2ViewData }) {
  const resolved = resolveCustomerGoals(data)
  const goal = resolved.goals[0]
  const context = customerGoalBusinessPlanContext(data)
  const progress = goal.currentProgress === null ? null : Math.max(0, Math.min(100, goal.currentProgress))
  return <div className="v2-fade-in space-y-4" data-real-backend-connected={resolved.realBackendConnected ? 'YES' : 'NO'} data-visual-design-pending="NO">
    <PageHeaderV2 eyebrow="Your plan" title="Goals & Business Plan" subtitle="Track your progress, see what is next, and keep your funding preparation grounded in evidence." />
    <CardV2 variant="feature" className="goclear-visual-card p-5">
      <BrandWave className="absolute inset-x-0 bottom-0 h-32 w-full" />
      <div className="grid gap-5 lg:grid-cols-[auto_minmax(0,1fr)_260px] items-center">
        <span className="flex h-14 w-14 items-center justify-center rounded-full bg-[#E6F7FA] text-[#00B4C6]"><Target size={30} strokeWidth={1.75} /></span>
        <div className="min-w-0"><div className="v2-section-label">Primary goal</div><h2 className="mt-1 text-v2xl font-semibold text-v2ink">{goal.title}</h2><p className="mt-1 text-[13px] text-v2muted">{goal.description}</p><div className="mt-4 flex items-center gap-3"><div className="v2-progress h-2 flex-1"><div style={{ width: `${progress ?? 0}%` }} /></div><span className="font-semibold text-[#00B4C6]">{progress === null ? 'Unknown' : `${Math.round(progress)}%`}</span></div><p className="mt-2 text-[11px] text-v2muted">Progress is derived from current readiness evidence.</p></div>
        <div className="border-l border-v2line pl-5 text-[13px] text-v2muted lg:block"><p className="font-semibold italic text-v2ink">One clear step at a time.</p><p className="mt-2">Next: {context.recommendedNextAction}</p></div>
      </div>
    </CardV2>
    <div className="grid gap-4 lg:grid-cols-3">
      <CardV2><SectionHeaderV2 eyebrow="Milestones" title="Next milestones" /><div className="mt-4 space-y-3">{goal.milestones.length ? goal.milestones.map(m => <div key={m.milestoneId} className="flex gap-3"><span className="mt-0.5 text-[#00B4C6]">{m.completionState === 'COMPLETE' ? <CheckCircle2 size={20} /> : <Circle size={20} />}</span><div><p className="text-[13px] font-semibold text-v2ink">{m.title}</p><p className="text-[11.5px] text-v2muted">{m.nextAction}</p></div></div>) : <p className="text-[13px] text-v2muted">No milestones recorded.</p>}</div></CardV2>
      <CardV2><SectionHeaderV2 eyebrow="Use of funds" title="Evidence summary" /><div className="mt-4 flex items-start gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#E6F7FA] text-[#0B2D5B]"><FileText size={19} /></span><div><p className="text-[13px] font-semibold text-v2ink">{context.useOfFunds.length ? `${context.useOfFunds.length} linked item(s)` : 'No items recorded'}</p><p className="mt-1 text-[11.5px] text-v2muted">Evidence: {context.useOfFunds[0]?.evidenceStatus || 'UNKNOWN'}</p></div></div><StatusBadgeV2 tone={context.useOfFunds[0]?.evidenceStatus === 'SUPPORTED' ? 'emerald' : 'amber'} className="mt-4">{context.useOfFunds[0]?.evidenceStatus || 'UNKNOWN'}</StatusBadgeV2></CardV2>
      <CardV2><SectionHeaderV2 eyebrow="Readiness" title="Business plan context" /><div className="mt-4 flex items-start gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#E6F7FA] text-[#00B4C6]"><TrendingUp size={19} /></span><div><p className="text-[13px] font-semibold text-v2ink">{goal.evidence.status}</p><p className="mt-1 text-[11.5px] text-v2muted">{goal.blockers.length ? `${goal.blockers.length} blocker(s) recorded` : 'No blockers recorded'}</p></div></div><p className="mt-4 text-[12px] leading-relaxed text-v2muted">Missing or unverified evidence remains visible and does not become a readiness claim.</p></CardV2>
    </div>
    <CardV2><SectionHeaderV2 eyebrow="Recommended next action" title={context.recommendedNextAction} /><p className="mt-2 text-[12.5px] text-v2muted">Source: {resolved.source}</p></CardV2>
  </div>
}
