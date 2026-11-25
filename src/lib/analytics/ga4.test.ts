import { describe, expect, it } from 'vitest';
import { GA4_MEASUREMENT_ID, initGa4, shouldTrack, trackEvent } from './ga4';

function fakeWindow(url: string, nav: Record<string, unknown> = {}) {
  const u = new URL(url);
  const scripts: Array<{ src: string; async: boolean }> = [];
  const w = {
    location: { hostname: u.hostname, pathname: u.pathname, origin: u.origin, search: u.search, hash: u.hash },
    navigator: nav,
    document: {
      title: 'GoClear',
      head: { appendChild: (s: { src: string; async: boolean }) => scripts.push(s) },
      createElement: () => ({ src: '', async: false }),
      querySelector: (sel: string) => (scripts.some((s) => sel.includes(GA4_MEASUREMENT_ID) && s.src.includes(GA4_MEASUREMENT_ID)) ? {} : null),
    },
  } as unknown as Window & { dataLayer?: unknown[] };
  return { w, scripts, calls: () => (w.dataLayer ?? []).map((a) => Array.from(a as ArrayLike<unknown>)) };
}

describe('GA4 production tag', () => {
  it('tracks only public pages on the production hostnames', () => {
    expect(shouldTrack({ hostname: 'goclearonline.cc', pathname: '/funding-readiness/' })).toBe(true);
    expect(shouldTrack({ hostname: 'www.goclearonline.cc', pathname: '/' })).toBe(true);
    expect(shouldTrack({ hostname: 'deploy-preview-12--goclear.netlify.app', pathname: '/' })).toBe(false);
    expect(shouldTrack({ hostname: 'localhost', pathname: '/' })).toBe(false);
    for (const p of ['/admin', '/admin/review', '/operator', '/client', '/update-password', '/auth/reset', '/invite/accept', '/tester/tasks', '/goclear/login']) {
      expect(shouldTrack({ hostname: 'goclearonline.cc', pathname: p })).toBe(false);
    }
  });
  it('honours Global Privacy Control and Do Not Track', () => {
    expect(shouldTrack({ hostname: 'goclearonline.cc', pathname: '/' }, { globalPrivacyControl: true })).toBe(false);
    expect(shouldTrack({ hostname: 'goclearonline.cc', pathname: '/' }, { doNotTrack: '1' })).toBe(false);
  });
  it('loads the tag once, denies ad storage and sends one page_view without query string or fragment', () => {
    const f = fakeWindow('https://goclearonline.cc/checkout/success?session_id=cs_test_secret#token=abc');
    initGa4(f.w);
    initGa4(f.w);
    expect(f.scripts).toHaveLength(1);
    expect(f.scripts[0].src).toBe(`https://www.googletagmanager.com/gtag/js?id=${GA4_MEASUREMENT_ID}`);
    const calls = f.calls();
    expect(calls[0]).toEqual(['consent', 'default', { ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied', analytics_storage: 'granted' }]);
    const pv = calls.filter((c) => c[0] === 'event' && c[1] === 'page_view');
    expect(pv).toHaveLength(1);
    expect(JSON.stringify(calls)).not.toMatch(/session_id|cs_test|token/);
    expect(pv[0][2]).toMatchObject({ page_location: 'https://goclearonline.cc/checkout/success', page_path: '/checkout/success' });
    const cfg = calls.find((c) => c[0] === 'config');
    expect(cfg?.[2]).toMatchObject({ send_page_view: false, allow_google_signals: false });
  });
  it('never loads on preview hosts or private screens', () => {
    for (const url of ['https://main--nexus.netlify.app/', 'https://goclearonline.cc/admin']) {
      const f = fakeWindow(url);
      initGa4(f.w);
      expect(f.scripts).toHaveLength(0);
      expect(f.w.dataLayer).toBeUndefined();
    }
  });
  it('sends only allowlisted, non-identifying event params', () => {
    const f = fakeWindow('https://goclearonline.cc/readiness-review');
    initGa4(f.w);
    trackEvent('sign_up', { method: 'email', email: 'a@b.c' } as Record<string, string>, f.w);
    trackEvent('begin_checkout', { offer_slug: 'readiness-review-97' }, f.w);
    trackEvent('purchase' as never, { value: '97' }, f.w);
    const ev = f.calls().filter((c) => c[0] === 'event' && c[1] !== 'page_view');
    expect(ev).toEqual([['event', 'sign_up', { method: 'email' }], ['event', 'begin_checkout', { offer_slug: 'readiness-review-97' }]]);
  });
});
