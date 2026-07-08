import { useEffect, useState, type ReactNode } from 'react';
import { checkAdminAccess, type AdminAccessResult } from '../../lib/adminAccess';

interface AdminGuardProps {
  children: (access: AdminAccessResult) => ReactNode;
}

export function AdminGuard({ children }: AdminGuardProps) {
  const [access, setAccess] = useState<AdminAccessResult>({ allowed: false, source: 'none', reason: 'Checking admin access…' });
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setChecking(true);
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
        <div className="muted">Admin access required. You do not have permission to view this page.</div>
        <button className="btn ghost" style={{ marginTop: 12 }} onClick={() => window.location.assign('/client/dashboard')}>Go to client dashboard</button>
      </div>
    );
  }

  return <>{children(access)}</>;
}
