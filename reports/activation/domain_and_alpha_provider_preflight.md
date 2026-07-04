# Domain and Alpha Provider Preflight

> INTERNAL ACTIVATION EVIDENCE — NO CLIENT DATA — NO EXTERNAL ACTIONS

- Branch: `main`
- Starting commit: `c0fb258 activate Nexus bots and GoClear lead funnel for operational testing`
- Dirty files at lock: only the known YouTube metadata cache, NotebookLM export, manual-publish reports, and runtime Ray Review queue.
- `public/got-funding/index.html`: present.
- `dist/got-funding/index.html`: produced by the existing Vite public-folder build.
- Root cause: Vite development history fallback and Netlify’s catch-all SPA rewrite had no explicit `/got-funding` rule. A stale deployment initially returned the Nexus SPA. Explicit rewrites now protect both slash variants before the SPA fallback.
- Current QR before correction: `https://nexusv20.netlify.app/got-funding`.
- Corrected primary QR: `https://goclearonline.cc/got-funding/`; Netlify URL remains fallback only.
- Custom domain before correction: not represented in QR/config.
- Netlify form: static build-time POST form with form name, hidden form-name, honeypot, consent, and disclaimer; no Supabase/email code.
- Alpha provider before correction: deterministic local only.
- Ollama: installed (`0.20.5`), local API reachable, and local models detected. It lacked a browser-safe same-origin Alpha bridge.
- Groq: frontend-safe status unknown; no browser call allowed. Server bridge/key required.
- OpenRouter: frontend-safe status unknown; no browser call allowed. Server bridge/key required.
- Real Alpha chat blockers: no same-origin provider endpoint, no runtime status discovery, and no server-side hosted-provider bridge. Live web remains unavailable.
- Safe to proceed: yes.
