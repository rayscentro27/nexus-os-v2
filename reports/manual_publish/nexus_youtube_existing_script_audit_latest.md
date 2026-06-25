# Nexus — Existing YouTube/Transcript Script Audit

- generated_at: 2026-06-25
- mission: find the existing Mac Mini / legacy scraper, audit it, design a stable v2 rating pipeline.
- result: a real legacy scraper exists; v2 already has the right tables; built a thin dry-run wrapper
  + canonical rating model + mapping. No scheduler started, no scraping run, nothing published.

---

## 1. Existing script found — YES
**Primary:** `~/nexus-ai/research-engine/` (v1 "Nexus AI"). The real YouTube transcript scraper.

| Field | Finding |
|---|---|
| Script path | `~/nexus-ai/research-engine/collector.py` (+ `channels.py`, `summarize.py`, `strategy_extractor.py`, `strategy_ranker.py`, `supabase_store.py`) |
| Owner/project | legacy v1 `~/nexus-ai` (separate from nexus-os-v2) |
| Language | Python (also a JS variant: `~/nexus-ai/workflows/research_ingestion/transcript_extractor.js` + `youtube_researcher.js`) |
| What it does | Downloads **auto-subtitles/transcripts via yt-dlp** for the last N videos of allowlisted channels, summarizes, extracts/ranks **trading** strategies, stores to Supabase |
| Required env/config (names only) | `COLLECTOR_MAX_VIDEOS`, `TABLE_NAME`, `NEXUS_LLM_BASE_URL`/`OPENROUTER_BASE_URL` (+ provider key), Supabase URL/key; channel list `channels/trading_channels.json` |
| Writes files | Yes — `./transcripts/*` |
| Writes Supabase | Yes — `supabase_store.py` upserts into a **`research`** table (v1 project), deduped by `title` UNIQUE / `on_conflict=title`; has DRY_RUN |
| External APIs | yt-dlp (public YouTube), Supabase, **external AI** (`summarize.py` → OpenAI-compatible gateway / OpenRouter, Gemini fallback) |
| yt-dlp / transcript libs | Yes — `requirements.txt`: `yt-dlp`, `youtube-transcript-api`, pandas, supabase, requests |
| Scheduling | Yes (v1) — launchd: `com.nexus.monetization-research`, `com.nexus.research-worker`, `com.nexus.youtube-channel-poller`, `com.nexus.research-signal-bridge` |
| Dedupes videos | By `title` UNIQUE upsert (title-based, not url/video-id) |
| Logs/proofs | `./transcripts` files + `research` table rows |
| Safe to adapt | The **collector** (yt-dlp, skip-download, channel allowlist, bounded MAX_VIDEOS=3) is safe to reference/wrap. The **summarize** step (external AI) should be optional/off by default in v2. |

Also present in v2 already: `scripts/intake/` (`capture_intake_event.py`, `review_transcript.py`,
`extract_service_opportunity.py`) and `scripts/seed_day8_transcript_intake.py` — deterministic intake
review, but **no YouTube fetch**.

## 2. Reuse / wrap / replace
| Component | Classification |
|---|---|
| `research-engine/collector.py` (yt-dlp transcript capture) | **Wrap with v2 runner** (reference its yt-dlp capture; do not duplicate) |
| `research-engine/summarize.py` (external AI) | **Reference only** — keep OFF by default (`--no-external-ai`); deterministic scoring in v2 |
| `research-engine/strategy_*` (trading focus) | **Reference only** — v2 categories are broader (GoClear/credit/funding first) |
| `supabase_store.py` (writes v1 `research` table) | **Do not use from v2** — v2 writes to its own tables |
| v1 launchd research jobs | **Obsolete for v2 / leave running** — do not touch; v2 schedules independently |
| `scripts/intake/*` (v2) | **Reuse** — v2 deterministic review pattern |

**Chosen approach:** a thin v2 wrapper that runs dry-run first, bounded, deterministic (no external
AI), normalizes to the canonical v1 rating model, and writes to existing v2 tables. **Do not
duplicate the legacy scraper.**

## 3. What was built (this task)
- `docs/operations/NEXUS_VIDEO_RESEARCH_RATING_MODEL.md` — canonical rating model (v1).
- `docs/operations/NEXUS_RESEARCH_SUPABASE_MAPPING.md` — model → existing tables (no new tables).
- `docs/operations/NEXUS_YOUTUBE_SCHEDULE_PLAN.md` + `com.nexus.v2.youtube-monitor.plist.example`
  (scheduler plan; NOT loaded).
- `scripts/intake/run_existing_youtube_monitor.py` — thin wrapper (`--dry-run` default, `--once`,
  `--limit`, `--source-url`, `--no-external-ai`, `--write-events`, `--max-age-days`).

## 4. Dry-run result (verified)
`run_existing_youtube_monitor.py --once --limit 1 --dry-run --no-external-ai --source-url …` →
`{ ok: true, dry_run: true, no_external_ai: true, processed: 1, run_id: null }`. It wrote **nothing**
to Supabase (`research_sources` still 0 rows), only the report. Deterministic scoring worked
(example title with no signal keywords → `ignore_or_park`, score 19, priority `reject`).

## 5. Does YouTube intake write to Supabase today?
- **Legacy (v1):** yes → v1 `research` table (separate project).
- **v2:** not yet from real capture. The wrapper writes to v2 `research_sources` / `intake_events` /
  `transcript_reviews` **only with `--no-dry-run`** (not done here). Dry-run writes nothing.

## 6. What still needs connecting
1. Real capture path: enable the wrapper to shell out to the legacy `collector.py` (yt-dlp) for a
   single `--source-url` and feed the transcript into scoring — gated behind `--no-dry-run`
   `--allow-capture`, after Ray approves.
2. A committed **channel/source allowlist** for v2 (so monitoring isn't ad-hoc URLs).
3. Source Intake & Review UI surface (see schedule/mapping docs) to show score/category/destination.
4. Ray approval to enable the daily launchd schedule (`.plist.example` → loaded).

## 7. Safety confirmations
No scheduler started; no broad scraping; no private/unlisted download; no login/captcha/paywall
bypass; no external AI used (deterministic only); no publish/send/trade/deploy; no Oracle changes;
no secrets printed; `.env` not committed. Build + `nexus:watch` pass (watch: `published: []`,
`already_sent`).
