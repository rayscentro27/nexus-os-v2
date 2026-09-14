import { FormEvent, useMemo, useState } from 'react';
import { acceptGuestInvitation } from '../../lib/testerInvitationClient';
import { FREE_GUEST_ACCESS } from '../../lib/guestAccessPolicy';
import '../goclear/goclear-public.css';

export default function GuestAcceptPage() {
  const token = useMemo(() => new URLSearchParams(window.location.search).get('token') || '', []);
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!token || password.length < 8 || !consent || busy) return;
    setBusy(true); setMessage('');
    const result = await acceptGuestInvitation({ token, password, consentAccepted: consent, name });
    setBusy(false);
    if (!result.ok) { setMessage(result.error || 'This invitation could not be activated.'); return; }
    setMessage('Your free guest access is active. Sign in to continue onboarding and readiness preparation.');
  }
  return <main className="gc-page"><section className="gc-container gc-auth-shell"><form className="gc-signup-form" onSubmit={submit} data-testid="guest-accept-form"><span className="gc-pill">FREE GUEST ACCESS</span><h1>Activate your GoClear invitation</h1><p>Explore onboarding and readiness preparation at no charge. Paid funding execution remains behind a payment or service-agreement gate.</p><label>Name<input value={name} onChange={e => setName(e.target.value)} autoComplete="name" required /></label><label>Create password<input type="password" value={password} onChange={e => setPassword(e.target.value)} minLength={8} autoComplete="new-password" required /></label><label className="gc-checkbox"><input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} /> <span>I accept the GoClear terms and privacy notice.</span></label>{message && <div className="gc-notice" role="status">{message}</div>}<button className="gc-btn gc-btn-primary gc-full-btn" disabled={!token || password.length < 8 || !consent || busy}>{busy ? 'Activating…' : 'Activate free access'}</button><small>{FREE_GUEST_ACCESS.accessTier} · {FREE_GUEST_ACCESS.paymentBypassScope}</small></form></section></main>;
}
