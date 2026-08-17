import type { GuidedFundingReadiness } from '../../lib/clientFundingReadiness'
import { describeArc, scoreTone } from '../utils/arc'
import { StatusBadgeV2 } from './primitives'

const ARC_START = 180
const ARC_END = 360
const TICK_MARKS = [0, 1, 2, 3, 4] as const

export function ReadinessArcV2({
  readiness,
  credit,
  business,
  funding,
}: {
  readiness: GuidedFundingReadiness
  credit: number
  business: number
  funding: number
}) {
  const size = 190
  const stroke = 14
  const radius = (size - stroke) / 2 - 6
  const cx = size / 2
  const cy = size / 2 + 4
  const score = readiness.overallScore || funding
  const clamped = Math.max(0, Math.min(100, score))
  const fillAngle = ARC_START + (clamped / 100) * (ARC_END - ARC_START)
  const tone = scoreTone(clamped)
  const label = readiness.state.replace(/_/g, ' ')

  const rows = [
    { key: 'credit', label: 'Credit', value: credit },
    { key: 'business', label: 'Business', value: business },
    { key: 'funding', label: 'Funding', value: funding },
  ]

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size / 2 + 10 }}>
        <svg width={size} height={size / 2 + 10}>
          <defs>
            <linearGradient id="v2ArcGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#1157D6" />
              <stop offset="55%" stopColor="#1768F2" />
              <stop offset="100%" stopColor="#12B886" />
            </linearGradient>
          </defs>
          <path d={describeArc(cx, cy, radius, ARC_START, ARC_END)} stroke="#E7ECF5" strokeWidth={stroke} strokeLinecap="round" fill="none" />
          <path
            d={describeArc(cx, cy, radius, ARC_START, fillAngle)}
            stroke="url(#v2ArcGradient)"
            strokeWidth={stroke}
            strokeLinecap={clamped >= 99 ? 'round' : 'butt'}
            fill="none"
            className="v2-arc-fill"
          />
          {TICK_MARKS.map((t) => {
            const angle = ARC_START + (t / 4) * 180
            return (
              <circle
                key={t}
                cx={polarX(cx, radius + stroke / 2 + 7, angle)}
                cy={polarY(cy, radius + stroke / 2 + 7, angle)}
                r={2.5}
                fill={angle <= fillAngle ? tone === 'emerald' ? '#12B886' : '#1768F2' : '#C9D4E6'}
              />
            )
          })}
        </svg>
        <div className="absolute inset-x-0 bottom-0 flex flex-col items-center">
          <div className="text-[30px] leading-none font-bold tracking-tight text-v2ink">
            {Math.round(clamped)}
            <span className="text-[16px] font-semibold text-v2muted">/100</span>
          </div>
          <div className="mt-0.5 text-[11px] font-semibold uppercase tracking-wider text-v2muted">Funding Readiness</div>
        </div>
      </div>

      <div className="mt-3">
        <StatusBadgeV2 tone={tone === 'red' ? 'red' : tone === 'amber' ? 'amber' : tone === 'emerald' ? 'emerald' : 'brand'} dot>
          {tone === 'emerald' ? 'Ready' : label}
        </StatusBadgeV2>
      </div>

      <div className="mt-4 w-full space-y-2.5">
        {rows.map((row) => (
          <div key={row.key}>
            <div className="flex items-center justify-between text-[11.5px] mb-1">
              <span className="font-medium text-v2muted">{row.label}</span>
              <span className="font-semibold tabular-nums text-v2ink">{row.value}</span>
            </div>
            <div className="v2-progress h-1.5 w-full">
              <div style={{ width: `${row.value}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

const polarX = (cx: number, radius: number, angleDeg: number) => cx + radius * Math.cos(((angleDeg - 90) * Math.PI) / 180)
const polarY = (cy: number, radius: number, angleDeg: number) => cy + radius * Math.sin(((angleDeg - 90) * Math.PI) / 180)