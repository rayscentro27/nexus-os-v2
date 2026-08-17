import { ArrowRight, Clock, Sparkles } from 'lucide-react'
import { mapRouteToV2, navigateV2 } from '../utils/navigate'
import { StatusBadgeV2 } from './primitives'

export function NextMoveCardV2({
  action,
  route,
  outstandingCount,
  waitingOnProvider,
  providerLabel,
}: {
  action: string
  route: string
  outstandingCount: number
  waitingOnProvider?: boolean
  providerLabel?: string
}) {
  const target = mapRouteToV2(route)
  return (
    <div className="v2-card v2-card--solid-navy v2-card--feature relative overflow-hidden">
      <div className="absolute -top-10 -right-10 w-40 h-40 rounded-full bg-v2brand/20 blur-2xl" />
      <div className="flex items-start justify-between gap-4 relative">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="w-6 h-6 rounded-lg bg-white/10 flex items-center justify-center">
              <Sparkles size={14} className="text-[#9DB8FF]" />
            </span>
            <span className="v2-section-label text-white/50">Nexus Next Move</span>
            {waitingOnProvider && <StatusBadgeV2 tone="amber" className="ml-auto md:hidden">Waiting</StatusBadgeV2>}
          </div>
          <h3 className="mt-2 text-v2lg font-semibold leading-snug text-white">{action}</h3>
          <p className="mt-1.5 text-[12.5px] text-white/60 leading-relaxed">
            {waitingOnProvider
              ? `${providerLabel || 'Your fulfillment provider'} is working on the next step. Nexus will surface verified results here the moment they are ready — no action required from you.`
              : outstandingCount > 0
                ? `This move clears ${outstandingCount} outstanding${outstandingCount === 1 ? ' requirement' : ' requirements'} and keeps your readiness on track.`
                : 'Nothing is blocking your path right now. Check back after your next provider update.'}
          </p>
        </div>
        <div className="flex-shrink-0">
          {waitingOnProvider ? (
            <span className="hidden md:inline-flex items-center gap-2 v2-chip bg-white/10 text-white/80">
              <Clock size={13} /> Waiting on provider
            </span>
          ) : (
            <button
              type="button"
              className="v2-btn v2-btn--primary v2-btn--lg"
              onClick={() => navigateV2(target)}
              disabled={!target}
            >
              Continue
              <ArrowRight size={16} />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}