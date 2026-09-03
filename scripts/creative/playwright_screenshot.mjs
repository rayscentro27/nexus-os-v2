import { chromium } from 'playwright';

const [url, output, width, height] = process.argv.slice(2);
if (!url || !output || !width || !height) process.exit(2);
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: Number(width), height: Number(height) } });
try {
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.screenshot({ path: output, fullPage: false, timeout: 15000 });
} finally {
  await context.close();
  await browser.close();
}
process.exit(0);
