import {
  Building2,
  CreditCard,
  FileText,
  Info,
  Target,
  TrendingUp,
  Upload,
} from 'lucide-react'
import type { V2ViewData } from '../types/v2-models'
import { navigateV2 } from '../utils/navigate'
import { PageHeaderV2 } from '../layouts/PageHeaderV2'
import { KpiTileV2, SectionHeaderV2, StatusBadgeV2, CardV2 } from '../components/primitives'
import { JourneyRailV2 } from '../components/JourneyRailV2'
import { NextMoveCardV2 } from '../components/NextMoveCardV2'
import { ReadinessArcV2 } from '../components/ReadinessArcV2'
import { HealthStripV2, type HealthItem } from '../components/HealthStripV2'
import { HermesPanelV2 } from '../components/HermesPanelV2'
import { DocumentStatusCardV2 } from '../components/DocumentStatusCardV2'
import { ActivityFeedV2 } from '../components/ActivityFeedV2'

const greeting = () => {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 18) return 'Good afternoon'
  return 'Good evening'
}

const trackTone = (status: string) => {
  const s = status.toLowerCase()
  if (/missing|blocked/.test(s)) return { tone: 'amber' as const, dot: 'v2-dot--amber' }
  if (/in_progress/.test(s)) return { tone: 'brand' as const, dot: 'v2-dot--brand' }
  if (/ready|complete|good/.test(s)) return { tone: 'emerald' as const, dot: 'v2-dot--emerald' }
  return { tone: 'slate' as const, dot: 'v2-dot--slate' }
}

const textColor: Record<string, string> = {
  'v2-dot--amber': 'text-v2amber-deep',
  'v2-dot--brand': 'text-v2brand',
  'v2-dot--emerald': 'text-[#0E8A65]',
  'v2-dot--slate': 'text-v2muted',
}

export function DashboardV2({ data }: { data: V2ViewData }) {
  const { profile, scores, readiness, journey, flow, documents, creditRepair, railStages, activities, hermes, isDemo } = data

  if (data.mode === 'loading') return <LoadingSkeleton />
  const firstName = profile?.name ? profile.name.replace(/\(.*?\)/g, '').trim().split(/\s+/)[0] : 'there'

  const pendingReview = flow.reviewStatus?.status === 'in_progress' || readiness.processingDocuments.length > 0

  const healthItems: HealthItem[] = [
    {
      id: 'credit',
      label: 'Credit',
      value: scores.credit >= 80 ? 'Strong' : scores.credit >= 60 ? 'Building' : 'Needs attention',
      tone: (scores.credit >= 80 ? 'emerald' : scores.credit >= 40 ? 'amber' : 'red') as 'emerald' | 'amber' | 'red',
      route: '/client-v2/credit-review',
    },
    {
      id: 'documents',
      label: 'Documents',
      value: `${documents.uploadedCount}/${documents.requiredCount || 0} complete`,
      tone: documents.missing.length === 0 && documents.processingCount === 0 ? 'emerald' : documents.processingCount > 0 ? 'emerald' : 'amber',
      route: '/client-v2/documents',
    },
    {
      id: 'business',
      label: 'Business',
      value: scores.business >= 80 ? 'Solid foundation' : scores.business >= 50 ? 'In progress' : 'Getting started',
      tone: scores.business >= 50 ? 'emerald' : 'slate',
      route: '/client-v2/business-foundation',
    },
    {
      id: 'funding',
      label: 'Funding',
      value: readiness.state.replace(/_/g, ' '),
      tone: readiness.state === 'ready_to_review' ? 'emerald' : readiness.state === 'insufficient_information' ? 'red' : 'amber',
      route: '/client-v2/funding-readiness',
    },
  ]

  const insights = hermes.messages
    .filter((m) => m?.priority === 'high' || m?.type === 'action')
    .slice(0, 3)
    .map((m) => String(m?.text || ''))
    .filter(Boolean)

  const flowRows = [
    { label: 'Credit profile', pct: flow.creditProfileStatus?.percentComplete || 0, tone: trackTone(flow.creditProfileStatus?.status || '').dot },
    { label: 'Business profile', pct: flow.businessProfileStatus?.percentComplete || 0, tone: trackTone(flow.businessProfileStatus?.status || '').dot },
    { label: 'Business funding', pct: flow.businessFundingStatus?.percentComplete || 0, tone: trackTone(flow.businessFundingStatus?.status || '').dot },
    { label: 'Documents', pct: flow.documentsStatus?.percentComplete || 0, tone: trackTone(flow.documentsStatus?.status || '').dot },
  ]

  return (
    <div className="v2-fade-in space-y-4">
      <PageHeaderV2
        eyebrow={`${profile?.overallStatus || 'Overview'} · ${isDemo ? 'Demo preview' : 'Live'}`}
        title={`${greeting()}, ${firstName}`}
        subtitle={profile?.currentGoal}
        actions={
          <>
            {pendingReview && (
              <button type="button" className="v2-btn v2-btn--ghost v2-btn--sm" onClick={() => navigateV2('/client-v2/funding-access')}>
                <Info size={14} /> Provider review pending
              </button>
            )}
            <button type="button" className="v2-btn v2-btn--primary v2-btn--sm" onClick={() => navigateV2('/client-v2/documents')}>
              <Upload size={14} /> Upload document
            </button>
          </>
        }
      />

      <HealthStripV2 items={healthItems} />

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_300px] gap-4">
        <div className="space-y-4 min-w-0">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <KpiTileV2
              label="Credit Profile"
              value={scores.credit}
              sub={flow.creditProfileStatus?.nextBestAction || 'Review your credit snapshot'}
              icon={CreditCard}
              progress={scores.credit}
              onClick={() => navigateV2('/client-v2/credit-review')}
            />
            <KpiTileV2
              label="Credit Improvement"
              value={creditRepair.progressPercent}
              sub={`${creditRepair.goclearReviewsPending} items pending GoClear review`}
              icon={TrendingUp}
              progress={creditRepair.progressPercent}
              onClick={() => navigateV2('/client-v2/credit-improvement')}
            />
            <KpiTileV2
              label="Business Foundation"
              value={scores.business}
              sub={flow.businessProfileStatus?.nextBestAction || 'Establish your business profile'}
              icon={Building2}
              progress={scores.business}
              onClick={() => navigateV2('/client-v2/business-foundation')}
            />
            <KpiTileV2
              label="Funding Readiness"
              value={scores.funding}
              sub={`${readiness.outstandingRequirements.length} requirements remaining`}
              icon={Target}
              progress={scores.funding}
              onClick={() => navigateV2('/client-v2/funding-readiness')}
            />
          </div>

          <CardV2 pad={false}>
            <div className="p-4 pb-0">
              <SectionHeaderV2
                eyebrow="Journey"
                title="Your funding readiness journey"
                right={
                  <div className="flex items-center gap-1.5 text-[11.5px] text-v2muted">
                    <span className="v2-dot v2-dot--emerald" />
                    <span>Complete</span>
                    <span className="mx-0.5 text-v2line">|</span>
                    <span className="v2-dot v2-dot--amber" />
                    <span>Current</span>
                  </div>
                }
              />
            </div>
            <div className="p-4">
              <JourneyRailV2 stages={railStages} />
            </div>
          </CardV2>

          <NextMoveCardV2
            action={readiness.nextBestAction || journey.nextBestAction}
            route={readiness.nextBestActionRoute || journey.nextBestActionRoute}
            outstandingCount={readiness.outstandingRequirements.length}
            waitingOnProvider={readiness.processingDocuments.length > 0}
            providerLabel="GoClear Review Team"
          />

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <DocumentStatusCardV2 documents={documents} />
            <ActivityFeedV2 activities={activities} />
            <div className="v2-card p-4">
              <div className="flex items-center gap-2">
                <span className="w-8 h-8 rounded-lg bg-v2emerald-tint text-[#0E8A65] flex items-center justify-center">
                  <FileText size={16} />
                </span>
                <span className="text-v2base font-semibold text-v2ink">At a glance</span>
              </div>
              <ul className="mt-3 space-y-3">
                {flowRows.map((row) => (
                  <li key={row.label}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="flex items-center gap-1.5 text-[12.5px] font-medium text-v2muted">
                        <span className={`v2-dot ${row.tone}`} />
                        {row.label}
                      </span>
                      <span className={`text-[12.5px] font-semibold tabular-nums ${textColor[row.tone]}`}>{row.pct}%</span>
                    </div>
                    <div className={`v2-progress h-1.5 ${row.tone.includes('emerald') ? 'v2-progress--emerald' : row.tone.includes('amber') ? 'v2-progress--amber' : ''}`}>
                      <div style={{ width: `${row.pct}%` }} />
                    </div>
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-[11px] leading-relaxed text-v2muted">
                Readiness track percentages are a guidance measure, not a lender decision.
              </p>
            </div>
          </div>
        </div>

        <aside className="space-y-4">
          <CardV2 variant="feature">
            <ReadinessArcV2 readiness={readiness} credit={scores.credit} business={scores.business} funding={scores.funding} />
          </CardV2>
          <HermesPanelV2
            stageLabel={railStages.find((s) => s.state === 'current')?.shortLabel || profile?.advisorName || 'Funding readiness'}
            nextAction={readiness.nextBestAction || 'Your next step will appear here once reviewed.'}
            quickActions={hermes.quickActions}
            insights={insights}
          />
        </aside>
      </div>

      {readiness.primaryBlocker && (
        <div className="flex items-start gap-2 rounded-xl bg-v2amber-tint border border-amber-100 px-3.5 py-3">
          <StatusBadgeV2 tone="amber" dot>Blocker</StatusBadgeV2>
          <p className="text-[12.5px] leading-relaxed text-[#8A6420]">{readiness.primaryBlocker}. Resolve this to unlock the next stage of funding readiness.</p>
        </div>
      )}
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      <div className="h-14 w-72 rounded-xl bg-[#E7ECF5] animate-pulse" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-16 rounded-2xl bg-[#E7ECF5] animate-pulse" />
        ))}
      </div>
      <div className="h-40 rounded-2xl bg-[#E7ECF5] animate-pulse" />
      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_300px] gap-4">
        <div className="h-40 rounded-2xl bg-[#E7ECF5] animate-pulse" />
        <div className="h-40 rounded-2xl bg-[#E7ECF5] animate-pulse" />
      </div>
    </div>
  )
}