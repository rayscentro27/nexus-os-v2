# Nexus YouTube Real Capture — Status

- generated_at: 2026-06-25
- rating_model_version: v1
- wrapper: scripts/intake/run_existing_youtube_monitor.py

## Was a real capture run? — NO (awaiting a Ray-approved public URL)
The gated real-capture path is **built and verified for safety**, but **no real capture was run**
because no approved public YouTube URL was provided. Per the safety rules, the script does not pick
its own URL, and the only allowlist entry is a disabled placeholder.

| Item | Status |
|---|---|
| Real capture run | **No** — paused for an approved URL |
| Source URL used | none |
| Rows written by table | none (dry-run only wrote reports; `research_sources` still 0) |
| Transcript status | n/a |
| Category / destination / score | n/a (dry-run example: `ignore_or_park` / Ignore/Park / 19) |
| nexus_event proof id | none |
| External AI used | **No** (deterministic only) |
| summarize.py used | **No** |
| v1 `research` table written | **No** |
| Scheduler loaded | **No** |

## What was verified (safe)
- Syntax OK; dry-run runs offline, writes nothing to Supabase (`captured:false`).
- `--approved-only` **refuses** a non-allowlisted URL **before** any yt-dlp/network call.
- Real-capture path uses `yt-dlp --skip-download` (transcript only, no media), bounded `--limit`
  (hard cap 3), dedup by `source_url`, writes only to v2 tables, no external AI.

## To run the one real capture (Ray)
Provide an approved **public** YouTube URL, then either add it to
`config/youtube_sources_allowlist.json` (`enabled:true`) or pass it directly:
```
python3 scripts/intake/run_existing_youtube_monitor.py \
    --source-url "<APPROVED_PUBLIC_YOUTUBE_URL>" --once --limit 1 \
    --no-external-ai --write-events --no-dry-run
```
This will: capture metadata + transcript (if public subs exist), score it (v1), write
`research_sources` + `intake_events` + `transcript_reviews` (+ `research_runs`), and a
`nexus_events` proof. No external AI, no scheduler, no publish/send/trade/deploy.
