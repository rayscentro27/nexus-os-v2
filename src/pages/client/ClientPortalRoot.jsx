import React, { useEffect, useState } from 'react'
import { ClientPortalShell, clientRoutes } from '../../components/client/ClientPortalShell'
import { clientPageMap } from './ClientPortalPages'
import WorldClassClientPortal from './WorldClassClientPortal'

const fallbackPath = '/client/dashboard'

function normalizePath(pathname) {
  const trimmed = pathname.length > 1 ? pathname.replace(/\/+$/, '') : pathname
  return clientRoutes.some(route => route.path === trimmed) ? trimmed : fallbackPath
}

export default function ClientPortalRoot() {
  const [path, setPath] = useState(() => normalizePath(window.location.pathname))
  useEffect(() => {
    if (window.location.pathname !== path) window.history.replaceState({}, '', path)
    const onPopState = () => setPath(normalizePath(window.location.pathname))
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [path])
  function navigate(nextPath) {
    window.history.pushState({}, '', nextPath)
    setPath(nextPath)
  }
  if (path === '/client/dispute-review') {
    return <ClientPortalShell path={path} onNavigate={navigate}>{clientPageMap[path]}</ClientPortalShell>
  }
  return <WorldClassClientPortal path={path} onNavigate={navigate} />
}
