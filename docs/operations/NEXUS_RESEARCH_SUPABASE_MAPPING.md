# Nexus Research → Supabase Mapping (canonical, v1)

Pairs with `NEXUS_VIDEO_RESEARCH_RATING_MODEL.md`. Goal: **stop changing destination logic.** The
canonical rating model maps onto **existing v2 tables** — **no new tables are required**. Rich
rating fields that have no dedicated column live in each table's `metadata jsonb` under
`rating_model_version: v1`.

## Table existence (verified in project iqjwgpnujbeoyaeuwehj)
All present: `research_runs` (0), `research_sources` (0), `intake_events` (10),
`transcript_reviews` (5), `orientation_notes` (5), `dispositions` (5),
`monetization_opportunities` (2), `improvement_candidates` (17), `seo_opportunities` (0),
`creative_assets` (14), `trading_strategy_candidates` (0), `nexus_lessons` (1), `nexus_events` (348).
(`service_opportunities` does not exist — not needed for this pipeline.)

## Canonical role → table
| Pipeline role | Table | Notes |
|---|---|---|
| Batch/run log | `research_runs` | one row per monitor run (question/research_type=`youtube_monitor`, status, summary) |
| **Source capture (canonical)** | **`research_sources`** | one row per source. Canonical home of source identity + full v1 rating in `metadata`. |
| Intake log / raw transcript | `intake_events` | `source_type`, `source_url`, `title`, `raw_text`=transcript, `status`, `category` |
| **Review / rating (canonical)** | **`transcript_reviews`** | scores + decision + recommendation; links to `intake_events` |
| Orientation note | `orientation_notes` | short "what is this / what should Nexus do" summary |
| Routing decision | `dispositions` | `subject_table`+`subject_id` → `disposition` (= priority/destination) |
| Opportunity destination | `monetization_opportunities` | money/affiliate/client opportunities |
| Ops/system destination | `improvement_candidates` | system_improvement / ai_tooling / operations |
| SEO destination | `seo_opportunities` | seo_marketing |
| Creative destination | `creative_assets` | creative_media |
| Trading destination | `trading_strategy_candidates` | trading_research |
| Knowledge/memory | `nexus_lessons` | research_memory / durable lessons |
| Proof (every step) | `nexus_events` | append-only ledger |

## Field mapping — model → `research_sources`
| Model field | Column |
|---|---|
| source_id | `id` (uuid) |
| source_type | `source_type` |
| source_url | `url` (dedup key) |
| title | `title` |
| creator | `author` |
| published_at | `published_at` |
| captured_at | `accessed_at` |
| plain_english_summary | `snippet` |
| why_it_matters | `why_it_matters` |
| confidence (0–10 → numeric) | `confidence` |
| run link | `research_run_id` |
| everything else (transcript_status, review_status, primary_category, secondary_tags, all 0–10 scores, total_opportunity_score, priority, recommended_destination, reasons, compliance_notes, `rating_model_version`) | `metadata` jsonb |

## Field mapping — model → `transcript_reviews`
| Model field | Column |
|---|---|
| title | `title` |
| plain_english_summary | `core_idea` |
| primary_category | `category` |
| money_potential | `money_now_score` |
| automation_value | `automation_score` |
| compliance_risk (0–10) | `risk_score`; `compliance_risk` text = low/medium/high band |
| (overall) | `usefulness_score` = total_opportunity_score/10 |
| priority / decision | `decision` (now/next/later/park/reject) |
| recommended_next_action | `recommended_action` |
| nexus_should_do | `nexus_should_do` jsonb |
| hermes_should_say | `hermes_should_say` |
| jobs to create | `jobs_to_create` jsonb |
| destination tables | `tables_to_update` jsonb |
| memory | `memory_to_store` jsonb |
| compliance flags | `claim_flags` jsonb |
| full v1 scores + tags + reasons + `rating_model_version` | `metadata` jsonb |
| link | `intake_event_id` → `intake_events.id` |

## How records link (IDs)
```
research_runs.id
   └─< research_sources.research_run_id          (sources captured in this run)
intake_events.id  (raw transcript + source_url)
   └─< transcript_reviews.intake_event_id        (the rating of that source)
         └─ dispositions(subject_table='transcript_reviews', subject_id=<review.id>)  (routing)
               └─ destination row (monetization_opportunities / improvement_candidates /
                  seo_opportunities / creative_assets / trading_strategy_candidates / nexus_lessons)
               └─ (optional) approvals / task_requests when an action needs Ray sign-off
nexus_events  ← one proof row per step (source_captured, transcript_captured, source_reviewed, routed)
```
Cross-link key: `research_sources.url` == `intake_events.source_url` (dedup join). Reviews reference
the intake event; dispositions reference the review; destinations reference the disposition via
`metadata.disposition_id`.

## Canonical vs legacy/scaffolded
- **Canonical:** `research_sources` (source capture) + `transcript_reviews` (review) + `dispositions`
  (routing) + `nexus_events` (proof). Use these.
- **Supporting:** `research_runs`, `intake_events`, `orientation_notes`.
- **Destinations:** the six destination tables above (write only the relevant one).
- **Legacy (v1, do not target from v2):** the v1 `research` table in the old `~/nexus-ai` Supabase
  (the legacy collector upserts there, deduped by `title`). v2 must NOT write to it.

## Dedup rule
Dedup on `research_sources.url` (and a normalized video-id key in `metadata.video_id`). Before
insert, check for an existing source with the same url; if present, update `metadata`/review rather
than inserting a duplicate. (Legacy collector deduped by `title`; v2 dedups by `url`/`video_id`.)

## Schema change policy
No migration is needed for v1 — existing columns + `metadata` cover the model. If a future version
needs a real column (e.g., a dedicated `total_opportunity_score`), propose ONE minimal additive
migration and bump `rating_model_version`. Do not churn the schema.
