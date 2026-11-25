/**
 * GA4 for the public GoClear site — existing property 500324822, web stream
 * "goclearonline.cc" (measurement ID G-VLX3KSMYNF). No new property.
 *
 * Rules (NEXUS_AUTONOMOUS_OPERATIONAL_ACTIVATION_R1, finding GA4_TAG_NOT_ON_PRODUCTION_SITE):
 * - production hostnames only: preview/branch deploys (netlify.app, lovable, localhost) never send hits,
 *   so they stop polluting the property;
 * - public marketing pages only: admin, operator, client portal, auth, invite and tester screens are never tracked;
 * - one tag per page load (duplicate-load guard), no automatic page_view: we send one sanitized page_view;
 * - no query string or fragment ever leaves the browser (magic links, reset tokens and checkout ids live there);
 * - no personal data in events: event params are an explicit allowlist of non-identifying values;
 * - Consent Mode v2 defaults: ad storage/personalization denied (no ads use), analytics allowed unless the
 *   browser sends Global Privacy Control or Do Not Track, in which case nothing is loaded.
 */
export const GA4_MEASUREMENT_ID = 'G-VLX3KSMYNF';
const PRODUCTION_HOSTS = ['goclearonline.cc', 'www.goclearonline.cc'];
export const TRACKED_PATHS = [
  '/',
  '/goclear',
  '/goclear/signup',
  '/goclear/pricing',
  '/pricing',
  '/funding-readiness',
  '/readiness-review',
  '/readiness-action-plan',
  '/funding-readiness-concierge',
  '/checkout/success',
  '/checkout/pending',
  '/checkout/cancelled',
  '/checkout/failed',
];
const ALLOWED_EVENTS: Record<string, string[]> = {
  sign_up: ['method'],
  select_offer: ['offer_slug'],
  begin_checkout: ['offer_slug'],
};

type Gtag = (...args: unknown[]) => void;
declare global {
  interface Window {
    dataLayer?: unknown[];
    gtag?: Gtag;
    __nexusGa4?: 'loaded' | 'skipped';
  }
  interface Navigator {
    globalPrivacyControl?: boolean;
  }
}

export function normalizePath(pathname: string): string {
  return pathname.replace(/\/+$/, '') || '/';
}

export function shouldTrack(loc: { hostname: string; pathname: string }, nav: { globalPrivacyControl?: boolean; doNotTrack?: string | null } = {}): boolean {
  if (!PRODUCTION_HOSTS.includes(loc.hostname)) return false;
  if (nav.globalPrivacyControl === true || nav.doNotTrack === '1') return false;
  return TRACKED_PATHS.includes(normalizePath(loc.pathname));
}

/** Load the tag once and send one page_view (origin + path only). Safe to call more than once. */
export function initGa4(win: Window = window): void {
  if (win.__nexusGa4) return;
  if (!shouldTrack(win.location, win.navigator)) {
    win.__nexusGa4 = 'skipped';
    return;
  }
  if (win.document.querySelector(`script[src*="googletagmanager.com/gtag/js?id=${GA4_MEASUREMENT_ID}"]`)) {
    win.__nexusGa4 = 'loaded';
    return;
  }
  win.__nexusGa4 = 'loaded';
  win.dataLayer = win.dataLayer || [];
  // gtag must push the arguments object itself
  win.gtag = function gtag() {
    // eslint-disable-next-line prefer-rest-params
    win.dataLayer!.push(arguments);
  };
  win.gtag('consent', 'default', { ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied', analytics_storage: 'granted' });
  win.gtag('js', new Date());
  const path = normalizePath(win.location.pathname);
  win.gtag('config', GA4_MEASUREMENT_ID, {
    send_page_view: false,
    allow_google_signals: false,
    allow_ad_personalization_signals: false,
    page_location: `${win.location.origin}${path}`,
  });
  win.gtag('event', 'page_view', { page_location: `${win.location.origin}${path}`, page_path: path, page_title: win.document.title });
  const s = win.document.createElement('script');
  s.async = true;
  s.src = `https://www.googletagmanager.com/gtag/js?id=${GA4_MEASUREMENT_ID}`;
  win.document.head.appendChild(s);
}

/** Send an allowlisted conversion event; unknown events or params are dropped, never sent. */
export function trackEvent(name: keyof typeof ALLOWED_EVENTS, params: Record<string, string> = {}, win: Window = window): void {
  if (win.__nexusGa4 !== 'loaded' || typeof win.gtag !== 'function') return;
  const allowed = ALLOWED_EVENTS[name];
  if (!allowed) return;
  const clean: Record<string, string> = {};
  for (const k of allowed) if (typeof params[k] === 'string' && params[k].length <= 60 && !params[k].includes('@')) clean[k] = params[k];
  win.gtag('event', name, clean);
}
