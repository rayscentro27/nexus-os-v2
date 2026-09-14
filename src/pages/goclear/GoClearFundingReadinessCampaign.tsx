import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, CheckCircle2, ClipboardCheck, FileText, ShieldCheck, Sparkles } from 'lucide-react';
import { trackEvent } from '../../lib/clientAnalytics';
import './goclear-public.css';

const CAMPAIGN_ID = 'goclear-funding-readiness-r20b';
const RESTAURANT_CAMPAIGN_ID = 'goclear-restaurant-expansion-r20d';
type Variant = 'A' | 'B';

function readVariant(): Variant {
  const requested = new URLSearchParams(window.location.search).get('variant')?.toUpperCase();
  return requested === 'B' ? 'B' : 'A';
}

function readCampaign() {
  return new URLSearchParams(window.location.search).get('campaign_id') === RESTAURANT_CAMPAIGN_ID ? RESTAURANT_CAMPAIGN_ID : CAMPAIGN_ID;
}

function attribution(variant: Variant) {
  const value = { campaign_id: CAMPAIGN_ID, variant, entered_at: new Date().toISOString() };
  try { sessionStorage.setItem('goclear-r20b-attribution', JSON.stringify(value)); } catch {}
  return value;
}

export default function GoClearFundingReadinessCampaign() {
  const [campaignId] = useState(() => readCampaign());
  const restaurantCampaign = campaignId === RESTAURANT_CAMPAIGN_ID;
  const [variant, setVariant] = useState<Variant>(() => readVariant());
  const offer = useMemo(() => variant === 'B' ? {
    label: '$97 readiness review + future-service credit',
    detail: 'Pay $97 for the same readiness review. If you later choose a qualifying GoClear service, the $97 is credited once toward that service under its written terms.'
  } : {
    label: '$97 one-time readiness review',
    detail: 'Pay $97 for a focused review of your current readiness, documentation gaps, and practical next steps.'
  }, [variant]);

  useEffect(() => {
    attribution(variant);
    trackEvent({ event: 'LANDING_PAGE_VIEW', route: '/funding-readiness', detail: `${campaignId}:${variant}` });
  }, [campaignId, variant]);

  function chooseVariant(next: Variant) {
    setVariant(next);
    const url = new URL(window.location.href);
    url.searchParams.set('variant', next);
    window.history.replaceState({}, '', url);
  }

  function ctaHref() {
    return `/readiness-review?campaign_id=${campaignId}&variant=${variant}`;
  }

  function onCtaClick() {
    trackEvent({ event: 'PRIMARY_CTA_CLICK', route: '/funding-readiness', detail: `${campaignId}:${variant}` });
    attribution(variant);
  }

  return <main className="gc-page r20b-page" data-testid="r20b-campaign" data-variant={variant}>
    <header className="gc-header"><div className="gc-container gc-header-inner"><a className="gc-logo" href="/"><span className="gc-logo-mark">✓</span><span>GoClear</span></a><nav className="gc-nav" aria-label="Campaign navigation"><a href="#review">The review</a><a href="#how-it-works">How it works</a><a href="#faq">FAQ</a></nav><a className="gc-btn gc-btn-secondary" href="/goclear/login">Client login</a></div></header>

    <section className="r20b-hero"><div className="gc-container r20b-hero-grid"><div><span className="r20b-kicker">{restaurantCampaign ? 'GOCLEAR · RESTAURANT EXPANSION' : 'GOCLEAR · FUNDING READINESS'}</span><h1>{restaurantCampaign ? 'You have customers. Are you ready for your own restaurant?' : 'Know what to prepare before you apply.'}</h1><p className="r20b-lede">{restaurantCampaign ? 'A practical $97 review for catering owners planning the move from reliable demand to a permanent storefront.' : 'A practical $97 review for small-business owners who want a clearer picture of their credit, business foundation, documents, and next move.'}</p><div className="r20b-actions"><a className="gc-btn gc-btn-primary" href={ctaHref()} onClick={onCtaClick}>Start your $97 readiness review <ArrowRight size={18} /></a><a className="gc-btn gc-btn-secondary" href="#review">See what you receive</a></div><div className="r20b-trust"><span><ShieldCheck size={17} /> Readiness guidance, not a funding promise</span><span><FileText size={17} /> One-time service</span><span><LockIcon /> Your information stays protected</span></div></div><div className="r20b-hero-media"><img src={restaurantCampaign ? '/creative-r20d/restaurant-hero.jpg' : '/creative-r20a/final/goclear-readiness-story.png'} alt={restaurantCampaign ? 'Restaurant staff preparing food in a commercial kitchen' : 'Small-business owner preparing at her desk'} /><div className="r20b-hero-card"><span>One clear next step</span><strong>{restaurantCampaign ? 'Prepare the business behind the dream.' : 'Prepare with confidence.'}</strong></div></div></div></section>

    <section className="r20b-proof"><div className="gc-container r20b-proof-grid"><div><span className="r20b-kicker">THE QUESTION</span><h2>Is your business funding-ready?</h2><p>You do not need another vague promise. You need to understand what may be helping, what may be holding you back, and what to organize next.</p></div><div className="r20b-proof-list"><div><CheckCircle2 /><span><b>Personal credit context</b><small>See which readiness factors deserve attention.</small></span></div><div><CheckCircle2 /><span><b>Business foundation</b><small>Clarify setup, banking, and documentation gaps.</small></span></div><div><CheckCircle2 /><span><b>Prioritized next actions</b><small>Leave with a practical preparation path.</small></span></div></div></div></section>

    <section className="gc-container r20b-section" id="review"><div className="r20b-section-head"><span className="r20b-kicker">WHAT THE REVIEW DOES</span><h2>A focused review built for your next decision.</h2><p>GoClear reviews the information and evidence available at the time, then translates it into plain-language findings.</p></div><div className="r20b-card-grid"><article><span className="r20b-icon"><ClipboardCheck /></span><h3>Readiness snapshot</h3><p>Understand the current picture across credit, business setup, bankability, and funding preparation.</p></article><article><span className="r20b-icon"><FileText /></span><h3>Document-gap review</h3><p>See which supporting information may be useful to organize before a later funding conversation.</p></article><article><span className="r20b-icon"><Sparkles /></span><h3>Next-action plan</h3><p>Get prioritized steps and a recommended review path based on your actual starting point.</p></article></div></section>

    <section className="r20b-dark"><div className="gc-container" id="how-it-works"><div className="r20b-section-head light"><span className="r20b-kicker">HOW IT WORKS</span><h2>Simple process. Clear boundary.</h2></div><div className="r20b-steps"><div><b>01</b><h3>Start securely</h3><p>Create or sign in to your GoClear account. The next page explains the information needed.</p></div><div><b>02</b><h3>Share context</h3><p>Provide your current profile information and relevant reports or documents.</p></div><div><b>03</b><h3>Review the findings</h3><p>Receive a readiness snapshot and practical next-action plan after review.</p></div></div></div></section>

    <section className="gc-container r20b-offer"><div><span className="r20b-kicker">CHOOSE THE TEST VARIANT</span><h2>Same review. Clear pricing test.</h2><p>Research is testing whether a plain $97 price or a clearly defined future-service credit is easier to understand. Both variants deliver the same review.</p></div><div className="r20b-variant-toggle" role="group" aria-label="Pricing experiment"><button className={variant === 'A' ? 'active' : ''} onClick={() => chooseVariant('A')}>A · $97 review</button><button className={variant === 'B' ? 'active' : ''} onClick={() => chooseVariant('B')}>B · $97 credit</button></div><div className="r20b-offer-card"><div><span className="gc-pill">Variant {variant}</span><h3>{offer.label}</h3><p>{offer.detail}</p></div><a className="gc-btn gc-btn-primary" href={ctaHref()} onClick={onCtaClick}>Continue to the review <ArrowRight size={18} /></a></div><small className="r20b-experiment-note">Variant B credit applies only toward a later qualifying GoClear service, if selected, under that service’s written terms. No automatic upgrade or funding outcome is implied.</small></section>

    <section className="gc-container r20b-trust-section"><div><span className="r20b-kicker">TRUST & TRANSPARENCY</span><h2>Useful guidance without overpromising.</h2><p>GoClear is not a lender. This is not a loan application or a promise of approval. Results depend on the information available, documentation, program requirements, and your follow-through.</p></div><div className="r20b-trust-box"><ShieldCheck size={24} /><b>Your $97 covers the readiness review service.</b><span>It does not purchase funding, a credit-score increase, deletion, a specific limit, or a guaranteed timeline.</span></div></section>

    <section className="gc-container r20b-faq" id="faq"><div className="r20b-section-head"><span className="r20b-kicker">FAQ</span><h2>Questions owners ask before they start.</h2></div><div className="r20b-faq-grid">{[
      ['What is a funding-readiness review?', 'A focused review that turns your current information into a readiness snapshot, document-gap review, and prioritized next-action plan.'],
      ['Does this guarantee funding?', 'No. GoClear does not guarantee funding approval, credit-score increases, deletions, limits, or specific outcomes.'],
      ['What documents might I need?', 'Current profile information, relevant credit or business reports, supporting documents, and the authorizations explained during onboarding.'],
      ['Does personal credit matter?', 'It can be one part of the overall readiness picture. The review considers the information available at the time and does not make a lender decision.'],
      ['What happens after the review?', 'You receive the findings and next-action plan. Any later service or consultation is a separate, approval-gated decision.'],
      ['How does Variant B work?', 'You pay the same $97 for the same review. If you later select a qualifying GoClear service, the $97 can be credited once under that service’s written terms.']
    ].map(([q,a]) => <details key={q}><summary>{q}</summary><p>{a}</p></details>)}</div></section>

    <section className="r20b-final-cta"><div className="gc-container"><span className="r20b-kicker">READY FOR A CLEARER NEXT STEP?</span><h2>Start with what you know today.</h2><p>Review the offer, create your secure account, and see exactly what the readiness process asks of you.</p><a className="gc-btn gc-btn-primary" href={ctaHref()} onClick={onCtaClick}>Start your $97 readiness review <ArrowRight size={18} /></a></div></section>
    <footer className="gc-footer"><div className="gc-container gc-footer-bottom"><span>© 2026 GoClear · Advisory services only</span><span>GoClear is not a lender · No funding or credit outcome is guaranteed.</span></div></footer>
  </main>;
}

function LockIcon() { return <span aria-hidden="true">🔒</span>; }
