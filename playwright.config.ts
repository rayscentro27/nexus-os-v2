import { defineConfig } from 'playwright/test'

// Authenticated browser flows can write workflow and customer state. They are
// disabled by default and require an explicitly approved durable test job.
if (process.env.NEXUS_E2E_APPROVED !== '1'
  || !process.env.NEXUS_DURABLE_JOB_ID
  || !process.env.NEXUS_CORRELATION_ID
  || !process.env.NEXUS_APPROVAL_ID) {
  throw new Error('E2E_DISABLED_REQUIRES_APPROVED_DURABLE_JOB')
}

const requestedBaseURL = process.env.E2E_BASE_URL || 'http://127.0.0.1:4173'
const requestedHost = new URL(requestedBaseURL).hostname
if (!['127.0.0.1', 'localhost', '::1'].includes(requestedHost)) {
  throw new Error('E2E_EXTERNAL_TARGET_DENIED')
}

export default defineConfig({
  testDir: './tests/e2e', timeout: 60_000, retries: 0,
  use: {
    baseURL: requestedBaseURL,
    trace: 'off', screenshot: 'off', video: 'off',
    launchOptions: process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : undefined,
  },
  webServer: process.env.E2E_BASE_URL ? undefined : { command: 'VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT=true npm run build && npm run preview -- --host 127.0.0.1 --port 4173', url: 'http://127.0.0.1:4173', reuseExistingServer: true, timeout: 180_000 },
})
