import React, { useEffect, useState } from 'react'
import { ClientPortalShell, clientRoutes } from '../../components/client/ClientPortalShell'
import { clientPageMap } from './ClientPortalPages'

const fallbackPath = '/client/dashboard'

function normalizePath(pathname) {
  const trimmed = pathname.length > 1 ? pathname.replace(/\/+$/, '') : pathname
  return clientRoutes.some(route => route.path === trimmed) ? trimmed : fallbackPath
}

function DemoBanner() {
  return (
    <div style={{
      background: 'linear-gradient(135deg, #fef3c7, #fde68a)',
      borderBottom: '2px solid #f59e0b',
      padding: '10px 20px',
      textAlign: 'center',
      fontWeight: 600,
      fontSize: '0.9rem',
      color: '#92400e',
      position: 'sticky',
      top: 0,
      zIndex: 9999,
    }}>
      Preview Mode — Demo data only. Not connected to a live client record.
    </div>
  )
}

export default function ClientPreviewPage() {
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
  return (
    <>
      <DemoBanner />
      <ClientPortalShell path={path} onNavigate={navigate}>
        {clientPageMap[path] || clientPageMap[fallbackPath]}
      </ClientPortalShell>
    </>
  )
}
