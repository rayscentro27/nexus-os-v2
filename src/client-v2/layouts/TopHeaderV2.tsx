import { Database, MonitorCheck } from 'lucide-react'
import { StatusBadgeV2 } from '../components/primitives'
import { ROUTE_LABELS, navigateV2 } from '../utils/navigate'

export function TopHeaderV2({
  currentPath,
  isDemo,
}: {
  currentPath: string
  isDemo: boolean
}) {
  const label = ROUTE_LABELS[currentPath] || 'Dashboard'
  return (
    <header className="h-16 shrink-0 bg-white border-b border-v2line flex items-center px-5 gap-4 sticky top-0 z-20">
      <div className="flex items-center gap-2 text-[13px] min-w-0">
        <span className="text-v2muted">Nexus Client Portal</span>
        <span className="text-v2line">/</span>
        <span className="font-semibold text-v2ink truncate">{label}</span>
      </div>
      <div className="flex-1" />
      <StatusBadgeV2 tone={isDemo ? 'amber' : 'emerald'} dot>
        {isDemo ? 'Demo data preview' : 'Live data'}
      </StatusBadgeV2>
      <button
        type="button"
        className="hidden lg:inline-flex items-center gap-1.5 text-[12px] font-medium text-v2muted hover:text-v2brand transition-colors"
        onClick={() => navigateV2('/client-v2/dashboard')}
      >
        <MonitorCheck size={15} /> Readiness monitor
      </button>
      <span className="hidden md:inline-flex items-center gap-1.5 text-[12px] font-medium text-v2muted">
        <Database size={14} />
        Supabase connected
      </span>
    </header>
  )
}