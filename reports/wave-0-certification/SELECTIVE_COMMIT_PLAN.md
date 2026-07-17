# Selective Commit Plan

Date: 2026-07-17

## Proposed Staged Files

| Path | Why It Belongs | Requirement | Verification | Existed Before Sprint | Generated/Sensitive |
|---|---|---|---|---:|---|
| `package.json` | Fixes `npm test` under zsh by quoting E2E exclude glob | Regression certification | `npm test` PASS, 83 files/1,389 tests | yes | no |
| `playwright.config.ts` | Keeps existing 60s timeout needed for authenticated browser suites | Browser certification | Auth, credit workflow, guided portal PASS | yes | no |
| `tests/e2e/authenticated-certification.spec.ts` | Keeps existing admin/client boundary stabilization wait | Browser certification | 11 authenticated tests PASS | yes | no |
| `reports/wave-0-certification/WAVE_0_FINAL_REPORT.md` | Required final certification report | Wave 0 reporting | Report review and secret scan | no | sanitized |
| `reports/wave-0-certification/WAVE_0_WORKTREE_CLASSIFICATION.md` | Required worktree classification | Repository safety | Report review and secret scan | no | sanitized |
| `reports/wave-0-certification/BUILD_DIAGNOSTIC.md` | Required build/type/unit evidence | Build and TypeScript | Report review and secret scan | no | sanitized |
| `reports/wave-0-certification/PLAYWRIGHT_DIAGNOSTIC.md` | Required browser evidence | Persona/admin browser | Report review and secret scan | no | sanitized |
| `reports/wave-0-certification/SUPABASE_MIGRATION_TRUTH.md` | Required migration truth | Migration gate | Report review and secret scan | no | sanitized |
| `reports/wave-0-certification/RLS_CERTIFICATION.md` | Required RLS evidence | RLS gate | Report review and secret scan | no | sanitized |
| `reports/wave-0-certification/STORAGE_UPLOAD_CERTIFICATION.md` | Required storage evidence | Storage gate | Report review and secret scan | no | sanitized |
| `reports/wave-0-certification/PARSER_COMPARISON_CERTIFICATION.md` | Required parser/comparison evidence | Parser/comparison gate | Report review and secret scan | no | sanitized |
| `reports/wave-0-certification/CUSTOMER_ADMIN_PROGRESS_CERTIFICATION.md` | Required journey evidence | Customer/admin journey gate | Report review and secret scan | no | sanitized |
| `reports/wave-0-certification/SECURITY_AND_SECRET_CERTIFICATION.md` | Required security evidence | Security gate | Report review and secret scan | no | sanitized |
| `reports/wave-0-certification/PROCESS_CLEANUP.md` | Required cleanup evidence | Cleanup gate | Report review and secret scan | no | sanitized |
| `reports/wave-0-certification/SELECTIVE_COMMIT_PLAN.md` | Required staging plan | Checkpoint gate | Report review and secret scan | no | sanitized |
| `reports/wave-0-certification/wave_0_manifest.json` | Required manifest | Checkpoint gate | JSON review and secret scan | no | sanitized |

## Excluded Dirty Files

Excluded categories:

- Runtime/cache: `data/cache/**`, `data/runtime/**`, `reports/runtime/**`, `tmp/**`, `test-results/**`.
- Telegram: `reports/telegram/**`, `scripts/ops/nexus_telegram_*`.
- Alpha/research: `data/alpha/**`, `reports/alpha/**`, `reports/hermes/web_search/**`.
- Work orders: `reports/work_orders/**`, `data/runtime/work_order_draft_latest.json`.
- Prior audit docs: `reports/executive-architecture-audit/**`.
- Manual publish/report artifacts: `reports/manual_publish/**`, `reports/nexus_research/**`, `reports/scheduler/**`.
- Unknown local scripts: `collect_router_repair_results.sh`, `review_latest_nexus_reports.sh`.
- Local env files, auth state, caches, previews, screenshots: never staged.

## Staging Command Plan

Explicit paths only:

```bash
git add package.json
git add playwright.config.ts
git add tests/e2e/authenticated-certification.spec.ts
git add reports/wave-0-certification/WAVE_0_FINAL_REPORT.md
git add reports/wave-0-certification/WAVE_0_WORKTREE_CLASSIFICATION.md
git add reports/wave-0-certification/BUILD_DIAGNOSTIC.md
git add reports/wave-0-certification/PLAYWRIGHT_DIAGNOSTIC.md
git add reports/wave-0-certification/SUPABASE_MIGRATION_TRUTH.md
git add reports/wave-0-certification/RLS_CERTIFICATION.md
git add reports/wave-0-certification/STORAGE_UPLOAD_CERTIFICATION.md
git add reports/wave-0-certification/PARSER_COMPARISON_CERTIFICATION.md
git add reports/wave-0-certification/CUSTOMER_ADMIN_PROGRESS_CERTIFICATION.md
git add reports/wave-0-certification/SECURITY_AND_SECRET_CERTIFICATION.md
git add reports/wave-0-certification/PROCESS_CLEANUP.md
git add reports/wave-0-certification/SELECTIVE_COMMIT_PLAN.md
git add reports/wave-0-certification/wave_0_manifest.json
```

Do not use `git add .` or `git add -A`.
