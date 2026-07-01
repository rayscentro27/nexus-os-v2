# Research Live Row Shape Audit

Generated: 2026-07-01T14:30:00+00:00

## Table: `research_sources`

**Total rows:** 52
**YouTube rows:** 0 (YouTube research not proven live)
**Transcripts available:** No
**NotebookLM status:** Not present

## Actual Columns

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid | Present on all rows |
| `research_run_id` | uuid | Present on all rows |
| `source_type` | text | 'article', 'youtube', etc. |
| `title` | text | Present on all rows |
| `url` | text | Source URL |
| `author` | text | Nullable |
| `published_at` | timestamp | Nullable |
| `accessed_at` | timestamp | When accessed |
| `snippet` | text | Brief description |
| `why_it_matters` | text | Reasoning |
| `confidence` | integer | 0-100 score |
| `metadata` | jsonb | Extra fields (lane, type, etc.) |
| `created_at` | timestamp | Creation time |

## Fields Missing vs UI Expectations

The `ResearchEnginePanel.jsx` expects these fields that do NOT exist as top-level columns:

- **`lane`** — stored in `metadata.lane`, default to `'research'`
- **`type`** — stored in `metadata.type`, derive from `source_type`
- **`score`** — use `confidence` or `metadata.score`
- **`status`** — stored in `metadata.status`, default `'scored'`
- **`reason`** — use `why_it_matters` or `snippet`
- **`nextAction`** — stored in `metadata.nextAction`
- **`convertOptions`** — stored in `metadata.convertOptions`
- **`revenueRange`** — stored in `metadata.revenueRange`

## Crash Root Cause

`ResearchEnginePanel.jsx` calls `.replace(/_/g, ' ')` on `c.lane`, which is `undefined` for live Supabase rows because `lane` is nested inside `metadata`, not a top-level column.

## Normalizer Applied

Normalizer function `normalizeResearchRow()` added to `src/lib/liveDataLoader.ts`.
Maps all raw research_sources rows to UI-safe shape before rendering.

## YouTube Research Status

**Label: YouTube research not proven live.**

- 0 YouTube-specific rows in research_sources
- No transcript extraction proof
- No recent YouTube metadata fetch proof
