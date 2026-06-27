import { AuthGate } from '../components/auth';
// Redesigned Nexus admin dashboard (mock data, no backend calls). Rendered after auth.
// The previous Shell remains in the repo (src/components/Shell.tsx) and can be restored if needed.
import NexusAdminUI from '../admin/NexusAdminUI';

export function App() {
  return <AuthGate>{(user) => <NexusAdminUI email={user.email} />}</AuthGate>;
}
