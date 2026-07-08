import { useEffect } from 'react';
import { AuthGate, useSession } from '../components/auth';
import NexusAdminUI from '../admin/NexusAdminUI';
import ClientPortalRoot from '../pages/client/ClientPortalRoot';
import UpdatePasswordPage from '../pages/UpdatePasswordPage';
import {
  GoClearLandingPage,
  GoClearSignupPage,
  GoClearPricingPage,
  GoClearLoginPage,
} from '../pages/goclear/GoClearPublicPages';

function ClientPortalGate() {
  const { user, loading } = useSession();
  if (loading) return <div className="authwrap"><div className="muted">Loading…</div></div>;
  if (!user) {
    window.location.assign('/goclear/login');
    return <div className="authwrap"><div className="muted">Redirecting to login…</div></div>;
  }
  return <ClientPortalRoot />;
}

const GOCLEAR_ROUTES = ['/goclear', '/goclear/signup', '/goclear/login', '/goclear/pricing'];

function GoClearScrollUnlock() {
  useEffect(() => {
    const html = document.documentElement;
    const body = document.body;
    html.classList.add('goclear-public-html');
    body.classList.add('goclear-public-body');
    return () => {
      html.classList.remove('goclear-public-html');
      body.classList.remove('goclear-public-body');
    };
  }, []);
  return null;
}

export function App() {
  const path = window.location.pathname.replace(/\/+$/, '') || '/';
  const isGoClear = GOCLEAR_ROUTES.includes(path);
  const isAdmin = path === '/admin' || path.startsWith('/admin/');

  if (isGoClear || path === '/') {
    return (
      <>
        <GoClearScrollUnlock />
        {path === '/' && <GoClearLandingPage />}
        {path === '/goclear' && <GoClearLandingPage />}
        {path === '/goclear/signup' && <GoClearSignupPage />}
        {path === '/goclear/pricing' && <GoClearPricingPage />}
        {path === '/goclear/login' && <GoClearLoginPage />}
      </>
    );
  }

  if (path === '/update-password') {
    return <UpdatePasswordPage />;
  }
  if (path === '/client' || path.startsWith('/client/')) {
    return <ClientPortalGate />;
  }
  if (isAdmin) {
    if (import.meta.env.DEV && new URLSearchParams(window.location.search).get('ui-smoke') === '1') {
      return <NexusAdminUI email="local-ui-smoke@nexus.invalid" />;
    }
    return <AuthGate>{(user) => <NexusAdminUI email={user.email} />}</AuthGate>;
  }
  window.location.replace('/');
  return null;
}
