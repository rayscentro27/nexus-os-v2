# Nexus 3.0 Regression

Commands and results:
- npm run typecheck: PASS
- npm run build: PASS
- npx vitest run tests/revenue_activation.test.ts: PASS, 12/12
- npx vitest run tests/hermes_context_layer.test.js --testTimeout=20000: PASS, 25/25
- npx vitest run tests/hermes_live_context.test.ts --testTimeout=20000: PASS, 18/18
- npx vitest run tests/hermes_readiness_review_delivery.test.ts tests/readiness_review_intake_admin_flow.test.ts tests/tester_readiness.test.ts --testTimeout=20000: PASS, 103/103
- npx vitest run tests/goclear_readiness_report_builder.test.ts tests/goclear_readiness_internal_test_runner.test.ts --testTimeout=20000: PASS, 35/35
- python3 scripts/checks/certify_authenticated_rls.py: PASS, 45/45

Build warning:
- existing large JS chunk warning remains.
