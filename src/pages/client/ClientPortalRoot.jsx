import React, { useEffect, useState } from 'react'
import { clientRoutes } from '../../components/client/ClientPortalShell'
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
    const nextUrl = new URL(nextPath, window.location.origin)
    window.history.pushState({}, '', nextPath)
    setPath(normalizePath(nextUrl.pathname))
  }
  return <WorldClassClientPortal path={path} onNavigate={navigate} />
}
