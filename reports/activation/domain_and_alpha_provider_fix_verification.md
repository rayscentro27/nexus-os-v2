# Domain and Alpha Provider Fix Verification

> VERIFIED 2026-07-04 — INTERNAL TESTING EVIDENCE

## Got Funding

- Local Vite `/got-funding`, `/got-funding/`, and `/got-funding/index.html`: all returned **Got Funding? | GoClear Funding Readiness**.
- Build: `dist/got-funding/index.html`, QR SVG/PNG, and print-test page present.
- Public read-only checks: primary domain, `www` redirect, and Netlify fallback all returned HTTP 200 with the teaser title.
- QR SVG target: `https://goclearonline.cc/got-funding/`.
- Netlify form markup: complete and build-time visible.
- Synthetic form submission: not performed, because notification/integration behavior is not yet proven. Exact safe steps are documented.
- Shirt printing: blocked pending two-phone scan plus synthetic capture/deletion proof.

## Alpha

- Deterministic greeting/capability/voice-agent/startup/current-sports responses verified by tests.
- Ollama: installed, reachable, local models detected, and one safe local prompt returned through the same-origin Vite bridge.
- Groq: disabled; server-side key/production bridge verification missing.
- OpenRouter: disabled; server-side key/production bridge verification missing.
- Live web: unavailable.
- Supabase/client data: not connected/blocked.

## Verification totals

- Focused route/provider/Alpha tests: 8 files, 42 tests passed.
- Full suite: 65 files, 1,067 tests passed in one run.
- Production build: passed; existing large-chunk warning only.
- Post-build route artifact test: 3/3 passed.
- External sends, posts, charges, trades, applications, disputes, Supabase writes, and real-client records: 0.
