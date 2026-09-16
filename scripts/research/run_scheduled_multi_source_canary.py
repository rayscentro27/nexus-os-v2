#!/usr/bin/env python3
"""Exercise the normal watched-resource router with approved public sources."""
from __future__ import annotations

import json
from scheduled_research_router import process_scheduled_batch


ITEMS = [
    {"source_type": "YOUTUBE_VIDEO", "source_id": "PVdS3r1EjrU", "source_url": "https://www.youtube.com/watch?v=PVdS3r1EjrU", "title": "The Key to Unlimited Funding The Real Hack", "category": "business_funding"},
    {"source_type": "WEB_PAGE", "source_id": "python-home", "source_url": "https://www.python.org/", "title": "Python home", "category": "technology"},
    {"source_type": "GITHUB_REPO", "source_id": "mvanhorn/last30days-skill", "source_url": "https://github.com/mvanhorn/last30days-skill", "title": "mvanhorn/last30days-skill", "category": "deep_research"},
    {"source_type": "LAST_30_DAYS", "source_id": "last30days-live-commits", "source_url": "https://github.com/mvanhorn/last30days-skill", "title": "Last 30 days live repository activity", "category": "recency"},
    {"source_type": "SEO_RESEARCH", "source_id": "google-seo-starter", "source_url": "https://developers.google.com/search/docs/fundamentals/seo-starter-guide", "title": "Google SEO Starter Guide", "category": "seo"},
]


def main() -> int:
    print(json.dumps(process_scheduled_batch(ITEMS), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
