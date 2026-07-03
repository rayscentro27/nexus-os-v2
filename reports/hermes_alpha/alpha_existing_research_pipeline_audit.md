# Existing Research Pipeline Audit for Hermes Alpha

Existing processes feed Alpha; they are not Alpha's brain.

| Process | Current output | Status | Safe for Alpha | Relevance / owner | Next safe action |
|---|---|---|---|---|---|
| YouTube target/API metadata | `reports/manual_publish/youtube_research_engine_activation_latest.md`, cache metadata, review/opportunity/content records | Active metadata; transcripts absent | Curated metadata reports only | Opportunity + marketing; Alpha, approved summaries to Nexus | Read through file adapter; do not rerun network intake automatically |
| Transcript dropzone/import/review | `data/sources/youtube_transcripts/`, transcript reports | Partial: zero imported | Yes after manual approval and prompt-injection review | All Alpha desks | Add one approved text transcript manually |
| NotebookLM export/watch/import | `data/exports/notebooklm/`, `data/sources/notebooklm_exports/`, memory reports | Partial/blocked: no selected export imported | Yes, curated export only | Research Intake; Alpha | Validate manual export format; no browser/cookie automation |
| Repo/tool research | source registry, repo activation and opportunity reports | Active/partial | Yes after license/security review | Opportunity Desk; Alpha | Route verified project summaries, not cloned code |
| Research scoring/opportunity extraction | source scores and `research_opportunities_latest` | Active | Yes as evidence, not authority | Opportunity Desk; both after promotion | Re-score with Alpha framework and retain original source |
| Research-to-money | `research_to_money_pipeline_latest` (50 candidates; 26 money-now) | Active local | Yes | Business Opportunity Desk; Alpha | Filter Alpha-relevant candidates and create experiments |
| Research-to-content | `research_to_content_pipeline_latest` (18 draft candidates; 0 published) | Active local | Yes | Marketing Studio; Alpha, Nexus after approval | Separate Alpha vs GoClear audiences before drafting |
| Research-to-offer | `research_to_offer_pipeline_latest` (20 review-required candidates) | Active local | Yes | Offer Lab; Alpha, handoff to Nexus | Validate demand/compliance; no checkout activation |
| Monetization/scoreboards | opportunity/offer/revenue reports | Active/partial | Yes | Opportunity Desk; both | Treat revenue estimates as hypotheses |
| Marketing builders | social, newsletter, landing, video, calendar reports | Active draft-only | Yes | Nexus Marketing for GoClear; Alpha can research variants | Keep publishing/sending disabled |
| Trading backtest importer | `trading_backtest_import_latest.md` and fixture | Active sample/dry-run | Yes, sanitized backtest summaries | Trading Lab; Alpha | Add deterministic strategy ID/data-window contract |
| Trading demo readiness/Oanda evidence | practice account/pricing/instrument and bridge reports | Partial/gated | Summary only; no credentials/endpoints | Future Trading Lab; Nexus display only | Do not connect Alpha or place trades |

Classification: YouTube/NotebookLM/transcript/repo inputs belong in Research Intake. Opportunity/offer/monetization outputs feed Business Opportunity Desk. Research-to-content and marketing drafts feed Marketing Studio. Backtest and strategy artifacts feed Trading Lab. Nexus Hermes receives only Ray-promoted operational summaries; Alpha may read allowed curated files directly in a future adapter.
