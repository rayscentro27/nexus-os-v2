# Alpha URL Review Cost Controls

## Limits
- Max 10 URL reviews per day per browser session (localStorage).
- Max 1 Firecrawl extraction call per URL review.
- Max 1 hosted model call per URL review if Ray opts into summarization/evaluation.
- No crawl by default.
- No autonomous loops.

## Tracking Fields
- `urlReviewCalls` - incremented on every URL review attempt.
- `urlReviewCalls` is checked against `MAX_URL_REVIEW_CALLS_PER_DAY` (10).
- `blockedDeepCalls` - still enforced for Deep Mode approval gating.
- `estimated_spend_usd` - only populated when an actual hosted model call occurs with known pricing.
- `fallbackCount` - incremented on every failed URL review or fallback path.

## UI Labels
- URL review calls: `{usage.urlReviewCalls || 0} / {usage.maxUrlReviews || 10}`
- Policy line: "One message = max 1 hosted call + 1 search/url-review call; no autonomous loops."

## Backend Limits
- Single URL per request (extracted from prompt).
- Max content chars before model: 12,000.
- Timeout: 15 seconds.
- Failed extraction does not fake content.
