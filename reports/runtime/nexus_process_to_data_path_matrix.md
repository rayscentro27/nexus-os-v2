# Nexus Process-to-Data-Path Matrix

**Generated**: 2026-07-05

---

## Matrix: Process → Data Source → Supabase Project → Write Path

| Process | Data Source | Supabase Project | Write Path | Activation Mode |
|---------|------------|-----------------|------------|-----------------|
| Hermes Chat (Edge) | Env vars (LLM providers) | None (no DB) | None | SANDBOX_TEST |
| Hermes Search (Edge) | Env vars (search providers) | None (no DB) | None | SANDBOX_TEST |
| Alpha Search (Netlify) | SearXNG via env | None | None | SANDBOX_TEST |
| Alpha URL Review (Netlify) | Firecrawl via env | None | None | SANDBOX_TEST |
| Alpha Provider (Netlify) | OpenRouter/Gemini/Ollama | None | None | SANDBOX_TEST |
| Supabase Client (Frontend) | VITE_SUPABASE_URL | Current v2 | READ only | OBSERVE |
| DB Service (Frontend) | VITE_SUPABASE_URL | Current v2 | READ only | OBSERVE |
| Hermes Context Adapter | VITE_SUPABASE_URL | Current v2 | READ only | OBSERVE |
| Client Dashboard Data | VITE_SUPABASE_URL | Current v2 | READ only | OBSERVE |
| Department Feeders (18) | SUPABASE_URL + service role | Current v2 | WRITE | DRY_RUN |
| Seed Scripts (Python) | SUPABASE_URL + service role | Current v2 | WRITE | SANDBOX_TEST |
| Social Publish | SUPABASE_URL + service role | Current v2 | WRITE | DRY_RUN |
| Nexus Runner | SUPABASE_URL + service role | Current v2 | WRITE | DRY_RUN |
| YouTube Researcher | Local files + API | None | Local only | OBSERVE |
| NotebookLM | Local files | None | Local only | OBSERVE |
| Trading Lab | OANDA env vars | None | Local only | SANDBOX_TEST |
| Research Engine | Local files | None | Local only | OBSERVE |
| Got Funding | Netlify forms | None | Netlify | APPROVED_LIVE |
| Command Center UI | Local data files | None | Local only | OBSERVE |
| Client Portal | VITE_SUPABASE_URL | Current v2 | READ | OBSERVE |
| Ray Review | Local data + Supabase | Current v2 | READ/WRITE | OBSERVE |
