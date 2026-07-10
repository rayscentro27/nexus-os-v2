import { useEffect, useState } from 'react';
import { clearNexusAuthSession, type AuthCleanupResult } from '../lib/authSessionCleanup';

export default function AuthResetPage() {
  const [result, setResult] = useState<AuthCleanupResult | null>(null);

  useEffect(() => {
    let cancelled = false;
    clearNexusAuthSession('auth-reset-page').then((cleanup) => {
      if (!cancelled) setResult(cleanup);
    });
    return () => { cancelled = true };
  }, []);

  return (
    <main className="authwrap">
      <section className="authcard">
        <h1>Session cleared</h1>
        <p className="muted">Nexus cleared local Supabase/client/admin session cache for this browser. No tokens or secrets are displayed.</p>
        {!result && <p className="muted">Clearing session…</p>}
        {result && <p className="muted">Removed {result.removedKeys.length} matching local/session storage key(s). Supabase sign-out: {result.signOut}.</p>}
        <button className="btn" type="button" style={{ width: '100%', marginTop: 12 }} onClick={() => window.location.assign('/client/login')}>Go to client login</button>
        <button className="btn ghost" type="button" style={{ width: '100%', marginTop: 8 }} onClick={() => window.location.assign('/admin/login')}>Go to admin login</button>
      </section>
    </main>
  );
}
