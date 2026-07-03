# Hermes Alpha Phase 1 Evaluation Harness Report

Status: **working offline with deterministic mock/evaluation-only fixtures**.

The harness loads 11 local JSON fixtures, routes them through pure Alpha functions, records score/rating, recommendation, draft output location, safety status, draft-only state, prohibited-adapter state, pass/fail, and report path. It performs no file write, network, model, database, broker, send, publish, charge, or production action.

| Fixture | Category | Route | Score/rating | Safety | Draft output | Result |
|---|---|---|---:|---|---|---|
| mock_business_opportunity | business opportunity | business_opportunity | deterministic score | passed | none | pass |
| mock_affiliate_referral | affiliate/referral | affiliate_offer | deterministic score | passed | none | pass |
| mock_landing_page | landing draft | marketing_asset | deterministic score | passed | aggregate fixture result | pass |
| mock_newsletter | newsletter draft | marketing_asset | deterministic score | passed | aggregate fixture result | pass |
| mock_social_post | Facebook/social draft | marketing_asset | deterministic score | passed | aggregate fixture result | pass |
| mock_image_prompt | creative prompt | marketing_asset | deterministic score | passed | aggregate fixture result | pass |
| mock_trading_strategy | strategy research | trading_research | deterministic score | passed | none | pass |
| mock_backtest_plan | backtest plan | trading_research | deterministic score | passed | aggregate fixture result | pass |
| mock_trading_risk_review | risk review | trading_research | deterministic score | passed | aggregate fixture result | pass |
| mock_ray_review_proposal | proposal | business_opportunity | deterministic score | passed | aggregate fixture result | pass |
| blocked_external_action | prohibited charge/publish request | marketing_asset | blocked | blocked as expected | none | pass |

Sources: `hermes_alpha/evaluations/fixtures/phase1_fixtures.json`, `src/hermes/alpha/alphaEvaluationHarness.ts`, and `hermes_alpha/evaluations/results/phase1_results.json`.

All outputs are temporary evaluation artifacts. They are not real research ingestion, market evidence, revenue, client activity, marketing performance, backtests, or trades.
