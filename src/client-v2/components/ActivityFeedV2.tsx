import { Activity } from 'lucide-react'
import type { V2ActivityItem } from '../types/v2-models'
import { StatusBadgeV2 } from './primitives'

const toneFor = (status: string): 'emerald' | 'brand' | 'amber' | 'slate' => {
  const s = status.toLowerCase()
  if (/complete|approved|verified|good/.test(s)) return 'emerald'
  if (/missing|blocked|attention|action|urgent|open|needs/.test(s)) return 'amber'
  if (/processing|pending|review|in_progress/.test(s)) return 'brand'
  return 'slate'
}

const dotFor = (tone: 'emerald' | 'brand' | 'amber' | 'slate') =>
  tone === 'emerald' ? '#12B886' : tone === 'amber' ? '#F6B33D' : tone === 'brand' ? '#1768F2' : '#B7C4DC'

export function ActivityFeedV2({ activities }: { activities: V2ActivityItem[] }) {
  const items = activities.slice(0, 4)
  return (
    <div className="v2-card p-4">
      <div className="flex items-center gap-2">
        <span className="w-8 h-8 rounded-lg bg-v2indigo-tint text-v2indigo flex items-center justify-center">
          <Activity size={16} />
        </span>
        <span className="text-v2base font-semibold text-v2ink">Recent activity</span>
      </div>
      <ul className="mt-3 space-y-2.5">
        {items.map((item) => (
          <li key={item.id} className="flex items-start gap-2.5">
            <span className="mt-1.5 w-2 h-2 rounded-full shrink-0" style={{ background: dotFor(toneFor(item.status)) }} />
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-2">
                <span className="text-[12.5px] font-medium text-v2ink truncate">{item.label}</span>
                <StatusBadgeV2 tone={toneFor(item.status)} className="shrink-0">
                  {item.status}
                </StatusBadgeV2>
              </div>
              {(item.detail || item.date) && (
                <div className="text-[11.5px] text-v2muted truncate">{item.detail || item.date}</div>
              )}
            </div>
          </li>
        ))}
        {items.length === 0 && <li className="text-[12.5px] text-v2muted">No recent activity yet.</li>}
      </ul>
    </div>
  )
}