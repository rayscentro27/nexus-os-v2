# Nexus Department Workspace UI Latest

NotebookLM-style department workspaces were added as a first-pass product model and UI shell.

## What Changed

- Added reusable left/middle/right workspace components.
- Added universal project card model and live Supabase mappers.
- Refactored Source Intake, Opportunity Lab, Design Library, Creative Studio, SEO / Marketing, Ops & Improvements, and Agent Jobs into department rooms.
- Added Command Center Executive Office overview cards.
- Source Intake now saves one-off research immediately to `research_sources` and separately files safe enrichment/capture requests.

## Safety

No scheduler was installed or activated. No capture worker, publish, send, trade, deploy, external AI on sensitive data, raw v1 execution, or secret handling was added.

## Still Needed

Backend automation should deepen the project feeds: NotebookLM enrichment, SEO scanner, monetization scanner, design organizer, process registry refresh, and Hermes memory consolidation.

## Next Recommendation

Connect deterministic enrichment results back to `research_sources` so Source Intake cards gain summaries/scores without changing the instant intake UX.
