import { useState, useEffect } from 'react';
import { acceptTesterInvitation, validateInviteToken, type ValidatedInvitation } from '../../lib/testerInvitationClient';
import { PILOT_DISCLOSURE_TEXT } from '../../config/serviceOfferCatalog';
import { supabase } from '../../lib/supabaseClient';

export default function TesterAcceptPage() {
  const [token, setToken] = useState('');
  const [invitation, setInvitation] = useState<ValidatedInvitation | null>(null);
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [consentAccepted, setConsentAccepted] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [validated, setValidated] = useState(false);
  const [accepting, setAccepting] = useState(false);
  const [accepted, setAccepted] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const qToken = params.get('token');
    if (qToken) setToken(qToken);
  }, []);

  const handleValidate = async () => {
    if (!token) { setError('Token is required.'); return; }
    setLoading(true); setError('');
    const result = await validateInviteToken(token);
    if (!result.ok) { setError(result.error || 'Invalid invitation.'); setLoading(false); return; }
    setInvitation(result.data.invitation);
    setValidated(true);
    setLoading(false);
  };

  const handleAccept = async () => {
    if (password.length < 8) { setError('Password must be at least 8 characters.'); return; }
    if (password !== confirmPassword) { setError('Passwords do not match.'); return; }
    if (!consentAccepted) { setError('You must accept the terms and disclosure.'); return; }
    setAccepting(true); setError('');
    try {
      const result = await acceptTesterInvitation({ token, password, consentAccepted });
      if (!result.ok) { setError(result.error || 'Acceptance failed.'); setAccepting(false); return; }
      setAccepted(true);

      const { data: { session } } = await supabase?.auth.getSession() || { data: { session: null } };
      if (!session) {
        await supabase?.auth.signInWithPassword({ email: invitation?.tester_email || '', password });
      }
    } catch {
      setError('Failed to accept invitation.');
    }
    setAccepting(false);
  };

  if (accepted) {
    return (
      <div className="nxos-stack" style={{ maxWidth: 600, margin: '40px auto', padding: '0 20px' }} data-testid="tester-accepted">
        <div className="nxos-callout" style={{ borderLeft: '4px solid #10b981' }}>
          <strong>Invitation Accepted!</strong>
          <p>Your account has been created. You can now sign in and begin your testing assignment.</p>
        </div>
        <a href="/tester/tasks" style={{ display: 'inline-block', padding: '10px 20px', background: '#10b981', color: '#fff', borderRadius: 8, textDecoration: 'none', textAlign: 'center' }} data-testid="go-to-tasks">
          Go to Testing Tasks
        </a>
      </div>
    );
  }

  if (!validated) {
    return (
      <div className="nxos-stack" style={{ maxWidth: 500, margin: '60px auto', padding: '0 20px' }} data-testid="tester-accept-validate">
        <h1 style={{ color: '#f8fafc', fontSize: 24 }}>Accept Tester Invitation</h1>
        <p style={{ color: '#94a3b8' }}>Enter the token from your invitation email.</p>
        <div style={{ display: 'flex', gap: 8 }}>
          <input type="text" value={token} onChange={(e) => setToken(e.target.value)} placeholder="Invitation token" style={{ flex: 1, padding: '10px 14px', borderRadius: 8, border: '1px solid #334155', background: '#1e293b', color: '#f8fafc' }} data-testid="accept-token-input" />
          <button onClick={handleValidate} disabled={loading} className="nxos-button" style={{ padding: '10px 20px', background: '#3b82f6', color: '#fff', borderRadius: 8, border: 'none' }} data-testid="accept-validate-btn">
            {loading ? 'Checking...' : 'Check Token'}
          </button>
        </div>
        {error && <p style={{ color: '#ef4444', fontSize: 13 }}>{error}</p>}
      </div>
    );
  }

  if (!invitation) return null;

  const testingLevelLabel = invitation.testing_level === 'invited_test_mode' ? 'Invited Stripe Test Mode'
    : invitation.testing_level === 'controlled_live_pilot' ? 'Controlled $1 Live Pilot'
    : 'Synthetic Internal';

  return (
    <div className="nxos-stack" style={{ maxWidth: 600, margin: '40px auto', padding: '0 20px' }} data-testid="tester-accept-form">
      <h1 style={{ color: '#f8fafc', fontSize: 24 }}>Set Up Your Tester Account</h1>

      <section className="nxos-table-card">
        <h2>Assignment</h2>
        <div style={{ display: 'grid', gap: 8 }}>
          <div><strong>Name:</strong> {invitation.tester_name}</div>
          <div><strong>Testing Level:</strong> {testingLevelLabel}</div>
          <div><strong>Expires:</strong> {new Date(invitation.expires_at).toLocaleDateString()}</div>
          {invitation.assigned_persona && <div><strong>Persona:</strong> {invitation.assigned_persona.toUpperCase()}</div>}
          {invitation.payment_offer_slug && <div><strong>Test Offer:</strong> {invitation.payment_offer_slug}</div>}
        </div>
      </section>

      <section className="nxos-table-card">
        <h2>Create Your Password</h2>
        <p style={{ color: '#94a3b8', fontSize: 13 }}>Choose a secure password for your tester account. Your password is never stored in the invitation record or emailed to you.</p>
        <div style={{ display: 'grid', gap: 12, marginTop: 12 }}>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password (min 8 characters)" style={{ padding: '10px 14px', borderRadius: 8, border: '1px solid #334155', background: '#1e293b', color: '#f8fafc' }} data-testid="password-input" />
          <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder="Confirm password" style={{ padding: '10px 14px', borderRadius: 8, border: '1px solid #334155', background: '#1e293b', color: '#f8fafc' }} data-testid="confirm-password-input" />
        </div>
      </section>

      <section className="nxos-table-card">
        <h2>Pilot Disclosure</h2>
        <div style={{ background: '#1e293b', padding: 16, borderRadius: 8, border: '1px solid #334155', fontSize: 13, color: '#94a3b8', lineHeight: 1.6 }}>
          {PILOT_DISCLOSURE_TEXT}
        </div>
      </section>

      <section className="nxos-table-card">
        <h2>Terms & Consent</h2>
        <p style={{ color: '#94a3b8', fontSize: 13 }}>By accepting this invitation, you agree to participate in controlled testing, submit feedback, and acknowledge that this is a test environment with synthetic data. No real funding or financial services are provided.</p>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12, color: '#e2e8f0', fontSize: 13, cursor: 'pointer' }}>
          <input type="checkbox" checked={consentAccepted} onChange={(e) => setConsentAccepted(e.target.checked)} data-testid="consent-checkbox" />
          I accept the terms and pilot disclosure
        </label>
      </section>

      {invitation.testing_level === 'invited_test_mode' && (
        <div className="nxos-callout" style={{ borderLeft: '4px solid #f59e0b' }}>
          <strong>Stripe Test Mode Notice</strong>
          <p>This invitation includes a test-mode payment flow. You will use a Stripe test card. No real money will be charged.</p>
        </div>
      )}

      {error && <p style={{ color: '#ef4444', fontSize: 13 }}>{error}</p>}

      <button onClick={handleAccept} disabled={accepting} className="nxos-button" style={{ padding: '12px 24px', background: '#10b981', color: '#fff', borderRadius: 8, border: 'none', cursor: accepting ? 'wait' : 'pointer', fontSize: 15, fontWeight: 600 }} data-testid="accept-invitation-btn">
        {accepting ? 'Setting up...' : 'Accept Invitation & Create Account'}
      </button>
    </div>
  );
}
