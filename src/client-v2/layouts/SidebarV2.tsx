import {
  BookOpen,
  Building2,
  CircleDollarSign,
  CreditCard,
  FileText,
  LayoutDashboard,
  MessageSquare,
  Receipt,
  Sparkles,
  Target,
  TrendingUp,
} from 'lucide-react'
import type { V2ProfileView, V2RailStage } from '../types/v2-models'

const WORKSPACE_NAV = [
  { id: 'dashboard', label: 'Dashboard', path: '/client-v2/dashboard', icon: LayoutDashboard },
  { id: 'documents', label: 'Documents', path: '/client-v2/documents', icon: FileText },
  { id: 'resources', label: 'Resources', path: '/client-v2/resources', icon: BookOpen },
]

const SUPPORT_NAV = [
  { id: 'messages', label: 'Messages', path: '/client-v2/messages', icon: MessageSquare },
  { id: 'billing', label: 'Billing', path: '/client-v2/billing', icon: Receipt },
]

const STAGE_ICON: Record<string, typeof CreditCard> = {
  credit_review: CreditCard,
  credit_improvement: TrendingUp,
  business_foundation: Building2,
  funding_readiness: Target,
  funding_access: CircleDollarSign,
}

export function SidebarV2({
  profile,
  railStages,
  currentPath,
  onNavigate,
}: {
  profile: V2ProfileView | null
  railStages: V2RailStage[]
  currentPath: string
  onNavigate: (path: string) => void
}) {
  const isActive = (path: string) => currentPath === path
  return (
    <aside className="v2-sidebar w-[220px] shrink-0 h-screen sticky top-0 flex flex-col overflow-y-auto v2-thin-scroll">
      <div className="px-4 pt-5 pb-4 flex items-center gap-2.5">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-v2brand to-v2indigo flex items-center justify-center shadow-lg shadow-[#0A1329]/40">
          <Sparkles size={18} className="text-white" />
        </div>
        <div className="leading-none">
          <div className="text-[15px] font-bold tracking-tight text-white">Nexus</div>
          <div className="text-[10.5px] font-medium text-white/45 tracking-wide">Client Portal</div>
        </div>
      </div>

      <nav className="flex-1 px-3 pb-4 space-y-5 mt-1">
        <div>
          <div className="v2-nav-section-label mb-1.5">Your Journey</div>
          <div className="space-y-1">
            {railStages.map((stage) => {
              const Icon = STAGE_ICON[stage.id]
              return (
                <button
                  key={stage.id}
                  type="button"
                  className={`v2-nav-item ${isActive(stage.path) ? 'is-active' : ''}`}
                  onClick={() => onNavigate(stage.path)}
                >
                  <Icon size={16} strokeWidth={2} />
                  <span className="flex-1 truncate">{stage.shortLabel}</span>
                  <span
                    className={`w-2 h-2 rounded-full ${
                      stage.state === 'completed'
                        ? 'bg-v2emerald'
                        : stage.state === 'current'
                          ? 'bg-white'
                          : stage.state === 'blocked'
                            ? 'bg-v2amber'
                            : 'bg-white/15'
                    }`}
                  />
                </button>
              )
            })}
          </div>
        </div>

        <div>
          <div className="v2-nav-section-label mb-1.5">Workspace</div>
          <div className="space-y-1">
            {WORKSPACE_NAV.map((item) => {
              const Icon = item.icon
              return (
                <button
                  key={item.id}
                  type="button"
                  className={`v2-nav-item ${isActive(item.path) ? 'is-active' : ''}`}
                  onClick={() => onNavigate(item.path)}
                >
                  <Icon size={16} strokeWidth={2} />
                  <span className="flex-1 truncate">{item.label}</span>
                </button>
              )
            })}
          </div>
        </div>

        <div>
          <div className="v2-nav-section-label mb-1.5">Support</div>
          <div className="space-y-1">
            {SUPPORT_NAV.map((item) => {
              const Icon = item.icon
              return (
                <button
                  key={item.id}
                  type="button"
                  className={`v2-nav-item ${isActive(item.path) ? 'is-active' : ''}`}
                  onClick={() => onNavigate(item.path)}
                >
                  <Icon size={16} strokeWidth={2} />
                  <span className="flex-1 truncate">{item.label}</span>
                </button>
              )
            })}
          </div>
        </div>
      </nav>

      <div className="px-3 pb-4">
        <div className="rounded-2xl bg-white/[0.05] border border-white/10 p-3">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-full v2-avatar-glyph flex items-center justify-center text-[13px] font-bold shrink-0">
              {profile?.name ? initials(profile.name) : '·'}
            </div>
            <div className="min-w-0">
              <div className="text-[12.5px] font-semibold text-white truncate">{profile?.name || 'Client'}</div>
              <div className="text-[10.5px] text-white/50 truncate">{profile?.membershipTier || 'Membership'}</div>
            </div>
          </div>
          <button
            type="button"
            className="mt-2.5 w-full text-[11px] font-medium text-white/45 hover:text-white transition-colors text-left"
            onClick={() => {
              window.location.href = '/client/dashboard'
            }}
          >
            Open classic portal →
          </button>
        </div>
      </div>
    </aside>
  )
}

const initials = (name: string) =>
  name
    .replace(/\(.*?\)/g, '')
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((n) => n[0])
    .join('')
    .toUpperCase()