import { useEffect, useState, type ReactNode } from 'react';
import { supabase, isSupabaseConfigured } from '../lib/supabaseClient';
import { getPasswordResetRedirectUrl, updateRecoveredPassword } from '../lib/authHelpers';
import { forceAuthResetAndRedirect } from '../lib/authSessionCleanup';

interface SessionUser { email: string | null; id: string; }

export function useSession() {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [recoveryMode, setRecoveryMode] = useState(() => new URLSearchParams(window.location.search).get('password-recovery') === '1' || window.location.hash.includes('type=recovery'));
  useEffect(() => {
    if (!supabase) { setLoading(false); return; }
    supabase.auth.getSession().then(({ data }) => {
      setUser(data.session ? { email: data.session.user.email ?? null, id: data.session.user.id } : null);
      setLoading(false);
    });
    const { data: sub } = supabase.auth.onAuthStateChange((event, session) => {
      setUser(session ? { email: session.user.email ?? null, id: session.user.id } : null);
      if (event === 'PASSWORD_RECOVERY') setRecoveryMode(true);
      if (event === 'SIGNED_OUT') setUser(null);
    });
    return () => sub.subscription.unsubscribe();
  }, []);
  return { user, loading, recoveryMode };
}

export function SignInForm({ adminOnly = false }: { adminOnly?: boolean }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const [resetMode, setResetMode] = useState(false);
  const [notice, setNotice] = useState(() => new URLSearchParams(window.location.search).get('password-reset') === 'success' ? 'Password updated. Sign in with your new password.' : '');

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!supabase) return;
    setBusy(true); setErr('');
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) setErr(error.message);
    setBusy(false);
  }

  async function requestReset(e: React.FormEvent) {
    e.preventDefault();
    if (!supabase) return;
    setBusy(true); setErr(''); setNotice('');
    const redirectTo = getPasswordResetRedirectUrl();
    const { error } = await supabase.auth.resetPasswordForEmail(email, { redirectTo });
    if (error) setErr(error.message);
    else setNotice('If this email belongs to an administrator, a secure password-reset link has been sent. Check spam if it does not arrive.');
    setBusy(false);
  }

  if (resetMode) return <div className="authwrap"><form className="authcard" onSubmit={requestReset}>
    <h1>Reset Nexus OS password</h1>
    <p>Enter the administrator email. The new password will be chosen only after opening the secure Supabase recovery link.</p>
    <div className="field"><label htmlFor="admin-reset-email">Email</label><input id="admin-reset-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required /></div>
    {err && <div className="err">{err}</div>}{notice && <div role="status">{notice}</div>}
    <button className="btn" type="submit" disabled={busy || !isSupabaseConfigured} style={{ width:'100%',marginTop:8 }}>{busy?'Requesting…':'Send secure reset link'}</button>
    <button className="btn ghost" type="button" onClick={()=>{setResetMode(false);setErr('');setNotice('')}} style={{ width:'100%',marginTop:8 }}>Back to sign in</button>
  </form></div>;

  return (
    <div className="authwrap">
      <form className="authcard" onSubmit={submit}>
        <h1>Nexus <span style={{ color: 'var(--accent)' }}>OS v2</span></h1>
        <p>{adminOnly ? 'Use an approved GoClear admin account.' : 'Admin sign-in. Authenticated admins only — no public access.'}</p>
        {!isSupabaseConfigured && (
          <div className="err">Supabase not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in .env.</div>
        )}
        <div className="field">
          <label htmlFor="admin-email">Email</label>
          <input id="admin-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" required />
        </div>
        <div className="field">
          <label htmlFor="admin-password">Password</label>
          <input id="admin-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
        </div>
        {err && <div className="err">{err}</div>}
        {notice && <div role="status">{notice}</div>}
        <button className="btn" type="submit" disabled={busy || !isSupabaseConfigured} style={{ width: '100%', marginTop: 8 }}>
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
        <button className="btn ghost" type="button" onClick={() => { setResetMode(true); setErr(''); setNotice(''); }} style={{ width:'100%',marginTop:8 }}>Forgot password?</button>
        <button className="btn ghost" type="button" onClick={() => forceAuthResetAndRedirect('/admin/login')} style={{ width:'100%',marginTop:8 }}>Reset stuck session</button>
      </form>
    </div>
  );
}

export function UpdatePasswordForm() {
  const [password,setPassword]=useState(''); const [confirm,setConfirm]=useState(''); const [err,setErr]=useState(''); const [busy,setBusy]=useState(false);
  async function update(e:React.FormEvent){e.preventDefault();if(!supabase)return;if(password.length<12){setErr('Use at least 12 characters.');return}if(password!==confirm){setErr('Passwords do not match.');return}setBusy(true);setErr('');const {error}=await updateRecoveredPassword(password);if(error){setErr(error);setBusy(false)}}
  return <div className="authwrap"><form className="authcard" onSubmit={update}><h1>Choose a new password</h1><p>Use a unique password with at least 12 characters. Nexus OS will not display or store it in a file.</p><div className="field"><label>New password</label><input type="password" value={password} onChange={e=>setPassword(e.target.value)} autoComplete="new-password" required minLength={12}/></div><div className="field"><label>Confirm new password</label><input type="password" value={confirm} onChange={e=>setConfirm(e.target.value)} autoComplete="new-password" required minLength={12}/></div>{err&&<div className="err">{err}</div>}<button className="btn" type="submit" disabled={busy} style={{width:'100%',marginTop:8}}>{busy?'Updating…':'Set new password'}</button></form></div>
}

export function UserMenu({ email }: { email: string | null }) {
  async function signOut() { await forceAuthResetAndRedirect('/admin/login'); }
  return (
    <div className="usermenu">
      <span>{email ?? 'admin'}</span>
      <button className="btn ghost" onClick={signOut}>Sign out</button>
    </div>
  );
}

export function AuthGate({ children }: { children: (user: SessionUser) => ReactNode }) {
  const { user, loading, recoveryMode } = useSession();
  if (loading) return <div className="authwrap"><div className="muted">Loading…</div></div>;
  if (recoveryMode) return <UpdatePasswordForm />;
  if (!user) return <SignInForm />;
  return <>{children(user)}</>;
}

export function AdminLoginPage() {
  const { user, loading, recoveryMode } = useSession();
  useEffect(() => {
    if (!loading && !recoveryMode && user) {
      window.location.assign('/admin');
    }
  }, [user, loading, recoveryMode]);
  if (loading) return <div className="authwrap"><div className="muted">Loading…</div></div>;
  if (recoveryMode) return <UpdatePasswordForm />;
  if (user) return <div className="authwrap"><div className="muted">Redirecting to admin…</div></div>;
  return <SignInForm adminOnly />;
}
