import { navigateV2 } from '../utils/navigate'

export interface HealthItem {
  id: string
  label: string
  value: string
  tone: 'emerald' | 'amber' | 'red' | 'slate'
  route: string
}

const toneDot = { emerald: 'v2-dot--emerald', amber: 'v2-dot--amber', red: 'v2-dot--red', slate: 'v2-dot--slate' }
const toneText = {
  emerald: 'text-[#0E8A65]',
  amber: 'text-v2amber-deep',
  red: 'text-v2red-deep',
  slate: 'text-v2muted',
}

export function HealthStripV2({ items }: { items: HealthItem[] }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          className="v2-health-item text-left focus:outline-none focus:ring-2 focus:ring-v2brand/30"
          onClick={() => navigateV2(item.route)}
        >
          <span className={`v2-dot ${toneDot[item.tone]}`} />
          <span className="min-w-0">
            <span className="block text-[10.5px] font-semibold uppercase tracking-wide text-v2muted truncate">{item.label}</span>
            <span className={`block text-[12.5px] font-semibold leading-tight truncate capitalize ${toneText[item.tone]}`}>{item.value}</span>
          </span>
        </button>
      ))}
    </div>
  )
}