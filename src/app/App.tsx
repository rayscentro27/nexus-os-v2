import { AuthGate } from '../components/auth';
// Redesigned Nexus admin dashboard (mock data, no backend calls). Rendered after auth.
// The previous Shell remains in the repo (src/components/Shell.tsx) and can be restored if needed.
import NexusAppShell from '../components/NexusAppShell';
import ClientPortalRoot from '../pages/client/ClientPortalRoot';

export function App() {
  if (window.location.pathname === '/client' || window.location.pathname.startsWith('/client/')) {
    return <ClientPortalRoot />;
  }
  // Local browser smoke tests need to exercise the operating shell without a real admin session.
  // Vite replaces DEV with false in production, so this route cannot bypass live authentication.
  if (import.meta.env.DEV && new URLSearchParams(window.location.search).get('ui-smoke') === '1') {
    return <NexusAppShell email="local-ui-smoke@nexus.invalid" />;
  }
  return <AuthGate>{(user) => <NexusAppShell email={user.email} />}</AuthGate>;
}
