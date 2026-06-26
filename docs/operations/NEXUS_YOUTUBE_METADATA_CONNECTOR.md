# Nexus YouTube Metadata Connector

`scripts/research/youtube_metadata_connector.py` is a metadata-only connector foundation.

## Current Status

If no safe YouTube metadata connector/API is configured, it returns `not_configured` and still writes a local report.

## Allowed

- channel handle validation
- latest video metadata lookup when a safe connector is configured
- video title, URL, ID, publish date, description snippet, duration, thumbnail URL

## Blocked

- media download
- audio download
- transcript capture
- broad scraping
- scheduler activation
- external AI
- secrets/cookies/tokens in repo

Command:

```bash
python3 scripts/research/youtube_metadata_connector.py --dry-run --mode status --json
```
