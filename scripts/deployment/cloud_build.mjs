import { spawnSync } from 'node:child_process'
import { cpSync, existsSync } from 'node:fs'

const commit = String(process.env.COMMIT_REF || '').trim()
const branch = String(process.env.BRANCH || 'main').trim()
const deployId = String(process.env.DEPLOY_ID || '').trim()
if (!/^[0-9a-f]{40}$/i.test(commit)) {
  console.error('CLOUD_BUILD_BLOCKED: Netlify COMMIT_REF must be a full Git SHA.')
  process.exit(2)
}

const result = spawnSync('npm', ['run', 'build'], {
  stdio: 'inherit',
  env: {
    ...process.env,
    VITE_BUILD_COMMIT: commit,
    VITE_BUILD_BRANCH: branch,
    VITE_BUILD_TIMESTAMP: deployId || new Date().toISOString(),
  },
})
if ((result.status ?? 1) !== 0) process.exit(result.status ?? 1)

// Approved Admin Center (React 19 / Vite 8) is an isolated sub-build served at /admin/.
// /admin/login, /admin/operations and /admin/review stay on the main app (no file shadows them).
const adminEnv = { ...process.env, VITE_BUILD_COMMIT: commit }
const step = (args, cwd) => spawnSync('npm', args, { stdio: 'inherit', cwd, env: adminEnv }).status ?? 1
if (step(['ci', '--no-audit', '--no-fund'], 'admin-app') !== 0) process.exit(3)
if (step(['run', 'build'], 'admin-app') !== 0) process.exit(4)
cpSync('admin-app/dist', 'dist/admin', { recursive: true })
if (!existsSync('dist/admin/index.html') || !existsSync('dist/index.html')) {
  console.error('CLOUD_BUILD_BLOCKED: admin or main index missing after build.')
  process.exit(5)
}
process.exit(0)
