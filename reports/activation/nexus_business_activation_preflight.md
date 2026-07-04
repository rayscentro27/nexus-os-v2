# Nexus Business Activation Preflight

> INTERNAL ACTIVATION EVIDENCE — RAY REVIEW REQUIRED

- Branch: `main`
- Starting commit: `014027a make Nexus OS operational for internal testing and opportunity discovery`
- Dirty files at lock:
```text
M data/cache/youtube/api_metadata/alec_delpuech.json
 M data/cache/youtube/api_metadata/credit_plug.json
 M data/cache/youtube/api_metadata/michael_ionita.json
 M data/cache/youtube/api_metadata/stedman_waiters.json
 M data/cache/youtube/api_metadata/video_zbAmmnMh5ew.json
 M data/exports/notebooklm/research_bundles/final_daily_research_memory_latest.json
 M reports/manual_publish/daily_operating_cycle_latest.md
 M reports/manual_publish/evening_closeout_cycle_latest.md
 M reports/manual_publish/research_to_money_pipeline_latest.md
 M reports/runtime/ray_review_queue_latest.json
```

## State lock

- Operational now: `/#operations`, reports, Ray Review, System Health, Nexus operator responses, local research/scheduler runner, SEO opportunity engine, trading plan pipeline, marketing previews, setup center, and hypothetical GoClear readiness.
- Preview/mock before this sprint: `/#alpha` was an evaluation fixture page with mock-only provider language. It is now replaced by a direct local conversation workspace.
- Nexus Hermes operator responses: working deterministic responses; workhorse and improvement-loop layers added.
- Schedulers: existing Python operational cycles plus Level-1 research and closeout runners; launchd remains disabled.
- Connectors present/referenced: Supabase, Netlify, GitHub, Resend, Meta, YouTube, NotebookLM, Stripe, Oanda practice, Ollama, OpenRouter, Groq. External/mutating connectors remain disabled or unverified.
- Missing: Alpha-safe provider bridge, public web/search, GSC, Analytics, approved affiliate URLs, and several deployment/automation credentials.
- Static previews: `public/marketing-previews`; Vite copies `public/` to build output.
- Public teaser safety: static `/got-funding/` page is compatible with current Netlify deployment.
- QR: generated locally using macOS CoreImage; no package installed. Default target is `https://nexusv20.netlify.app/got-funding` and requires phone verification.
- Lead capture: Netlify Forms-ready markup with honeypot and consent; no Supabase write or automatic email. Capture activates only on a verified Netlify deploy.
- Safe to proceed: yes. Existing unrelated dirty files remain excluded.
