# Shared Recommendation Layer

## What It Is

A unified scoring and tracking system that connects Hermes, Alpha, and Nexus recommendations into a single ranked list. One schema, one composite score, one follow-up mechanism — regardless of which source generated the recommendation.

## Why It Exists

Before this layer, Hermes, Alpha, and Nexus each had their own scoring formats, ranking logic, and follow-up mechanisms. This made it impossible to:
- Compare recommendations across sources
- Get a unified "what should we do next?" answer
- Track follow-up status consistently
- Generate cross-source summaries for /report

## Architecture

```
Hermes (web search)  ──→ ingest_hermes() ──→ ┌─────────────────────┐
Alpha (research)     ──→ ingest_alpha()  ──→ │  Recommendation      │
Nexus (system)       ──→ ingest_nexus()  ──→ │  Engine              │
                                              │  (shared schema)     │
                                              └─────────┬───────────┘
                                                        │
                                              ┌─────────▼───────────┐
                                              │  Unified ranked      │
                                              │  recommendations     │
                                              │  + follow-up         │
                                              └─────────────────────┘
```

## Scoring Dimensions (7)

| Dimension | Range | Weight | Description |
|-----------|-------|--------|-------------|
| speed_to_value | 0-10 | 1.0x | How fast can this produce measurable results? |
| cost_to_execute | 0-10 | 1.0x | How affordable is the initial attempt? |
| fit_goclear | 0-10 | 1.5x | How well does this serve GoClear credit readiness? |
| fit_nexus | 0-10 | 1.0x | How well does this serve Nexus platform? |
| ease_of_execution | 0-10 | 0.8x | How straightforward is implementation? |
| proof_quality | 0-10 | 0.7x | How strong is the evidence or source? |
| risk_adjustment | -3 to +3 | 1.0x | Risk penalty or bonus |

**Composite formula**: weighted_sum / total_weight

## Source Mapping

### Alpha → Unified
- Alpha's 5 dimensions (speed_to_value, cost, difficulty, risk, relevance) map to 7 unified dimensions
- Alpha risk=10 maps to unified risk_adjustment=+3; risk=1 maps to -3
- Proof quality defaults to 5 (neutral)

### Hermes → Unified
- Hermes already uses 7 dimensions; direct mapping with renamed fields
- `speed_to_money` → `speed_to_value`, `cost_to_try` → `cost_to_execute`, etc.

### Nexus → Unified
- System recommendations use default scores (5s) unless explicitly provided
- Auto-tagged as `system` source

## Files

| File | Purpose |
|------|---------|
| `scripts/recommendations/recommendation_schema.py` | Canonical schema, scoring, persistence |
| `scripts/recommendations/recommendation_engine.py` | Cross-source ingestion, querying, summaries |
| `scripts/recommendations/__init__.py` | Package marker |
| `data/recommendations/recommendations_latest.json` | Active recommendations |
| `data/recommendations/history/` | Timestamped snapshots |
| `tests/test_shared_recommendations.py` | 18 tests covering all operations |

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/recs top [n]` | Top N recommendations by composite score |
| `/recs summary` | Overview: total, by status, by source |
| `/recs next` | Top 3 actionable next steps |
| `/recs approve <n>` | Approve recommendation number n |
| `/recs reject <n> [reason]` | Reject recommendation number n |

## Recommendation Status Flow

```
new → acknowledged → in_progress → approved → completed
  ↘       ↘              ↘            ↘
   rejected  rejected      rejected     superseded
```

## Usage in Code

```python
from recommendation_schema import new_recommendation, append_recommendation
from recommendation_engine import ingest_alpha, ingest_hermes, ingest_nexus, get_top_recommendations

# Alpha ingestion (automatic from Telegram bridge)
ingest_alpha("credit monitoring tools", ranked_ideas, avg_score, category="client_acquisition")

# Hermes ingestion (automatic from research advisor)
ingest_hermes("best credit tools", search_result, advisory_answer)

# Nexus system recommendation
ingest_nexus("Add error monitoring", "System needs better alerting", priority="high")

# Query
top = get_top_recommendations(n=5)
```

## Deduplication

Recommendations with the same title + source within 24 hours are deduplicated. If the same research runs twice, only the first is stored.

## Persistence

- Active recommendations: `data/recommendations/recommendations_latest.json`
- Historical snapshots: `data/recommendations/history/snapshot_<timestamp>.json`
- Max 100 historical snapshots (oldest auto-pruned)
