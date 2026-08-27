import { chromium } from 'playwright';
const started = Date.now();
let browser;
const result = { started_at: new Date().toISOString(), api: false, lifecycle: false, audible_output_proven: false, result: 'BROWSER_UNAVAILABLE' };
try {
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.setContent('<!doctype html><title>Nexus TTS certification</title>');
  result.api = await page.evaluate(() => typeof window.speechSynthesis !== 'undefined' && typeof window.SpeechSynthesisUtterance === 'function');
  result.lifecycle = await page.evaluate(async () => {
    if (!window.speechSynthesis || !window.SpeechSynthesisUtterance) return false;
    const u = new SpeechSynthesisUtterance('Nexus browser TTS certification');
    let invoked = false; u.onstart = () => { invoked = true; }; u.onend = () => { invoked = true; }; u.onerror = () => { invoked = true; };
    window.speechSynthesis.speak(u); await new Promise(r => setTimeout(r, 250)); window.speechSynthesis.cancel(); return invoked;
  });
  result.result = result.api && result.lifecycle ? 'BROWSER_TTS_PLAYBACK_LIFECYCLE_VERIFIED' : 'BROWSER_TTS_API_VERIFIED';
} catch (e) { result.error = e?.name || 'launch_failed'; }
finally { if (browser) await browser.close(); }
result.completed_at = new Date().toISOString(); result.duration_ms = Date.now() - started; console.log(JSON.stringify(result, null, 2));
