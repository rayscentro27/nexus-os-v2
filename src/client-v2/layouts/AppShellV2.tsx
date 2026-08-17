import type { ReactNode } from 'react'
import type { V2ProfileView, V2RailStage } from '../types/v2-models'
import { SidebarV2 } from './SidebarV2'
import { TopHeaderV2 } from './TopHeaderV2'

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
      <div className="flex min-h-screen">
        <SidebarV2 profile={profile} railStages={railStages} currentPath={currentPath} onNavigate={onNavigate} />
        <div className="flex-1 flex flex-col min-w-0 h-screen overflow-y-auto v2-thin-scroll">
          <TopHeaderV2 currentPath={currentPath} isDemo={isDemo} />
          <main className="flex-1 p-5">
            <div className="space-y-4 max-w-[1200px]">{children}</div>
          </main>
        </div>
      </div>
    </div>
  )
}