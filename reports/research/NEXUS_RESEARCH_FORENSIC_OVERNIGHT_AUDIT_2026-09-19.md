# NEXUS Research Forensic Overnight Audit — 2026-09-19

Forensic BEFORE-state audit. No Research, Alpha, scheduler, threshold, source-rotation, classification, retry, or handoff logic was changed.

## Exact scope

- AUDIT_WINDOW_START=2026-09-18T23:09:33.015771+00:00
- AUDIT_WINDOW_END=2026-09-19T13:13:39.678200+00:00
- Source: data/runtime/research_execution_jobs.jsonl, reduced by execution_id.
- Exact reconstruction: 131 execution IDs, 112 COMPLETED, 16 FAILED_RETRYABLE, 3 without a terminal event by the exact end.
- The previously reported 115 terminal completions does not reconcile to this exact bounded ledger. It is preserved as a prior aggregate, not silently substituted.
- New intelligence is counted conservatively only when durable execution evidence records distinct information gain. Current ledger does not preserve sufficient content/version markers to promote processed sources into confirmed new intelligence.

## Executive finding

Research selected 125 source executions across 18 unique source IDs. Of 112 completed executions, 66 were fully processed and 46 were duplicate/unchanged. The exact-window executions show no Alpha invocation and no department handoff. Five source-level observations were visible in artifacts, but none became a durable evidence-to-Alpha item in this exact window.

## Required totals

TOTAL_EXECUTIONS=131
TOTAL_COMPLETED=112
UNIQUE_SOURCE_COUNT=18
FULLY_PROCESSED=66
DUPLICATE_COUNT=46
DUPLICATE_RATE=36.8%
DUPLICATE_UNIQUE_SOURCES=7
RETRYABLE_FAILURE_COUNT=16
INSUFFICIENT_SOURCE_OUTCOMES=0

## 1. Complete execution ledger

Blank fields mean the ledger did not persist the field; they are not inferred.

| execution_id | started | completed | lane | objective | source_id | source_type | source_url/reference | source_title | selection_reason | processor | model | model_calls | disposition | new_information | evidence_package | classification | alpha_eligible | alpha_invoked | alpha_decision | department_handoff | retry_count | failure_reason | final_state |
|---|---|---|---|---|---|---|---|---|---|---|---|---:|---|---|---|---|---|---|---|---|---:|---|---|
| research_exec_0a2506fd54b74f28a759 | 2026-09-18T23:09:37.786485+00:00 | 2026-09-18T23:10:03.032276+00:00 |  |  |  |  |  |  |  |  |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FAILED_RETRYABLE |
| research_exec_922ed581f1094cb2bea0 | 2026-09-18T23:09:38.246574+00:00 | 2026-09-18T23:09:46.037033+00:00 |  |  | google-seo-starter | SEO_RESEARCH | https://developers.google.com/search/docs/fundamentals/seo-starter-guide |  | scheduled_lane_source_pool | research_document_pipeline.web_page (SEO mode) |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_8f9e63f423294f0f9a93 | 2026-09-18T23:11:37.973253+00:00 | 2026-09-18T23:11:40.485779+00:00 |  |  | sba-grants | WEB_PAGE | https://www.sba.gov/funding-programs/grants |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_ecdb356be3714d6bb62c | 2026-09-18T23:11:38.613805+00:00 | 2026-09-18T23:11:43.182543+00:00 |  |  | sushantkarn/SEO-engine | GITHUB_REPO | https://github.com/sushantkarn/SEO-engine |  | scheduled_lane_source_pool | research_document_pipeline.github_deep |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_d2744436022042519ad2 | 2026-09-18T23:11:39.074673+00:00 | 2026-09-18T23:12:06.156161+00:00 |  |  | 4-HNOWyfemk | YOUTUBE_VIDEO | https://www.youtube.com/watch?v=4-HNOWyfemk |  | approved_channel_watchlist | youtube_full_pipeline.process_youtube_video |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FAILED_RETRYABLE |
| research_exec_1c0861c4497744938c3b | 2026-09-18T23:31:40.300638+00:00 | 2026-09-18T23:31:45.719600+00:00 |  |  | google-seo-starter | SEO_RESEARCH | https://developers.google.com/search/docs/fundamentals/seo-starter-guide |  | scheduled_lane_source_pool | research_document_pipeline.web_page (SEO mode) |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_9473349febb84ef6bd1f | 2026-09-18T23:31:41.119518+00:00 | 2026-09-18T23:31:45.719223+00:00 |  |  | hubspot-affiliate | WEB_PAGE | https://www.hubspot.com/partners/affiliates |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_c90b830a612740b2a9b2 | 2026-09-18T23:31:41.207843+00:00 | 2026-09-18T23:31:45.720430+00:00 |  |  | google-seo-starter | SEO_RESEARCH | https://developers.google.com/search/docs/fundamentals/seo-starter-guide |  | scheduled_lane_source_pool | research_document_pipeline.web_page (SEO mode) |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_ff811b48f74b4aa7bc36 | 2026-09-18T23:51:41.733764+00:00 | 2026-09-18T23:51:45.264851+00:00 |  |  | mobile-detailing-academy-phoenix | WEB_PAGE | https://mobiledetailingacademy.com/mobile-detailing/phoenix-az |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_38257a69f52741e392f8 | 2026-09-18T23:51:42.041751+00:00 | 2026-09-18T23:51:44.371254+00:00 |  |  | sba-business-guide | WEB_PAGE | https://www.sba.gov/business-guide |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_aed618cd7ed04f448716 | 2026-09-18T23:51:42.450102+00:00 | 2026-09-18T23:51:45.267405+00:00 |  |  | mobile-detailing-academy-phoenix | WEB_PAGE | https://mobiledetailingacademy.com/mobile-detailing/phoenix-az |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_3cd94ce24a294265a5d3 | 2026-09-19T00:11:46.623471+00:00 | 2026-09-19T00:11:50.581104+00:00 |  |  | investor-investing-basics | WEB_PAGE | https://www.investor.gov/introduction-investing |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_c552e3b5929e4d7dbffa | 2026-09-19T00:11:46.793114+00:00 | 2026-09-19T00:11:51.388016+00:00 |  |  | sba-grants | WEB_PAGE | https://www.sba.gov/funding-programs/grants |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_86ac4bea6b5b42558cb1 | 2026-09-19T00:11:46.963983+00:00 | 2026-09-19T00:11:50.908824+00:00 |  |  | reddit-smallbusiness | WEB_PAGE | https://www.reddit.com/r/smallbusiness/ |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_76eec20da70e4e0c96b3 | 2026-09-19T00:31:48.636979+00:00 | 2026-09-19T00:32:04.986716+00:00 |  |  | crj-goclear-capability-research-v1 | RESEARCH_OBJECTIVE |  |  | bounded CRJ research requested by current execution certification | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FAILED_RETRYABLE |
| research_exec_2273f79d053e49c69e1d | 2026-09-19T00:31:52.627471+00:00 | 2026-09-19T00:32:27.299980+00:00 |  |  | google-seo-starter | SEO_RESEARCH | https://developers.google.com/search/docs/fundamentals/seo-starter-guide |  | scheduled_lane_source_pool | research_document_pipeline.web_page (SEO mode) |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_c1dbca402be144f59b24 | 2026-09-19T00:31:54.610846+00:00 | 2026-09-19T00:32:27.680366+00:00 |  |  | hubspot-affiliate | WEB_PAGE | https://www.hubspot.com/partners/affiliates |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_718bc0fcc01f4ea8943c | 2026-09-19T00:52:01.054573+00:00 | 2026-09-19T00:52:29.891432+00:00 |  |  | sushantkarn/SEO-engine | GITHUB_REPO | https://github.com/sushantkarn/SEO-engine |  | scheduled_lane_source_pool | research_document_pipeline.github_deep |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_91f97e9f9630497fba0a | 2026-09-19T00:52:04.407893+00:00 | 2026-09-19T00:52:30.385357+00:00 |  |  | mvanhorn/last30days-skill | GITHUB_REPO | https://github.com/mvanhorn/last30days-skill |  | scheduled_lane_source_pool | research_document_pipeline.github_deep |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_5353fa01098b473db2f6 | 2026-09-19T00:52:06.783049+00:00 | 2026-09-19T00:52:29.435325+00:00 |  |  | sushantkarn/SEO-engine | GITHUB_REPO | https://github.com/sushantkarn/SEO-engine |  | scheduled_lane_source_pool | research_document_pipeline.github_deep |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_b3e9390a5b8341cab668 | 2026-09-19T01:12:15.178737+00:00 | 2026-09-19T01:12:18.604977+00:00 |  |  | mobile-detailing-academy-phoenix | WEB_PAGE | https://mobiledetailingacademy.com/mobile-detailing/phoenix-az |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_e923d32238e34e7fb5ba | 2026-09-19T01:12:15.354970+00:00 | 2026-09-19T01:12:30.332615+00:00 |  |  | LdDr2viNh2w | YOUTUBE_VIDEO | https://www.youtube.com/watch?v=LdDr2viNh2w |  | approved_channel_watchlist | youtube_full_pipeline.process_youtube_video |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FAILED_RETRYABLE |
| research_exec_6510667e50bc42a396cf | 2026-09-19T01:12:15.489670+00:00 | 2026-09-19T01:12:17.818374+00:00 |  |  | sba-loans | WEB_PAGE | https://www.sba.gov/loans |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_55ad8fd41ca7457392be | 2026-09-19T01:32:16.122079+00:00 | 2026-09-19T01:33:13.554646+00:00 |  |  | 6XngV5NQgMg | YOUTUBE_VIDEO | https://www.youtube.com/watch?v=6XngV5NQgMg |  | approved_channel_watchlist | youtube_full_pipeline.process_youtube_video |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_1db640024a904f5d876e | 2026-09-19T01:32:16.513277+00:00 | 2026-09-19T01:32:20.595020+00:00 |  |  | sba-business-guide | WEB_PAGE | https://www.sba.gov/business-guide |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_55c120ea858f4e78a5c8 | 2026-09-19T01:32:16.888558+00:00 | 2026-09-19T01:32:20.998022+00:00 |  |  | mobile-detailing-academy-phoenix | WEB_PAGE | https://mobiledetailingacademy.com/mobile-detailing/phoenix-az |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_0e5ebe2f24ef4869b35b | 2026-09-19T01:52:17.312575+00:00 | 2026-09-19T01:52:19.016495+00:00 |  |  | shopify-partners | WEB_PAGE | https://www.shopify.com/partners |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_4afe5654a1ab42a4aede | 2026-09-19T01:52:17.588730+00:00 | 2026-09-19T01:52:20.859311+00:00 |  |  | sba-grants | WEB_PAGE | https://www.sba.gov/funding-programs/grants |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_393b4997dc38426d9754 | 2026-09-19T01:52:17.713037+00:00 | 2026-09-19T01:52:19.818522+00:00 |  |  | sba-business-guide | WEB_PAGE | https://www.sba.gov/business-guide |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_5f55ac3eb11c43b69e7c | 2026-09-19T02:12:19.486837+00:00 | 2026-09-19T02:12:22.203828+00:00 |  |  | reddit-smallbusiness | WEB_PAGE | https://www.reddit.com/r/smallbusiness/ |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_82d931ecc1f54026b9ad | 2026-09-19T02:12:20.084922+00:00 | 2026-09-19T02:12:22.616139+00:00 |  |  | google-seo-starter | SEO_RESEARCH | https://developers.google.com/search/docs/fundamentals/seo-starter-guide |  | scheduled_lane_source_pool | research_document_pipeline.web_page (SEO mode) |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_dc4fed8de904420392fc | 2026-09-19T02:12:20.745974+00:00 | 2026-09-19T02:12:22.616310+00:00 |  |  | hubspot-affiliate | WEB_PAGE | https://www.hubspot.com/partners/affiliates |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_0ab34cb520cd481c9c1c | 2026-09-19T02:32:21.155852+00:00 | 2026-09-19T02:32:27.518042+00:00 |  |  | mvanhorn/last30days-skill | GITHUB_REPO | https://github.com/mvanhorn/last30days-skill |  | scheduled_lane_source_pool | research_document_pipeline.github_deep |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_4700a7dc9c1d4e818123 | 2026-09-19T02:32:21.570120+00:00 | 2026-09-19T02:32:26.581367+00:00 |  |  | sushantkarn/SEO-engine | GITHUB_REPO | https://github.com/sushantkarn/SEO-engine |  | scheduled_lane_source_pool | research_document_pipeline.github_deep |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_ba9916af3fd44b69b85d | 2026-09-19T02:32:21.754888+00:00 | 2026-09-19T02:32:23.045181+00:00 |  |  | google-seo-starter | SEO_RESEARCH | https://developers.google.com/search/docs/fundamentals/seo-starter-guide |  | scheduled_lane_source_pool | research_document_pipeline.web_page (SEO mode) |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_07d3e801a6ab4c73b500 | 2026-09-19T02:52:22.116561+00:00 | 2026-09-19T02:52:35.726970+00:00 |  |  | LdDr2viNh2w | YOUTUBE_VIDEO | https://www.youtube.com/watch?v=LdDr2viNh2w |  | approved_channel_watchlist | youtube_full_pipeline.process_youtube_video |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FAILED_RETRYABLE |
| research_exec_93a79711e81047cf85fd | 2026-09-19T02:52:22.338565+00:00 | 2026-09-19T02:52:39.811929+00:00 |  |  | CiGQ7to-5J4 | YOUTUBE_VIDEO | https://www.youtube.com/watch?v=CiGQ7to-5J4 |  | approved_channel_watchlist | youtube_full_pipeline.process_youtube_video |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FAILED_RETRYABLE |
| research_exec_95a67514ec40410fb0e4 | 2026-09-19T02:52:22.519083+00:00 | 2026-09-19T02:52:23.934382+00:00 |  |  | hubspot-affiliate | WEB_PAGE | https://www.hubspot.com/partners/affiliates |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_b1fb151a5d8f4b0da3a3 | 2026-09-19T03:12:23.995039+00:00 | 2026-09-19T03:12:26.624693+00:00 |  |  | CiGQ7to-5J4 | WEB_PAGE |  |  | unfinished_high_value_investigation | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FAILED_RETRYABLE |
| research_exec_b9ff566794cf402b8e20 | 2026-09-19T03:12:24.964053+00:00 | 2026-09-19T03:12:28.038683+00:00 |  |  | sba-grants | WEB_PAGE | https://www.sba.gov/funding-programs/grants |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_81f2ee0bc610476f8e26 | 2026-09-19T03:12:25.481426+00:00 | 2026-09-19T03:12:27.685258+00:00 |  |  | google-seo-starter | SEO_RESEARCH | https://developers.google.com/search/docs/fundamentals/seo-starter-guide |  | scheduled_lane_source_pool | research_document_pipeline.web_page (SEO mode) |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_8c51c8f48d384d8590b7 | 2026-09-19T03:32:26.052287+00:00 | 2026-09-19T03:32:37.969704+00:00 |  |  | TlpJdvFQLeY | YOUTUBE_VIDEO | https://www.youtube.com/watch?v=TlpJdvFQLeY |  | approved_channel_watchlist | youtube_full_pipeline.process_youtube_video |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FAILED_RETRYABLE |
| research_exec_8256c94e825443e0a28f | 2026-09-19T03:32:26.217728+00:00 | 2026-09-19T03:32:27.471091+00:00 |  |  | hubspot-affiliate | WEB_PAGE | https://www.hubspot.com/partners/affiliates |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_32ed72b5a35848aebb5e | 2026-09-19T03:32:26.423434+00:00 | 2026-09-19T03:32:37.973626+00:00 |  |  | 4-HNOWyfemk | YOUTUBE_VIDEO | https://www.youtube.com/watch?v=4-HNOWyfemk |  | approved_channel_watchlist | youtube_full_pipeline.process_youtube_video |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FAILED_RETRYABLE |
| research_exec_3d58c46709cc400a9c22 | 2026-09-19T03:52:26.771533+00:00 | 2026-09-19T03:52:27.382058+00:00 |  |  | 4-HNOWyfemk | WEB_PAGE |  |  | unfinished_high_value_investigation | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FAILED_RETRYABLE |
| research_exec_9a728b1e48794e0b81d0 | 2026-09-19T03:52:26.970822+00:00 | 2026-09-19T03:52:27.714895+00:00 |  |  | shopify-partners | WEB_PAGE | https://www.shopify.com/partners |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_4fb9a4e831f147f68343 | 2026-09-19T03:52:27.095132+00:00 | 2026-09-19T03:52:28.289681+00:00 |  |  | google-seo-starter | SEO_RESEARCH | https://developers.google.com/search/docs/fundamentals/seo-starter-guide |  | scheduled_lane_source_pool | research_document_pipeline.web_page (SEO mode) |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_9e6540b51f5b4cb5a932 | 2026-09-19T04:12:28.593559+00:00 | 2026-09-19T04:12:29.811260+00:00 |  |  | investor-investing-basics | WEB_PAGE | https://www.investor.gov/introduction-investing |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_d30348c2684d444c9e4e | 2026-09-19T04:12:28.835728+00:00 | 2026-09-19T04:12:29.812033+00:00 |  |  | reddit-smallbusiness | WEB_PAGE | https://www.reddit.com/r/smallbusiness/ |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_9e4108f99cba46b9aa25 | 2026-09-19T04:12:29.059200+00:00 | 2026-09-19T04:12:29.810516+00:00 |  |  | investor-investing-basics | WEB_PAGE | https://www.investor.gov/introduction-investing |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_b1984b8d033544148cd9 | 2026-09-19T04:32:29.358963+00:00 | 2026-09-19T04:32:31.978660+00:00 |  |  | mobile-detailing-academy-phoenix | WEB_PAGE | https://mobiledetailingacademy.com/mobile-detailing/phoenix-az |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_6411c23246124d4295bf | 2026-09-19T04:32:29.507843+00:00 | 2026-09-19T04:32:31.978439+00:00 |  |  | mobile-detailing-academy-phoenix | WEB_PAGE | https://mobiledetailingacademy.com/mobile-detailing/phoenix-az |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_4bba7b1cf66e422e8ed9 | 2026-09-19T04:32:29.637012+00:00 | 2026-09-19T04:32:31.251680+00:00 |  |  | sba-grants | WEB_PAGE | https://www.sba.gov/funding-programs/grants |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_e7992a58ba9d4049a77c | 2026-09-19T04:52:30.038660+00:00 | 2026-09-19T04:52:34.329498+00:00 |  |  | sushantkarn/SEO-engine | GITHUB_REPO | https://github.com/sushantkarn/SEO-engine |  | scheduled_lane_source_pool | research_document_pipeline.github_deep |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_a2b21decd850492f95b6 | 2026-09-19T04:52:30.270653+00:00 | 2026-09-19T04:52:31.931220+00:00 |  |  | hubspot-affiliate | WEB_PAGE | https://www.hubspot.com/partners/affiliates |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_3f492618229b4767a67c | 2026-09-19T04:52:30.443761+00:00 | 2026-09-19T04:52:35.328942+00:00 |  |  | mvanhorn/last30days-skill | GITHUB_REPO | https://github.com/mvanhorn/last30days-skill |  | scheduled_lane_source_pool | research_document_pipeline.github_deep |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_2332821af7764e018598 | 2026-09-19T05:12:33.174218+00:00 | 2026-09-19T05:12:40.227630+00:00 |  |  | google-seo-starter | SEO_RESEARCH | https://developers.google.com/search/docs/fundamentals/seo-starter-guide |  | scheduled_lane_source_pool | research_document_pipeline.web_page (SEO mode) |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_1be27055dbc74614bb51 | 2026-09-19T05:12:33.789048+00:00 | 2026-09-19T05:12:40.153269+00:00 |  |  | google-seo-starter | SEO_RESEARCH | https://developers.google.com/search/docs/fundamentals/seo-starter-guide |  | scheduled_lane_source_pool | research_document_pipeline.web_page (SEO mode) |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_f9e6e6137a474fe4962a | 2026-09-19T05:12:34.519264+00:00 | 2026-09-19T05:12:40.083991+00:00 |  |  | google-seo-starter | SEO_RESEARCH | https://developers.google.com/search/docs/fundamentals/seo-starter-guide |  | scheduled_lane_source_pool | research_document_pipeline.web_page (SEO mode) |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_1317ebd35cf84b00ab8a | 2026-09-19T05:32:43.464149+00:00 | 2026-09-19T05:35:05.850237+00:00 |  |  |  |  |  |  |  |  |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FAILED_RETRYABLE |
| research_exec_81b56fece7c64f92a414 | 2026-09-19T05:32:47.491578+00:00 | 2026-09-19T05:34:52.149140+00:00 |  |  | mobile-detailing-academy-phoenix | WEB_PAGE | https://mobiledetailingacademy.com/mobile-detailing/phoenix-az |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_2f8adbfba7c849c2aad7 | 2026-09-19T05:32:48.734893+00:00 | 2026-09-19T05:34:47.156633+00:00 |  |  | sba-business-guide | WEB_PAGE | https://www.sba.gov/business-guide |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_15369ee318ba497d8be6 | 2026-09-19T05:52:50.882812+00:00 | 2026-09-19T05:52:57.256013+00:00 |  |  | investor-investing-basics | WEB_PAGE | https://www.investor.gov/introduction-investing |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_b152c921f98348418e10 | 2026-09-19T05:52:51.252180+00:00 | 2026-09-19T05:53:15.618600+00:00 |  |  | 4-HNOWyfemk | YOUTUBE_VIDEO | https://www.youtube.com/watch?v=4-HNOWyfemk |  | approved_channel_watchlist | youtube_full_pipeline.process_youtube_video |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FAILED_RETRYABLE |
| research_exec_5111b540173e4812b946 | 2026-09-19T05:52:52.092617+00:00 | 2026-09-19T05:52:58.417488+00:00 |  |  | mobile-detailing-academy-phoenix | WEB_PAGE | https://mobiledetailingacademy.com/mobile-detailing/phoenix-az |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_266a4a6658444bf18ba7 | 2026-09-19T06:12:58.905703+00:00 | 2026-09-19T06:14:11.701945+00:00 |  |  | reddit-smallbusiness | WEB_PAGE | https://www.reddit.com/r/smallbusiness/ |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_ef287e6f70244c00b236 | 2026-09-19T06:13:00.597701+00:00 | 2026-09-19T06:14:12.032185+00:00 |  |  | hubspot-affiliate | WEB_PAGE | https://www.hubspot.com/partners/affiliates |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_af22f9bf7dcf45409769 | 2026-09-19T06:13:01.634019+00:00 | 2026-09-19T06:13:52.772649+00:00 |  |  | sba-grants | WEB_PAGE | https://www.sba.gov/funding-programs/grants |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_cecb519b1fa94b6f8b99 | 2026-09-19T06:33:04.704582+00:00 | 2026-09-19T06:33:40.456778+00:00 |  |  |  |  |  |  |  |  |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FAILED_RETRYABLE |
| research_exec_85eca8e050aa4c0295d0 | 2026-09-19T06:33:05.861461+00:00 | 2026-09-19T06:33:27.676022+00:00 |  |  | mobile-detailing-academy-phoenix | WEB_PAGE | https://mobiledetailingacademy.com/mobile-detailing/phoenix-az |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_80cf6681aec740329fe0 | 2026-09-19T06:33:06.722107+00:00 | 2026-09-19T06:33:27.881534+00:00 |  |  | hubspot-affiliate | WEB_PAGE | https://www.hubspot.com/partners/affiliates |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_d4cf9c928cec440c82b4 | 2026-09-19T06:53:07.886534+00:00 | 2026-09-19T06:53:12.257454+00:00 |  |  | sba-loans | WEB_PAGE | https://www.sba.gov/loans |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_191c8e5825504eafaa82 | 2026-09-19T06:53:08.299747+00:00 | 2026-09-19T06:53:11.046269+00:00 |  |  | shopify-partners | WEB_PAGE | https://www.shopify.com/partners |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_7c0fabf479c14078a368 | 2026-09-19T06:53:09.083131+00:00 | 2026-09-19T06:53:13.924430+00:00 |  |  | sushantkarn/SEO-engine | GITHUB_REPO | https://github.com/sushantkarn/SEO-engine |  | scheduled_lane_source_pool | research_document_pipeline.github_deep |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_c04bb89817f44f5d86d8 | 2026-09-19T07:13:11.877561+00:00 | 2026-09-19T07:13:15.106184+00:00 |  |  | google-seo-starter | SEO_RESEARCH | https://developers.google.com/search/docs/fundamentals/seo-starter-guide |  | scheduled_lane_source_pool | research_document_pipeline.web_page (SEO mode) |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_c6b87f3a2e674980baf7 | 2026-09-19T07:13:12.019110+00:00 | 2026-09-19T07:13:15.106628+00:00 |  |  | google-seo-starter | SEO_RESEARCH | https://developers.google.com/search/docs/fundamentals/seo-starter-guide |  | scheduled_lane_source_pool | research_document_pipeline.web_page (SEO mode) |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_5a5fb1355d51486c8369 | 2026-09-19T07:13:12.130849+00:00 | 2026-09-19T07:13:15.466233+00:00 |  |  | google-seo-starter | SEO_RESEARCH | https://developers.google.com/search/docs/fundamentals/seo-starter-guide |  | scheduled_lane_source_pool | research_document_pipeline.web_page (SEO mode) |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_ea152f5d6bb54422bc72 | 2026-09-19T07:33:13.523633+00:00 | 2026-09-19T07:33:49.109149+00:00 |  |  | dOpBsbXGflc | YOUTUBE_VIDEO | https://www.youtube.com/watch?v=dOpBsbXGflc |  | approved_channel_watchlist | youtube_full_pipeline.process_youtube_video |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FAILED_RETRYABLE |
| research_exec_266d6e858b4a474ca17c | 2026-09-19T07:33:15.025992+00:00 | 2026-09-19T07:33:23.748395+00:00 |  |  | mobile-detailing-academy-phoenix | WEB_PAGE | https://mobiledetailingacademy.com/mobile-detailing/phoenix-az |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_6389bb4975424f618257 | 2026-09-19T07:33:15.651208+00:00 | 2026-09-19T07:33:49.151294+00:00 |  |  | dOpBsbXGflc | YOUTUBE_VIDEO | https://www.youtube.com/watch?v=dOpBsbXGflc |  | approved_channel_watchlist | youtube_full_pipeline.process_youtube_video |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FAILED_RETRYABLE |
| research_exec_f2bec3091ec945e28c7f | 2026-09-19T07:53:16.636086+00:00 | 2026-09-19T07:53:20.889205+00:00 |  |  | mobile-detailing-academy-phoenix | WEB_PAGE | https://mobiledetailingacademy.com/mobile-detailing/phoenix-az |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_0558c02ae45942f6bc7d | 2026-09-19T07:53:16.918821+00:00 | 2026-09-19T07:53:19.949861+00:00 |  |  | hubspot-affiliate | WEB_PAGE | https://www.hubspot.com/partners/affiliates |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_f9cb6aa074a2462aa04b | 2026-09-19T07:53:17.504082+00:00 | 2026-09-19T07:53:19.944160+00:00 |  |  | hubspot-affiliate | WEB_PAGE | https://www.hubspot.com/partners/affiliates |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_350c474336094530ba52 | 2026-09-19T08:13:19.979188+00:00 | 2026-09-19T08:14:10.291741+00:00 |  |  | 6XngV5NQgMg | YOUTUBE_VIDEO | https://www.youtube.com/watch?v=6XngV5NQgMg |  | approved_channel_watchlist | youtube_full_pipeline.process_youtube_video |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_c0e457df1958448383b9 | 2026-09-19T08:13:20.120955+00:00 | 2026-09-19T08:13:23.108378+00:00 |  |  | hubspot-affiliate | WEB_PAGE | https://www.hubspot.com/partners/affiliates |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_c7e6d5304d174478b3da | 2026-09-19T08:13:20.226225+00:00 | 2026-09-19T08:13:23.486106+00:00 |  |  | sba-business-guide | WEB_PAGE | https://www.sba.gov/business-guide |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_9d6a66e76bcd49f4b86e | 2026-09-19T08:33:20.800043+00:00 | 2026-09-19T08:33:23.436638+00:00 |  |  | reddit-smallbusiness | WEB_PAGE | https://www.reddit.com/r/smallbusiness/ |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_866b86f0cc3c4cd593f3 | 2026-09-19T08:33:21.000232+00:00 | 2026-09-19T08:33:27.172047+00:00 |  |  | mvanhorn/last30days-skill | GITHUB_REPO | https://github.com/mvanhorn/last30days-skill |  | scheduled_lane_source_pool | research_document_pipeline.github_deep |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_e959ef734895457caa49 | 2026-09-19T08:33:21.272219+00:00 | 2026-09-19T08:33:23.435443+00:00 |  |  | reddit-smallbusiness | WEB_PAGE | https://www.reddit.com/r/smallbusiness/ |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_84219f4d26ce453bbd7f | 2026-09-19T08:53:21.602825+00:00 | 2026-09-19T08:53:24.013056+00:00 |  |  | sba-grants | WEB_PAGE | https://www.sba.gov/funding-programs/grants |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_4eb3664f5c304290acb4 | 2026-09-19T08:53:21.790119+00:00 | 2026-09-19T08:53:22.522929+00:00 |  |  | shopify-partners | WEB_PAGE | https://www.shopify.com/partners |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_1458bbf2e4e64deb8d2b | 2026-09-19T08:53:21.940929+00:00 | 2026-09-19T08:53:22.727978+00:00 |  |  | hubspot-affiliate | WEB_PAGE | https://www.hubspot.com/partners/affiliates |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_3676dcaa16814bd1a5b4 | 2026-09-19T09:13:23.873780+00:00 | 2026-09-19T09:13:25.896031+00:00 |  |  | google-seo-starter | SEO_RESEARCH | https://developers.google.com/search/docs/fundamentals/seo-starter-guide |  | scheduled_lane_source_pool | research_document_pipeline.web_page (SEO mode) |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_9025f306e7cd42e491c8 | 2026-09-19T09:13:24.207948+00:00 | 2026-09-19T09:13:25.732885+00:00 |  |  | google-seo-starter | SEO_RESEARCH | https://developers.google.com/search/docs/fundamentals/seo-starter-guide |  | scheduled_lane_source_pool | research_document_pipeline.web_page (SEO mode) |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_de5b513b316b41918750 | 2026-09-19T09:13:24.410442+00:00 | 2026-09-19T09:13:25.768797+00:00 |  |  | google-seo-starter | SEO_RESEARCH | https://developers.google.com/search/docs/fundamentals/seo-starter-guide |  | scheduled_lane_source_pool | research_document_pipeline.web_page (SEO mode) |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_fbf950a5e211477ba21b | 2026-09-19T09:33:24.730916+00:00 | 2026-09-19T09:35:42.810756+00:00 |  |  | 6XngV5NQgMg | YOUTUBE_VIDEO | https://www.youtube.com/watch?v=6XngV5NQgMg |  | approved_channel_watchlist | youtube_full_pipeline.process_youtube_video |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_a43d965f93eb49de9a6c | 2026-09-19T09:33:24.908081+00:00 | 2026-09-19T09:33:27.439075+00:00 |  |  | mobile-detailing-academy-phoenix | WEB_PAGE | https://mobiledetailingacademy.com/mobile-detailing/phoenix-az |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_277ba87b11964affb802 | 2026-09-19T09:33:25.087132+00:00 | 2026-09-19T09:34:39.021319+00:00 |  |  | dOpBsbXGflc | YOUTUBE_VIDEO | https://www.youtube.com/watch?v=dOpBsbXGflc |  | approved_channel_watchlist | youtube_full_pipeline.process_youtube_video |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_84cab72b76cd4200802a | 2026-09-19T09:53:25.518272+00:00 | 2026-09-19T09:53:26.965529+00:00 |  |  | dOpBsbXGflc | WEB_PAGE |  |  | unfinished_high_value_investigation | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FAILED_RETRYABLE |
| research_exec_5738890226844aa2aa43 | 2026-09-19T09:53:25.864236+00:00 | 2026-09-19T09:53:27.523227+00:00 |  |  | investor-investing-basics | WEB_PAGE | https://www.investor.gov/introduction-investing |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_371fcef2df6a4a43a67d | 2026-09-19T09:53:25.957626+00:00 | 2026-09-19T09:53:29.284602+00:00 |  |  | mobile-detailing-academy-phoenix | WEB_PAGE | https://mobiledetailingacademy.com/mobile-detailing/phoenix-az |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_80d8cbad3585466686bc | 2026-09-19T10:13:27.057571+00:00 | 2026-09-19T10:13:28.956354+00:00 |  |  | hubspot-affiliate | WEB_PAGE | https://www.hubspot.com/partners/affiliates |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_80ada671a53e443381a5 | 2026-09-19T10:13:27.374230+00:00 | 2026-09-19T10:13:30.264660+00:00 |  |  | mobile-detailing-academy-phoenix | WEB_PAGE | https://mobiledetailingacademy.com/mobile-detailing/phoenix-az |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_431f989026e84f788e6a | 2026-09-19T10:13:28.012304+00:00 | 2026-09-19T10:13:29.338029+00:00 |  |  | hubspot-affiliate | WEB_PAGE | https://www.hubspot.com/partners/affiliates |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_6b93a0082b524ad9b614 | 2026-09-19T10:33:28.537315+00:00 | 2026-09-19T10:33:29.418643+00:00 |  |  | reddit-smallbusiness | WEB_PAGE | https://www.reddit.com/r/smallbusiness/ |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_29a1a297981f46d28726 | 2026-09-19T10:33:28.696611+00:00 | 2026-09-19T10:33:29.461734+00:00 |  |  | reddit-smallbusiness | WEB_PAGE | https://www.reddit.com/r/smallbusiness/ |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_2608e9989cda4217a0e2 | 2026-09-19T10:33:28.870960+00:00 | 2026-09-19T10:33:29.464952+00:00 |  |  | reddit-smallbusiness | WEB_PAGE | https://www.reddit.com/r/smallbusiness/ |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_9e18b49af6074eafa12a | 2026-09-19T10:53:29.292088+00:00 | 2026-09-19T10:53:34.663532+00:00 |  |  | sushantkarn/SEO-engine | GITHUB_REPO | https://github.com/sushantkarn/SEO-engine |  | scheduled_lane_source_pool | research_document_pipeline.github_deep |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_7f95a35de5804e5880db | 2026-09-19T10:53:29.475942+00:00 | 2026-09-19T10:53:31.300581+00:00 |  |  | sba-grants | WEB_PAGE | https://www.sba.gov/funding-programs/grants |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_a7d098176e0045cea6f0 | 2026-09-19T10:53:29.588766+00:00 | 2026-09-19T10:53:30.522822+00:00 |  |  | hubspot-affiliate | WEB_PAGE | https://www.hubspot.com/partners/affiliates |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_75072abb5c4641faaafb | 2026-09-19T11:13:30.869617+00:00 | 2026-09-19T11:13:36.320709+00:00 |  |  | mvanhorn/last30days-skill | GITHUB_REPO | https://github.com/mvanhorn/last30days-skill |  | scheduled_lane_source_pool | research_document_pipeline.github_deep |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_e76870cda8c94de49e4c | 2026-09-19T11:13:31.303505+00:00 | 2026-09-19T11:13:33.709429+00:00 |  |  | sba-business-guide | WEB_PAGE | https://www.sba.gov/business-guide |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_eb81b1c5bd864deea103 | 2026-09-19T11:13:32.053157+00:00 | 2026-09-19T11:13:34.081264+00:00 |  |  | google-seo-starter | SEO_RESEARCH | https://developers.google.com/search/docs/fundamentals/seo-starter-guide |  | scheduled_lane_source_pool | research_document_pipeline.web_page (SEO mode) |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_3d7cef8686ef4996b3f3 | 2026-09-19T11:33:32.791896+00:00 | 2026-09-19T11:34:23.100308+00:00 |  |  | dOpBsbXGflc | YOUTUBE_VIDEO | https://www.youtube.com/watch?v=dOpBsbXGflc |  | approved_channel_watchlist | youtube_full_pipeline.process_youtube_video |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_4f290598cd9e4804b9b9 | 2026-09-19T11:33:33.065757+00:00 | 2026-09-19T11:33:34.043185+00:00 |  |  | investor-investing-basics | WEB_PAGE | https://www.investor.gov/introduction-investing |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_5ceb8e80a71848bf9481 | 2026-09-19T11:33:33.187614+00:00 | 2026-09-19T11:33:34.043656+00:00 |  |  | reddit-smallbusiness | WEB_PAGE | https://www.reddit.com/r/smallbusiness/ |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_e690ab55e3574e0f81fa | 2026-09-19T11:53:33.590210+00:00 | 2026-09-19T11:53:35.534272+00:00 |  |  | sba-grants | WEB_PAGE | https://www.sba.gov/funding-programs/grants |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_dc1e0a66e4ea40adaa56 | 2026-09-19T11:53:33.805821+00:00 | 2026-09-19T11:53:35.128008+00:00 |  |  | hubspot-affiliate | WEB_PAGE | https://www.hubspot.com/partners/affiliates |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_9de62cf26e614ad3a47f | 2026-09-19T11:53:33.972263+00:00 | 2026-09-19T11:53:35.704112+00:00 |  |  | sba-grants | WEB_PAGE | https://www.sba.gov/funding-programs/grants |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_6766952171824af98e25 | 2026-09-19T12:13:35.214942+00:00 | 2026-09-19T12:13:37.140390+00:00 |  |  | sba-business-guide | WEB_PAGE | https://www.sba.gov/business-guide |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_4c7df9dd30294263bff7 | 2026-09-19T12:13:35.410823+00:00 | 2026-09-19T12:13:37.111210+00:00 |  |  | google-seo-starter | SEO_RESEARCH | https://developers.google.com/search/docs/fundamentals/seo-starter-guide |  | scheduled_lane_source_pool | research_document_pipeline.web_page (SEO mode) |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_a074f9319822486581fd | 2026-09-19T12:13:35.566225+00:00 | 2026-09-19T12:13:38.976642+00:00 |  |  | sushantkarn/SEO-engine | GITHUB_REPO | https://github.com/sushantkarn/SEO-engine |  | scheduled_lane_source_pool | research_document_pipeline.github_deep |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_b7e45c3e39864aa59121 | 2026-09-19T12:33:36.006617+00:00 | 2026-09-19T12:33:40.069838+00:00 |  |  | mvanhorn/last30days-skill | GITHUB_REPO | https://github.com/mvanhorn/last30days-skill |  | scheduled_lane_source_pool | research_document_pipeline.github_deep |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_e6e0c66891a649c8b93d | 2026-09-19T12:33:36.239146+00:00 | 2026-09-19T12:33:40.056337+00:00 |  |  | mvanhorn/last30days-skill | GITHUB_REPO | https://github.com/mvanhorn/last30days-skill |  | scheduled_lane_source_pool | research_document_pipeline.github_deep |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_d081e8dff0f44d1ca8fc | 2026-09-19T12:33:36.409301+00:00 | 2026-09-19T12:33:40.068417+00:00 |  |  | mvanhorn/last30days-skill | GITHUB_REPO | https://github.com/mvanhorn/last30days-skill |  | scheduled_lane_source_pool | research_document_pipeline.github_deep |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_b884a0fb703441618e5a | 2026-09-19T12:53:36.776865+00:00 | 2026-09-19T12:54:35.448025+00:00 |  |  | 6XngV5NQgMg | YOUTUBE_VIDEO | https://www.youtube.com/watch?v=6XngV5NQgMg |  | approved_channel_watchlist | youtube_full_pipeline.process_youtube_video |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_569d97ef86ef4c2a897b | 2026-09-19T12:53:37.003307+00:00 | 2026-09-19T12:53:37.803534+00:00 |  |  | investor-investing-basics | WEB_PAGE | https://www.investor.gov/introduction-investing |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_10afb6b54ac84422a84f | 2026-09-19T12:53:37.140912+00:00 | 2026-09-19T12:53:37.876364+00:00 |  |  | shopify-partners | WEB_PAGE | https://www.shopify.com/partners |  | scheduled_lane_source_pool | research_document_pipeline.web_page |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| FULLY_PROCESSED |
| research_exec_f94a7771d1874230bb78 | 2026-09-19T13:13:39.258229+00:00 |  |  |  |  |  |  |  |  |  |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| NO_TERMINAL_EVENT_AT_WINDOW_END |
| research_exec_b10c8376d1f74b179156 | 2026-09-19T13:13:39.506783+00:00 |  |  |  |  |  |  |  |  |  |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| NO_TERMINAL_EVENT_AT_WINDOW_END |
| research_exec_d0fdff95b3df47a998bf | 2026-09-19T13:13:39.668643+00:00 |  |  |  |  |  |  |  |  |  |  |  |NO_TERMINAL_EVENT_AT_WINDOW_END||  || NO | NO |  |  | 1 |NO_TERMINAL_EVENT_AT_WINDOW_END| NO_TERMINAL_EVENT_AT_WINDOW_END |

## 2. Unique source ledger

UNIQUE_SOURCE_COUNT=18. Counts are source selections in the exact window.

| source_id | title | URL/domain | first_selected_at | times_selected | times_fully_processed | times_duplicate | times_failed | audit observation |
|---|---|---|---:|---:|---:|---:|---:|---|
| 4-HNOWyfemk |  | www.youtube.com | 2026-09-18T23:11:39.074673+00:00 |4|0|0|4| Processed source; no durable distinct information-gain field preserved. |
| 6XngV5NQgMg |  | www.youtube.com | 2026-09-19T01:32:16.122079+00:00 |4|4|0|0| Processed source; no durable distinct information-gain field preserved. |
| CiGQ7to-5J4 |  | www.youtube.com | 2026-09-19T02:52:22.338565+00:00 |2|0|0|2| Processed source; no durable distinct information-gain field preserved. |
| LdDr2viNh2w |  | www.youtube.com | 2026-09-19T01:12:15.354970+00:00 |2|0|0|2| Processed source; no durable distinct information-gain field preserved. |
| TlpJdvFQLeY |  | www.youtube.com | 2026-09-19T03:32:26.052287+00:00 |1|0|0|1| Processed source; no durable distinct information-gain field preserved. |
| crj-goclear-capability-research-v1 |  |  | 2026-09-19T00:31:48.636979+00:00 |1|0|0|1| Processed source; no durable distinct information-gain field preserved. |
| dOpBsbXGflc |  | www.youtube.com | 2026-09-19T07:33:13.523633+00:00 |5|2|0|3| Processed source; no durable distinct information-gain field preserved. |
| google-seo-starter |  | developers.google.com | 2026-09-18T23:09:38.246574+00:00 |19|19|0|0| SEO fundamentals: crawling/indexing, sitemaps, robots, metadata, canonicalization, Search Console/Analytics; no downstream item. |
| hubspot-affiliate |  | www.hubspot.com | 2026-09-18T23:31:41.119518+00:00 |16|16|0|0| Affiliate/partner ecosystem and commission evidence visible; no canonical monetization candidate. |
| investor-investing-basics |  | www.investor.gov | 2026-09-19T00:11:46.623471+00:00 |7|0|7|0| Investor education/risk/diversification material; no opportunity record. |
| mobile-detailing-academy-phoenix |  | mobiledetailingacademy.com | 2026-09-18T23:51:41.733764+00:00 |14|14|0|0| Phoenix service/pricing/neighborhood/rebook signals visible; no demand record. |
| mvanhorn/last30days-skill |  | github.com | 2026-09-19T00:52:04.407893+00:00 |8|1|7|0| Multi-source recent-research capability observation; no qualification or handoff. |
| reddit-smallbusiness |  | www.reddit.com | 2026-09-19T00:11:46.963983+00:00 |10|10|0|0| Extraction recorded NOT_PRESENT; no individual demand signal preserved. |
| sba-business-guide |  | www.sba.gov | 2026-09-18T23:51:42.041751+00:00 |7|0|7|0| Business credit/funding/counseling guidance; repeated unchanged selections. |
| sba-grants |  | www.sba.gov | 2026-09-18T23:11:37.973253+00:00 |10|0|10|0| Grant eligibility/STEP/export framing; repeated unchanged selections. |
| sba-loans |  | www.sba.gov | 2026-09-19T01:12:15.489670+00:00 |2|0|2|0| Processed source; no durable distinct information-gain field preserved. |
| shopify-partners |  | www.shopify.com | 2026-09-19T01:52:17.312575+00:00 |5|0|5|0| Partner/referral/app/theme ecosystem; no downstream opportunity record. |
| sushantkarn/SEO-engine |  | github.com | 2026-09-18T23:11:38.613805+00:00 |8|0|8|0| SEO engine capability observation; no qualification or handoff. |

## 3. Duplicate forensics

DUPLICATE_COUNT=46 across 7 unique sources. Duplicate status is only visible on the completed result; no preflight content fingerprint or freshness decision is persisted.

| execution_id | source_id | previous matching execution | time_since_previous | why selected | duplicate knowable | full processing before detection | alternative source | useful state change |
|---|---|---|---|---|---|---|---|---|
| research_exec_8f9e63f423294f0f9a93 | sba-grants |  |  | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_ecdb356be3714d6bb62c | sushantkarn/SEO-engine |  |  | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_38257a69f52741e392f8 | sba-business-guide |  |  | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_3cd94ce24a294265a5d3 | investor-investing-basics |  |  | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_c552e3b5929e4d7dbffa | sba-grants | research_exec_8f9e63f423294f0f9a93 | 1:00:08.819861 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_718bc0fcc01f4ea8943c | sushantkarn/SEO-engine | research_exec_ecdb356be3714d6bb62c | 1:40:22.440768 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_91f97e9f9630497fba0a | mvanhorn/last30days-skill |  |  | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_5353fa01098b473db2f6 | sushantkarn/SEO-engine | research_exec_718bc0fcc01f4ea8943c | 0:00:05.728476 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_6510667e50bc42a396cf | sba-loans |  |  | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_1db640024a904f5d876e | sba-business-guide | research_exec_38257a69f52741e392f8 | 1:40:34.471526 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_0e5ebe2f24ef4869b35b | shopify-partners |  |  | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_4afe5654a1ab42a4aede | sba-grants | research_exec_c552e3b5929e4d7dbffa | 1:40:30.795616 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_393b4997dc38426d9754 | sba-business-guide | research_exec_1db640024a904f5d876e | 0:20:01.199760 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_0ab34cb520cd481c9c1c | mvanhorn/last30days-skill | research_exec_91f97e9f9630497fba0a | 1:40:16.747959 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_4700a7dc9c1d4e818123 | sushantkarn/SEO-engine | research_exec_5353fa01098b473db2f6 | 1:40:14.787071 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_b9ff566794cf402b8e20 | sba-grants | research_exec_4afe5654a1ab42a4aede | 1:20:07.375323 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_9a728b1e48794e0b81d0 | shopify-partners | research_exec_0e5ebe2f24ef4869b35b | 2:00:09.658247 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_9e6540b51f5b4cb5a932 | investor-investing-basics | research_exec_3cd94ce24a294265a5d3 | 4:00:41.970088 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_9e4108f99cba46b9aa25 | investor-investing-basics | research_exec_9e6540b51f5b4cb5a932 | 0:00:00.465641 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_4bba7b1cf66e422e8ed9 | sba-grants | research_exec_b9ff566794cf402b8e20 | 1:20:04.672959 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_e7992a58ba9d4049a77c | sushantkarn/SEO-engine | research_exec_4700a7dc9c1d4e818123 | 2:20:08.468540 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_2f8adbfba7c849c2aad7 | sba-business-guide | research_exec_393b4997dc38426d9754 | 3:40:31.021856 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_15369ee318ba497d8be6 | investor-investing-basics | research_exec_9e4108f99cba46b9aa25 | 1:40:21.823612 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_af22f9bf7dcf45409769 | sba-grants | research_exec_4bba7b1cf66e422e8ed9 | 1:40:31.997007 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_d4cf9c928cec440c82b4 | sba-loans | research_exec_6510667e50bc42a396cf | 5:40:52.396864 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_191c8e5825504eafaa82 | shopify-partners | research_exec_9a728b1e48794e0b81d0 | 3:00:41.328925 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_7c0fabf479c14078a368 | sushantkarn/SEO-engine | research_exec_e7992a58ba9d4049a77c | 2:00:39.044471 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_c7e6d5304d174478b3da | sba-business-guide | research_exec_2f8adbfba7c849c2aad7 | 2:40:31.491332 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_866b86f0cc3c4cd593f3 | mvanhorn/last30days-skill | research_exec_3f492618229b4767a67c | 3:40:50.556471 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_84219f4d26ce453bbd7f | sba-grants | research_exec_af22f9bf7dcf45409769 | 2:40:19.968806 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_4eb3664f5c304290acb4 | shopify-partners | research_exec_191c8e5825504eafaa82 | 2:00:13.490372 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_5738890226844aa2aa43 | investor-investing-basics | research_exec_15369ee318ba497d8be6 | 4:00:34.981424 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_9e18b49af6074eafa12a | sushantkarn/SEO-engine | research_exec_7c0fabf479c14078a368 | 4:00:20.208957 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_7f95a35de5804e5880db | sba-grants | research_exec_84219f4d26ce453bbd7f | 2:00:07.873117 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_75072abb5c4641faaafb | mvanhorn/last30days-skill | research_exec_866b86f0cc3c4cd593f3 | 2:40:09.869385 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_e76870cda8c94de49e4c | sba-business-guide | research_exec_c7e6d5304d174478b3da | 3:00:11.077280 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_4f290598cd9e4804b9b9 | investor-investing-basics | research_exec_5738890226844aa2aa43 | 1:40:07.201521 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_e690ab55e3574e0f81fa | sba-grants | research_exec_7f95a35de5804e5880db | 1:00:04.114268 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_9de62cf26e614ad3a47f | sba-grants | research_exec_e690ab55e3574e0f81fa | 0:00:00.382053 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_6766952171824af98e25 | sba-business-guide | research_exec_e76870cda8c94de49e4c | 1:00:03.911437 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_a074f9319822486581fd | sushantkarn/SEO-engine | research_exec_9e18b49af6074eafa12a | 1:20:06.274137 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_b7e45c3e39864aa59121 | mvanhorn/last30days-skill | research_exec_75072abb5c4641faaafb | 1:20:05.137000 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_e6e0c66891a649c8b93d | mvanhorn/last30days-skill | research_exec_b7e45c3e39864aa59121 | 0:00:00.232529 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_d081e8dff0f44d1ca8fc | mvanhorn/last30days-skill | research_exec_e6e0c66891a649c8b93d | 0:00:00.170155 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_569d97ef86ef4c2a897b | investor-investing-basics | research_exec_4f290598cd9e4804b9b9 | 1:20:03.937550 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |
| research_exec_10afb6b54ac84422a84f | shopify-partners | research_exec_4eb3664f5c304290acb4 | 4:00:15.350793 | scheduled selection; no persisted freshness/change reason | after result processing | YES | NO | NO |

TOP_DUPLICATE_SOURCES=sba-grants (10), sushantkarn/SEO-engine (8), investor-investing-basics (7), mvanhorn/last30days-skill (7), sba-business-guide (7), shopify-partners (5), sba-loans (2)
DUPLICATES_DETECTED_BEFORE_EXPENSIVE_PROCESSING=0 evidenced
DUPLICATES_DETECTED_AFTER_EXPENSIVE_PROCESSING=46
REPEATED_SOURCE_SELECTION_DEFECTS=YES; repeated unchanged selection has no persisted freshness/change rationale.

## 4. Retryable failure forensics

All 16 retryables had retry/attempt count 1, no alternate source, alternate processor, or fallback event in the exact ledger.

| execution_id | source | title | processor | exact failure | failure_class | retry | same_strategy | alternate_source | alternate_processor | fallback | later_source_success | final_outcome |
|---|---|---|---|---|---|---:|---|---|---|---|---|---|
| research_exec_0a2506fd54b74f28a759 |  |  |  | scheduled selection failed: RSS=HTTP Error 500: Internal Server Error; yt-dlp=command timed out after 20s | SOURCE_SELECTION_FAILURE | 1 | YES | NO | NO | NO | NO | FAILED_RETRYABLE |
| research_exec_d2744436022042519ad2 | 4-HNOWyfemk |  | youtube_full_pipeline.process_youtube_video | scheduled processor failed | SCHEDULED_PROCESSOR_FAILURE | 1 | YES | NO | NO | NO | NO | FAILED_RETRYABLE |
| research_exec_76eec20da70e4e0c96b3 | crj-goclear-capability-research-v1 |  | research_document_pipeline.web_page | unknown url type: '' | MISSING_OR_EMPTY_URL | 1 | YES | NO | NO | NO | NO | FAILED_RETRYABLE |
| research_exec_e923d32238e34e7fb5ba | LdDr2viNh2w |  | youtube_full_pipeline.process_youtube_video | scheduled processor failed | SCHEDULED_PROCESSOR_FAILURE | 1 | YES | NO | NO | NO | NO | FAILED_RETRYABLE |
| research_exec_07d3e801a6ab4c73b500 | LdDr2viNh2w |  | youtube_full_pipeline.process_youtube_video | scheduled processor failed | SCHEDULED_PROCESSOR_FAILURE | 1 | YES | NO | NO | NO | NO | FAILED_RETRYABLE |
| research_exec_93a79711e81047cf85fd | CiGQ7to-5J4 |  | youtube_full_pipeline.process_youtube_video | scheduled processor failed | SCHEDULED_PROCESSOR_FAILURE | 1 | YES | NO | NO | NO | NO | FAILED_RETRYABLE |
| research_exec_b1fb151a5d8f4b0da3a3 | CiGQ7to-5J4 |  | research_document_pipeline.web_page | unknown url type: '' | MISSING_OR_EMPTY_URL | 1 | YES | NO | NO | NO | NO | FAILED_RETRYABLE |
| research_exec_8c51c8f48d384d8590b7 | TlpJdvFQLeY |  | youtube_full_pipeline.process_youtube_video | scheduled processor failed | SCHEDULED_PROCESSOR_FAILURE | 1 | YES | NO | NO | NO | NO | FAILED_RETRYABLE |
| research_exec_32ed72b5a35848aebb5e | 4-HNOWyfemk |  | youtube_full_pipeline.process_youtube_video | scheduled processor failed | SCHEDULED_PROCESSOR_FAILURE | 1 | YES | NO | NO | NO | NO | FAILED_RETRYABLE |
| research_exec_3d58c46709cc400a9c22 | 4-HNOWyfemk |  | research_document_pipeline.web_page | unknown url type: '' | MISSING_OR_EMPTY_URL | 1 | YES | NO | NO | NO | NO | FAILED_RETRYABLE |
| research_exec_1317ebd35cf84b00ab8a |  |  |  | scheduled selection failed: RSS=HTTP Error 404: Not Found; yt-dlp=command timed out after 20s | SOURCE_SELECTION_FAILURE | 1 | YES | NO | NO | NO | NO | FAILED_RETRYABLE |
| research_exec_b152c921f98348418e10 | 4-HNOWyfemk |  | youtube_full_pipeline.process_youtube_video | scheduled processor failed | SCHEDULED_PROCESSOR_FAILURE | 1 | YES | NO | NO | NO | NO | FAILED_RETRYABLE |
| research_exec_cecb519b1fa94b6f8b99 |  |  |  | scheduled selection failed: RSS=HTTP Error 404: Not Found; yt-dlp=command timed out after 20s | SOURCE_SELECTION_FAILURE | 1 | YES | NO | NO | NO | NO | FAILED_RETRYABLE |
| research_exec_ea152f5d6bb54422bc72 | dOpBsbXGflc |  | youtube_full_pipeline.process_youtube_video | scheduled processor failed | SCHEDULED_PROCESSOR_FAILURE | 1 | YES | NO | NO | NO | YES | FAILED_RETRYABLE |
| research_exec_6389bb4975424f618257 | dOpBsbXGflc |  | youtube_full_pipeline.process_youtube_video | scheduled processor failed | SCHEDULED_PROCESSOR_FAILURE | 1 | YES | NO | NO | NO | YES | FAILED_RETRYABLE |
| research_exec_84cab72b76cd4200802a | dOpBsbXGflc |  | research_document_pipeline.web_page | unknown url type: '' | MISSING_OR_EMPTY_URL | 1 | YES | NO | NO | NO | YES | FAILED_RETRYABLE |

UNIQUE_FAILURE_ROOT_CAUSES=3: SCHEDULED_PROCESSOR_FAILURE, MISSING_OR_EMPTY_URL, SOURCE_SELECTION_FAILURE.
RECOVERY_SUCCESS_RATE=7.7% source-level later success among processor-failure rows; 0% failed-execution recovery.
FALLBACK_USAGE_RATE=0%
SAME_FAILURE_REPEATED_COUNT=13 scheduled processor failures; no strategy change evidenced.

## 5. New intelligence and investigation depth

NEW_INTELLIGENCE_COUNT=0 confirmed. The following five are source-level observations, not confirmed new intelligence because durable per-execution diff/evidence promotion is absent.

| observation | source | why interesting | followup | Alpha saw it | current state |
|---|---|---|---|---|---|
| Phoenix mobile-detailing pricing/rebook signals | mobile-detailing-academy-phoenix | possible local-service demand/offer evidence | NO | NO | stored in artifact; no need/opportunity record |
| HubSpot affiliate ecosystem/commission evidence | hubspot-affiliate | possible affiliate/referral path | NO | NO | processed; no monetization record |
| Shopify partner capabilities/referrals | shopify-partners | possible partner/service/affiliate path | NO | NO | processed; no Alpha/handoff |
| SEO-engine automation capability | sushantkarn/SEO-engine | possible internal capability | NO | NO | not qualified/routed |
| Last30Days multi-source capability | mvanhorn/last30days-skill | possible research capability | NO | NO | not qualified/routed |

MEANINGFUL_FINDINGS=0 confirmed / 5 observations
FINDINGS_WITH_FOLLOWUP=0
FINDINGS_WITHOUT_FOLLOWUP=5
FOLLOWUP_INVESTIGATION_RATE=0%

### Premature research stop ledger

| source | stored signal | stop state | missing next investigation |
|---|---|---|---|
| hubspot-affiliate | affiliate/commission evidence | processing ended | cross-source validation, economics, fit, Alpha |
| shopify-partners | partner/referral/service ecosystem | processing ended | customer demand, economics, fit, Alpha |
| mobile-detailing-academy-phoenix | local service/pricing signal | processing ended | demand language, alternatives, economics, Alpha |
| sushantkarn/SEO-engine | technical capability | processing ended | execution/license/maintenance/fit, Alpha |
| mvanhorn/last30days-skill | research capability | processing ended | capability qualification and routing, Alpha |

## 6. Customer-demand forensics

RAW_CUSTOMER_SIGNALS_FOUND=0 preserved as canonical demand records. CUSTOMER_SIGNALS_PROMOTED=0. CUSTOMER_SIGNALS_NOT_PROMOTED=0 identifiable. This means acquisition/extraction evidence was insufficient; it does not prove demand was absent.

| source | audience | problem/complaint/question | desired outcome/language | classification | confidence | next state |
|---|---|---|---|---|---|---|
| reddit-smallbusiness | small-business audience only | no individual signal; extraction NOT_PRESENT | none preserved | no demand record | unknown | stopped at source processing |

## 7. Business and monetization signals

BUSINESS_SIGNAL_COUNT=5 source-level observations, not qualified opportunities. No canonical monetization candidate or Alpha review was created.

| source | observed angle | recognized durably | investigated | Alpha | why stopped |
|---|---|---|---|---|---|
| hubspot-affiliate | affiliate/referral | NO | NO | NO | processing ended |
| shopify-partners | affiliate/referral/service | NO | NO | NO | processing ended |
| mobile-detailing-academy-phoenix | service/content/lead generation | NO | NO | NO | processing ended |
| sushantkarn/SEO-engine | internal capability/service/software | NO | NO | NO | processing ended |
| mvanhorn/last30days-skill | internal research capability | NO | NO | NO | processing ended |

## 8. Research-side gating

RESEARCH_VALUE_GATES: no direct business-value gate was persisted in exact execution decisions. Observed dispositions were MONITOR, DUPLICATE_UNCHANGED, DEEP_RESEARCH, INSUFFICIENT_SOURCE, and retryable failure.
IMPROPER_BUSINESS_GATING_FOUND=NO direct evidence; UNKNOWN for implicit source-pool suppression.
BUSINESS_GATING_LEDGER=EMPTY for explicit business-value gates.
Valid filters evidenced: duplicate/no-change, malformed/empty source, source-selection failure, processor failure.

## 9. Alpha forensics

ALPHA_RUNTIME_JOBS=0 in the exact window. MODEL_BACKED_ALPHA_REVIEWS=0. MODEL_CALLS_ZERO_REVIEWS=0. RESEARCH_V2_ALPHA_REVIEWS=0.
Alpha receipts found in the repository outside the exact window are not counted; the CRJ Alpha receipt at 2026-09-19T13:59:45Z is after the audit end.
ALPHA_DECISION_LEDGER=EMPTY for exact window.
ALPHA_REJECTIONS=0. VALID_REJECTIONS=0. SHOULD_HAVE_BEEN_RESEARCH_MORE=0. PREMATURE_REJECTIONS=0. SECONDARY_VALUE_MISSED=UNKNOWN because no exact-window Alpha decision occurred.

## 10. Source processing versus research

| activity class | count | interpretation |
|---|---:|---|
| DUPLICATE_CHECK | 46 | unchanged result |
| EXTRACTION_ONLY | 112 | completed source processor without persisted follow-up |
| OTHER | 19 | failed or unterminated execution |

SOURCE_PROCESSING_RATE=85.5% (112/131 execution IDs reached a terminal completed state; 89.6% of 125 source-selected executions)
TRUE_INVESTIGATION_RATE=0% evidenced
THESIS_DEVELOPMENT_RATE=0% evidenced

## 11. Wasted cycles

WASTED_CYCLE_COUNT=65 under the supplied strict definition (46 duplicates + 16 retryables + 3 unterminated).
WASTED_CYCLE_RATE=49.6% (65/131 execution IDs)
WASTED_CYCLE_ROOT_CAUSES=duplicate selection 46; retryable failure 16; unterminated-at-boundary 3. Full processing rows are not labeled wasted solely because downstream value is unobservable.

## 12. Root-cause matrix

| hypothesis | result | evidence |
|---|---|---|
| A. source pool too repetitive | YES | 125 selections / 18 source IDs; repeated sources dominate |
| B. scheduler selects badly | YES | unchanged sources selected without persisted freshness/change rationale |
| C. duplicate detection too late | YES | 0 duplicate results after processor events |
| D. retry policy ineffective | YES | 16 one-attempt retryables; no strategy change |
| E. fallback weak | YES | 0 fallback/alternate-source events |
| F. AI stops instead of investigating | PARTIAL | five observations ended without follow-up; AI-level trace absent |
| G. AI makes business-value decisions | UNKNOWN | no explicit business gate; implicit suppression unobservable |
| H. Alpha not invoked | YES | 112 completed rows show no Alpha invocation; exact-window Alpha jobs 0 |
| I. Alpha rejection-oriented | UNKNOWN | no exact-window Alpha decisions |
| J. demand lane insufficient | YES | zero preserved demand records; Reddit NOT_PRESENT |
| K. source quality poor | PARTIAL | some artifacts useful; multiple failures/empty sources |
| L. tooling insufficient | YES | no durable content diff/fingerprint/follow-up linkage |
| M. processor rather than investigator | YES | processing and duplicate activity; no exact-window follow-up/Alpha/handoff |

## 13. Top ten research findings

No confirmed new intelligence can be ranked from the exact ledger. The five inspectable observations above are the complete conservative set. The remaining top-five slots are UNKNOWN rather than invented.

1. Phoenix mobile-detailing service/pricing/rebook observation — source artifact only; no follow-up.
2. HubSpot affiliate/commission observation — source artifact only; no monetization route.
3. Shopify partner/referral observation — source artifact only; no Alpha.
4. SEO-engine capability observation — no qualification.
5. Last30Days capability observation — no qualification.
6–10. UNKNOWN from durable exact-window evidence.

## 14. Final audit fields

RESEARCH_VALUE_GATES=no explicit business-value gates; valid processing gates observed
IMPROPER_BUSINESS_GATING_FOUND=NO direct evidence; implicit UNKNOWN
PREMATURE_RESEARCH_STOP_LEDGER=5 observations listed above
TOP_DUPLICATE_SOURCES=sba-grants (10), sushantkarn/SEO-engine (8), investor-investing-basics (7), mvanhorn/last30days-skill (7), sba-business-guide (7), shopify-partners (5), sba-loans (2)

## Conclusion and next recommended repair

The evidence supports that Research primarily selected, processed, classified, and stored sources rather than running a closed-loop investigation. The next repair should be chosen after this before-state: preserve per-execution content/change evidence, suppress repeated unchanged selections before expensive processing, connect evidence-ready work to the existing Alpha consumer, and make follow-up investigation observable. Those are recommendations only; no behavior was changed in this audit.

RAY_ACTION_REQUIRED=NO
RAY_DECISION_REQUIRED=NO
NEXT_RECOMMENDED_REPAIR=Review this forensic report, then repair observability and evidence-ready-to-Alpha consumption before changing prompts or thresholds.

## Change control

NO_TERMINAL_COUNT=3
ROOT_CAUSE_MATRIX=COMPLETE (A–M classified with evidence above)
REPORT_PATH=reports/research/NEXUS_RESEARCH_FORENSIC_OVERNIGHT_AUDIT_2026-09-19.md
REPORT_COMPLETE=YES
FILES_CHANGED=reports/research/NEXUS_RESEARCH_FORENSIC_OVERNIGHT_AUDIT_2026-09-19.md
TESTS_RUN=read-only ledger reconstruction, exact-window count reconciliation, report validation
TEST_RESULTS=PASS bounded forensic reconstruction; no Research/Alpha behavior changes
COMMITS=PENDING
