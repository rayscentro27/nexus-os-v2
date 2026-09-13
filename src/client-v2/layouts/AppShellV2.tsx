import type { ReactNode } from 'react'
import { CircleGauge, FileText, Home, MoreHorizontal, Target } from 'lucide-react'
import type { V2ProfileView, V2RailStage } from '../types/v2-models'
import { SidebarV2 } from './SidebarV2'
import { TopHeaderV2 } from './TopHeaderV2'
import { ClientClydeDrawer } from '../components/ClientClydeDrawer'

export function AppShellV2({
  profile,
  railStages,
  currentPath,
  isDemo,
  onNavigate,
  children,
}: {
  profile: V2ProfileView | null
  railStages: V2RailStage[]
  currentPath: string
  isDemo: boolean
  onNavigate: (path: string) => void
  children: ReactNode
}) {
  return (
    <div className="v2-app min-h-screen">
      <div className="flex min-h-screen flex-col xl:flex-row">
        <SidebarV2 profile={profile} railStages={railStages} currentPath={currentPath} onNavigate={onNavigate} />
        <div className="flex-1 flex flex-col min-w-0 xl:h-screen xl:overflow-y-auto v2-thin-scroll">
          <TopHeaderV2 currentPath={currentPath} isDemo={isDemo} profile={profile} />
          <main className="flex-1 min-w-0 p-5">
            <div className="w-full min-w-0 space-y-4">{children}</div>
          </main>
          {currentPath === '/client-v2/messages' && <div className="fixed bottom-5 right-5 z-40"><ClientClydeDrawer /></div>}
        </div>
      </div>
      <MobileBottomNav currentPath={currentPath} onNavigate={onNavigate} />
    </div>
  )
}

function MobileBottomNav({ currentPath, onNavigate }: { currentPath: string; onNavigate: (path: string) => void }) {
  const items = [
    ['/client-v2/dashboard', 'Home', Home],
    ['/client-v2/funding-readiness', 'Readiness', CircleGauge],
    ['/client-v2/documents', 'Documents', FileText],
    ['/client-v2/goals', 'Goals', Target],
    ['/client-v2/account', 'More', MoreHorizontal],
  ] as const
  return <nav className="v2-mobile-bottom-nav fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-v2line bg-white/95 px-1 py-2 shadow-[0_-4px_18px_rgba(11,45,91,.08)]" aria-label="Mobile portal navigation">
    {items.map(([path, label, Icon]) => <button key={path as string} type="button" className={currentPath === path ? 'is-active' : ''} onClick={() => onNavigate(path as string)} aria-current={currentPath === path ? 'page' : undefined}><Icon size={19} strokeWidth={1.75} className="mx-auto" aria-hidden="true" /><span className="mt-1 block text-[10px]">{label}</span></button>)}
  </nav>
}
