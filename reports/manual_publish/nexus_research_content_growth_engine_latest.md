# Nexus Research + Content Growth Engine v1

Generated: 2026-06-26

## Summary

Nexus OS v2 now has a deterministic research and content growth layer that can turn approved resources, research topics, transcripts, affiliate programs, SEO keywords, content ideas, experiments, and content test imports into department-ready project card candidates.

No scheduler was activated. No capture, scraping, external AI, publish, send, trade, or deploy action was performed by the research/content runners.

## Scripts Added

- `scripts/research/watched_resource_registry.py`
- `scripts/research/run_watched_resource_backfill.py`
- `scripts/research/run_watched_resource_watch.py`
- `scripts/research/research_source_scout.py`
- `scripts/research/youtube_channel_watchlist.py`
- `scripts/research/youtube_transcript_review.py`
- `scripts/research/research_scoring.py`
- `scripts/research/affiliate_opportunity_tracker.py`
- `scripts/research/seo_keyword_scout.py`
- `scripts/research/seo_affiliate_content_planner.py`
- `scripts/research/research_to_experiment.py`
- `scripts/research/content_opportunity_lab.py`
- `scripts/research/content_test_tracker.py`

## Supported Outputs

- `watched_resource`
- `watched_resource_update`
- `youtube_transcript_review`
- `affiliate_opportunity`
- `seo_keyword_opportunity`
- `seo_affiliate_content_plan`
- `research_experiment`
- `content_opportunity`
- `content_test_result`

## Departments Affected

- Source Intake
- Opportunity Lab
- SEO / Marketing
- Creative Studio
- GoClear / Apex Revenue Hub
- Ops & Improvements
- Trading Lab, paper/research only
- Command Center

## Dry-Run Results

- Watched resource registry: passed, 3 resources, 0 created.
- Watched resource backfill: passed, 3 scanned, 0 created.
- Watched resource watch: passed, 3 new-item candidates, 0 created.
- Research source scout: passed, 5 candidates, 0 created.
- YouTube channel watchlist: passed, 2 channels, 0 enabled by default.
- YouTube transcript review: passed, 1 review candidate, 0 created.
- Affiliate opportunity tracker: passed, 2 program candidates, 0 created.
- SEO keyword scout: passed, 3 keyword candidates, 0 created.
- SEO-to-affiliate content planner: passed, 3 plan candidates, 0 created.
- Research-to-experiment conversion: passed, 5 experiment candidates, 0 created.
- Content opportunity lab: passed, 3 content opportunities, 0 created.
- Content test tracker: passed, 2 content test rows, 0 created.

## Safety Confirmation

- Scheduler activation: disabled.
- Cron/launchd/systemd: not created.
- Capture / yt-dlp: not run.
- Publish/send/trade/deploy: not run.
- Broker API: blocked in `nexus:watch` by default.
- External AI: not used by these runners.
- Secrets/cookies/tokens: not added.
- Live sample write: not run.

## Verification

- `npm run build`: passed.
- `npm run nexus:watch`: passed after default-blocking email send and broker status checks.
- Python compile check: passed.

## Next Recommendation

Ray should approve the first real watched resource list, then run a bounded dry-run watch against those approved resources before allowing any schedule-ready automation.
