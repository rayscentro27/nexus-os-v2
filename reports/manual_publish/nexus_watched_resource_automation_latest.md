# Nexus Watched Resource Automation

Generated: 2026-06-26

## Summary

Watched resources are now modeled as long-term Nexus assets. A watched resource can be registered, backfilled in bounded mode, checked in watch mode, scored deterministically, routed to a department, and converted into project card candidates.

## Supported Resource Types

- YouTube channel
- YouTube playlist
- YouTube video
- RSS feed
- Affiliate website
- Affiliate program page
- Competitor website
- SEO blog
- Credit repair resource
- Business funding resource
- Business credit resource
- Online business opportunity resource
- AI tools directory
- AI automation blog/channel
- Trading strategy resource
- Newsletter/archive
- Manual URL list

## Modes

- Backfill Mode: bounded catch-up over approved sample or registered resources.
- Watch Mode: checks approved/enabled resources for new items and avoids duplicates.

## Safety Gates

- Dry-run default.
- Bounded `--limit`.
- Approved/enabled resources required for live watch behavior.
- No broad scraping.
- No scheduler activation.
- No external AI.
- No capture by default.
- No publish/send/trade/deploy.
- Trading outputs remain paper/research only.

## Dry-Run Results

- Registry dry-run: passed, 3 sample resources.
- Backfill dry-run: passed, 3 resources scanned.
- Watch dry-run: passed, 3 synthetic new item candidates.
- YouTube watchlist dry-run: passed, 2 disabled sample channels.
- YouTube transcript review dry-run: passed, 1 transcript scored.

## Reports Written

- `reports/runtime/watched_resource_registry_latest.json`
- `reports/runtime/watched_resource_backfill_latest.json`
- `reports/runtime/watched_resource_watch_latest.json`
- `reports/runtime/youtube_channel_watchlist_latest.json`
- `reports/runtime/youtube_transcript_review_latest.json`

## Next Recommendation

Ray should move selected real public resources into the registry, explicitly approve and enable them, then run `run_watched_resource_watch.py` in dry-run mode before any bounded live metadata write.
