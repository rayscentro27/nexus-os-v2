import { AuthGate } from '../components/auth';
import { Shell } from '../components/Shell';

export function App() {
  return <AuthGate>{(user) => <Shell email={user.email} />}</AuthGate>;
}
