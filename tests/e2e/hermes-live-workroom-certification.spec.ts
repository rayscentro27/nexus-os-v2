import { expect, test, type Page } from 'playwright/test';

const enabled = process.env.E2E_ENABLE_AUTHENTICATED === 'true';
const admin = { email: process.env.E2E_ADMIN_EMAIL, password: process.env.E2E_ADMIN_PASSWORD };
const personaA = { email: process.env.E2E_PERSONA_A_EMAIL, password: process.env.E2E_PERSONA_A_PASSWORD };

async function loginAdmin(page: Page) {
  await page.context().clearCookies();
  await page.goto('/admin/login');
  await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); }).catch(() => {});
  await page.goto('/admin/login');
  await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {});
  await page.getByLabel(/email/i).fill(admin.email!);
  await page.getByLabel(/password/i).fill(admin.password!);
  await page.getByRole('button', { name: /sign in|log in/i }).click();
  await expect(page).toHaveURL(/\/admin\/?$/, { timeout: 20_000 });
}

async function loginClient(page: Page) {
  await page.context().clearCookies();
  await page.goto('/client/login');
  await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); }).catch(() => {});
  await page.goto('/client/login');
  await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {});
  await page.getByLabel(/email/i).fill(personaA.email!);
  await page.getByLabel(/password/i).fill(personaA.password!);
  await page.getByRole('button', { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/client\/(dashboard|documents|credit-profile)/, { timeout: 20_000 });
}

function attachErrorGates(page: Page, errors: string[]) {
  page.on('console', (msg) => {
    if (msg.type() === 'error' && !/favicon|Failed to load resource/i.test(msg.text())) errors.push(`console:${msg.text()}`);
  });
  page.on('pageerror', (error) => errors.push(`pageerror:${error.message}`));
}

async function askHermes(page: Page, message: string): Promise<string> {
  await page.locator('textarea[aria-label="Message Hermes"]').first().fill(message);
  await page.getByRole('button', { name: /^Send$/ }).click();
  await expect(page.getByText(/Hermes Workroom hit a local rendering error/i)).toHaveCount(0);
  await expect(page.locator('.nxos-message.ray').last()).toContainText(message, { timeout: 10_000 });
  await expect(page.locator('.nxos-message.hermes').last()).toBeVisible({ timeout: 10_000 });
  const text = await page.locator('.nxos-message.hermes p').last().innerText();
  expect(text.trim().length).toBeGreaterThan(10);
  return text;
}

async function expectNoHorizontalOverflow(page: Page) {
  const metrics = await page.evaluate(() => ({
    htmlOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    bodyOverflow: document.body.scrollWidth - document.body.clientWidth,
  }));
  expect(Math.max(metrics.htmlOverflow, metrics.bodyOverflow)).toBeLessThanOrEqual(2);
}

test.describe('Hermes live Workroom certification', () => {
  test.setTimeout(180_000);
  test.skip(!enabled || !admin.email || !admin.password, 'Set authenticated admin credentials.');

  test('admin Workroom sends, renders, uses operating context, and persists without refresh', async ({ page }) => {
    const errors: string[] = [];
    attachErrorGates(page, errors);
    await loginAdmin(page);
    await page.goto('/admin#hermes');
    await expect(page.getByRole('heading', { name: /Hermes Workroom/i })).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText(/Operating context/i)).toBeVisible();
    await expect(page.getByText(/Client live-data flag off/i)).toBeVisible();

    const greeting = await askHermes(page, 'good morning');
    expect(greeting).toMatch(/Good morning, Ray/i);
    expect(greeting).not.toMatch(/human tastes|lived experiences|Ray Review queue/i);

    const priority = await askHermes(page, 'what should we focus on today?');
    expect(priority).toMatch(/Focus first/i);
    expect(priority).toMatch(/Client live-data flag off/i);
    expect(priority).toMatch(/First step/i);
    expect(priority).not.toMatch(/unknown context|concrete decision|general recommendation|category/i);
    await expect(page.locator('.nxos-message.ray')).toHaveCount(2);

    const why = await askHermes(page, 'why that one?');
    expect(why).toMatch(/Client live-data flag off|customer/i);
    const realistic = await askHermes(page, 'is that realistic?');
    expect(realistic).toMatch(/realistic|bounded/i);
    const stop = await askHermes(page, 'what would stop us?');
    expect(stop).toMatch(/blockers|risk|dependency|customer/i);
    const second = await askHermes(page, 'go deeper on number 2');
    expect(second).toMatch(/Fake customer not inserted|Stripe test completion|Resend|readiness review journey|revenue/i);
    expect(second).toMatch(/Going deeper/i);
    const task = await askHermes(page, 'turn that one into a task');
    expect(task).toMatch(/conversation-only|governed|approval/i);
    await expect(page.locator('.nxos-message.hermes').last().getByRole('button', { name: /Prepare governed task|Draft Ray Review|specialist handoff/i }).first()).toBeVisible();

    await page.reload();
    await expect(page.getByRole('heading', { name: /Hermes Workroom/i })).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText(/Hermes Workroom hit a local rendering error/i)).toHaveCount(0);
    await expect(page.locator('.nxos-message.hermes').filter({ hasText: /Client live-data flag off|governed/i }).first()).toBeVisible();
    expect(errors).toEqual([]);
    await expectNoHorizontalOverflow(page);
  });

  test('priority paraphrases route to useful Executive context', async ({ page }) => {
    const errors: string[] = [];
    attachErrorGates(page, errors);
    await loginAdmin(page);
    await page.goto('/admin#hermes');
    await expect(page.getByRole('heading', { name: /Hermes Workroom/i })).toBeVisible({ timeout: 20_000 });
    for (const prompt of ['what should we do first?', 'what needs my attention?', 'where should we start?', 'what is the top priority?']) {
      const answer = await askHermes(page, prompt);
      expect(answer).toMatch(/Focus first|Client live-data flag off|First step/i);
      expect(answer).not.toMatch(/unknown context|concrete decision|category/i);
    }
    expect(errors).toEqual([]);
  });

  test('client cannot access Executive Hermes Workroom', async ({ page }) => {
    test.skip(!personaA.email || !personaA.password, 'Set authenticated Persona A credentials.');
    await loginClient(page);
    await page.goto('/admin#hermes');
    await expect(page.getByRole('heading', { name: /admin access required|admin login/i })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole('heading', { name: /Hermes Workroom/i })).toHaveCount(0);
  });

  for (const viewport of [
    { name: 'desktop', width: 1920, height: 1080 },
    { name: 'laptop', width: 1440, height: 900 },
    { name: 'tablet', width: 1024, height: 768 },
    { name: 'mobile', width: 390, height: 844 },
  ]) {
    test(`Workroom remains usable on ${viewport.name}`, async ({ browser }) => {
      const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height } });
      const page = await context.newPage();
      const errors: string[] = [];
      attachErrorGates(page, errors);
      await loginAdmin(page);
      await page.goto('/admin#hermes');
      await expect(page.getByRole('heading', { name: /Hermes Workroom/i })).toBeVisible({ timeout: 20_000 });
      await askHermes(page, 'what should we focus on today?');
      await expectNoHorizontalOverflow(page);
      expect(errors).toEqual([]);
      await context.close();
    });
  }
});
