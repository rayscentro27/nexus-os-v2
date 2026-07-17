# Process Cleanup

Date: 2026-07-17

## Temporary Processes Started

Playwright webServer processes were started by Playwright during:

- Persona A focused authenticated test.
- Admin focused authenticated test.
- Full authenticated certification spec.
- Client credit workflow certification.
- Guided client portal certification.

The webServer command was managed by Playwright:

```bash
VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT=true npm run build && npm run preview -- --host 127.0.0.1 --port 4173
```

No manual dev server was left running.

## Cleanup Checks

Commands:

```bash
pgrep -fl "vite|playwright|chromium|chrome|node.*4173|npm run preview" || true
lsof -nP -iTCP:4173 -sTCP:LISTEN 2>/dev/null || true
```

Result:

- No Vite/Playwright/preview listener remained on port 4173.
- `pgrep` only returned the unrelated Chrome Remote Desktop host, not a Wave 0 process.

Process Cleanup Gate: PASS.
