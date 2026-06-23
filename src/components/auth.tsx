import { useEffect, useState, type ReactNode } from 'react';
import { supabase, isSupabaseConfigured } from '../lib/supabaseClient';

interface SessionUser { email: string | null; id: string; }

export function useSession() {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!supabase) { setLoading(false); return; }
    supabase.auth.getSession().then(({ data }) => {
      setUser(data.session ? { email: data.session.user.email ?? null, id: data.session.user.id } : null);
      setLoading(false);
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_e, session) => {
      setUser(session ? { email: session.user.email ?? null, id: session.user.id } : null);
    });
    return () => sub.subscription.unsubscribe();
  }, []);
  return { user, loading };
}

export function SignInForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!supabase) return;
    setBusy(true); setErr('');
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) setErr(error.message);
    setBusy(false);
  }

  return (
    <div className="authwrap">
      <form className="authcard" onSubmit={submit}>
        <h1>Nexus <span style={{ color: 'var(--accent)' }}>OS v2</span></h1>
        <p>Admin sign-in. Authenticated admins only — no public access.</p>
        {!isSupabaseConfigured && (
          <div className="err">Supabase not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in .env.</div>
        )}
        <div className="field">
          <label>Email</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" required />
        </div>
        <div className="field">
          <label>Password</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
        </div>
        {err && <div className="err">{err}</div>}
        <button className="btn" type="submit" disabled={busy || !isSupabaseConfigured} style={{ width: '100%', marginTop: 8 }}>
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </div>
  );
}

export function UserMenu({ email }: { email: string | null }) {
  async function signOut() { await supabase?.auth.signOut(); }
  return (
    <div className="usermenu">
      <span>{email ?? 'admin'}</span>
      <button className="btn ghost" onClick={signOut}>Sign out</button>
    </div>
  );
}

export function AuthGate({ children }: { children: (user: SessionUser) => ReactNode }) {
  const { user, loading } = useSession();
  if (loading) return <div className="authwrap"><div className="muted">Loading…</div></div>;
  if (!user) return <SignInForm />;
  return <>{children(user)}</>;
}
