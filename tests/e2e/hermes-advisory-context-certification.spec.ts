import { expect, test, type Page } from 'playwright/test';

const enabled = process.env.E2E_ENABLE_AUTHENTICATED === 'true';
const admin = { email: process.env.E2E_ADMIN_EMAIL, password: process.env.E2E_ADMIN_PASSWORD };

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

function attachStrictErrorGates(page: Page, errors: string[]) {
  page.on('console', (msg) => {
    const text = msg.text();
    if (msg.type() === 'error' && !/favicon|Failed to load resource/i.test(text)) errors.push(`console:${text}`);
  });
  page.on('pageerror', (error) => errors.push(`pageerror:${error.message}`));
}

async function openHermesWorkroom(page: Page) {
  await page.goto('/admin#hermes');
  await expect(page.getByRole('heading', { name: /Hermes Workroom/i })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText(/Operating context/i)).toBeVisible();
}

async function askHermes(page: Page, message: string): Promise<{ text: string; strategy: string; intent: string }> {
  await page.locator('textarea[aria-label="Message Hermes"]').first().fill(message);
  await page.getByRole('button', { name: /^Send$/ }).click();
  await expect(page.getByText(/Hermes Workroom hit a local rendering error|n is not a function/i)).toHaveCount(0);
  await expect(page.locator('.nxos-message.ray').last()).toContainText(message, { timeout: 10_000 });
  const last = page.locator('.nxos-message.hermes').last();
  await expect(last).toBeVisible({ timeout: 10_000 });
  const text = (await last.locator('p').innerText()).trim();
  expect(text.length).toBeGreaterThan(10);
  expect(text).not.toMatch(/unknown context|need a concrete decision|general recommendation|broad category/i);
  return {
    text,
    strategy: await last.getAttribute('data-hermes-strategy') || '',
    intent: await last.getAttribute('data-hermes-intent') || '',
  };
}

async function expectNoHorizontalOverflow(page: Page) {
  const metrics = await page.evaluate(() => ({
    htmlOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    bodyOverflow: document.body.scrollWidth - document.body.clientWidth,
  }));
  expect(Math.max(metrics.htmlOverflow, metrics.bodyOverflow)).toBeLessThanOrEqual(2);
}

test.describe('Hermes advisory context ownership certification', () => {
  test.setTimeout(240_000);
  test.skip(!enabled || !admin.email || !admin.password, 'Set authenticated admin credentials.');

  test('newest recommendation owns ambiguous follow-ups while explicit older-topic recall still works', async ({ page }) => {
    const errors: string[] = [];
    attachStrictErrorGates(page, errors);
    await loginAdmin(page);
    await openHermesWorkroom(page);

    const greeting = await askHermes(page, 'good morning');
    expect(greeting.text).toMatch(/Good morning, Ray/i);

    const priority = await askHermes(page, 'what should we focus on today?');
    expect(priority.strategy).toBe('executive_priority_response');
    expect(priority.text).toMatch(/Client live-data flag off|Focus first/i);

    const priorityWhy = await askHermes(page, 'why that one?');
    expect(priorityWhy.strategy).toBe('followup_rationale_response');
    expect(priorityWhy.text).toMatch(/Client live-data flag off|customer-facing evidence/i);

    const revenue = await askHermes(page, 'how can we make money today?');
    expect(revenue.strategy).toBe('revenue_action_response');
    expect(revenue.text).toMatch(/\$97|readiness review|fastest revenue action/i);

    const revenueWhy = await askHermes(page, 'why that one?');
    expect(revenueWhy.strategy).toBe('followup_rationale_response');
    expect(revenueWhy.text).toMatch(/\$97|readiness review|entry offer|monetization/i);
    expect(revenueWhy.text).not.toMatch(/Client live-data flag off/i);

    const realistic = await askHermes(page, 'is that realistic?');
    expect(realistic.strategy).toBe('followup_feasibility_response');
    expect(realistic.text).toMatch(/\$97|readiness review|test-mode|bounded/i);
    expect(realistic.text).not.toMatch(/Client live-data flag off/i);

    const blockers = await askHermes(page, 'what would stop us?');
    expect(blockers.strategy).toBe('followup_blockers_response');
    expect(blockers.text).toMatch(/Stripe remains test-only|configuration checks|Lead audience/i);
    expect(blockers.text).not.toMatch(/Client live-data flag off/i);

    const stripe = await askHermes(page, 'is Stripe live?');
    expect(stripe.text).toMatch(/test mode|deferred/i);

    const afterStatus = await askHermes(page, 'why that one?');
    expect(afterStatus.text).toMatch(/\$97|readiness review|entry offer|monetization/i);
    expect(afterStatus.text).not.toMatch(/Client live-data flag off/i);

    const older = await askHermes(page, 'going back to the client live-data flag, what would stop us?');
    expect(older.text).toMatch(/Client live-data flag off|live-data|customer-facing evidence/i);

    await expectNoHorizontalOverflow(page);
    expect(errors).toEqual([]);
  });

  test('numbered revenue selection targets the governed task draft only', async ({ page }) => {
    const errors: string[] = [];
    attachStrictErrorGates(page, errors);
    await loginAdmin(page);
    await openHermesWorkroom(page);

    const revenueList = await askHermes(page, 'give me three ways to make money today');
    expect(revenueList.text).toMatch(/Other viable money actions|2\./i);

    const second = await askHermes(page, 'go deeper on number 2');
    expect(second.strategy).toBe('followup_deep_dive_response');
    expect(second.text).toMatch(/lead|reactivation|offer|money action/i);

    const task = await askHermes(page, 'turn that one into a task');
    expect(task.text).toMatch(/conversation-only|governed|approval/i);
    await expect(page.locator('.nxos-message.hermes').last().getByRole('button', { name: /Prepare governed task/i })).toBeVisible();
    expect(errors).toEqual([]);
  });
});
