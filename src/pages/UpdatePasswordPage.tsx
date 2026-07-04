import { useEffect, useState } from 'react';
import { supabase, isSupabaseConfigured } from '../lib/supabaseClient';
import { updateRecoveredPassword } from '../lib/authHelpers';

export default function UpdatePasswordPage() {
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const [checking, setChecking] = useState(true);
  const [recoveryReady, setRecoveryReady] = useState(false);

  useEffect(() => {
    if (!supabase) { setChecking(false); return; }
    supabase.auth.getSession().then(({ data }) => {
      setRecoveryReady(!!data.session);
      setChecking(false);
    });
    const { data: sub } = supabase.auth.onAuthStateChange((event) => {
      if (event === 'PASSWORD_RECOVERY') {
        setRecoveryReady(true);
        setChecking(false);
      }
    });
    return () => sub.subscription.unsubscribe();
  }, []);

  async function handleUpdate(e: React.FormEvent) {
    e.preventDefault();
    setErr('');
    if (password.length < 12) { setErr('Password must be at least 12 characters.'); return; }
    if (password !== confirm) { setErr('Passwords do not match.'); return; }
    setBusy(true);
    const { error } = await updateRecoveredPassword(password);
    if (error) { setErr(error); setBusy(false); }
  }

  if (checking) {
    return (
      <div className="authwrap">
        <div className="authcard">
          <h1>Verifying reset link…</h1>
          <p>Please wait while we verify your password reset link.</p>
        </div>
      </div>
    );
  }

  if (!recoveryReady) {
    return (
      <div className="authwrap">
        <div className="authcard">
          <h1>Reset link expired</h1>
          <p>This password reset link is expired or invalid. Request a new password reset email from the sign-in page.</p>
          {!isSupabaseConfigured && (
            <div className="err" style={{ marginTop: 12 }}>Supabase not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in .env.</div>
          )}
          <a className="btn" href="/" style={{ display: 'block', textAlign: 'center', marginTop: 16, textDecoration: 'none' }}>
            Back to sign in
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="authwrap">
      <form className="authcard" onSubmit={handleUpdate}>
        <h1>Choose a new password</h1>
        <p>Use a unique password with at least 12 characters. Nexus OS will not display or store it in a file.</p>
        <div className="field">
          <label>New password</label>
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            autoComplete="new-password"
            required
            minLength={12}
          />
        </div>
        <div className="field">
          <label>Confirm new password</label>
          <input
            type="password"
            value={confirm}
            onChange={e => setConfirm(e.target.value)}
            autoComplete="new-password"
            required
            minLength={12}
          />
        </div>
        {err && <div className="err">{err}</div>}
        <button className="btn" type="submit" disabled={busy} style={{ width: '100%', marginTop: 8 }}>
          {busy ? 'Updating…' : 'Set new password'}
        </button>
      </form>
    </div>
  );
}
