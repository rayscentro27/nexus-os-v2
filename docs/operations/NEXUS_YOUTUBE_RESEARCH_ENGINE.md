# Nexus YouTube Research Engine

The YouTube research engine is an autonomous internal research lane. It watches approved channels, prepares bounded metadata/backfill candidates, scores transcripts when explicit safe transcript text is available, routes findings to departments, and generates reports for Hermes.

## Current Scope

- Manual fixture import/list.
- Manual dry-run watch.
- Manual bounded backfill dry-run.
- Deterministic transcript scoring profiles.
- Weekly/top YouTube research report.

## Scoring Profiles

Credit/business funding:

- money potential
- GoClear relevance
- SEO potential
- affiliate potential
- content potential
- compliance risk
- implementation difficulty
- urgency
- uniqueness
- testability

AI/online business/marketing:

- offer potential
- product strategy value
- content potential
- automation leverage
- SEO potential
- affiliate potential
- implementation speed
- uniqueness
- testability
- risk

Trading:

- paper strategy potential
- clarity of rules
- backtestability
- risk/reward discussion
- drawdown/risk caution
- market specificity
- educational value
- compliance/safety risk
- paper-only routing

Trading findings route to Trading Lab as paper-only research. Nexus must not recommend live trading, broker execution, or auto-executor use.

## Report

```bash
python3 scripts/research/generate_youtube_research_report.py --dry-run --limit 10 --no-external-ai --json
```

The report does not create Ray Review Queue items unless a future pass identifies true execution decisions.

## Backend Foundation v1

Added foundation scripts:

- `youtube_metadata_connector.py`
- `run_youtube_metadata_check.py`
- `youtube_transcript_availability.py`
- `generate_hermes_youtube_prep_brief.py`
- `youtube_to_seo_affiliate_plan.py`
- `youtube_to_content_experiments.py`

The metadata connector currently reports not configured unless a future safe connector/API is configured.
