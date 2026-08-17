import claudeHermesImg from '../../assets/nexus-3/shared/clyde-hermes-agent.png'
import { ArrowUpRight, Sparkles } from 'lucide-react'
import { mapRouteToV2, navigateV2 } from '../utils/navigate'

export function HermesPanelV2({
  stageLabel,
  nextAction,
  quickActions,
  insights,
}: {
  stageLabel: string
  nextAction: string
  quickActions: Array<Record<string, any>>
  insights: string[]
}) {
  return (
    <div className="v2-card v2-card--feature p-4">
      <div className="flex items-center gap-3">
        <div className="v2-hermes-avatar w-11 h-11 rounded-full flex items-center justify-center shrink-0 overflow-hidden">
          <img src={claudeHermesImg} alt="Hermes" className="w-full h-full object-cover" />
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-v2base font-semibold text-v2ink">Hermes</span>
            <span className="w-1.5 h-1.5 rounded-full bg-v2emerald" />
          </div>
          <div className="text-[11.5px] text-v2muted truncate">Your Nexus advisor · {stageLabel}</div>
        </div>
        <button
          type="button"
          className="ml-auto flex items-center gap-1 text-[12px] font-semibold text-v2brand hover:text-[#1157D6] transition-colors"
          onClick={() => navigateV2('/client-v2/messages')}
        >
          Chat <ArrowUpRight size={14} />
        </button>
      </div>

      <div className="mt-3 rounded-xl bg-white/60 border border-v2line p-3">
        <div className="flex items-start gap-2">
          <Sparkles size={14} className="text-v2indigo mt-0.5 shrink-0" />
          <p className="text-[12.5px] leading-relaxed text-v2ink">{nextAction}</p>
        </div>
      </div>

      {insights.length > 0 && (
        <div className="mt-3 space-y-1.5">
          {insights.slice(0, 3).map((insight, i) => (
            <div key={i} className="flex items-start gap-2 text-[12px] text-v2muted leading-snug">
              <span className="w-1 h-1 rounded-full bg-v2brand mt-1.5 shrink-0" />
              <span>{insight}</span>
            </div>
          ))}
        </div>
      )}

      <div className="mt-3 flex flex-wrap gap-1.5">
        {quickActions.slice(0, 3).map((action, i) => (
          <button
            key={i}
            type="button"
            className="v2-chip bg-white border border-v2line text-v2ink hover:border-[#C9D4E6] hover:bg-v2brand-tint transition-colors"
            onClick={() => {
              const route = action?.route
              if (route) navigateV2(mapRouteToV2(route))
              else if (action?.actionType === 'focus') navigateV2('/client-v2/dashboard')
              else if (action?.actionType === 'next') navigateV2('/client-v2/dashboard')
            }}
          >
            {action?.label || 'Open'}
          </button>
        ))}
      </div>
    </div>
  )
}