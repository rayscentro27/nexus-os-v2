import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'
import { scoreTone } from '../utils/arc'

type Tone = 'emerald' | 'brand' | 'amber' | 'red' | 'slate' | 'indigo'

const toneClasses: Record<Tone, string> = {
  emerald: 'bg-v2emerald-tint text-[#0E8A65]',
  brand: 'bg-v2brand-tint text-v2brand',
  amber: 'bg-v2amber-tint text-v2amber-deep',
  red: 'bg-v2red-tint text-v2red-deep',
  slate: 'bg-[#EEF2F9] text-[#5B6B84]',
  indigo: 'bg-v2indigo-tint text-v2indigo',
}

const dotClasses: Record<Tone, string> = {
  emerald: 'bg-v2emerald',
  brand: 'bg-v2brand',
  amber: 'bg-v2amber',
  red: 'bg-v2red',
  slate: 'bg-[#B7C4DC]',
  indigo: 'bg-v2indigo',
}

export function CardV2({
  variant = 'default',
  className = '',
  children,
  pad = true,
}: {
  variant?: 'default' | 'feature' | 'navy' | 'plain'
  className?: string
  children: ReactNode
  pad?: boolean
}) {
  const variantClass =
    variant === 'feature'
      ? 'v2-card v2-card--feature'
      : variant === 'navy'
        ? 'v2-card v2-card--solid-navy'
        : variant === 'plain'
          ? 'v2-card'
          : 'v2-card'
  return (
    <div className={`${variantClass} ${pad ? 'p-4' : ''} ${className}`}>{children}</div>
  )
}

export function StatusBadgeV2({
  tone = 'slate',
  dot = false,
  children,
  className = '',
}: {
  tone?: Tone
  dot?: boolean
  children: ReactNode
  className?: string
}) {
  return (
    <span className={`v2-chip ${toneClasses[tone]} ${className}`}>
      {dot && <span className={`v2-dot ${dotClasses[tone]}`} />}
      {children}
    </span>
  )
}

export function SectionHeaderV2({
  eyebrow,
  title,
  right,
}: {
  eyebrow?: string
  title: string
  right?: ReactNode
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="min-w-0">
        {eyebrow && <div className="v2-section-label mb-0.5">{eyebrow}</div>}
        <h2 className="text-v2lg font-semibold text-v2ink truncate">{title}</h2>
      </div>
      {right && <div className="flex items-center gap-2 flex-shrink-0">{right}</div>}
    </div>
  )
}

export function KpiTileV2({
  label,
  value,
  sub,
  icon: Icon,
  progress,
  onClick,
}: {
  label: string
  value: string | number
  sub?: string
  icon?: LucideIcon
  progress?: number
  onClick?: () => void
}) {
  const tone = scoreTone(typeof value === 'number' ? value : 0)
  return (
    <button
      type="button"
      onClick={onClick}
      className="v2-card v2-card--feature w-full p-3.5 text-left hover:border-[#C9D4E6] transition-colors focus:outline-none focus:ring-2 focus:ring-v2brand/30"
    >
      <div className="flex items-center justify-between gap-2">
        <div className="text-v2xs font-semibold tracking-wide text-v2muted uppercase truncate">{label}</div>
        {Icon && (
          <span className="w-7 h-7 rounded-lg bg-v2brand-tint text-v2brand flex items-center justify-center">
            <Icon size={15} strokeWidth={2.2} />
          </span>
        )}
      </div>
      <div className="mt-1.5 flex items-baseline gap-1.5">
        <span
          className={`text-v2hero font-bold tracking-tight ${
            tone === 'emerald' ? 'text-[#0E8A65]' : tone === 'red' ? 'text-v2red-deep' : tone === 'amber' ? 'text-v2amber-deep' : 'text-v2ink'
          }`}
        >
          {value}
        </span>
        {typeof progress === 'number' && <span className="text-v2xs font-semibold text-v2muted">%</span>}
      </div>
      {sub && <div className="mt-1 text-[11.5px] text-v2muted leading-tight line-clamp-2">{sub}</div>}
      {typeof progress === 'number' && (
        <div className="v2-progress mt-2 h-1.5 w-full">
          <div style={{ width: `${Math.max(0, Math.min(100, progress))}%` }} />
        </div>
      )}
      {onClick && (
        <div className="mt-2.5 flex items-center gap-1 text-v2xs font-semibold text-v2brand">
          Open <span className="text-[10px]">→</span>
        </div>
      )}
    </button>
  )
}

export function ProgressRingV2({
  score,
  size = 60,
  stroke = 6,
  label,
}: {
  score: number
  size?: number
  stroke?: number
  label?: string
}) {
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const pct = Math.max(0, Math.min(100, score))
  const tone = scoreTone(pct)
  const strokeColor = tone === 'emerald' ? '#12B886' : tone === 'red' ? '#E5534C' : tone === 'amber' ? '#E8A13D' : '#1768F2'
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#E7ECF5" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={strokeColor}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c - (pct / 100) * c}
          className="transition-all duration-700 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className={`font-bold tabular-nums ${size > 52 ? 'text-[15px]' : 'text-[12px]'}`} style={{ color: strokeColor }}>
          {Math.round(pct)}
        </span>
      </div>
      {label && (
        <div className="absolute left-1/2 top-[calc(50%+14px)] -translate-x-1/2 text-[9px] font-semibold uppercase tracking-wide text-v2muted">
          {label}
        </div>
      )}
    </div>
  )
}

export function EmptyStateV2({
  icon: Icon,
  title,
  body,
  actionLabel,
  onAction,
}: {
  icon?: LucideIcon
  title: string
  body?: string
  actionLabel?: string
  onAction?: () => void
}) {
  return (
    <div className="v2-card flex flex-col items-center justify-center gap-3 px-6 py-10 text-center">
      {Icon && (
        <span className="w-12 h-12 rounded-xl bg-v2brand-tint text-v2brand flex items-center justify-center">
          <Icon size={24} strokeWidth={1.8} />
        </span>
      )}
      <div>
        <div className="text-v2base font-semibold text-v2ink">{title}</div>
        {body && <div className="mt-1 text-[12.5px] text-v2muted max-w-sm">{body}</div>}
      </div>
      {actionLabel && onAction && (
        <button type="button" className="v2-btn v2-btn--primary v2-btn--sm" onClick={onAction}>
          {actionLabel}
        </button>
      )}
    </div>
  )
}