import { useEffect, useState } from 'react';
import { validateInviteToken, type ValidatedInvitation } from '../../lib/testerInvitationClient';

const TESTING_LEVEL_LABELS: Record<string, string> = {
  synthetic_internal: 'Synthetic Internal Testing',
  invited_test_mode: 'Invited Stripe Test Mode',
  controlled_live_pilot: 'Controlled $1 Live Pilot',
};

export default function TesterInvitePage() {
  const [token, setToken] = useState('');
  const [invitation, setInvitation] = useState<ValidatedInvitation | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [validated, setValidated] = useState(false);

  useEffect(() => {
    const hash = window.location.hash;
    const parts = hash.split('/');
    const lastPart = parts[parts.length - 1];
    if (lastPart && lastPart.length > 10) {
      setToken(lastPart);
    }
  }, []);

  const handleValidate = async () => {
    if (!token) { setError('Please enter your invitation token.'); return; }
    setLoading(true);
    setError('');
    try {
      const result = await validateInviteToken(token);
      if (!result.ok) { setError(result.error || 'Invalid invitation.'); setLoading(false); return; }
      setInvitation(result.data.invitation);
      setValidated(true);
    } catch {
      setError('Failed to validate invitation.');
    }
    setLoading(false);
  };

  if (validated && invitation) {
    const expiresAt = new Date(invitation.expires_at);
    const isExpired = expiresAt < new Date();
    return (
      <div className="nxos-stack" style={{ maxWidth: 600, margin: '40px auto', padding: '0 20px' }} data-testid="tester-invite-validated">
        <div className="nxos-callout" style={{ borderLeft: '4px solid #10b981' }}>
          <strong>Invitation Validated</strong>
          <p>You have a valid tester invitation. Please proceed to accept and set up your account.</p>
        </div>
        <section className="nxos-table-card">
          <h2>Invitation Details</h2>
          <div style={{ display: 'grid', gap: 8 }}>
            <div><strong>Name:</strong> {invitation.tester_name}</div>
            <div><strong>Testing Level:</strong> {TESTING_LEVEL_LABELS[invitation.testing_level] || invitation.testing_level}</div>
            <div><strong>Expires:</strong> {expiresAt.toLocaleDateString()} {expiresAt.toLocaleTimeString()}</div>
            {invitation.assigned_persona && <div><strong>Assigned Persona:</strong> {invitation.assigned_persona.toUpperCase()}</div>}
            {invitation.payment_offer_slug && <div><strong>Payment Offer:</strong> {invitation.payment_offer_slug}</div>}
            <div><strong>Payment Mode:</strong> {invitation.payment_mode === 'test' ? 'Stripe Test Mode (no real charge)' : invitation.payment_mode}</div>
          </div>
        </section>
        {isExpired ? (
          <div className="nxos-callout" style={{ borderLeft: '4px solid #ef4444' }}>
            <strong>This invitation has expired.</strong>
            <p>Please contact the administrator for a new invitation.</p>
          </div>
        ) : (
          <a href={`/tester/accept?token=${token}`} className="nxos-button" style={{ display: 'inline-block', textAlign: 'center', padding: '10px 20px', background: '#10b981', color: '#fff', borderRadius: 8, textDecoration: 'none' }}>
            Accept Invitation & Set Password
          </a>
        )}
      </div>
    );
  }

  return (
    <div className="nxos-stack" style={{ maxWidth: 500, margin: '60px auto', padding: '0 20px' }} data-testid="tester-invite-page">
      <h1 style={{ color: '#f8fafc', fontSize: 24 }}>Tester Invitation</h1>
      <p style={{ color: '#94a3b8' }}>Enter your invitation token to proceed. You should have received this via email.</p>
      <div style={{ display: 'flex', gap: 8 }}>
        <input
          type="text"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          placeholder="Paste your invitation token"
          style={{ flex: 1, padding: '10px 14px', borderRadius: 8, border: '1px solid #334155', background: '#1e293b', color: '#f8fafc', fontSize: 14 }}
          data-testid="invite-token-input"
        />
        <button onClick={handleValidate} disabled={loading} className="nxos-button" style={{ padding: '10px 20px', background: '#3b82f6', color: '#fff', borderRadius: 8, border: 'none', cursor: loading ? 'wait' : 'pointer' }} data-testid="invite-validate-btn">
          {loading ? 'Validating...' : 'Validate'}
        </button>
      </div>
      {error && <p style={{ color: '#ef4444', fontSize: 13 }} data-testid="invite-error">{error}</p>}
      <div className="nxos-callout" style={{ marginTop: 20 }}>
        <strong>Synthetic Test Data Notice</strong>
        <p>This is a controlled testing environment. No real funding, credit, or financial services are being provided. Your participation helps us verify system functionality.</p>
      </div>
    </div>
  );
}
