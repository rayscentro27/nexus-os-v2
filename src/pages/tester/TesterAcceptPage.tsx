import { useState, useEffect } from 'react';
import { acceptTesterInvitation, validateInviteToken, type ValidatedInvitation } from '../../lib/testerInvitationClient';
import { supabase } from '../../lib/supabaseClient';

const TYPE_LABELS: Record<string, string> = {
  friends_family_free: 'Free Friends & Family Preview',
  friends_family_one_dollar: '$1 Friends & Family Pilot',
  invited_test_mode: 'Invited Preview',
  synthetic_internal: 'Internal Testing',
  controlled_live_pilot: 'Controlled Pilot',
};

export default function TesterAcceptPage() {
  const [token, setToken] = useState('');
  const [invitation, setInvitation] = useState<ValidatedInvitation | null>(null);
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [consentAccepted, setConsentAccepted] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [validated, setValidated] = useState(false);
  const [accepting, setAccepting] = useState(false);
  const [accepted, setAccepted] = useState(false);

  useEffect(() => {
    const extractToken = (): string | null => {
      const params = new URLSearchParams(window.location.search);
      const qToken = params.get('token');
      if (qToken) return qToken;
      const path = window.location.pathname;
      const parts = path.split('/').filter(Boolean);
      const acceptIdx = parts.indexOf('accept');
      if (acceptIdx !== -1 && acceptIdx + 1 < parts.length) {
        return parts[acceptIdx + 1];
      }
      const inviteIdx = parts.indexOf('invite');
      if (inviteIdx !== -1 && inviteIdx + 2 < parts.length && parts[inviteIdx + 1] === 'accept') {
        return parts[inviteIdx + 2];
      }
      return null;
    };

    const foundToken = extractToken();
    if (foundToken && foundToken.length >= 10) {
      setToken(foundToken);
      (async () => {
        try {
          const result = await validateInviteToken(foundToken);
          if (result.ok) {
            setInvitation(result.data.invitation);
            setValidated(true);
          } else {
            const errCode = result.error || '';
            if (errCode.includes('expired')) setError('This invitation has expired.');
            else if (errCode.includes('revoked')) setError('This invitation is no longer available.');
            else if (errCode.includes('already_accepted') || errCode.includes('completed')) {
              setError('This invitation has already been used. Please sign in.');
            } else setError('Invalid invitation link.');
          }
        } catch {
          setError('Unable to verify your invitation. Please try again.');
        }
        setLoading(false);
      })();
    } else {
      setLoading(false);
    }
  }, []);

  const handleAccept = async () => {
    if (password.length < 8) { setError('Password must be at least 8 characters.'); return; }
    if (password !== confirmPassword) { setError('Passwords do not match.'); return; }
    if (!consentAccepted) { setError('You must accept the terms and disclosure.'); return; }
    setAccepting(true); setError('');
    try {
      const result = await acceptTesterInvitation({ token, password, consentAccepted });
      if (!result.ok) { setError(result.error || 'Acceptance failed.'); setAccepting(false); return; }
      const { data: { session } } = await supabase?.auth.getSession() || { data: { session: null } };
      if (!session) {
        await supabase?.auth.signInWithPassword({ email: invitation?.tester_email || '', password });
      }
      setAccepted(true);
    } catch {
      setError('Failed to accept invitation.');
    }
    setAccepting(false);
  };

  if (accepted) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #0f1729 0%, #1a2744 50%, #0f1729 100%)' }}>
        <div style={{ maxWidth: 500, padding: '40px 32px', background: '#1e293b', borderRadius: 16, border: '1px solid #334155', textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🎉</div>
          <h1 style={{ color: '#f8fafc', fontSize: 22, margin: '0 0 12px' }}>Welcome to GoClear!</h1>
          <p style={{ color: '#94a3b8', fontSize: 14, lineHeight: 1.6, margin: '0 0 24px' }}>
            Your account is ready. Start exploring the complete GoClear experience.
          </p>
          <a href="/client/login?accepted=1" style={{ display: 'block', textAlign: 'center', padding: '14px 24px', background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)', color: '#fff', borderRadius: 10, textDecoration: 'none', fontWeight: 600, fontSize: 16 }} data-testid="start-journey-btn">
            Sign In and Start My GoClear Journey
          </a>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #0f1729 0%, #1a2744 50%, #0f1729 100%)' }}>
        <div style={{ textAlign: 'center', color: '#e2e8f0' }}>
          <div style={{ width: 48, height: 48, border: '3px solid #334155', borderTopColor: '#3b82f6', borderRadius: '50%', margin: '0 auto 16px', animation: 'spin 1s linear infinite' }} />
          <p style={{ fontSize: 16, color: '#94a3b8' }}>Setting up your account...</p>
        </div>
      </div>
    );
  }

  if (!validated || error) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #0f1729 0%, #1a2744 50%, #0f1729 100%)' }}>
        <div style={{ maxWidth: 480, padding: '40px 32px', background: '#1e293b', borderRadius: 16, border: '1px solid #334155', textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>❌</div>
          <h1 style={{ color: '#f8fafc', fontSize: 22, margin: '0 0 12px' }}>Invitation Issue</h1>
          <p style={{ color: '#94a3b8', fontSize: 14, lineHeight: 1.6, margin: '0 0 24px' }}>{error || 'Unable to load your invitation.'}</p>
          <a href="/" style={{ display: 'inline-block', padding: '10px 24px', background: '#3b82f6', color: '#fff', borderRadius: 8, textDecoration: 'none', fontWeight: 600 }}>
            Go to GoClear
          </a>
        </div>
      </div>
    );
  }

  if (!invitation) return null;

  const typeName = TYPE_LABELS[invitation.testing_level] || 'Friends & Family Preview';
  const isFree = invitation.testing_level === 'friends_family_free' || invitation.testing_level === 'invited_test_mode';

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #0f1729 0%, #1a2744 50%, #0f1729 100%)', padding: '40px 20px' }}>
      <div style={{ maxWidth: 520, width: '100%' }}>
        <div style={{ background: '#1e293b', borderRadius: 16, border: '1px solid #334155', overflow: 'hidden' }}>
          <div style={{ background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)', padding: '28px 28px 20px', textAlign: 'center' }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'rgba(255,255,255,0.8)', letterSpacing: 1, textTransform: 'uppercase', marginBottom: 6 }}>
              GoClear Friends & Family
            </div>
            <h1 style={{ color: '#ffffff', fontSize: 20, margin: 0, fontWeight: 700 }}>
              Create Your Account
            </h1>
          </div>

          <div style={{ padding: '24px 28px' }}>
            <div style={{ background: '#0f172a', borderRadius: 10, padding: '14px 18px', marginBottom: 20, border: '1px solid #1e293b' }}>
              <div style={{ display: 'grid', gap: 6 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#94a3b8', fontSize: 12 }}>Welcome</span>
                  <span style={{ color: '#e2e8f0', fontSize: 12, fontWeight: 500 }}>{invitation.tester_name}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#94a3b8', fontSize: 12 }}>Type</span>
                  <span style={{ color: '#10b981', fontSize: 12, fontWeight: 500 }}>{typeName}</span>
                </div>
              </div>
            </div>

            <div style={{ marginBottom: 20 }}>
              <label style={{ color: '#e2e8f0', fontSize: 13, display: 'block', marginBottom: 6 }}>Password</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Create a password (min 8 characters)" style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid #334155', background: '#0f172a', color: '#f8fafc', fontSize: 14, boxSizing: 'border-box' }} data-testid="password-input" />
            </div>

            <div style={{ marginBottom: 20 }}>
              <label style={{ color: '#e2e8f0', fontSize: 13, display: 'block', marginBottom: 6 }}>Confirm Password</label>
              <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder="Confirm your password" style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid #334155', background: '#0f172a', color: '#f8fafc', fontSize: 14, boxSizing: 'border-box' }} data-testid="confirm-password-input" />
            </div>

            <div style={{ background: '#f8fbff', borderRadius: 8, padding: '12px 16px', marginBottom: 20, border: '1px solid #d6e3f3' }}>
              <h4 style={{ color: '#0f1729', margin: '0 0 6px', fontSize: 13 }}>Friends & Family Preview Terms</h4>
              <p style={{ color: '#4a5568', fontSize: 12, margin: 0, lineHeight: 1.5 }}>
                By creating your account, you agree to participate in the GoClear Friends & Family Preview, submit feedback about your experience, and acknowledge that this is a preview environment. No real funding or financial services are provided during the free preview.
              </p>
            </div>

            {isFree && (
              <div style={{ background: '#f0fdf4', borderRadius: 8, padding: '10px 14px', marginBottom: 16, border: '1px solid #bbf7d0' }}>
                <p style={{ color: '#166534', fontSize: 12, margin: 0 }}>No payment is required for your Free Friends & Family Preview.</p>
              </div>
            )}

            {!isFree && invitation.testing_level === 'friends_family_one_dollar' && (
              <div style={{ background: '#fffbeb', borderRadius: 8, padding: '10px 14px', marginBottom: 16, border: '1px solid #fde68a' }}>
                <p style={{ color: '#92400e', fontSize: 12, margin: 0 }}>Your $1 pilot access is reserved. Payment testing has not been activated yet.</p>
              </div>
            )}

            <label style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 20, color: '#e2e8f0', fontSize: 12, cursor: 'pointer', lineHeight: 1.5 }}>
              <input type="checkbox" checked={consentAccepted} onChange={(e) => setConsentAccepted(e.target.checked)} style={{ marginTop: 2, flexShrink: 0 }} data-testid="consent-checkbox" />
              I accept the Friends & Family Preview terms and privacy disclosure
            </label>

            {error && <p style={{ color: '#ef4444', fontSize: 13, marginBottom: 16 }}>{error}</p>}

            <button onClick={handleAccept} disabled={accepting} style={{ width: '100%', padding: '14px 24px', background: accepting ? '#6b7280' : 'linear-gradient(135deg, #10b981 0%, #059669 100%)', color: '#fff', borderRadius: 10, border: 'none', cursor: accepting ? 'wait' : 'pointer', fontSize: 15, fontWeight: 600 }} data-testid="accept-invitation-btn">
              {accepting ? 'Creating Account...' : 'Create My Account'}
            </button>
          </div>
        </div>

        <p style={{ color: '#475569', fontSize: 11, textAlign: 'center', marginTop: 16 }}>
          GoClear · Advisory services only
        </p>
      </div>
    </div>
  );
}
