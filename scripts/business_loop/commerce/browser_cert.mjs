// Real-browser certification of the storefront conversion layer.
// usage: node browser_cert.mjs <page_url_with_query> <out_json> [screenshot_png]
import { chromium, devices } from 'playwright';
import fs from 'node:fs';

const [, , url, outPath, shot] = process.argv;
const email = `cert-${Date.now().toString(36)}@example.com`;
const browser = await chromium.launch(fs.existsSync('/Applications/Google Chrome.app') ? { channel: 'chrome', headless: true } : {});
const ctx = await browser.newContext({ ...devices['iPhone 13'] });
const page = await ctx.newPage();
const posted = [];
page.on('request', r => { if (r.method() === 'POST' && r.url().includes('/rest/v1/')) posted.push({ table: r.url().split('/rest/v1/')[1], body: JSON.parse(r.postData() || '{}') }); });
const statuses = [];
page.on('response', r => { if (r.request().method() === 'POST' && r.url().includes('/rest/v1/')) statuses.push({ table: r.url().split('/rest/v1/')[1], status: r.status() }); });
await page.goto(url, { waitUntil: 'networkidle' });
const sid = await page.evaluate(() => sessionStorage.getItem('nx_sid'));
await page.click('.mobile-bar a.btn-primary');            // sticky CTA -> CTA_CLICK + focuses form
await page.waitForTimeout(600);
await page.fill('#nx-email', 'not-an-email');
await page.click('#nx-submit');
const invalidMsg = await page.textContent('#nx-msg');
await page.fill('#nx-email', email);
await page.fill('#nx-first', 'Cert');
await page.click('#nx-submit');
await page.waitForFunction(() => /on the list/.test(document.querySelector('#nx-msg').textContent), null, { timeout: 15000 });
const okMsg = await page.textContent('#nx-msg');
await page.click('#nx-submit');                            // same browser: local duplicate guard
const dupLocalMsg = await page.textContent('#nx-msg');
await page.evaluate(() => localStorage.clear());           // new device, same email: server unique constraint
await page.click('#nx-submit');
await page.waitForFunction(() => /already on the list/.test(document.querySelector('#nx-msg').textContent), null, { timeout: 15000 });
const dupServerMsg = await page.textContent('#nx-msg');
const checkoutVisible = await page.isVisible('#nx-test-checkout');
const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
if (shot) { await page.locator('#preview').scrollIntoViewIfNeeded(); await page.screenshot({ path: shot }); }
await page.waitForTimeout(1500);
await browser.close();
fs.writeFileSync(outPath, JSON.stringify({ sid, email, invalidMsg, okMsg, dupLocalMsg, dupServerMsg, checkoutVisible, mobileHorizontalOverflow: overflow,
  posted: posted.map(p => ({ table: p.table, event_type: p.body.event_type, utm_content: p.body.utm_content, source: p.body.source, campaign: p.body.campaign, has_email: !!p.body.email })),
  statuses }, null, 1));
