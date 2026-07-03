# Alpha Research Intake Room Design

Purpose: collect, inspect, deduplicate, label, score, and route allowed research artifacts without making them Alpha memory or truth automatically.

## Views

- Inbox with source type, title, received time, provenance, license/terms note, freshness, safety scan, and status.
- YouTube metadata/imports; NotebookLM exports; transcripts; repo/tool research; market/business research.
- Candidate tabs for opportunities, trading strategies, and marketing ideas.
- Detail panel with excerpt, source link/path, claims, assumptions, prompt-injection warning, and routing history.

## States and routing

`received → quarantined/validated → summarized → scored → routed → promoted/rejected`.

Destinations: Business Opportunity Desk, Marketing Asset Studio, Affiliate/Offer Lab, Trading Research Lab, or archive. Promotion requires a human decision. Phase 1 uses local files only through `AlphaResearchFileAdapter`; no database, client data, broker, publish, or send tools.

Minimum artifact contract: ID, title, type, path/source, author/publisher if known, fetched/created date, license/terms, hash, summary, claims, tags, allowed destination, sensitivity, and validation notes.
