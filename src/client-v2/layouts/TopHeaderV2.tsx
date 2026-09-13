import { Database, MonitorCheck, User } from 'lucide-react'
import { StatusBadgeV2 } from '../components/primitives'
import { ROUTE_LABELS, navigateV2 } from '../utils/navigate'
import type { V2ProfileView } from '../types/v2-models'

export function TopHeaderV2({
  currentPath,
  isDemo,
  profile,
}: {
  currentPath: string
  isDemo: boolean
  profile: V2ProfileView | null
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
      <button type="button" className="v2-header-profile flex items-center gap-2 rounded-xl px-2 py-1.5 hover:bg-[#E6F7FA]" aria-label={profile?.name ? `Open account for ${profile.name}` : 'Open account'} onClick={() => navigateV2('/client-v2/account')}>
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#E6F7FA] text-v2brand font-semibold text-[11px]">{profile?.name ? initials(profile.name) : <User size={16} />}</span>
        <span className="hidden sm:block text-left"><span className="block text-[12px] font-semibold text-v2ink truncate max-w-[140px]">{profile?.name || 'Account'}</span>{profile?.membershipTier && <span className="block text-[10px] text-v2muted">{profile.membershipTier}</span>}</span>
      </button>
    </header>
  )
}

const initials = (name: string) => name.replace(/\(.*?\)/g, '').trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
