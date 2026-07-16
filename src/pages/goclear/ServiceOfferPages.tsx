import { useEffect, useState } from 'react';
import { ArrowRight, CheckCircle2, LockKeyhole, ShieldCheck } from 'lucide-react';
import { SERVICE_OFFER_CATALOG, SERVICE_OFFER_DISCLAIMERS, formatOfferPrice, getServiceOffer, type ServiceOffer } from '../../config/serviceOfferCatalog';
import { createRevenueCheckout } from '../../lib/revenueActivationClient';
import { loadClientRevenueState } from '../../lib/revenueActivationClient';
import { isSupabaseConfigured, supabase } from '../../lib/supabaseClient';
import { trackEvent } from '../../lib/clientAnalytics';
import './goclear-public.css';

function ServiceHeader({ active = 'pricing' }: { active?: string }) {
  return <header className="gc-header"><div className="gc-container gc-header-inner"><a className="gc-logo" href="/"> <span className="gc-logo-mark">✓</span><span>GoClear</span></a><nav className="gc-nav" aria-label="Service navigation"><a href="/pricing" className={active === 'pricing' ? 'active' : ''}>Pricing</a><a href="/goclear">How It Works</a><a href="/goclear/login">Login</a></nav><a className="gc-btn gc-btn-primary" href="/goclear/signup">Create account</a></div></header>
}

function Disclaimers() {
  return <div className="gc-compliance-note" data-testid="offer-disclaimers"><p>{SERVICE_OFFER_DISCLAIMERS.join(' ')}</p></div>
}

function OfferCard({ offer }: { offer: ServiceOffer }) {
  return <article className="gc-card gc-plan-card" data-testid={`offer-card-${offer.slug}`}><span className="gc-pill">Tier {offer.tier} · one-time service</span><h2>{offer.name}</h2><p>{offer.description}</p><div className="gc-price"><strong>{formatOfferPrice(offer)}</strong><span>one time</span></div><ul className="gc-check-list">{offer.deliverables.map(item => <li key={item}><CheckCircle2 size={16} />{item}</li>)}</ul><a className="gc-btn gc-btn-primary gc-full-btn" href={offer.public_route}>Review service <ArrowRight size={16} /></a><small>Terms {offer.terms_version} · {offer.refund_policy_reference}</small></article>
}

export function ServicePricingPage() {
  return <main className="gc-page" data-testid="service-pricing"><ServiceHeader /><section className="gc-container gc-pricing-hero"><h1>Readiness services with a clear next step</h1><p>Choose the review scope that matches the amount of support you need. Every service is approval-gated, test-mode ready, and free of funding promises.</p></section><section className="gc-container gc-plan-grid">{SERVICE_OFFER_CATALOG.map(offer => <OfferCard offer={offer} key={offer.slug} />)}</section><section className="gc-container gc-card" style={{ marginTop: 28 }}><h2>What you provide</h2><p>Current profile information, relevant reports and documents, answers to the required intake questions, and authorization acknowledgements. Uploads remain protected in the client portal.</p><div className="gc-three-col">{['Credit readiness', 'Business Foundation', 'Bankability and funding preparation'].map(item => <div key={item}><ShieldCheck size={20} /><strong>{item}</strong><p>Review based on information and evidence available at the time.</p></div>)}</div></section><Disclaimers /></main>
}

export function ServiceOfferPage({ slug }: { slug: string }) {
  const offer = getServiceOffer(slug);
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [signedIn, setSignedIn] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  useEffect(() => { let mounted = true; supabase?.auth.getUser().then(({ data }) => mounted && setSignedIn(Boolean(data.user))); return () => { mounted = false } }, []);
  if (!offer) return <main className="gc-page"><ServiceHeader /><section className="gc-container gc-card"><h1>Service not found</h1><a href="/pricing" className="gc-btn gc-btn-primary">View pricing</a></section></main>;
  const checkout = async () => {
    setMessage('');
    if (!signedIn) { window.location.assign(`/goclear/signup?offer=${encodeURIComponent(offer.slug)}`); return; }
    if (!termsAccepted) { setMessage('Please accept the service terms before starting checkout.'); return; }
    setBusy(true);
    const result = await createRevenueCheckout({ offerSlug: offer.slug, termsAccepted: true, termsVersion: offer.terms_version });
    setBusy(false);
    if (!result.ok) { setMessage('Test checkout is not available in this environment. No payment was attempted.'); return; }
    trackEvent({ event: 'revenue_offer_selected', route: offer.public_route, detail: offer.slug });
    if (result.data?.checkout_url) window.location.assign(result.data.checkout_url); else setMessage('Checkout session created in test mode. Awaiting hosted checkout configuration.');
  };
  return <main className="gc-page" data-testid={`service-offer-${offer.slug}`}><ServiceHeader /><section className="gc-container gc-auth-shell"><div className="gc-signup-form"><span className="gc-pill">Tier {offer.tier} · controlled test mode</span><h1>{offer.name}</h1><p>{offer.description}</p><div className="gc-price"><strong>{formatOfferPrice(offer)}</strong><span>one time</span></div><h3>Included</h3><ul className="gc-check-list">{offer.deliverables.map(item => <li key={item}><CheckCircle2 size={16} />{item}</li>)}</ul><h3>What you provide</h3><ul className="gc-check-list">{offer.client_provides.map(item => <li key={item}><CheckCircle2 size={16} />{item}</li>)}</ul><p><LockKeyhole size={16} /> Checkout uses a hosted Stripe test-mode session. Payment details remain with the hosted provider and are never persisted by Nexus.</p><label className="gc-checkbox"><input type="checkbox" checked={termsAccepted} onChange={e => setTermsAccepted(e.target.checked)} /> <span>I accept {offer.terms_version}, the {offer.refund_policy_reference}, and the {offer.privacy_notice_reference}. I understand this is a professional readiness service with no funding or credit outcome guarantee.</span></label>{message && <div className="gc-notice" role="status">{message}</div>}<button className="gc-btn gc-btn-primary gc-full-btn" onClick={checkout} disabled={busy || !isSupabaseConfigured} data-testid="start-test-checkout">{busy ? 'Preparing test checkout…' : signedIn ? 'Start test-mode checkout' : 'Create account to continue'} <ArrowRight size={16} /></button><p className="gc-muted">{signedIn ? 'Payment remains pending until the signed server-side webhook confirms it.' : 'An authenticated client account is required before checkout can begin.'}</p></div><aside className="gc-card"><ShieldCheck size={28} /><h3>Protected review path</h3><p>After verified payment: onboarding → intake → protected documents → readiness analysis → admin review → Ray approval when required → controlled delivery.</p><p>No automatic packet delivery, mail, DocuPost submission, or funding application is created.</p></aside></section><Disclaimers /></main>
}

export function CheckoutStatusPage({ status }: { status: 'success' | 'pending' | 'cancelled' | 'failed' }) {
  const [orderState, setOrderState] = useState<any>(null);
  useEffect(() => { if (status === 'success' || status === 'pending') loadClientRevenueState().then(setOrderState).catch(() => setOrderState({ orders: [] })); }, [status]);
  const orderId = new URLSearchParams(window.location.search).get('order');
  const order = orderState?.orders?.find((item: any) => item.id === orderId || item.order_number === orderId);
  const verified = order?.status === 'paid';
  const copy = status === 'success' && verified ? ['Payment verified', 'The server confirmed your test-mode payment. Your onboarding and fulfillment state are now available in the authenticated portal.'] : status === 'success' ? ['Payment verification in progress', 'This page reads persisted order state. A return URL or query string alone never marks an order paid.'] : status === 'pending' ? ['Payment pending', 'The hosted checkout returned, but the server has not confirmed payment yet.'] : status === 'cancelled' ? ['Checkout cancelled', 'No fulfillment was started. You can return to pricing when ready.'] : ['Payment not verified', 'No client access or fulfillment is activated until a verified payment succeeds.'];
  return <main className="gc-page" data-testid={`checkout-${status}`}><ServiceHeader /><section className="gc-container gc-card" style={{ maxWidth: 760, margin: '80px auto' }}><span className="gc-pill">TEST MODE</span><h1>{copy[0]}</h1><p>{copy[1]}</p>{order && <p><strong>Order {order.order_number}</strong> · {order.service_offers?.name || 'Readiness service'} · fulfillment {(order.fulfillment_status || 'not_started').replaceAll('_', ' ')}</p>}<p>Next: sign in to the client portal to see the verified payment state, onboarding tasks, required documents, and current fulfillment stage.</p><a className="gc-btn gc-btn-primary" href="/client">Open client portal</a><a className="gc-btn gc-btn-secondary" href="/pricing">View services</a></section></main>
}
