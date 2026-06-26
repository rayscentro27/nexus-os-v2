# Nexus Watched Resource Automation

Watched resources are durable research assets. Ray can save a channel, feed, website, program page, newsletter archive, or manual URL list, then Nexus can backfill historical/high-value content and later check for new items.

## Resource Types

- YouTube channel
- YouTube playlist
- YouTube video
- RSS feed
- affiliate website
- affiliate program page
- competitor website
- SEO blog
- credit repair resource
- business funding resource
- business credit resource
- online business opportunity resource
- AI tools directory
- AI automation blog/channel
- trading strategy resource
- newsletter/archive
- manual URL list

## Fields

`resource_id`, `resource_name`, `resource_type`, `resource_url`, `category`, `department_destination`, `watch_frequency`, `enabled`, `approved_by_ray`, `risk_level`, `scrape_policy`, `last_checked_at`, `last_seen_item_id`, `last_seen_item_url`, `last_seen_item_published_at`, `backfill_status`, `watch_status`, `notes`, `created_at`, and `updated_at`.

## Backfill Mode

Command:

```bash
python3 scripts/research/run_watched_resource_backfill.py --dry-run --limit 3 --no-external-ai --json
```

Backfill is bounded, dry-run first, duplicate-aware, and proof-logged when live. It does not broad scrape, capture media, use external AI, or touch private data.

## Watch Mode

Command:

```bash
python3 scripts/research/run_watched_resource_watch.py --dry-run --limit 3 --no-external-ai --json
```

Watch mode checks approved/enabled resources for new items, compares against last-seen metadata, creates candidates only for new items, and routes by deterministic score. Scheduler activation remains disabled until Ray approves.

## Registry

Command:

```bash
python3 scripts/research/watched_resource_registry.py --dry-run --json
```

Resources are disabled by default unless explicitly approved/enabled.

## Ray YouTube resources

Ray's first approved/enabled manual YouTube watchlist is stored in `tests/fixtures/research/ray_watched_youtube_channels.json`.

These resources are enabled for manual dry-run/watch only. Scheduler activation remains disabled until Ray approves it separately.
