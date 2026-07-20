import { expect, test, type Page } from 'playwright/test';

const enabled = process.env.E2E_ENABLE_AUTHENTICATED === 'true';
const admin = { email: process.env.E2E_ADMIN_EMAIL, password: process.env.E2E_ADMIN_PASSWORD };

type Turn = {
  prompt: string;
  checks: RegExp[];
  noWork?: boolean;
  createsTaskDraft?: boolean;
  createsRayReview?: boolean;
};

const genericFallback = /My read: answer the immediate question first|I need one focused clarification|allowed unknown context|general recommendation, a Nexus build plan/i;
const noExecution = /nothing has been created|not execution|conversation-only|nothing has been saved|no task|not been assigned|not been approved|not been executed/i;
const governedTaskDraft = /governed|task draft|draft-only|conversation-only|nothing has been saved|requires/i;
const rayReviewDraft = /Ray Review|review request|approval|Hermes cannot approve|conversation-only|requires/i;

const sequence: Turn[] = [
  { prompt: 'good morning', checks: [/morning|Ray|Hermes/i] },
  { prompt: 'did we build department operations', checks: [/Department Operations|Wave 4|active|PARTIAL|department/i] },
  { prompt: 'what departments are active', checks: [/Operations|Engineering|Research|Knowledge|Credit and Funding/i] },
  { prompt: 'how is Operations doing', checks: [/Operations|open|blocked|approval|health|HEALTHY|DEGRADED/i] },
  { prompt: 'what is Engineering working on', checks: [/Engineering|Hermes provider-state reconciliation|Engineering Lead|DRAFT_ONLY/i] },
  { prompt: 'what is blocked in Credit and Funding', checks: [/Credit and Funding|blocked|Ray approval|required|readiness/i] },
  { prompt: 'what needs my approval', checks: [/approval|Ray Davis|Ray Review|Credit and Funding|Engineering/i] },
  { prompt: 'which department has the biggest risk', checks: [/Engineering|risk|P0_COMPANY|provider-state|critical/i] },
  { prompt: 'why that one', checks: [/because|risk|priority|P0|Engineering|evidence/i] },
  { prompt: 'what completed recently', checks: [/completed|Knowledge|stale Hermes report evidence|verification|PASS/i] },
  { prompt: 'what is overdue', checks: [/overdue|none|no overdue|0/i] },
  { prompt: 'what does Engineering need from me', checks: [/Engineering|Ray|approval|provider-state|needs/i] },
  { prompt: 'where did you get that answer from', checks: [/source|evidence|previous answer|Department Operations|tool/i] },
  { prompt: 'prepare a plan for the top blocked item', checks: [/Plan, not execution|blocked|first step|Ray approval|readiness/i], noWork: true },
  { prompt: 'do not create a task yet', checks: [/do not create|nothing|no task|not execution/i], noWork: true },
  { prompt: 'what would the first step be', checks: [/first step|Ray approval|deliverable|evidence|readiness/i], noWork: true },
  { prompt: 'okay create a governed task draft for that first step', checks: [governedTaskDraft], createsTaskDraft: true },
  { prompt: 'prepare a Ray Review request for it', checks: [rayReviewDraft], createsRayReview: true },
];

function attachErrorGates(page: Page, errors: string[]) {
  page.on('console', (msg) => {
    const text = msg.text();
    if (msg.type() === 'error' && !/favicon|Failed to load resource/i.test(text)) errors.push(`console:${text}`);
  });
  page.on('pageerror', (error) => errors.push(`pageerror:${error.message}`));
  page.on('requestfailed', (request) => {
    const failure = request.failure()?.errorText || '';
    if (!/favicon|net::ERR_ABORTED/i.test(request.url() + failure)) errors.push(`requestfailed:${request.url()}:${failure}`);
  });
}

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

async function openHermes(page: Page) {
  await page.goto('/admin#hermes', { waitUntil: 'domcontentloaded' });
  await expect(page.getByRole('heading', { name: /Hermes Workroom/i })).toBeVisible({ timeout: 20_000 });
  await expect(page.locator('textarea[aria-label="Message Hermes"]').first()).toBeVisible({ timeout: 30_000 });
}

async function askHermes(page: Page, prompt: string) {
  await page.locator('textarea[aria-label="Message Hermes"]').first().fill(prompt);
  await page.getByRole('button', { name: /^Send$/ }).click();
  await expect(page.locator('.nxos-message.ray').last()).toContainText(prompt, { timeout: 15_000 });
  const last = page.locator('.nxos-message.hermes').last();
  await expect(last).toBeVisible({ timeout: 25_000 });
  const text = (await last.locator('p').innerText()).trim();
  const trace = {
    mode: (await last.getAttribute('data-hermes-mode')) || '',
    intent: (await last.getAttribute('data-hermes-intent')) || '',
    strategy: (await last.getAttribute('data-hermes-strategy')) || '',
  };
  return { text, trace };
}

test.describe('Department Operations live Hermes certification', () => {
  test.setTimeout(360_000);
  test.skip(!enabled || !admin.email || !admin.password, 'Set authenticated admin credentials.');

  test('Hermes answers department operations questions with evidence and action separation', async ({ page }) => {
    const errors: string[] = [];
    attachErrorGates(page, errors);

    await loginAdmin(page);
    await openHermes(page);

    for (const turn of sequence) {
      const answer = await askHermes(page, turn.prompt);
      expect(answer.text, turn.prompt).not.toMatch(genericFallback);
      for (const check of turn.checks) expect(answer.text, turn.prompt).toMatch(check);
      if (turn.noWork) {
        expect(answer.text, turn.prompt).toMatch(noExecution);
        expect(answer.text, turn.prompt).not.toMatch(/task draft|Ray Review request|I.ll prepare/i);
      }
      if (turn.createsTaskDraft) expect(answer.text, turn.prompt).toMatch(governedTaskDraft);
      if (turn.createsRayReview) expect(answer.text, turn.prompt).toMatch(rayReviewDraft);
    }

    await expect(page.getByText(/Hermes Workroom hit a local rendering error|n is not a function/i)).toHaveCount(0);
    expect(errors).toEqual([]);
  });
});
