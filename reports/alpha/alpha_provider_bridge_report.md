# Alpha Provider Bridge Report

Alpha now uses same-origin `/api/alpha/status` and `/api/alpha/chat` endpoints.

- `deterministic_local`: always available; no model/web call.
- `ollama_local`: Vite development bridge only; local API health and local model list are detected server-side. No Supabase or browser CORS/key exposure.
- `groq`: Netlify server function only; disabled unless `GROQ_API_KEY` exists server-side.
- `openrouter`: Netlify server function only; disabled unless `OPENROUTER_API_KEY` exists server-side.
- Hosted keys never enter frontend source or responses.
- All provider prompts carry Alpha’s no-client-data, no-Supabase, no-execution, no-guarantee system boundary.
- Live web/search is not part of this bridge and remains unavailable.
