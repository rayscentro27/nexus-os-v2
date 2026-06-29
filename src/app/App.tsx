import { AuthGate } from '../components/auth';
// Redesigned Nexus admin dashboard (mock data, no backend calls). Rendered after auth.
// The previous Shell remains in the repo (src/components/Shell.tsx) and can be restored if needed.
import NexusAdminUI from '../admin/NexusAdminUI';
import ClientPortalRoot from '../pages/client/ClientPortalRoot';

export function App() {
  if (window.location.pathname === '/client' || window.location.pathname.startsWith('/client/')) {
    return <ClientPortalRoot />;
  }
  return <AuthGate>{(user) => <NexusAdminUI email={user.email} />}</AuthGate>;
}
