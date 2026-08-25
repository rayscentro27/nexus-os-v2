# Executive Portfolio Loop V1

The Executive Portfolio Loop is a deterministic planning layer above the
existing Phase 15 scheduler, business loops, Product Evolution, Release
Recovery, Alpha research, Builder/Codex, receipts, Mission Control, and Daily
Brief. It selects bounded work; those existing systems remain the executors.

## Authority

The portfolio may prioritize, park, queue internal work, and recommend an
approval. It cannot approve or deploy production, authorize retries, send
external outreach, change security boundaries, access secrets, synthesize a
human result, or enable live/funded trading.

## Objectives and lanes

Objectives use the canonical `PortfolioObjective` fields in
`scripts/nexus_agent_platform/executive_portfolio.py`. Initial lanes are
`RELIABILITY`, `PRODUCT`, `BUSINESS`, `INTELLIGENCE`, `RESEARCH`, and
`MAINTENANCE`. The current seed recognizes Voice recovery, Mission Control
freshness, Experience 2.0, Admin UX, GoClear revenue, opportunity/SEO work,
Forex research, and Creative Intelligence research without marking any of
them complete without evidence.

## Priority and budget

Scoring is deterministic and combines business/revenue/product value,
urgency, risk, readiness, dependencies, staleness, human gates, and repair
effort. Non-critical objectives receive diminishing priority after repair
cycles or disproportionate effort. One objective per lane is selected per
bounded cycle, preventing a single incident from monopolizing the portfolio.
The policy weights are Product 40%, Business 40%, Reliability 25%,
Intelligence 20%, Research 10%, and Maintenance 5%; these are slot weights,
not invented human-hour claims.

## Gates and blockers

Human-only objectives become `WAITING_HUMAN` with an exact requested action and
remain parked while other lanes continue. Internal repair is capped at two
cycles per unique signature; exhaustion parks or escalates the objective.
Credential, security, external-service, and subjective blockers are not
silently repaired.

## Runtime and observability

Phase 15 calls the portfolio step inside its existing one-shot cycle. It does
not create a scheduler or worker. The bounded receipt is
`reports/phase16a/executive_portfolio_latest.json`; the concise brief is
`reports/phase16a/executive_daily_brief.md`. Mission Control reads the
persisted portfolio model and reports `UNKNOWN` when it is absent or stale.
Trust metrics include autonomous progress, human interruption, portfolio
stall, and objective monopoly rates.
