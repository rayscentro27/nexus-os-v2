import React, { useState } from 'react';
import { changeCurrentUserPassword, sendPasswordResetEmail } from '../lib/authHelpers';

interface AccountSecurityPanelProps {
  email: string | null;
}

export default function AccountSecurityPanel({ email }: AccountSecurityPanelProps) {
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [changeBusy, setChangeBusy] = useState(false);
  const [changeMsg, setChangeMsg] = useState('');
  const [changeErr, setChangeErr] = useState('');

  const [resetEmail, setResetEmail] = useState(email ?? '');
  const [resetBusy, setResetBusy] = useState(false);
  const [resetMsg, setResetMsg] = useState('');
  const [resetErr, setResetErr] = useState('');

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault();
    setChangeErr(''); setChangeMsg('');
    if (newPassword.length < 12) { setChangeErr('Password must be at least 12 characters.'); return; }
    if (newPassword !== confirmPassword) { setChangeErr('Passwords do not match.'); return; }
    setChangeBusy(true);
    const { error } = await changeCurrentUserPassword(newPassword);
    if (error) { setChangeErr(error); setChangeBusy(false); return; }
    setChangeMsg('Password updated successfully. Your session remains active.');
    setNewPassword(''); setConfirmPassword('');
    setChangeBusy(false);
  }

  async function handleSendReset(e: React.FormEvent) {
    e.preventDefault();
    setResetErr(''); setResetMsg('');
    if (!resetEmail) { setResetErr('Enter your email address.'); return; }
    setResetBusy(true);
    const { error, sent } = await sendPasswordResetEmail(resetEmail);
    if (error) { setResetErr(error); setResetBusy(false); return; }
    if (sent) setResetMsg('If this email is associated with an account, a secure password-reset link has been sent. Check spam if it does not arrive.');
    setResetBusy(false);
  }

  return (
    <div style={{ display: 'grid', gap: 24, maxWidth: 560 }}>
      <section className="glass panel" style={{ padding: 24 }}>
        <h3 style={{ marginTop: 0 }}>Account Security</h3>
        <p style={{ color: 'var(--muted, #afbdd0)', fontSize: 14, margin: '0 0 16px' }}>
          Password changes are handled by Supabase Auth. Nexus does not store your password.
        </p>
        {email && (
          <div style={{ marginBottom: 16, padding: '10px 14px', background: 'rgba(99,179,255,0.08)', borderRadius: 8, fontSize: 14 }}>
            <strong>Signed in as:</strong> {email}
          </div>
        )}

        <form onSubmit={handleChangePassword}>
          <div className="field">
            <label>New password</label>
            <input
              type="password"
              value={newPassword}
              onChange={e => setNewPassword(e.target.value)}
              autoComplete="new-password"
              required
              minLength={12}
              placeholder="At least 12 characters"
            />
          </div>
          <div className="field">
            <label>Confirm new password</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
              required
              minLength={12}
            />
          </div>
          {changeErr && <div className="err">{changeErr}</div>}
          {changeMsg && <div role="status" style={{ color: '#68d391', marginBottom: 8 }}>{changeMsg}</div>}
          <button className="btn" type="submit" disabled={changeBusy} style={{ width: '100%', marginTop: 8 }}>
            {changeBusy ? 'Updating…' : 'Change password'}
          </button>
        </form>
      </section>

      <section className="glass panel" style={{ padding: 24 }}>
        <h3 style={{ marginTop: 0 }}>Send Password Reset Email</h3>
        <p style={{ color: 'var(--muted, #afbdd0)', fontSize: 14, margin: '0 0 16px' }}>
          Enter your email to receive a secure reset link. The link opens a page where you can set a new password.
        </p>
        <form onSubmit={handleSendReset}>
          <div className="field">
            <label>Email</label>
            <input
              type="email"
              value={resetEmail}
              onChange={e => setResetEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </div>
          {resetErr && <div className="err">{resetErr}</div>}
          {resetMsg && <div role="status" style={{ color: '#68d391', marginBottom: 8 }}>{resetMsg}</div>}
          <button className="btn" type="submit" disabled={resetBusy} style={{ width: '100%', marginTop: 8 }}>
            {resetBusy ? 'Sending…' : 'Send password reset email'}
          </button>
        </form>
      </section>
    </div>
  );
}
