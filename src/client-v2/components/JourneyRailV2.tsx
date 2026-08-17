import { Check } from 'lucide-react'
import type { V2RailStage } from '../types/v2-models'
import { navigateV2 } from '../utils/navigate'

export function JourneyRailV2({ stages }: { stages: V2RailStage[] }) {
  return (
    <div className="flex items-stretch gap-1">
      {stages.map((stage, i) => {
        const isLast = i === stages.length - 1
        const color =
          stage.state === 'completed'
            ? 'text-v2emerald'
            : stage.state === 'current'
              ? 'text-v2brand'
              : stage.state === 'blocked'
                ? 'text-v2amber-deep'
                : 'text-v2muted'
        return (
          <div key={stage.id} className="flex-1 min-w-0">
            <button type="button" className="v2-journey-node w-full" onClick={() => navigateV2(stage.path)} aria-label={`Go to ${stage.label}`}>
              <div className="relative" style={{ margin: '0 22px' }}>
                <div className={`connector ${!isLast ? '' : 'hidden'}`} />
                <div className={`node-dot ${stage.state}`}>
                  {stage.state === 'completed' ? <Check size={15} strokeWidth={3} /> : stage.score > 0 ? stage.score : i + 1}
                </div>
              </div>
            </button>
            <div className="mt-2 text-center px-0.5">
              <div className={`text-[11.5px] font-semibold leading-tight truncate ${color}`}>{stage.shortLabel}</div>
            </div>
          </div>
        )
      })}
    </div>
  )
}