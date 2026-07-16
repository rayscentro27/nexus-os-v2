import { useEffect, useState } from 'react';
import { AdminLoginPage, AuthGate, useSession } from '../components/auth';
import { AdminGuard } from '../components/auth/AdminGuard';
import NexusAdminUI from '../admin/NexusAdminUI';
import ClientPortalRoot from '../pages/client/ClientPortalRoot';
import ClientLoginPage from '../pages/client/ClientLoginPage';
import ClientPreviewPage from '../pages/client/ClientPreviewPage';
import UpdatePasswordPage from '../pages/UpdatePasswordPage';
import AuthResetPage from '../pages/AuthResetPage';
import {
  GoClearLandingPage,
  GoClearSignupPage,
  GoClearPricingPage,
  GoClearLoginPage,
} from '../pages/goclear/GoClearPublicPages';
import { CheckoutStatusPage, ServiceOfferPage, ServicePricingPage } from '../pages/goclear/ServiceOfferPages';
import TesterInvitePage from '../pages/tester/TesterInvitePage';
import TesterAcceptPage from '../pages/tester/TesterAcceptPage';
import TesterTasksPage from '../pages/tester/TesterTasksPage';
import { resolveClientContextForCurrentUser } from '../lib/clientAuthContext';
import { supabase, isSupabaseConfigured } from '../lib/supabaseClient';

async function isUserAdmin(userId: string): Promise<boolean> {
  if (!isSupabaseConfigured || !supabase) return false;
  try {
    const { data: adminRow } = await supabase
      .from('admin_users')
      .select('id')
      .eq('id', userId)
      .maybeSingle();
    if (adminRow) return true;
  } catch {}
  try {
    const { data: membership } = await supabase
      .from('tenant_memberships')
      .select('role')
      .eq('user_id', userId)
      .in('role', ['super_admin', 'admin', 'operator'])
      .limit(1)
      .maybeSingle();
    if (membership) return true;
  } catch {}
  return false;
}

function ClientPortalGate() {
  const { user, loading } = useSession();
  const [clientOk, setClientOk] = useState<boolean | null>(null);

  useEffect(() => {
    if (loading || !user) return;
    let cancelled = false;
    (async () => {
      try {
        const admin = await isUserAdmin(user.id);
        if (cancelled) return;
        if (admin) { setClientOk(false); return; }
        const ctx = await resolveClientContextForCurrentUser();
        if (!cancelled) setClientOk(!!ctx);
      } catch {
        if (!cancelled) setClientOk(false);
      }
    })();
    return () => { cancelled = true; };
  }, [user, loading]);

  if (loading || clientOk === null) {
    return <div className="authwrap"><div className="muted">Loading…</div></div>;
  }
  if (!user || !clientOk) {
    window.location.assign('/client/login');
    return <div className="authwrap"><div className="muted">Redirecting to login…</div></div>;
  }
  return <ClientPortalRoot />;
}

const GOCLEAR_ROUTES = ['/goclear', '/goclear/signup', '/goclear/login', '/goclear/pricing', '/pricing', '/readiness-review', '/readiness-action-plan', '/funding-readiness-concierge', '/checkout/success', '/checkout/pending', '/checkout/cancelled', '/checkout/failed'];

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
        {path === '/pricing' && <ServicePricingPage />}
        {path === '/readiness-review' && <ServiceOfferPage slug="readiness-review-97" />}
        {path === '/readiness-action-plan' && <ServiceOfferPage slug="readiness-action-plan-297" />}
        {path === '/funding-readiness-concierge' && <ServiceOfferPage slug="funding-readiness-concierge-497" />}
        {path === '/checkout/success' && <CheckoutStatusPage status="success" />}
        {path === '/checkout/pending' && <CheckoutStatusPage status="pending" />}
        {path === '/checkout/cancelled' && <CheckoutStatusPage status="cancelled" />}
        {path === '/checkout/failed' && <CheckoutStatusPage status="failed" />}
        {path === '/goclear/login' && <GoClearLoginPage />}
      </>
    );
  }

  if (path === '/tester/invite' || path.startsWith('/tester/invite/')) {
    return <TesterInvitePage />;
  }
  if (path === '/tester/accept') {
    return <TesterAcceptPage />;
  }
  if (path === '/tester/tasks') {
    return <TesterTasksPage />;
  }
  if (path === '/update-password') {
    return <UpdatePasswordPage />;
  }
  if (path === '/auth/reset') {
    return <AuthResetPage />;
  }
  if (path === '/admin/login') {
    return <AdminLoginPage />;
  }
  if (path === '/client/login') {
    return <ClientLoginPage />;
  }
  if (path === '/client/preview') {
    return <ClientPreviewPage />;
  }
  if (path === '/client' || path.startsWith('/client/')) {
    return <ClientPortalGate />;
  }
  if (isAdmin) {
    if (import.meta.env.DEV && new URLSearchParams(window.location.search).get('ui-smoke') === '1') {
      return <NexusAdminUI email="local-ui-smoke@nexus.invalid" />;
    }
    return (
      <AdminGuard>
        {() => (
          <AuthGate>
            {(user) => <NexusAdminUI email={user.email} />}
          </AuthGate>
        )}
      </AdminGuard>
    );
  }
  window.location.replace('/');
  return null;
}
