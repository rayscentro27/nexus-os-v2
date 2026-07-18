import { expect, test } from 'playwright/test';

const enabled = process.env.E2E_ENABLE_AUTHENTICATED === 'true';
const admin = { email: process.env.E2E_ADMIN_EMAIL, password: process.env.E2E_ADMIN_PASSWORD };
const personaA = { email: process.env.E2E_PERSONA_A_EMAIL, password: process.env.E2E_PERSONA_A_PASSWORD };

async function loginAdmin(page) {
  await page.context().clearCookies();
  await page.goto('/admin/login');
  await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); }).catch(() => {});
  await page.goto('/admin/login');
  await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {});
  await page.getByLabel(/email/i).fill(admin.email);
  await page.getByLabel(/password/i).fill(admin.password);
  await page.getByRole('button', { name: /sign in|log in/i }).click();
  await expect(page).toHaveURL(/\/admin\/?$/, { timeout: 20_000 });
}

async function loginClient(page) {
  await page.context().clearCookies();
  await page.goto('/client/login');
  await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); }).catch(() => {});
  await page.goto('/client/login');
  await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {});
  await page.getByLabel(/email/i).fill(personaA.email);
  await page.getByLabel(/password/i).fill(personaA.password);
  await page.getByRole('button', { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/client\/(dashboard|documents|credit-profile)/, { timeout: 20_000 });
}

async function expectNoHorizontalOverflow(page) {
  const metrics = await page.evaluate(() => ({
    htmlOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    bodyOverflow: document.body.scrollWidth - document.body.clientWidth,
  }));
  expect(Math.max(metrics.htmlOverflow, metrics.bodyOverflow)).toBeLessThanOrEqual(2);
}

test.describe('Executive Command Center Wave 1 certification', () => {
  test.setTimeout(120_000);
  test.skip(!enabled || !admin.email || !admin.password, 'Set authenticated admin credentials.');

  test('synthetic admin can access the Founder Mode command center', async ({ page }) => {
    await loginAdmin(page);
    await page.goto('/admin#command');
    await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {});
    await expect(page.getByTestId('executive-command-center')).toBeVisible();
    await expect(page.getByRole('heading', { name: /Executive Command Center/i })).toBeVisible();
    await expect(page.getByText(/Founder Mode Today/i)).toBeVisible();
    await expect(page.getByTestId('executive-daily-brief')).toBeVisible();
    await expect(page.getByTestId('executive-approval-queue')).toBeVisible();
    await expect(page.getByTestId('executive-governed-work')).toBeVisible();
    await expect(page.getByTestId('executive-department-status')).toBeVisible();
    await expect(page.getByTestId('executive-system-health')).toBeVisible();
    await expect(page.getByTestId('executive-repo-intelligence')).toContainText(/github\/github-mcp-server/i);
    await expect(page.getByTestId('executive-repo-intelligence')).toContainText(/INTEGRATE_AS_CONTROLLED_EXTERNAL_TOOL/i);
    await expect(page.getByTestId('executive-safety-boundaries')).toContainText(/Ray remains final authority/i);
    await expect(page.getByText(/STRIPE_MODE=test/i)).toBeVisible();
    await expect(page.getByText(/Live trading blocked/i)).toBeVisible();
    await expectNoHorizontalOverflow(page);
  });

  test('client cannot access the Executive Command Center', async ({ page }) => {
    test.skip(!personaA.email || !personaA.password, 'Set authenticated Persona A credentials.');
    await loginClient(page);
    await page.goto('/admin#command');
    await expect(page.getByRole('heading', { name: /admin access required|admin login/i })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId('executive-command-center')).toHaveCount(0);
  });

  for (const viewport of [
    { name: 'desktop', width: 1920, height: 1080 },
    { name: 'laptop', width: 1440, height: 900 },
    { name: 'tablet', width: 1024, height: 768 },
    { name: 'mobile', width: 390, height: 844 },
  ]) {
    test(`Executive Command Center has no horizontal overflow on ${viewport.name}`, async ({ browser }) => {
      const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height } });
      const page = await context.newPage();
      await loginAdmin(page);
      await page.goto('/admin#command');
      await expect(page.getByTestId('executive-command-center')).toBeVisible();
      await expectNoHorizontalOverflow(page);
      await context.close();
    });
  }
});
