import { chromium } from 'playwright';

const [url, output, width, height] = process.argv.slice(2);
if (!url || !output || !width || !height) process.exit(2);
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: Number(width), height: Number(height) } });
try {
  const page = await context.newPage();
  await page.goto(url, { waitUntil: 'load' });
  await page.screenshot({ path: output, fullPage: true });
} finally {
  await context.close();
  await browser.close();
}
