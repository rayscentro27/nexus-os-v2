import { useEffect } from 'react';
import { AdminLoginPage, AuthGate } from '../components/auth';
import { AdminGuard } from '../components/auth/AdminGuard';
import LiveCompanyIntelligence from '../admin/LiveCompanyIntelligence';
import ClientLoginPage from '../pages/client/ClientLoginPage';
import ClientOnboardingPage from '../pages/client/ClientOnboardingPage';
import ClientPreviewPage from '../pages/client/ClientPreviewPage';
import { ClientV2Gate } from '../client-v2/pages/ClientV2Root';
import { ClientV2PreviewPage } from '../client-v2/pages/ClientV2PreviewPage';
import UpdatePasswordPage from '../pages/UpdatePasswordPage';
import AuthResetPage from '../pages/AuthResetPage';
import {
  GoClearLandingPage,
  GoClearSignupPage,
  GoClearPricingPage,
  GoClearLoginPage,
} from '../pages/goclear/GoClearPublicPages';
import { CheckoutStatusPage, ServiceOfferPage, ServicePricingPage } from '../pages/goclear/ServiceOfferPages';
import GoClearFundingReadinessCampaign from '../pages/goclear/GoClearFundingReadinessCampaign';
import TesterInvitePage from '../pages/tester/TesterInvitePage';
import TesterAcceptPage from '../pages/tester/TesterAcceptPage';
import TesterTasksPage from '../pages/tester/TesterTasksPage';
import GuestAcceptPage from '../pages/guest/GuestAcceptPage';
import OperatorConsole from '../operator/OperatorConsole';
import NexusSocialPublisher from '../pages/public/NexusSocialPublisher';

const GOCLEAR_ROUTES = ['/goclear', '/goclear/signup', '/goclear/login', '/goclear/pricing', '/pricing', '/funding-readiness', '/readiness-review', '/readiness-action-plan', '/funding-readiness-concierge', '/checkout/success', '/checkout/pending', '/checkout/cancelled', '/checkout/failed'];
const CANONICAL_ADMIN_SURFACES = ['live-intelligence', 'ai-command', 'projects', 'tasks', 'research', 'knowledge', 'analytics', 'automation', 'campaigns', 'decisions', 'departments', 'trading', 'settings', 'support'];
const DIRECT_ADMIN_SURFACES: Record<string, string> = { research: 'research', campaigns: 'campaigns', decisions: 'decisions', trading: 'trading', team: 'departments' };

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
  const isOperator = path === '/operator' || path.startsWith('/operator/');

  if (path === '/nexus-social' || path.startsWith('/nexus-social/')) {
    return <NexusSocialPublisher path={path} />;
  }

  if (isGoClear || path === '/') {
    return (
      <>
        <GoClearScrollUnlock />
        {path === '/' && <GoClearLandingPage />}
        {path === '/goclear' && <GoClearLandingPage />}
        {path === '/goclear/signup' && <GoClearSignupPage />}
        {path === '/goclear/pricing' && <GoClearPricingPage />}
        {path === '/funding-readiness' && <GoClearFundingReadinessCampaign />}
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

  if (path === '/invite' || path.startsWith('/invite/')) {
    if (path === '/invite/accept' || path.startsWith('/invite/accept')) {
      return <TesterAcceptPage />;
    }
    return <TesterInvitePage />;
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
  if (path === '/guest/accept') {
    return <GuestAcceptPage />;
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
  if (isOperator) {
    return (
      <AdminGuard>
        {() => (
          <AuthGate>
            {(user) => <OperatorConsole email={user.email} />}
          </AuthGate>
        )}
      </AdminGuard>
    );
  }
  if (path === '/client/login') {
    return <ClientLoginPage />;
  }
  if (path === '/client/onboarding') {
    return <ClientOnboardingPage />;
  }
  if (path === '/client/preview') {
    return <ClientPreviewPage />;
  }
  if (path === '/client-v2/preview') {
    return <ClientV2PreviewPage />;
  }
  if (path === '/client-v2/login') {
    return <ClientLoginPage />;
  }
  if (path === '/client-v2' || path.startsWith('/client-v2/')) {
    return <ClientV2Gate />;
  }
  if (path === '/client' || path.startsWith('/client/')) return <ClientV2Gate />;
  if (isAdmin) {
    const hashSurface = window.location.hash.replace(/^#\/?/, '');
    const directSurface = !hashSurface && DIRECT_ADMIN_SURFACES[path.replace(/^\/admin\/?/, '')];
    const requestedAdminSurface = directSurface || hashSurface || 'live-intelligence';
    const adminHash = requestedAdminSurface === 'team' || requestedAdminSurface === 'dashboard' ? (requestedAdminSurface === 'team' ? 'departments' : 'live-intelligence') : requestedAdminSurface;
    if (CANONICAL_ADMIN_SURFACES.includes(adminHash)) {
      const canonicalAdmin = <LiveCompanyIntelligence surface={adminHash === 'live-intelligence' ? null : adminHash} />;
      if (import.meta.env.DEV && new URLSearchParams(window.location.search).get('ui-smoke') === '1') return canonicalAdmin;
      return (
        <AdminGuard>
          {() => (
            <AuthGate>
              {() => canonicalAdmin}
            </AuthGate>
          )}
        </AdminGuard>
      );
    }
    const canonicalFallback = <LiveCompanyIntelligence />;
    if (import.meta.env.DEV && new URLSearchParams(window.location.search).get('ui-smoke') === '1') return canonicalFallback;
    return <AdminGuard>{() => <AuthGate>{() => canonicalFallback}</AuthGate>}</AdminGuard>;
  }
  window.location.replace('/');
  return null;
}
