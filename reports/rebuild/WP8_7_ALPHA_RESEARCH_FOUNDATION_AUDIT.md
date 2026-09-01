# WP8.7 Alpha Research Foundation Audit

## Result

FOUNDATION_IMPLEMENTED

Existing surfaces audited: `scripts/alpha/alpha_live_research.py` (Brave/YouTube/OpenRouter bridge), `scripts/alpha/alpha_open_source_scout.py`, `scripts/activation/run_youtube_ytdlp_probe.py`, `scripts/activation/run_youtube_transcript_import.py`, `src/hermes/alpha/alphaUrlReview.ts`, `scripts/nexus_agent_platform/research/open_source_scout.py`, and the governed append-only store. The new layer adapts these boundaries and does not create a second registry or control plane.
## Existing capability decisions

YouTube metadata/subtitle probing is reused; remote caption ingestion is bounded through yt-dlp with no media/audio download. Page retrieval reuses the public-read boundary and uses a bounded curl fallback only when Python TLS fails. Repository intelligence remains the existing Nexus registry. Research state is persisted in governed `alpha_*` collections.
## Safety

Discovery is read-only. External publication, outreach, payments, trading, installation, and self-approval are outside Alpha authority. No client PII is used.
