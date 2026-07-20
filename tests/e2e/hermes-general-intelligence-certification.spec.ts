import { test, expect, type Page } from 'playwright/test';

const enabled = process.env.E2E_ENABLE_AUTHENTICATED === 'true';
const admin = { email: process.env.E2E_ADMIN_EMAIL, password: process.env.E2E_ADMIN_PASSWORD };

const sequence = [
  'good morning',
  'what time is it',
  'what day is it',
  'what should we focus on today',
  'how can we make money today',
  'why that one',
  'so lets work on the readines reviw journey',
  'what do we need to do first',
  'where did you get that answer from',
  'did we set up department operations and governed automation',
  'do you have any reports',
  'what is the latest Hermes report',
  'do we have any clients',
  'are those real clients or synthetic',
  'how is our system health',
  'can we redesign the command center',
  'what would you change first',
  'help me plan that redesign',
  'create a task for that redesign',
];

const genericFallbackPattern = /My read: answer the immediate question first|I need one focused clarification: what specific decision|unknown context|need a concrete decision|general recommendation|broad category/i;

const holdout = [
  'whats the time in arizona',
  'what date are we on today',
  'where are we at with the departments',
  'did automation departments ship yet',
  'what documents or reports can you see',
  'which report is newest',
  'what talks about Hermes lately',
  'are our customers real or test records',
  'do we got clients',
  'how do you know that',
  'what backs that answer up',
  'is that your opinion or a fact',
  'pick back up with the $97 offer',
  'what should that offer include',
  'break that offer into steps',
  'could the command center be easier to use',
  'what would make the dashboard clearer',
  'dont create anything yet just help me think it through',
  'okay now draft the task',
  'how is are systm health',
  'is stripe production live',
  'is live trading on',
  'can alpha access supabase',
  'what needs approval right now',
  'what should engineering do next',
];

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

async function openHermesWorkroom(page: Page) {
  await page.goto('/admin#hermes', { waitUntil: 'domcontentloaded' });
  await expect(page.getByRole('heading', { name: /Hermes Workroom/i })).toBeVisible({ timeout: 20_000 });
  const textarea = page.locator('textarea[aria-label="Message Hermes"]').first();
  await expect(textarea).toBeVisible({ timeout: 30000 });
  return textarea;
}

function attachErrorGates(page: Page, errors: string[]) {
  page.on('console', (msg) => {
    const text = msg.text();
    if (msg.type() === 'error' && !/favicon|Failed to load resource/i.test(text)) errors.push(`console:${text}`);
  });
  page.on('pageerror', (err) => errors.push(`pageerror:${err.message}`));
}

async function askHermes(page: Page, message: string): Promise<string> {
  const textarea = page.locator('textarea[aria-label="Message Hermes"]').first();
  await textarea.fill(message);
  await page.getByRole('button', { name: /^Send$/ }).click();
  await expect(page.getByText(/Hermes Workroom hit a local rendering error|n is not a function/i)).toHaveCount(0);
  await expect(page.locator('.nxos-message.ray').last()).toContainText(message, { timeout: 15_000 });
  const last = page.locator('.nxos-message.hermes').last();
  await expect(last).toBeVisible({ timeout: 20_000 });
  const text = (await last.locator('p').innerText()).trim();
  expect(text.length).toBeGreaterThan(10);
  expect(text).not.toMatch(genericFallbackPattern);
  return text;
}

function expectSemanticAnswer(prompt: string, answer: string) {
  if (/\b(time|date)\b|what day is it|what date are we on/i.test(prompt)) expect(answer).toMatch(/Phoenix|Arizona|today|AM|PM|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|July|2026/i);
  if (/focus|priority|engineering/i.test(prompt)) expect(answer).toMatch(/focus|priority|next|Engineering|client|Hermes|review/i);
  if (/money|revenue|\$97|offer/i.test(prompt)) expect(answer, prompt).toMatch(/\$97|readiness review|revenue|offer|money/i);
  if (/why|how do you know|source|evidence|fact|opinion/i.test(prompt)) expect(answer, prompt).toMatch(/source|evidence|because|recommendation|fact|interpretation|confidence|came from/i);
  if (/readines|readiness|pick back|break that offer|what should that offer/i.test(prompt)) expect(answer, prompt).toMatch(/readiness review|\$97|offer|journey|deliverable|intake|steps/i);
  if (/department|automation/i.test(prompt)) expect(answer, prompt).toMatch(/Department Operations|Governed Automation|NEXT|PARTIAL|not fully|not production-certified/i);
  if (/report|documents/i.test(prompt)) expect(answer, prompt).toMatch(/report|catalog|approved|Hermes|latest|indexed/i);
  if (/client|customer/i.test(prompt)) expect(answer, prompt).toMatch(/synthetic|test|real|paying|client|customer/i);
  if (/system|stripe|trading|alpha/i.test(prompt)) expect(answer, prompt).toMatch(/system|health|test mode|blocked|not active|Supabase|Alpha|trading/i);
  if (/command center|dashboard|redesign|layout|think it through/i.test(prompt)) expect(answer, prompt).toMatch(/Command Center|dashboard|redesign|layout|attention|blocked|plan/i);
  if (/create a task|draft the task/i.test(prompt)) expect(answer, prompt).toMatch(/conversation-only|governed|task|approval|draft|Ray Review/i);
}

test.describe('Hermes general intelligence certification', () => {
  test.setTimeout(420_000);
  test.skip(!enabled || !admin.email || !admin.password, 'Set authenticated admin credentials.');

  test('Workroom answers broad governed sequence without generic fallback or premature action', async ({ page }) => {
    const errors: string[] = [];
    attachErrorGates(page, errors);

    await loginAdmin(page);
    await openHermesWorkroom(page);
    const answers: Record<string, string> = {};
    for (const prompt of sequence) {
      answers[prompt] = await askHermes(page, prompt);
      expectSemanticAnswer(prompt, answers[prompt]);
    }

    expect(answers['help me plan that redesign']).not.toMatch(/I’ll prepare|governed work request|task created|has been saved/i);
    expect(answers['create a task for that redesign']).toMatch(/conversation-only|governed|task|approval|draft/i);
    expect(errors).toEqual([]);
  });

  test('production holdout paraphrases preserve honesty, provenance, and action separation', async ({ page }) => {
    const errors: string[] = [];
    attachErrorGates(page, errors);

    await loginAdmin(page);
    await openHermesWorkroom(page);
    let passed = 0;
    for (const prompt of holdout) {
      const answer = await askHermes(page, prompt);
      expectSemanticAnswer(prompt, answer);
      passed += 1;
    }
    expect(passed).toBeGreaterThanOrEqual(23);
    expect(errors).toEqual([]);
  });
});
