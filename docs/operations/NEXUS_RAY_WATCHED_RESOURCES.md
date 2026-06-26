# Nexus Ray Watched Resources

Ray's first real watched YouTube resources are stored in `tests/fixtures/research/ray_watched_youtube_channels.json`.

## Channels

- Credit Plug: credit repair, business credit, business funding. Routes to Source Intake, Opportunity Lab, SEO / Marketing, GoClear / Apex, and Creative Studio.
- Michael Ionita: online business, AI tools, marketing, automation, product strategy. Routes to Source Intake, Opportunity Lab, SEO / Marketing, Creative Studio, and Ops & Improvements.
- Alec Delpuech: online business, AI tools, marketing, content strategy. Routes to Source Intake, Opportunity Lab, SEO / Marketing, Creative Studio, and Ops & Improvements.
- Stedman Waiters: trading strategy, online business, market research. Routes to Source Intake, Trading Lab, Opportunity Lab, and SEO / Marketing. Trading stays paper-only.

## Rules

- Enabled means manual dry-run/watch is allowed.
- Enabled does not activate any scheduler.
- Scrape policy is metadata/transcript-only, bounded, no media download.
- No channel contents or current videos are claimed until checked.
- Internal review/scoring/routing does not go to Ray Review Queue.
- Ray Review Queue is only for campaign-ready, send-ready, publish-ready, scheduler-ready, client-contact, production-change, or live trading/execution items.

## Commands

```bash
python3 scripts/research/watched_resource_registry.py --dry-run --input-file tests/fixtures/research/ray_watched_youtube_channels.json --json
python3 scripts/research/youtube_channel_watchlist.py --dry-run --input-file tests/fixtures/research/ray_watched_youtube_channels.json --list --json
python3 scripts/research/run_watched_resource_backfill.py --dry-run --input-file tests/fixtures/research/ray_watched_youtube_channels.json --limit 4 --items-per-resource 3 --no-external-ai --json
```
