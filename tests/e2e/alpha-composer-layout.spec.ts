import { existsSync, readFileSync } from 'fs';
import { resolve } from 'path';
import { expect, test, type Page } from 'playwright/test';

const BASE_URL = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173';

function loadLocalE2EEnv() {
  if (process.env.E2E_ADMIN_EMAIL && process.env.E2E_ADMIN_PASSWORD) return;
  const envPath = resolve(process.cwd(), '.env.e2e.local');
  if (!existsSync(envPath)) return;
  for (const line of readFileSync(envPath, 'utf8').split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#') || !trimmed.includes('=')) continue;
    const [key, ...valueParts] = trimmed.split('=');
    if (!process.env[key]) process.env[key] = valueParts.join('=');
  }
}

loadLocalE2EEnv();

const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL || '';
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD || '';
const viewports = [
  { width: 1920, height: 1080 },
  { width: 1664, height: 960 },
  { width: 1536, height: 864 },
  { width: 1366, height: 768 },
  { width: 390, height: 844 },
];

async function loginAdmin(page: Page) {
  await page.goto(`${BASE_URL}/admin/login`);
  await page.fill('#admin-email', ADMIN_EMAIL);
  await page.fill('#admin-password', ADMIN_PASSWORD);
  await page.getByRole('button', { name: /sign in|log in/i }).click();
  await page.waitForURL(/\/admin\/?$/, { timeout: 25_000 });
}

async function openAlpha(page: Page) {
  await page.goto(`${BASE_URL}/admin#alpha`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('[data-testid="alpha-composer-input"]', { timeout: 20_000 });
}

async function composerGeometry(page: Page) {
  return page.evaluate(() => {
    const measure = (selector: string) => {
      const el = document.querySelector<HTMLElement>(selector);
      if (!el) return null;
      const rect = el.getBoundingClientRect();
      const centerX = Math.max(0, Math.min(window.innerWidth - 1, rect.left + rect.width / 2));
      const centerY = Math.max(0, Math.min(window.innerHeight - 1, rect.top + rect.height / 2));
      const topElement = document.elementFromPoint(centerX, centerY);
      return {
        rect: {
          top: rect.top,
          bottom: rect.bottom,
          width: rect.width,
          height: rect.height,
        },
        pointerEvents: getComputedStyle(el).pointerEvents,
        topTag: topElement?.tagName || '',
        topTestId: topElement?.getAttribute('data-testid') || '',
      };
    };
    const footer = document.querySelector<HTMLElement>('footer,.footer');
    const footerRect = footer?.getBoundingClientRect();
    return {
      footerTop: footerRect?.top || window.innerHeight,
      input: measure('[data-testid="alpha-composer-input"]'),
      send: measure('[data-testid="alpha-composer-send"]'),
    };
  });
}

test.describe('Hermes Alpha composer layout', () => {
  test.skip(!ADMIN_EMAIL || !ADMIN_PASSWORD, 'E2E admin credentials required');
  test.setTimeout(180_000);

  test('keeps the composer visible and clickable across certified viewports', async ({ page }) => {
    await loginAdmin(page);
    for (const viewport of viewports) {
      await page.setViewportSize(viewport);
      await openAlpha(page);
      const geometry = await composerGeometry(page);
      expect(geometry.input).toBeTruthy();
      expect(geometry.send).toBeTruthy();
      expect(geometry.input!.rect.top).toBeGreaterThanOrEqual(0);
      expect(geometry.input!.rect.bottom).toBeLessThanOrEqual(geometry.footerTop);
      expect(geometry.input!.rect.width).toBeGreaterThan(200);
      expect(geometry.input!.rect.height).toBeGreaterThanOrEqual(64);
      expect(geometry.input!.pointerEvents).not.toBe('none');
      expect(geometry.input!.topTag).toBe('TEXTAREA');
      expect(geometry.send!.rect.bottom).toBeLessThanOrEqual(geometry.footerTop);
      expect(geometry.send!.rect.width).toBeGreaterThan(40);
      expect(geometry.send!.rect.height).toBeGreaterThan(30);
      expect(geometry.send!.pointerEvents).not.toBe('none');
      expect(geometry.send!.topTag).toBe('BUTTON');
    }
  });

  test('supports click send, Enter send, and Shift+Enter newline', async ({ page }) => {
    await loginAdmin(page);
    await openAlpha(page);
    await page.getByRole('button', { name: /Clear conversation/i }).click();
    await expect(page.locator('article')).toHaveCount(0);

    await page.locator('[data-testid="alpha-composer-input"]').fill('good evening');
    await page.locator('[data-testid="alpha-composer-send"]').click();
    await expect(page.locator('article')).toHaveCount(2, { timeout: 45_000 });
    await expect(page.locator('[data-testid="alpha-composer-input"]')).toHaveValue('');

    await page.locator('[data-testid="alpha-composer-input"]').fill('what is a bicycle');
    await page.keyboard.press('Enter');
    await expect(page.locator('article')).toHaveCount(4, { timeout: 45_000 });
    await expect(page.locator('[data-testid="alpha-composer-input"]')).toHaveValue('');

    await page.locator('[data-testid="alpha-composer-input"]').fill('line one');
    await page.keyboard.down('Shift');
    await page.keyboard.press('Enter');
    await page.keyboard.up('Shift');
    await page.keyboard.type('line two');
    await expect(page.locator('[data-testid="alpha-composer-input"]')).toHaveValue('line one\nline two');
  });
});
