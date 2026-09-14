import React, { useEffect, useState } from 'react';
import { ArrowLeft, CheckCircle2, LockKeyhole, ShieldCheck } from 'lucide-react';
import { useSession } from '../../components/auth';
import { supabase } from '../../lib/supabaseClient';
import './nexus-social.css';

const appName = 'Nexus Social Publisher';

function Header() {
  return (
    <header className="ns-header">
      <a className="ns-brand" href="/nexus-social" aria-label={`${appName} home`}>
        <span className="ns-mark" aria-hidden="true">N</span>
        <span>{appName}</span>
      </a>
      <nav aria-label="Public app navigation">
        <a href="/nexus-social/terms">Terms</a>
        <a href="/nexus-social/privacy">Privacy</a>
      </nav>
    </header>
  );
}

function Shell({ children, title }: { children: React.ReactNode; title: string }) {
  return <div className="ns-page"><Header /><main className="ns-main" aria-labelledby="ns-title"><p className="ns-eyebrow">NEXUS SOCIAL PUBLISHER</p><h1 id="ns-title">{title}</h1>{children}</main><footer className="ns-footer"><span>© {new Date().getFullYear()} Nexus Social Publisher</span><span><a href="/nexus-social/terms">Terms</a> · <a href="/nexus-social/privacy">Privacy</a></span></footer></div>;
}

function Home() {
  const { user, loading: authLoading } = useSession();
  const [membership, setMembership] = useState<'checking' | 'present' | 'missing' | 'error'>('checking');
  const [connection, setConnection] = useState<'idle' | 'starting' | 'unavailable'>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [tiktokConnection, setTiktokConnection] = useState<any>(null);
  const [canary, setCanary] = useState<'idle' | 'running' | 'complete' | 'failed'>('idle');
  const [canaryResult, setCanaryResult] = useState<any>(null);
  useEffect(() => {
    let active = true;
    if (authLoading) { setMembership('checking'); return () => { active = false; }; }
    if (!user || !supabase) { setMembership('missing'); return () => { active = false; }; }
    setMembership('checking');
    supabase.from('tenant_memberships').select('tenant_id,role').eq('user_id', user.id).limit(1).then(({ data, error }) => {
      if (!active) return;
      setMembership(error ? 'error' : data?.length ? 'present' : 'missing');
    });
    return () => { active = false; };
  }, [authLoading, user]);
  useEffect(() => {
    let active = true;
    if (!user || membership !== 'present' || !supabase) { setTiktokConnection(null); return () => { active = false; }; }
    supabase.auth.getSession().then(({ data }) => {
      const token = data.session?.access_token;
      if (!token) return;
      fetch('/.netlify/functions/tiktok-connection-status', { headers: { Authorization: `Bearer ${token}` } })
        .then((response) => response.json())
        .then((body) => { if (active && body.connected) setTiktokConnection(body.connection); })
        .catch(() => undefined);
    });
    return () => { active = false; };
  }, [membership, user]);
  async function connectTikTok() {
    setConnection('starting');
    setErrorMessage('');
    try {
      if (authLoading) { setConnection('idle'); return; }
      if (!user || !supabase) { window.location.assign('/goclear/login?returnTo=%2Fnexus-social'); return; }
      if (membership !== 'present') { setConnection('unavailable'); setErrorMessage('An authorized Nexus workspace membership is required before connecting TikTok.'); return; }
      const session = await supabase.auth.getSession();
      const token = session?.data.session?.access_token;
      if (!token) { window.location.assign('/goclear/login?returnTo=%2Fnexus-social'); return; }
      const response = await fetch('/.netlify/functions/tiktok-auth-start', { headers: { Authorization: `Bearer ${token}` } });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || !data.authorization_url) {
        if (data.error === 'authenticated_nexus_session_required') { window.location.assign('/goclear/login?returnTo=%2Fnexus-social'); return; }
        if (data.error === 'tenant_membership_required' || data.error === 'tenant_binding_required') throw new Error('Your Nexus account needs an authorized workspace membership before connecting TikTok.');
        throw new Error(data.error?.startsWith('server_configuration_missing') ? 'TikTok integration is temporarily unavailable. Please try again later.' : 'Unable to start TikTok authorization.');
      }
      window.location.assign(data.authorization_url);
    } catch (error) { setConnection('unavailable'); setErrorMessage(error instanceof Error ? error.message : 'Unable to start TikTok authorization.'); }
  }
  async function runSandboxCanary() {
    if (!supabase || !user || !tiktokConnection) return;
    setCanary('running'); setCanaryResult(null); setErrorMessage('');
    try {
      const session = await supabase.auth.getSession();
      const token = session.data.session?.access_token;
      if (!token) throw new Error('Your Nexus session expired. Sign in again to run the canary.');
      const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
      const creatorResponse = await fetch('/.netlify/functions/tiktok-creator-info', { method: 'POST', headers });
      const creator = await creatorResponse.json().catch(() => ({}));
      if (!creatorResponse.ok) throw new Error('Creator information could not be verified.');
      const videoUrl = `${window.location.origin}/creative-r20a/final/goclear-funding-readiness-r20a.mp4`;
      const draftResponse = await fetch('/.netlify/functions/tiktok-post-init', { method: 'POST', headers, body: JSON.stringify({ mode: 'draft', video_url: videoUrl }) });
      const draft = await draftResponse.json().catch(() => ({}));
      if (!draftResponse.ok || !draft.publish_id) throw new Error('Sandbox draft upload was not accepted.');
      const pollStatus = async (publishId: string) => {
        let latest: any = {};
        for (let attempt = 0; attempt < 6; attempt += 1) {
          const response = await fetch(`/.netlify/functions/tiktok-post-status?publish_id=${encodeURIComponent(publishId)}`, { headers: { Authorization: `Bearer ${token}` } });
          latest = await response.json().catch(() => ({}));
          if (!response.ok || ['PUBLISH_COMPLETE', 'FAILED', 'CANCELED', 'SEND_TO_USER_INBOX'].includes(latest.status)) break;
          if (attempt < 5) await new Promise((resolve) => window.setTimeout(resolve, 1500));
        }
        return latest;
      };
      const draftStatus = await pollStatus(draft.publish_id);
      const directResponse = await fetch('/.netlify/functions/tiktok-post-init', { method: 'POST', headers, body: JSON.stringify({ mode: 'direct', approval_id: 'sandbox-canary-ui', privacy_level: 'SELF_ONLY', title: 'Nexus Social Publisher Sandbox Canary', video_url: videoUrl }) });
      const direct = await directResponse.json().catch(() => ({}));
      if (!directResponse.ok || !direct.publish_id) throw new Error('Sandbox private Direct Post was not accepted.');
      const status = await pollStatus(direct.publish_id);
      setCanaryResult({ creator: creator.creator_info || {}, draft: { publish_id: draft.publish_id, status: draftStatus.status || 'UNKNOWN' }, direct: { publish_id: direct.publish_id, privacy: 'SELF_ONLY', status: status.status || 'UNKNOWN' } });
      setCanary('complete');
    } catch (error) { setCanary('failed'); setErrorMessage(error instanceof Error ? error.message : 'Sandbox canary failed.'); }
  }
  const status = authLoading ? 'Checking your Nexus session…' : user && membership === 'checking' ? 'Checking your Nexus workspace access…' : user && membership === 'present' ? `Signed in${user.email ? ` as ${user.email}` : ''}` : user ? 'Your Nexus account needs an authorized workspace membership before connecting TikTok.' : 'Sign in to Nexus to connect an authorized TikTok account.';
  return <Shell title="Social publishing with permission at the center.">
    <p className="ns-lede">Nexus Social Publisher helps businesses create, review, manage, and publish approved social content to accounts they have explicitly authorized.</p>
    <div className="ns-actions"><a className="ns-button" href="#how-it-works">Learn how it works</a>{!authLoading && !user ? <a className="ns-button" href="/goclear/login?returnTo=%2Fnexus-social">Sign in to Nexus</a> : <button className="ns-button" type="button" onClick={connectTikTok} disabled={authLoading || membership === 'checking' || connection === 'starting' || membership !== 'present'}>{connection === 'starting' ? 'Connecting…' : 'Connect TikTok'}</button>}<a className="ns-text-link" href="/nexus-social/privacy">Read our privacy policy <span aria-hidden="true">→</span></a></div>
    <p className="ns-note" role="status">{errorMessage || status} {connection === 'unavailable' && !errorMessage ? 'No token or account data was stored.' : ''}</p>
    {tiktokConnection && <section className="ns-note" aria-labelledby="ns-tiktok-status"><h2 id="ns-tiktok-status">TikTok connected</h2><p>Environment: <strong>Sandbox</strong></p><p>Granted scopes: {tiktokConnection.scopes?.join(', ') || 'Recorded'}</p><button className="ns-button" type="button" onClick={runSandboxCanary} disabled={canary === 'running'}>{canary === 'running' ? 'Running Sandbox Canary…' : 'Run TikTok Sandbox Canary'}</button>{canaryResult && <div className="ns-canary-results" role="status"><p>Creator info: PASS</p><p>Draft upload: PASS · {canaryResult.draft.status}</p><p>Private Direct Post: PASS · SELF_ONLY</p><p>Status polling: PASS · {canaryResult.direct.status}</p><p>Environment: Sandbox · Visibility: SELF_ONLY</p></div>}{canary === 'failed' && <p role="alert">The Sandbox canary did not complete. No public post was attempted.</p>}</section>}
    <section id="how-it-works" className="ns-grid" aria-label="How Nexus Social Publisher works">
      <article><CheckCircle2 aria-hidden="true" /><h2>Create and review</h2><p>Teams prepare content and review it before it moves toward publication.</p></article>
      <article><LockKeyhole aria-hidden="true" /><h2>Connect authorized accounts</h2><p>Users connect only accounts they control or are authorized to manage. Nexus does not publish to unauthorized accounts.</p></article>
      <article><ShieldCheck aria-hidden="true" /><h2>Stay in control</h2><p>Platform permissions and workflow approvals govern publishing. You can disconnect or revoke access through the relevant platform controls.</p></article>
    </section>
    <section className="ns-note"><h2>Capability status</h2><p>Available features depend on the connected platform, granted permissions, and configured workflow. Public posting may require explicit approval. TikTok Content Posting API access is not represented as approved or active here.</p></section>
  </Shell>;
}

function LegalPage({ privacy = false }: { privacy?: boolean }) {
  const title = privacy ? 'Privacy Policy' : 'Terms of Service';
  return <Shell title={title}>
    <p className="ns-updated">Effective date: September 13, 2026</p>
    {privacy ? <PrivacyContent /> : <TermsContent />}
  </Shell>;
}

function TermsContent() { return <div className="ns-legal"><p>These terms describe use of {appName}, a software service operated by the Nexus OS project. No separate legal entity name is asserted on this page.</p><h2>Service description</h2><p>The service provides tools for preparing, reviewing, organizing, and—where supported and authorized—publishing social content. Features vary by platform and account configuration.</p><h2>Authorized accounts and responsibilities</h2><p>You may connect only accounts you own or are authorized to manage. You are responsible for your credentials, content, permissions, platform compliance, and all instructions submitted through your account.</p><h2>Acceptable use</h2><p>Do not use the service for unlawful, deceptive, abusive, infringing, unauthorized, or platform-prohibited activity. Do not attempt to bypass approval, permission, security, or tenant boundaries.</p><h2>Platform and third-party dependencies</h2><p>Social platforms and other third-party services control their own APIs, permissions, availability, policies, and review processes. Their terms apply to your use of those services.</p><h2>Content and publication</h2><p>You retain responsibility for content you provide and for confirming that it is accurate, lawful, and appropriate. Nexus does not promise that a platform will accept, deliver, display, or preserve any content.</p><h2>Availability and changes</h2><p>Features may change, be limited, or become unavailable. We may update these terms as the service evolves. Continued use after an update means the updated terms apply.</p><h2>Revocation and termination</h2><p>You may disconnect or revoke platform access using available account or platform controls. Access may be suspended or terminated for misuse, security concerns, or violation of these terms.</p><h2>Disclaimers and limitation of liability</h2><p>The service is provided as available. To the extent permitted by law, Nexus disclaims warranties and is not liable for indirect, incidental, special, consequential, or platform-caused losses.</p><h2>Contact</h2><p>For service or privacy questions, use the contact channel provided with your Nexus OS account or deployment. A dedicated public legal-entity contact is not currently configured.</p></div>; }

function PrivacyContent() { return <div className="ns-legal"><p>This policy explains the information {appName} may process when you use the service. It is written for the current foundation and does not claim collection beyond configured features.</p><h2>Information you provide</h2><p>This may include account details, workspace identifiers, content drafts, approvals, and support messages that you submit. The exact fields depend on the enabled workflow.</p><h2>Connected-platform data</h2><p>When you authorize a platform, the service may process account or profile identifiers, permission metadata, social-content metadata, publishing results, and status information needed for the requested workflow. Access tokens are handled as protected credentials and are not displayed in this page.</p><h2>How information is used</h2><p>Information is used to provide requested publishing workflows, enforce permissions and approvals, show status, troubleshoot failures, maintain security, and produce audit records.</p><h2>Sharing and third parties</h2><p>Data may be exchanged with a platform only as needed for an authorized integration. Platform providers process data under their own policies. Nexus does not sell personal information.</p><h2>Retention and deletion</h2><p>Retention periods are governed by the applicable Nexus policy and workflow configuration. A single universal duration is not asserted here. You may disconnect or revoke platform access; deletion requests should use the configured Nexus support channel.</p><h2>Security</h2><p>Nexus uses access controls, scoped permissions, tenant boundaries, and auditability appropriate to the configured workflow. No online service can guarantee absolute security.</p><h2>Your choices</h2><p>You may choose whether to connect an account, review or approve content where supported, disconnect access, and request help with account data. Revoking access may not delete data already retained by the platform provider.</p><h2>Policy updates and contact</h2><p>This policy may change as integrations evolve. For privacy questions, use the contact channel provided with your Nexus OS account or deployment. A dedicated public legal-entity contact is not currently configured.</p></div>; }

function Callback() {
  const [message, setMessage] = useState('Completing authorization…');
  useEffect(() => { (async () => { try { const session = await import('../../lib/supabaseClient').then(({ supabase }) => supabase?.auth.getSession()); const token = session?.data.session?.access_token; if (!token) throw new Error('Sign in to Nexus before connecting TikTok.'); const response = await fetch(`/.netlify/functions/tiktok-oauth-callback${window.location.search}`, { headers: { Authorization: `Bearer ${token}` } }); const data = await response.json(); if (!response.ok || !data.connected) throw new Error(data.error || 'TikTok authorization could not be completed.'); setMessage(`Connected account: ${data.account?.display_name || 'authorized creator'} · ${data.scopes?.join(', ') || 'scopes recorded'}`); } catch (error) { setMessage(error instanceof Error ? error.message : 'TikTok authorization could not be completed.'); } })(); }, []);
  return <Shell title="TikTok authorization"><p className="ns-lede" role="status">{message}</p><a className="ns-text-link" href="/nexus-social"><ArrowLeft aria-hidden="true" /> Return to Nexus Social Publisher</a></Shell>;
}

export default function NexusSocialPublisher({ path }: { path: string }) {
  if (path === '/nexus-social/terms') return <LegalPage />;
  if (path === '/nexus-social/privacy') return <LegalPage privacy />;
  if (path === '/nexus-social/oauth/tiktok/callback') return <Callback />;
  return <Home />;
}
