# Nexus YouTube Metadata Backfill

Metadata backfill creates safe internal candidates from approved watched YouTube resources.

Dry-run command:

```bash
python3 scripts/research/run_watched_resource_backfill.py --dry-run --input-file tests/fixtures/research/ray_watched_youtube_channels.json --limit 4 --items-per-resource 3 --metadata-only --no-external-ai --json
```

Live metadata backfill is allowed only after a safe metadata connector returns real candidates. It must write only `research_sources`/internal project metadata and proof events. It must not download media, capture transcripts, publish, send, trade, deploy, or schedule anything.

If the connector is not configured, Nexus reports that state and does not run live backfill.
