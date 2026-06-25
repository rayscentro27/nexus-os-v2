# Nexus Video / Source Research Rating Model — CANONICAL (v1)

`rating_model_version: v1`

This is the **single canonical standard** for rating and categorizing any research source
(YouTube video, channel, playlist, transcript, article, idea). Future scripts and UI must use
**these exact fields and values** instead of inventing new categories. Do not change this model
casually — if a field must change, bump `rating_model_version` (v2, …) and document the migration.

---

## Core identity
| Field | Values / format |
|---|---|
| `source_id` | stable id (uuid in Supabase; for YouTube, derive a natural key from the video id) |
| `source_type` | `youtube_video` \| `youtube_channel` \| `youtube_playlist` \| `transcript_file` \| `notebooklm_export` \| `article_url` \| `website_url` \| `manual_idea` |
| `source_url` | canonical URL (used for dedup) |
| `title` | source title |
| `creator` | channel / author |
| `published_at` | original publish timestamp |
| `captured_at` | when Nexus captured it |
| `transcript_status` | `missing` \| `captured` \| `partial` \| `unavailable` \| `failed` |
| `review_status` | `queued` \| `reviewing` \| `reviewed` \| `needs_ray_review` \| `rejected` \| `parked` |

## Primary category (exactly one)
`goclear_apex_revenue` · `credit_funding_readiness` · `affiliate_partner` · `seo_marketing` ·
`creative_media` · `system_improvement` · `ai_tooling` · `research_memory` · `trading_research` ·
`client_experience` · `operations` · `ignore_or_park`

## Secondary tags (zero or more)
`grants` · `business_credit` · `personal_credit` · `funding` · `bankability` · `ai_agents` ·
`automation` · `content` · `landing_page` · `email` · `social` · `youtube` · `trading_strategy` ·
`backtest` · `compliance` · `local_tools` · `mac_bridge` · `integrations` · `mcp` · `skills` ·
`affiliate` · `lead_generation`

## Scores (all integers 0–10)
`money_potential` · `speed_to_test` · `cost_to_test` · `goclear_fit` · `nexus_fit` ·
`automation_value` · `content_value` · `affiliate_value` · `client_value` · `compliance_risk` ·
`technical_difficulty` · `confidence`

Scoring sense: higher is better/more for value scores; for `compliance_risk` and
`technical_difficulty`, higher means MORE risk/difficulty (penalties in the derived score).

## Derived score
- `total_opportunity_score` 0–100. Canonical formula (v1):
  ```
  base = money_potential*3 + goclear_fit*2 + nexus_fit*2 + automation_value*1.5
       + speed_to_test*1.5 + (10 - cost_to_test)*1 + content_value*1 + affiliate_value*1
       + client_value*1
  penalty = compliance_risk*2 + technical_difficulty*1
  raw = base - penalty                      # weights sum so max base ≈ 145, clamp below
  total_opportunity_score = round( clamp(raw, 0, 145) / 145 * 100 ) * (confidence/10 scaled)
  ```
  Implementations must keep this formula identical across scripts and the UI. The exact weights
  live in one place (`scripts/intake/run_existing_youtube_monitor.py::score_source`) and are
  mirrored here for review.
- `priority`: `now` (≥75) · `next` (60–74) · `later` (40–59) · `park` (20–39) · `reject` (<20).
  (Compliance_risk ≥ 8 forces at most `needs_ray_review`/`park`.)
- `recommended_destination`: `Opportunity Lab` · `GoClear/Apex Revenue Hub` · `Creative Studio` ·
  `SEO Growth Engine` · `Source Intake & Review` · `Ops & Improvements` · `Trading Lab` ·
  `Design Library` · `Knowledge/Memory` · `Ignore/Park`.

### Category → destination defaults
| Primary category | Default destination |
|---|---|
| goclear_apex_revenue | GoClear/Apex Revenue Hub |
| credit_funding_readiness | GoClear/Apex Revenue Hub |
| affiliate_partner | Opportunity Lab |
| seo_marketing | SEO Growth Engine |
| creative_media | Creative Studio |
| system_improvement / operations | Ops & Improvements |
| ai_tooling | Ops & Improvements |
| research_memory | Knowledge/Memory |
| trading_research | Trading Lab |
| client_experience | Opportunity Lab |
| ignore_or_park | Ignore/Park |

## Required recommendation fields
`plain_english_summary` · `why_it_matters` · `recommended_next_action` · `smallest_low_cost_test` ·
`required_assets` · `compliance_notes` · `reasons_for_score` · `reasons_against` ·
`ray_decision_needed` (bool)

## Compliance guardrails (hard, GoClear/Apex)
Never frame any source/recommendation as guaranteed funding, guaranteed approval, guaranteed credit
repair, guaranteed score increase, guaranteed deletion, or guaranteed financing outcome. Use
readiness / education / preparation / next-step language. `compliance_risk` rises when a source
makes guarantee-style claims; high values route to `needs_ray_review`.

## Versioning
`rating_model_version: v1`. Any change → new version + a note here describing what changed and a
migration plan for stored `metadata.rating_model_version` values.
