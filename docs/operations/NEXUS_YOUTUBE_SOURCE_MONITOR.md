# Nexus YouTube Source Monitor (v2)

Wrapper: `scripts/intake/run_existing_youtube_monitor.py`. Pairs with the canonical
`NEXUS_VIDEO_RESEARCH_RATING_MODEL.md` and `NEXUS_RESEARCH_SUPABASE_MAPPING.md`.

## What it does
- **Default: DRY-RUN** — no network, no yt-dlp, no external AI. Deterministic scoring on title/url
  only; writes nothing to Supabase; writes a report.
- **Real capture (`--no-dry-run`)** — yt-dlp **transcript/subtitle extraction on PUBLIC videos**
  (`--skip-download`, never downloads media), bounded by `--limit` (hard cap 3), dedup by
  `source_url`, deterministic rating (no external AI), writes to **v2 tables only** + a
  `nexus_events` proof.
- **Never:** broad scraping, media download, login/captcha/paywall/rate-limit bypass, external AI on
  transcripts, `summarize.py`, or the v1 `research` table.

## Flags
`--dry-run` (default) · `--no-dry-run` (enable real capture+writes) · `--once` · `--limit N`
(≤3) · `--source-url URL` · `--channel-url URL` · `--playlist-url URL` · `--no-external-ai`
(default on) · `--write-events` · `--max-age-days N` · `--approved-only` (require allowlist match).

## Capture details (real mode)
1. Metadata via `yt-dlp -J --skip-download` → title, channel, upload_date, description, id. Skips
   anything not `availability=public`.
2. Transcript via `yt-dlp --skip-download --write-auto-sub --write-sub --sub-lang en.* --convert-subs
   vtt`; VTT parsed to plain text. If no subs → `transcript_status=unavailable` and the source
   metadata is still written.
3. Deterministic rating (canonical v1) on title+transcript+description.
4. Writes: `research_sources` (canonical source + full rating in `metadata`), `intake_events`,
   `transcript_reviews`; `research_runs` per run; `nexus_events` proof (`youtube_source_reviewed`).
   Destination routing per the mapping doc (no destination row is auto-created without Ray approval).
5. Reports: `reports/runtime|manual_publish/nexus_youtube_monitor_latest.md` and
   `reports/manual_publish/nexus_youtube_real_capture_latest.md`.

## Approved-source allowlist
`config/youtube_sources_allowlist.json` — only `enabled:true` entries pass `--approved-only`. Ray
approves additions; no random channels; no private/unlisted.

## UI readiness (not built in this task)
- The **capture path exists (CLI)**. Source rows + reviews now land in v2 tables.
- **Source Intake & Review UI submission is still TODO** — a tab to submit a URL, show transcript
  status, score, category, destination, reason, and an "Ask Hermes" button (reads the safe summary).
- Current real capture is **CLI / manual / approved-only**. **Automatic schedule is NOT enabled**
  (see `NEXUS_YOUTUBE_SCHEDULE_PLAN.md`; `.plist.example` not loaded).

## Commands
```
# dry-run (safe, offline)
python3 scripts/intake/run_existing_youtube_monitor.py --once --limit 1 --dry-run --no-external-ai \
    --source-url "https://www.youtube.com/watch?v=APPROVED"
# one gated real capture (approved public URL)
python3 scripts/intake/run_existing_youtube_monitor.py --source-url "https://www.youtube.com/watch?v=APPROVED" \
    --once --limit 1 --no-external-ai --write-events --no-dry-run
```
