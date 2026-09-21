import { spawnSync } from 'node:child_process'

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
process.exit(result.status ?? 1)
