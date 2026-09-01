import { expect, test } from 'playwright/test';

const enabled = process.env.E2E_ENABLE_AUTHENTICATED === 'true';
const email = process.env.E2E_ADMIN_EMAIL || '';
const password = process.env.E2E_ADMIN_PASSWORD || '';

async function login(page: import('playwright/test').Page) {
  await page.goto('/admin/login');
  await page.getByLabel(/email/i).fill(email);
  await page.getByLabel(/password/i).fill(password);
  await page.getByRole('button', { name: /sign in|log in/i }).click();
  await expect(page).toHaveURL(/\/admin\/?$/, { timeout: 20_000 });
}

async function noOverflow(page: import('playwright/test').Page) {
  const result = await page.evaluate(() => ({
    html: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    body: document.body.scrollWidth - document.body.clientWidth,
  }));
  expect(Math.max(result.html, result.body)).toBeLessThanOrEqual(2);
}

test.describe('Nexus Operator Console', () => {
  test.setTimeout(120_000);
  test.skip(!enabled || !email || !password, 'Synthetic admin credentials required');

  test('authenticated home and Creative review surface', async ({ page }) => {
    await login(page);
    await page.goto('/operator');
    await expect(page.getByRole('heading', { name: /Keep the system moving/i })).toBeVisible();
    await expect(page.getByText(/remote assets indexed/i)).toBeVisible();
    await page.getByRole('button', { name: /Open Creative Review/i }).click();
    await expect(page).toHaveURL(/\/operator\/creative$/);
    await expect(page.getByRole('heading', { name: /Choose the next move/i })).toBeVisible();
    await expect(page.getByRole('heading', { name: /Review the work without hunting for files/i })).toBeVisible();
    await expect(page.getByText(/publication blocked/i)).toBeVisible();
    await expect(page.locator('.creative-review-card')).toHaveCount(5);
    await page.locator('.creative-review-card').filter({ hasText: 'VIDEO' }).click();
    await expect(page.locator('.creative-review-detail video')).toBeVisible();
    await page.getByRole('button', { name: /Compare versions/i }).click();
    await expect(page.getByText(/Version comparison/i)).toBeVisible();
    await page.getByRole('button', { name: /^Approve$/i }).click();
    await expect(page.getByText(/APPROVED_FOR_NEXT_INTERNAL_STAGE/i)).toBeVisible();
    await page.getByRole('button', { name: /Request revision/i }).click();
    await expect(page.getByText(/REQUEST_REVISION/i)).toBeVisible();
    await page.getByRole('button', { name: /^Reject$/i }).click();
    await expect(page.getByText(/REJECTED_RETAINED/i)).toBeVisible();
    await noOverflow(page);
  });

  test('desktop and mobile operator baselines', async ({ page }) => {
    await login(page);
    await page.goto('/operator');
    await expect(page.getByRole('heading', { name: /Keep the system moving/i })).toBeVisible();
    await page.screenshot({ path: 'reports/rebuild/wp8_12_operator_home_desktop.png', fullPage: true });
    await page.goto('/operator/creative');
    await expect(page.getByRole('heading', { name: /Choose the next move/i })).toBeVisible();
    await expect(page.locator('.creative-review-card')).toHaveCount(5);
    await page.screenshot({ path: 'reports/rebuild/wp8_12_operator_creative_desktop.png', fullPage: true });
    await noOverflow(page);
  });

  test('mobile home, Creative gallery, and review controls', async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const page = await context.newPage();
    await login(page);
    await page.goto('/operator');
    await expect(page.getByRole('heading', { name: /Keep the system moving/i })).toBeVisible();
    await page.screenshot({ path: 'reports/rebuild/wp8_12_operator_home_mobile.png', fullPage: true });
    await page.goto('/operator/creative');
    await expect(page.getByRole('heading', { name: /Choose the next move/i })).toBeVisible();
    await expect(page.locator('.creative-review-card')).toHaveCount(5);
    await page.screenshot({ path: 'reports/rebuild/wp8_12_operator_creative_mobile.png', fullPage: true });
    await noOverflow(page);
    await context.close();
  });
});
