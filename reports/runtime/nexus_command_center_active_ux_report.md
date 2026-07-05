# Nexus Command Center — Active UX Report

**Generated**: 2026-07-05

---

## Section Status

| Section | Status | Mode | Last Checked | Active Process | Connected | Next Action |
|---------|--------|------|-------------|----------------|-----------|-------------|
| Supabase | ENV_PRESENT | ACTIVE_INTERNAL | 2026-07-05 | supabase_verification | Expected | Verify via browser |
| Daily Monitor | EXISTS | ACTIVE_INTERNAL | 2026-07-05 | daily_monitor | Yes | Run via runner |
| Active Runner | EXISTS | ACTIVE_INTERNAL | 2026-07-05 | active_operator_runner | Yes | Run --once |
| Process Registry | LOADED | ACTIVE_INTERNAL | 2026-07-05 | process_registry | Yes | Validate |
| Command Center | ACTIVE | OBSERVE | 2026-07-05 | command_center_health | Yes | Check UX |
| Client Portal | PARTIAL | OBSERVE | 2026-07-05 | client_portal_status | Synthetic | Build premium shell |
| Ray Review | EXISTS | ACTIVE_INTERNAL | 2026-07-05 | ray_review_queue | Local | Load queue |
| Hermes | ACTIVE | ACTIVE_INTERNAL | 2026-07-05 | hermes_router | Local | Route requests |
| Alpha | ACTIVE | ACTIVE_INTERNAL | 2026-07-05 | alpha_intake | Local | Process intake |
| Telegram | ACTIVE | TELEGRAM_OPERATOR | 2026-07-05 | telegram_operator | Mock bridge | Start bridge |
| Stripe/Paywall | BLOCKED | BLOCKED | 2026-07-05 | stripe_test_paywall | No env | Add keys |
| Research/NotebookLM | EXISTS | DRY_RUN | 2026-07-05 | research_intelligence | Local | Run dry-run |
| Creative Engine | EXISTS | DRY_RUN | 2026-07-05 | creative_quality_loop | Local | Run dry-run |
| Recovery | EXISTS | ACTIVE_INTERNAL | 2026-07-05 | recovery | Local | Run check |

---

## Data Sources

| Section | Data Source | Mock? |
|---------|------------|-------|
| Supabase | Env + config | No |
| Daily Monitor | Script output | No |
| Active Runner | Script output | No |
| Process Registry | JSON file | No |
| Command Center | Real Supabase queries | No |
| Client Portal | Synthetic fallback | Labeled |
| Ray Review | JSON file | No |
| Hermes | Local classification | No |
| Alpha | Local scoring | No |
| Telegram | Bridge mock | Labeled |
| Stripe | Missing env | N/A |
| Research | Local files | No |
| Creative | Local files | No |
| Recovery | Script output | No |

---

## Telegram Commands

| Command | Status |
|---------|--------|
| `/status` | Works (mock bridge) |
| `/daily` | Works (mock bridge) |
| `/health` | Works (mock bridge) |
| `/review` | Works (mock bridge) |
| `/approve` | Works (mock bridge) |
| `/reject` | Works (mock bridge) |
| `/revise` | Works (mock bridge) |
| `/request` | Works (mock bridge) |
| `/hermes` | Works (mock bridge) |
| `/alpha` | Works (mock bridge) |
| `/run` | Works (mock bridge) |
| `/blocked` | Works (mock bridge) |

---

## Assessment

Command Center is active and honest. All sections show real status. No mock data presented as live. Empty states are clearly labeled.
