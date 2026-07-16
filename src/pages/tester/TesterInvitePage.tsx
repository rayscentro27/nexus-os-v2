import { useEffect, useState } from 'react';
import { validateInviteToken, type ValidatedInvitation } from '../../lib/testerInvitationClient';
import { buildCustomerUrl } from '../../lib/canonicalDomain';

const TYPE_LABELS: Record<string, string> = {
  friends_family_free: 'Free Friends & Family Preview',
  friends_family_one_dollar: '$1 Friends & Family Pilot',
  invited_test_mode: 'Invited Preview',
  synthetic_internal: 'Internal Testing',
  controlled_live_pilot: 'Controlled Pilot',
};

export default function TesterInvitePage() {
  const [invitation, setInvitation] = useState<ValidatedInvitation | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<'loading' | 'valid' | 'error' | 'expired' | 'revoked' | 'used'>('loading');

  useEffect(() => {
    const extractToken = (): string | null => {
      const path = window.location.pathname;
      const parts = path.split('/').filter(Boolean);
      const inviteIdx = parts.indexOf('invite');
      if (inviteIdx !== -1 && inviteIdx + 1 < parts.length) {
        return parts[inviteIdx + 1];
      }
      const params = new URLSearchParams(window.location.search);
      return params.get('token');
    };

    const token = extractToken();
    if (!token || token.length < 10) {
      setStatus('error');
      setError('This invitation link appears to be invalid. Please check the link from your email.');
      setLoading(false);
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        const result = await validateInviteToken(token);
        if (cancelled) return;
        if (!result.ok) {
          const errCode = result.error || '';
          if (errCode.includes('expired')) {
            setStatus('expired');
            setError('This invitation has expired. Please contact Ray for a new invitation.');
          } else if (errCode.includes('revoked')) {
            setStatus('revoked');
            setError('This invitation is no longer available. Please contact Ray for assistance.');
          } else if (errCode.includes('already_accepted') || errCode.includes('completed')) {
            setStatus('used');
            setError('This invitation has already been used. Please sign in with your existing account.');
          } else {
            setStatus('error');
            setError('This invitation link is not valid. Please check the link from your email or contact Ray.');
          }
        } else {
          setInvitation(result.data.invitation);
          setStatus('valid');
        }
      } catch {
        if (!cancelled) {
          setStatus('error');
          setError('Unable to verify your invitation. Please try again or contact Ray.');
        }
      }
      if (!cancelled) setLoading(false);
    })();

    return () => { cancelled = true; };
  }, []);

  if (loading || status === 'loading') {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #0f1729 0%, #1a2744 50%, #0f1729 100%)' }}>
        <div style={{ textAlign: 'center', color: '#e2e8f0' }}>
          <div style={{ width: 48, height: 48, border: '3px solid #334155', borderTopColor: '#3b82f6', borderRadius: '50%', margin: '0 auto 16px', animation: 'spin 1s linear infinite' }} />
          <p style={{ fontSize: 16, color: '#94a3b8' }}>Verifying your invitation...</p>
        </div>
      </div>
    );
  }

  if (status === 'error' || status === 'expired' || status === 'revoked') {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #0f1729 0%, #1a2744 50%, #0f1729 100%)' }}>
        <div style={{ maxWidth: 480, padding: '40px 32px', background: '#1e293b', borderRadius: 16, border: '1px solid #334155', textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>
            {status === 'expired' ? '⏰' : status === 'revoked' ? '🚫' : '❌'}
          </div>
          <h1 style={{ color: '#f8fafc', fontSize: 22, margin: '0 0 12px' }}>
            {status === 'expired' ? 'Invitation Expired' : status === 'revoked' ? 'Invitation Unavailable' : 'Invalid Invitation'}
          </h1>
          <p style={{ color: '#94a3b8', fontSize: 14, lineHeight: 1.6, margin: '0 0 24px' }}>{error}</p>
          <a href="/" style={{ display: 'inline-block', padding: '10px 24px', background: '#3b82f6', color: '#fff', borderRadius: 8, textDecoration: 'none', fontWeight: 600 }}>
            Go to GoClear
          </a>
        </div>
      </div>
    );
  }

  if (status === 'used') {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #0f1729 0%, #1a2744 50%, #0f1729 100%)' }}>
        <div style={{ maxWidth: 480, padding: '40px 32px', background: '#1e293b', borderRadius: 16, border: '1px solid #334155', textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>✅</div>
          <h1 style={{ color: '#f8fafc', fontSize: 22, margin: '0 0 12px' }}>Account Already Created</h1>
          <p style={{ color: '#94a3b8', fontSize: 14, lineHeight: 1.6, margin: '0 0 24px' }}>{error}</p>
          <a href="/goclear/login" style={{ display: 'inline-block', padding: '10px 24px', background: '#10b981', color: '#fff', borderRadius: 8, textDecoration: 'none', fontWeight: 600 }}>
            Sign In to GoClear
          </a>
        </div>
      </div>
    );
  }

  const expiresAt = new Date(invitation!.expires_at);
  const isExpired = expiresAt < new Date();
  const typeName = TYPE_LABELS[invitation!.testing_level] || 'Friends & Family Preview';
  const isFree = invitation!.testing_level === 'friends_family_free' || invitation!.testing_level === 'invited_test_mode';
  const acceptanceUrl = buildCustomerUrl(`/invite/accept?token=${encodeURIComponent(window.location.pathname.split('/').filter(Boolean).pop() || new URLSearchParams(window.location.search).get('token') || '')}`);

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #0f1729 0%, #1a2744 50%, #0f1729 100%)' }}>
      <div style={{ maxWidth: 560, width: '100%', padding: '0 20px' }}>
        <div style={{ background: '#1e293b', borderRadius: 16, border: '1px solid #334155', overflow: 'hidden' }}>
          <div style={{ background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)', padding: '32px 32px 24px', textAlign: 'center' }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: 'rgba(255,255,255,0.8)', letterSpacing: 1, textTransform: 'uppercase', marginBottom: 8 }}>
              GoClear Friends & Family
            </div>
            <h1 style={{ color: '#ffffff', fontSize: 24, margin: 0, fontWeight: 700 }}>
              Welcome to GoClear
            </h1>
          </div>

          <div style={{ padding: '28px 32px' }}>
            <p style={{ color: '#e2e8f0', fontSize: 15, lineHeight: 1.7, margin: '0 0 20px' }}>
              Ray personally invited you to experience GoClear before its public release.
            </p>
            <p style={{ color: '#94a3b8', fontSize: 14, lineHeight: 1.6, margin: '0 0 20px' }}>
              GoClear is designed to help you understand your credit, organize important documents, strengthen your financial and business foundation, and prepare for future funding opportunities.
            </p>
            <p style={{ color: '#94a3b8', fontSize: 14, lineHeight: 1.6, margin: '0 0 24px' }}>
              Your feedback will help shape the experience for future GoClear clients.
            </p>

            <div style={{ background: '#0f172a', borderRadius: 10, padding: '16px 20px', marginBottom: 24, border: '1px solid #1e293b' }}>
              <div style={{ display: 'grid', gap: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#94a3b8', fontSize: 13 }}>Name</span>
                  <span style={{ color: '#e2e8f0', fontSize: 13, fontWeight: 500 }}>{invitation!.tester_name}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#94a3b8', fontSize: 13 }}>Invitation Type</span>
                  <span style={{ color: '#10b981', fontSize: 13, fontWeight: 500 }}>{typeName}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#94a3b8', fontSize: 13 }}>Expires</span>
                  <span style={{ color: '#e2e8f0', fontSize: 13 }}>{expiresAt.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}</span>
                </div>
                {isFree && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#94a3b8', fontSize: 13 }}>Payment</span>
                    <span style={{ color: '#10b981', fontSize: 13, fontWeight: 500 }}>No charge — Free Preview</span>
                  </div>
                )}
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#94a3b8', fontSize: 13 }}>Expected Time</span>
                  <span style={{ color: '#e2e8f0', fontSize: 13 }}>30-60 minutes</span>
                </div>
              </div>
            </div>

            <div style={{ background: '#f0fdf4', borderRadius: 8, padding: '12px 16px', marginBottom: 24, border: '1px solid #bbf7d0' }}>
              <p style={{ color: '#166534', fontSize: 13, margin: 0, lineHeight: 1.5 }}>
                During your preview, you'll explore a guided credit-improvement journey, review funding-readiness tools, upload documents, receive guidance from Clyde, and share feedback — all at no charge.
              </p>
            </div>

            {isExpired ? (
              <div style={{ background: '#fef2f2', borderRadius: 8, padding: '12px 16px', marginBottom: 20, border: '1px solid #fecaca' }}>
                <p style={{ color: '#991b1b', fontSize: 13, margin: 0 }}>This invitation has expired. Please contact Ray for a new invitation.</p>
              </div>
            ) : (
              <a href={acceptanceUrl} style={{ display: 'block', textAlign: 'center', padding: '14px 24px', background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)', color: '#fff', borderRadius: 10, textDecoration: 'none', fontWeight: 600, fontSize: 16 }} data-testid="accept-invitation-btn">
                Create My Account
              </a>
            )}

            <p style={{ color: '#64748b', fontSize: 12, textAlign: 'center', marginTop: 16, lineHeight: 1.5 }}>
              This personal invitation is intended only for you. Your feedback helps us build a better experience.
            </p>
          </div>
        </div>

        <p style={{ color: '#475569', fontSize: 11, textAlign: 'center', marginTop: 16 }}>
          GoClear · Advisory services only
        </p>
      </div>
    </div>
  );
}
