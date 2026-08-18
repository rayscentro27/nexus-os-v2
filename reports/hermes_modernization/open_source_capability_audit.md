# Open Source Capability Audit

Generated: 2026-08-18T01:55:38.845156+00:00

## Nexus-first audit

| Candidate | Nexus state | Existing owner | Existing agent | Existing module | Recommendation |
|---|---|---|---|---|---|
| markitdown | EQUIVALENT_CAPABILITY_EXISTS | knowledge | Hermes | scripts/credit/extract_credit_report_text.py; scripts/credit/parse_uploaded_credit_report.py | EXTEND_EXISTING |
| crawl4ai | EQUIVALENT_CAPABILITY_EXISTS | alpha | Alpha | src/hermes/alpha/alphaWebSearch.ts; src/hermes/alpha/alphaUrlReview.ts; scripts/alpha/alpha_live_research.py | WRAP |
| livekit_agents | NOT_PRESENT | none | none | none | WATCH |
| pipecat | NOT_PRESENT | none | none | none | PILOT |

## Candidate set

| Project | Repository | License | Maintenance | Release activity | Recommendation | Score |
|---|---|---|---|---|---|---|
| MarkItDown | microsoft/markitdown | MIT | active | version 0.1.7; latest release 3 weeks ago; 20 releases total | EXTEND_EXISTING | 66 |
| Crawl4AI | unclecode/crawl4ai | Apache-2.0 | active | v0.9.2 maintenance patch; latest release last month; 20 releases total | WRAP | 69 |
| LiveKit Agents | livekit/agents | Apache-2.0 | active | @livekit/agents 1.6.9 released 2026-08-07; active issue/PR stream | WATCH | 33 |
| Pipecat | pipecat-ai/pipecat | BSD-2-Clause | active | v1.7.0 released 2026-08-01; ongoing changelog updates and active ecosystem repos | PILOT | 31 |

## Deterministic proof

- source records collected: 8
- deduped sources: 4
- duplicate sources collapsed: 4
- zero-token executions: 1
- AI executions: 0
- input tokens: 0
- output tokens: 0
- estimated USD cost: 0.0

## Opportunity engine input

- qualifying candidate: Crawl4AI
- recommendation: WRAP
- canonical opportunity id: unclecode_crawl4ai
