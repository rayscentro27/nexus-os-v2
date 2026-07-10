import { useEffect, useState, type ReactNode } from 'react';
import { checkAdminAccess, type AdminAccessResult } from '../../lib/adminAccess';
import { supabase } from '../../lib/supabaseClient';
import { forceAuthResetAndRedirect } from '../../lib/authSessionCleanup';

interface AdminGuardProps {
  children: (access: AdminAccessResult) => ReactNode;
}

export function AdminGuard({ children }: AdminGuardProps) {
  const [access, setAccess] = useState<AdminAccessResult>({ allowed: false, source: 'none', reason: 'Checking admin access…' });
  const [checking, setChecking] = useState(true);
  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setChecking(true);
    supabase?.auth.getUser().then(({ data }) => {
      if (!cancelled) setEmail(data.user?.email ?? null);
    }).catch(() => {});
    checkAdminAccess().then(result => {
      if (!cancelled) {
        setAccess(result);
        setChecking(false);
      }
    });
    return () => { cancelled = true };
  }, []);

  if (checking) {
    return (
      <div className="authwrap">
        <div className="muted">Checking admin access…</div>
      </div>
    );
  }

  if (!access.allowed) {
    return (
      <div className="authwrap">
        <div className="authcard">
          <h1>Admin access required</h1>
          <p className="muted">
            {email ? `You are signed in as ${email}. This account does not have admin access.` : 'You are not signed in with an approved admin account.'}
          </p>
          <p className="muted">Use an approved GoClear admin account. AdminGuard remains active and client accounts stay blocked.</p>
          <button className="btn" style={{ width: '100%', marginTop: 12 }} onClick={() => forceAuthResetAndRedirect('/admin/login')}>Sign out and switch account</button>
          <button className="btn ghost" style={{ width: '100%', marginTop: 8 }} onClick={() => window.location.assign('/client/dashboard')}>Go to client dashboard</button>
          <button className="btn ghost" style={{ width: '100%', marginTop: 8 }} onClick={() => forceAuthResetAndRedirect('/admin/login')}>Admin login</button>
        </div>
      </div>
    );
  }

  return <>{children(access)}</>;
}
