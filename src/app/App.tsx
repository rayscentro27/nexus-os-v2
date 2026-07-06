import { AuthGate, useSession } from '../components/auth';
// Redesigned Nexus admin dashboard (mock data, no backend calls). Rendered after auth.
// The previous Shell remains in the repo (src/components/Shell.tsx) and can be restored if needed.
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

export function App() {
  const path = window.location.pathname.replace(/\/+$/, '') || '/';

  // GoClear public pages (no auth required)
  if (path === '/goclear') return <GoClearLandingPage />;
  if (path === '/goclear/signup') return <GoClearSignupPage />;
  if (path === '/goclear/pricing') return <GoClearPricingPage />;
  if (path === '/goclear/login') return <GoClearLoginPage />;

  // Existing protected routes
  if (path === '/update-password') {
    return <UpdatePasswordPage />;
  }
  if (path === '/client' || path.startsWith('/client/')) {
    return <ClientPortalGate />;
  }
  // Local browser smoke tests need to exercise the operating shell without a real admin session.
  // Vite replaces DEV with false in production, so this route cannot bypass live authentication.
  if (import.meta.env.DEV && new URLSearchParams(window.location.search).get('ui-smoke') === '1') {
    return <NexusAdminUI email="local-ui-smoke@nexus.invalid" />;
  }
  return <AuthGate>{(user) => <NexusAdminUI email={user.email} />}</AuthGate>;
}
