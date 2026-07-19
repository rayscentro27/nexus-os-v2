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

function similarity(a: string, b: string): number {
  const words = (value: string) => new Set(value.toLowerCase().replace(/[^a-z0-9\s]/g, ' ').split(/\s+/).filter((word) => word.length > 3));
  const left = words(a);
  const right = words(b);
  const intersection = [...left].filter((word) => right.has(word)).length;
  const union = new Set([...left, ...right]).size || 1;
  return intersection / union;
}

async function expectNoHorizontalOverflow(page: Page) {
  const metrics = await page.evaluate(() => ({
    htmlOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    bodyOverflow: document.body.scrollWidth - document.body.clientWidth,
  }));
  expect(Math.max(metrics.htmlOverflow, metrics.bodyOverflow)).toBeLessThanOrEqual(2);
}

async function seedLegacyHermesMessages(page: Page) {
  await page.evaluate(() => {
    localStorage.setItem('nexus_hermes_chat_history', JSON.stringify([
      { role: 'user', text: 'legacy question' },
      {
        role: 'hermes',
        text: 'legacy answer',
        workroomResponse: {
          messageId: 'legacy-hermes',
          role: 'hermes',
          text: 'legacy answer',
          mode: 'EXECUTIVE_ADVICE',
          intent: 'executive_priority',
          responseStrategy: 'executive_priority_response',
          evidenceState: 'REPORT_BACKED',
          confidence: 0.8,
          createdAt: new Date().toISOString(),
          actions: [
            { id: 'safe', type: 'DRAFT_RAY_REVIEW', label: 'Draft Ray Review request', enabled: true, requiresApproval: true },
            { id: 'bad', type: 'CALLBACK_FROM_STORAGE', label: 'Bad callback', enabled: true, requiresApproval: false, onClick: 'not-a-function' },
          ],
        },
      },
    ]));
  });
}

test.describe('Hermes production stack and intent certification', () => {
  test.setTimeout(210_000);
  test.skip(!enabled || !admin.email || !admin.password, 'Set authenticated admin credentials.');

  test('legacy persisted state and scroll polyfills do not crash the Workroom', async ({ page }) => {
    const errors: string[] = [];
    attachStrictErrorGates(page, errors);
    await page.addInitScript(() => {
      Element.prototype.scrollIntoView = function scrollIntoViewReturnsObject() {
        return { nonFunctionCleanup: true } as unknown as void;
      };
    });
    await loginAdmin(page);
    await seedLegacyHermesMessages(page);
    await openHermesWorkroom(page);
    await expect(page.getByText(/legacy answer/i)).toBeVisible();
    const priority = await askHermes(page, 'what should we focus on today?');
    expect(priority.strategy).toBe('executive_priority_response');
    await page.reload();
    await expect(page.getByText(/Hermes Workroom hit a local rendering error|n is not a function/i)).toHaveCount(0);
    expect(errors).toEqual([]);
  });

  test('Executive questions produce distinct live strategies and responses', async ({ page }) => {
    const errors: string[] = [];
    attachStrictErrorGates(page, errors);
    await loginAdmin(page);
    await openHermesWorkroom(page);

    const greeting = await askHermes(page, 'good morning');
    expect(greeting.text).toMatch(/Good morning, Ray/i);

    const priority = await askHermes(page, 'what should we focus on today?');
    expect(priority.strategy).toBe('executive_priority_response');
    expect(priority.text).toMatch(/Focus first|Client live-data flag off|First step/i);

    const rationale = await askHermes(page, 'why that one?');
    expect(rationale.strategy).toBe('followup_rationale_response');
    expect(rationale.text).toMatch(/I chose|comes before/i);

    const feasibility = await askHermes(page, 'is that realistic?');
    expect(feasibility.strategy).toBe('followup_feasibility_response');
    expect(feasibility.text).toMatch(/realistic|bounded scope/i);
    expect(feasibility.text).not.toMatch(/Wave 4A corpus|source file|router/i);

    const blockers = await askHermes(page, 'what would stop us?');
    expect(blockers.strategy).toBe('followup_blockers_response');
    expect(blockers.text).toMatch(/concrete blockers|Mitigation/i);

    const deepDive = await askHermes(page, 'go deeper on number 2');
    expect(deepDive.strategy).toBe('followup_deep_dive_response');
    expect(deepDive.text).toMatch(/Going deeper|Dependencies|Next step/i);

    const risk = await askHermes(page, 'what is our biggest risk right now?');
    expect(risk.strategy).toBe('executive_risk_response');
    expect(risk.text).toMatch(/biggest risk|mitigation|affected area/i);
    expect(risk.text).not.toMatch(/Focus first/i);

    const revenue = await askHermes(page, 'how can we make money today?');
    expect(revenue.strategy).toBe('revenue_action_response');
    expect(revenue.text).toMatch(/fastest revenue action|\$97|Stripe stays test-only|offer/i);
    expect(revenue.text).not.toMatch(/Focus first|biggest risk is/i);

    const stripe = await askHermes(page, 'is Stripe live?');
    expect(stripe.text).toMatch(/test mode|Live activation.*deferred/i);

    const alpha = await askHermes(page, 'can Alpha access Supabase?');
    expect(alpha.text).toMatch(/No\. Alpha|not allowed|client PII/i);

    const task = await askHermes(page, 'turn number 2 into a task');
    expect(task.text).toMatch(/conversation-only|governed|approval/i);
    await expect(page.locator('.nxos-message.hermes').last().getByRole('button', { name: /Prepare governed task/i })).toBeVisible();

    expect(similarity(priority.text, risk.text)).toBeLessThan(0.72);
    expect(similarity(priority.text, revenue.text)).toBeLessThan(0.72);
    expect(similarity(rationale.text, feasibility.text)).toBeLessThan(0.72);
    expect(similarity(feasibility.text, blockers.text)).toBeLessThan(0.72);
    await expectNoHorizontalOverflow(page);
    expect(errors).toEqual([]);
  });

  for (const viewport of [
    { name: 'desktop', width: 1920, height: 1080 },
    { name: 'laptop', width: 1440, height: 900 },
    { name: 'tablet', width: 1024, height: 768 },
    { name: 'mobile', width: 390, height: 844 },
  ]) {
    test(`Workroom production intent flow is responsive on ${viewport.name}`, async ({ browser }) => {
      const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height } });
      const page = await context.newPage();
      const errors: string[] = [];
      attachStrictErrorGates(page, errors);
      await loginAdmin(page);
      await openHermesWorkroom(page);
      const answer = await askHermes(page, viewport.name === 'mobile' ? 'how can we make money today?' : 'what is our biggest risk right now?');
      expect(answer.strategy).toMatch(/revenue_action_response|executive_risk_response/);
      await expectNoHorizontalOverflow(page);
      expect(errors).toEqual([]);
      await context.close();
    });
  }

  test('client cannot access Executive Hermes Workroom', async ({ page }) => {
    test.skip(!personaA.email || !personaA.password, 'Set authenticated Persona A credentials.');
    await loginClient(page);
    await page.goto('/admin#hermes');
    await expect(page.getByRole('heading', { name: /admin access required|admin login/i })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole('heading', { name: /Hermes Workroom/i })).toHaveCount(0);
  });
});
