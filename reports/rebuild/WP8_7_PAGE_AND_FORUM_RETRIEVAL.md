# WP8.7 Page and Forum Retrieval

## Real retrieval

REAL_PAGE_RETRIEVAL=PASS. The run retrieved mobile-detailing, SEO, GitHub, and trading pages through a bounded public-read request. Forum URLs were classified as COMMUNITY_EXPERIENCE, not primary authority.
## Failure handling

Python TLS failure was observed and recovered with curl fallback. A failed page remains failed; no snippet is promoted to evidence. Anti-bot, redirect, and unavailable-content states remain explicit.
