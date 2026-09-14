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
  async function connectTikTok() {
    setConnection('starting');
    try {
      if (authLoading) { setConnection('idle'); return; }
      if (!user || !supabase) { window.location.assign('/goclear/login?returnTo=%2Fnexus-social'); return; }
      if (membership !== 'present') { setConnection('unavailable'); return; }
      const session = await supabase.auth.getSession();
      const token = session?.data.session?.access_token;
      if (!token) { window.location.assign('/goclear/login?returnTo=%2Fnexus-social'); return; }
      const response = await fetch('/api/tiktok/auth/start', { headers: { Authorization: `Bearer ${token}` } });
      const data = await response.json();
      if (!response.ok || !data.authorization_url) throw new Error('TikTok authorization is unavailable');
      window.location.assign(data.authorization_url);
    } catch { setConnection('unavailable'); }
  }
  const status = authLoading ? 'Checking your Nexus session…' : user && membership === 'checking' ? 'Checking your Nexus workspace access…' : user && membership === 'present' ? `Signed in${user.email ? ` as ${user.email}` : ''}` : user ? 'Your Nexus account needs an authorized workspace membership before connecting TikTok.' : 'Sign in to Nexus to connect an authorized TikTok account.';
  return <Shell title="Social publishing with permission at the center.">
    <p className="ns-lede">Nexus Social Publisher helps businesses create, review, manage, and publish approved social content to accounts they have explicitly authorized.</p>
    <div className="ns-actions"><a className="ns-button" href="#how-it-works">Learn how it works</a>{!authLoading && !user ? <a className="ns-button" href="/goclear/login?returnTo=%2Fnexus-social">Sign in to Nexus</a> : <button className="ns-button" type="button" onClick={connectTikTok} disabled={authLoading || membership === 'checking' || connection === 'starting' || membership !== 'present'}>{connection === 'starting' ? 'Connecting…' : 'Connect TikTok'}</button>}<a className="ns-text-link" href="/nexus-social/privacy">Read our privacy policy <span aria-hidden="true">→</span></a></div>
    <p className="ns-note" role="status">{status} {connection === 'unavailable' && membership !== 'present' ? 'No token or account data was stored.' : ''}</p>
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
