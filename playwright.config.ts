import { defineConfig } from 'playwright/test'

export default defineConfig({
  testDir: './tests/e2e', timeout: 30_000, retries: 0,
  use: { baseURL: process.env.E2E_BASE_URL || 'http://127.0.0.1:4173', trace: 'off', screenshot: 'off', video: 'off' },
  webServer: process.env.E2E_BASE_URL ? undefined : { command: 'VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT=true npm run build && npm run preview -- --host 127.0.0.1 --port 4173', url: 'http://127.0.0.1:4173', reuseExistingServer: true, timeout: 180_000 },
})
