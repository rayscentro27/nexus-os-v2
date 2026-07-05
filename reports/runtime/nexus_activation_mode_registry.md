# Nexus Activation Mode Registry

**Generated**: 2026-07-05

---

## Mode Definitions

| Mode | Definition | When to Use |
|------|-----------|-------------|
| OBSERVE | Read-only inspection | Confirming files, status, routes, reports |
| DRY_RUN | Generate without sending | Producing reports, drafts, scoring without external action |
| SANDBOX_TEST | Test mode with synthetic data | Using test accounts, demo modes, staging routes |
| APPROVED_LIVE | Production ready | Real accounts, real data, real actions, Ray approved |

---

## Registry: All Capabilities by Mode

### OBSERVE (22 capabilities)
1. Supabase Client reads
2. DB Service reads
3. Hermes Context Adapter reads
4. Client Dashboard Data reads
5. YouTube metadata cache
6. NotebookLM exports
7. Report index reading
8. Config reading
9. Command Center UI
10. System Health Panel
11. Client Portal (all pages)
12. Credit profile (placeholder)
13. Credit utilization (placeholder)
14. Business setup profile (migration exists)
15. Funding readiness (migration exists)
16. Documents (migration exists)
17. Recommendations (placeholder)
18. Resources/affiliate options
19. Ray Review/Approvals
20. Route/page inventory
21. Connector registry
22. Process registry

### DRY_RUN (12 capabilities)
1. Department Feeders (18 feeders)
2. Social publish job
3. Nexus runner
4. Email sending (Resend)
5. YouTube research scripts
6. Research-to-money pipeline
7. Opportunity scoring
8. Report generation
9. Meta/Instagram posting
10. YouTube API calls
11. Marketing drafts
12. Content calendar

### SANDBOX_TEST (14 capabilities)
1. Seed day 1 event
2. Seed premium foundation
3. Seed static data
4. Alpha Search (Netlify)
5. Alpha URL Review (Netlify)
6. Alpha Provider (Netlify)
7. Hermes Chat (Edge)
8. Hermes Search (Edge)
9. Oanda demo trading
10. Trading research pipeline
11. Full activation script
12. Continuous loop
13. OpenRouter LLM routing
14. Firecrawl URL review

### APPROVED_LIVE (4 capabilities)
1. Got Funding landing page
2. Vite dev server
3. Vite build
4. Test suite

---

## Mode Distribution

| Mode | Count | Percentage |
|------|-------|-----------|
| OBSERVE | 22 | 42% |
| DRY_RUN | 12 | 23% |
| SANDBOX_TEST | 14 | 27% |
| APPROVED_LIVE | 4 | 8% |
| **Total** | **52** | **100%** |

---

## Key Insight

Only **8%** of capabilities are APPROVED_LIVE. The system has strong foundations (42% OBSERVE, 23% DRY_RUN, 27% SANDBOX_TEST) but most capabilities need verification before going live. Prompt 2 should focus on:
1. Verifying Supabase live connectivity
2. Testing DRY_RUN capabilities with real data
3. Promoting SANDBOX_TEST capabilities to DRY_RUN or APPROVED_LIVE
4. Building missing capabilities (Credit/Funding, Billing/Referral)
