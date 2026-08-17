import { useEffect, useState } from 'react'
import '../styles/v2-tailwind.generated.css'
import '../styles/v2-theme.css'
import { useV2ClientData } from '../hooks/useV2ClientData'
import { AppShellV2 } from '../layouts/AppShellV2'
import { renderV2Page, normalizePath } from './ClientV2Root'
import { ROUTE_LABELS, setV2NavigateHandler } from '../utils/navigate'

export function ClientV2PreviewPage() {
  const [path, setPath] = useState('/client-v2/dashboard')

  useEffect(() => {
    setV2NavigateHandler((p) => setPath(normalizePath(p)))
    return () => setV2NavigateHandler(null)
  }, [])

  const data = useV2ClientData(path)
  const known = Boolean(ROUTE_LABELS[path])
  const safePath = known ? path : '/client-v2/dashboard'

  return (
    <>
      <div className="v2-banner px-5 py-2.5 flex items-center justify-between gap-3">
        <span className="truncate">
          Design preview — V2 Clean-Room Client Portal. Data shown is demo/fallback unless a live test client is enabled.
        </span>
        <a
          href="/client/preview"
          className="shrink-0 font-semibold text-[#8A6420] hover:text-[#5E4316] transition-colors"
        >
          Compare classic preview →
        </a>
      </div>
      <AppShellV2
        profile={data.profile}
        railStages={data.railStages}
        currentPath={safePath}
        isDemo={data.isDemo}
        onNavigate={(p) => setPath(normalizePath(p))}
      >
        {renderV2Page(safePath, data)}
      </AppShellV2>
    </>
  )
}