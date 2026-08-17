import type { ReactNode } from 'react'

export function PageHeaderV2({
  eyebrow,
  title,
  subtitle,
  actions,
}: {
  eyebrow?: string
  title: string
  subtitle?: string
  actions?: ReactNode
}) {
  return (
    <div className="flex items-center justify-between gap-4 flex-wrap">
      <div className="min-w-0">
        {eyebrow && <div className="v2-section-label mb-1">{eyebrow}</div>}
        <h1 className="text-v2hero font-bold tracking-tight text-v2ink leading-snug">{title}</h1>
        {subtitle && <p className="mt-1 text-[13px] text-v2muted max-w-2xl leading-relaxed">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2 flex-shrink-0">{actions}</div>}
    </div>
  )
}