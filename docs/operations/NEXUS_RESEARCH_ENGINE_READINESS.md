# Nexus Research Engine Readiness

Date: 2026-06-24

## Classification

Status: **partially ready**.

Nexus can process pasted transcripts, local transcript files, copied text, manual ideas, and NotebookLM-style exports when Ray or an operator gives the text to CLI scripts. It cannot yet fetch YouTube transcripts, crawl article/website URLs, or accept source uploads through the UI.

## Supported Inputs

| Input | Supported | How | Storage | Analyzer | Output |
|---|---|---|---|---|---|
| Pasted transcript | yes | `capture_intake_event.py --text`, `review_transcript.py --text` | `intake_events`, `transcript_reviews` | deterministic regex/scoring | orientation notes, dispositions, opportunities |
| Transcript file | yes | `--file` | same | deterministic | same |
| Copied text/manual idea | yes | `--text` | same | deterministic | same |
| NotebookLM export | manual | paste/file | same | deterministic | same |
| YouTube transcript text | yes if pasted | paste/file | same | deterministic | same |
| YouTube URL | no | no fetcher | source_url only if manually captured | none | none |
| Article/blog URL | no | no fetcher | source_url only | none | none |
| Website URL | no | no crawler | source_url only | none | none |
| Uploaded file through UI | no | no UI/storage path | none | none | none |

## Existing Pipeline

1. `scripts/intake/capture_intake_event.py` captures text/file into `intake_events`.
2. `scripts/intake/review_transcript.py` classifies and scores the source.
3. It writes `transcript_reviews`, `orientation_notes`, `dispositions`, and sometimes `improvement_candidates`, `monetization_opportunities`, or `nexus_lessons`.
4. `scripts/intake/extract_service_opportunity.py` can create a draft monetization opportunity.
5. UI tabs can display these tables, but there is no guided submission workflow.

## Routing Status

| Destination | Status |
|---|---|
| Opportunity Lab | partial; monetization rows can be created |
| Creative Studio | partial/manual; no automatic source-to-campaign flow |
| SEO / Marketing | scaffolded; tables empty |
| Ops & Improvements | partial; improvement candidates can be created |
| Approvals | no automatic approval from source review |
| Task requests | not integrated; table empty |
| Hermes | can review visible table/report summaries, but no source-specific workflow yet |

## Missing for YouTube/Transcript Readiness

- YouTube URL parser/transcript fetcher.
- Article/website fetcher.
- File upload UI.
- Source dedupe.
- Queue/status UI.
- Review result detail page.
- Hermes source-review command path.
- Safe public/private data classifier before model routing.

## Recommendation

Build `Source Intake & Review` before adding more external research integrations. The first version should support pasted text and local file upload, then store to `intake_events`, run deterministic review, and show outputs in the UI.
