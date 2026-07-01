#!/usr/bin/env node
import { spawn } from 'node:child_process';
import { chromium } from 'playwright';

const base = process.env.HERMES_TEST_BASE || 'http://127.0.0.1:4201/?ui-smoke=1';
const server = process.env.HERMES_TEST_BASE ? null : spawn('./node_modules/.bin/vite', ['--port', '4201', '--host', '127.0.0.1'], { stdio: 'ignore' });
const results = {};

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function waitForServer() {
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(base);
      if (response.ok) return;
    } catch {}
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  throw new Error('Vite startup timed out');
}

async function sendWorkroom(page, message) {
  const before = await page.locator('.nxos-message.hermes').count();
  await page.getByLabel('Message Hermes').fill(message, { force: true });
  await page.locator('.nxos-chat-compose button', { hasText: 'Send' }).click({ force: true });
  await page.locator('.nxos-message.hermes').nth(before).waitFor();
  return page.locator('.nxos-message.hermes').nth(before).locator('p').innerText();
}

async function sendDrawer(page, message) {
  const before = await page.locator('.inline-message.hermes').count();
  await page.getByRole('textbox', { name: 'Ask Hermes inline', exact: true }).fill(message, { force: true });
  await page.locator('.hermes-inline-compose button', { hasText: 'Send' }).click({ force: true });
  await page.locator('.inline-message.hermes').nth(before).waitFor();
  return page.locator('.inline-message.hermes').nth(before).locator('p').innerText();
}

try {
  console.log('Starting Hermes live UI test');
  await waitForServer();
  console.log('Vite is ready');
  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  console.log('Browser launched');
  const page = await browser.newPage();
  page.setDefaultTimeout(10_000);

  await page.goto(`${base}#hermes`);
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  const hermesCases = [
    ['what is todays date', /(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday).*(?:january|february|march|april|may|june|july|august|september|october|november|december)/i],
    ['what is today’s date', /(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday).*(?:january|february|march|april|may|june|july|august|september|october|november|december)/i],
    ['what day is it', /monday|tuesday|wednesday|thursday|friday|saturday|sunday/i],
    ['what time is it', /\d{1,2}:\d{2}.*(?:AM|PM).*(?:Phoenix|timezone)/i],
    ['good afternoon', /good (?:morning|afternoon|evening|night)/i],
    ['are you real AI or scripted right now', /local bundled Nexus context.*do not yet have live Supabase.*real AI model access/is],
    ['where are you getting your answers from', /local bundled Nexus context.*page context.*browser time.*local activity journal/is],
  ];
  const hermesAnswers = [];
  for (const [message, expected] of hermesCases) {
    console.log(`Testing: ${message}`);
    const answer = await sendWorkroom(page, message);
    assert(expected.test(answer), `${message}: unexpected answer: ${answer}`);
    assert(!/I'm not sure what you're asking for/i.test(answer), `${message}: hit old fallback`);
    results[message] = answer;
    hermesAnswers.push(answer);
  }
  assert(hermesAnswers[0] !== hermesAnswers[4] && hermesAnswers[4] !== hermesAnswers[6], 'Unrelated date, greeting, and source questions returned the same answer');
  assert(!/I have live (?:Supabase|web|model)|I can query Supabase directly|live web search is available/i.test(hermesAnswers.slice(-2).join(' ')), 'Source transparency claimed unavailable live sources');

  await page.goto(`${base}#trading`);
  console.log('Testing Trading page context');
  await page.getByLabel('Ask Hermes without leaving this page').click();
  const first = await sendDrawer(page, 'tell me about the first strategy on this page');
  assert(/Half Trend Forex Strategy/i.test(first) && /paper|demo/i.test(first), `First strategy was not grounded: ${first}`);
  results.trading_first_strategy = first;
  const clicks = await sendDrawer(page, 'what can I click here');
  assert(/Open a strategy row|Review paper backtest details/i.test(clicks), `Trading actions missing: ${clicks}`);
  const comparison = await sendDrawer(page, 'compare that strategy with another trading strategy');
  assert(/Half Trend Forex Strategy/i.test(comparison) && /which comparison target/i.test(comparison), `Comparison did not use the reference or clarify: ${comparison}`);
  results.trading_comparison = comparison;
  const tradingMode = await sendDrawer(page, 'is this live trading or paper only');
  assert(/paper|demo/i.test(tradingMode) && /live trading.*blocked/i.test(tradingMode), `Trading mode answer unsafe: ${tradingMode}`);

  await page.goto(`${base}#reports`);
  console.log('Testing Reports page context');
  if (!(await page.getByRole('dialog', { name: 'Ask Hermes inline chat' }).isVisible())) {
    await page.getByLabel('Ask Hermes without leaving this page').click();
  }
  const report = await sendDrawer(page, 'what does this revenue dashboard mean and what should I do next');
  assert(/report-backed local snapshot/i.test(report) && /supporting report/i.test(report), `Revenue dashboard answer not grounded: ${report}`);
  results.reports_revenue_dashboard = report;

  const unclear = await sendDrawer(page, 'can you find out');
  assert(/You asked: “can you find out.”/i.test(unclear) && /I checked Reports page context/i.test(unclear) && /Which|Do you want/i.test(unclear), `Fallback was not focused: ${unclear}`);
  results.generic_fallback = unclear;

  await browser.close();
  console.log(JSON.stringify({ ok: true, results }, null, 2));
} catch (error) {
  console.error(error.stack || error);
  process.exitCode = 1;
} finally {
  server?.kill('SIGTERM');
}
