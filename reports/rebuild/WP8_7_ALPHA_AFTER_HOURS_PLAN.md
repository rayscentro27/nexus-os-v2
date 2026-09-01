# WP8.7 Alpha After-Hours Plan

## Bounded configuration

Recommended first window: one bounded daily run, LAST_30_DAYS default, rotate one theme per cycle across TRADING/BUSINESS/MARKETING/AI_NEXUS, max 4 queries, 12 results, 1 transcript, 4 page fetches, 4 repos, 2 forums, 8 research calls, 1 AI call, 180 seconds.
## Operator command

`python3 scripts/alpha/run_alpha_discovery_cycle.py --theme TRADING --question "bounded current strategy discovery" --window LAST_30_DAYS --json` with Ray-approved source URLs/provider discovery. Do not start an indefinite crawler.
