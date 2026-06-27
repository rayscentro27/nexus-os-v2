# Nexus Night Run + Monetization

Prepares Nexus OS v2 to run/test every safe internal process, improve Hermes plain-language
recommendations, research GoClear subscription pricing, and propose 4 revenue streams. Everything is
internal/dry-run/report-only — nothing publishes, sends, mails, charges, trades, spends, or contacts.

## Source of truth

- Pricing: `src/config/goclearSubscriptionTiers.ts`
- Online bank affiliates: `src/config/onlineBusinessBankAffiliates.ts`
- Revenue streams: `src/config/nexusRevenueStreams.ts`
- Workflow monetization: `src/lib/clientWorkflowMonetization.ts`
- Hermes plain language: `src/lib/hermesPlainLanguage.ts`
- Scripts: `scripts/night_run/*` (shared `night_run_model.py` + generators)
- Command Center: `NightRunMonetizationCard` in `MissionControl.tsx`

## Run the night run

```
python3 scripts/night_run/generate_night_run_readiness.py --dry-run --json
```

This runs all 28 safe dry-run scripts (automation, ai_access, client_vault, client_workflow, and the
night-run/monetization reports) and aggregates: what ran, what failed, what's blocked, what needs
approval, and what should happen next. JSON → `reports/runtime/`, Markdown → `reports/manual_publish/`.

## Revenue streams (proposed only)

1. **Readiness review** — $97 credit + business funding readiness review at signup.
2. **Monthly subscription** — tiers: Credit Action Plan (~$49) → Credit + Business Setup (~$97, core)
   → Funding Readiness (~$197) → Post-Funding Growth (~$149).
3. **Affiliate + partner engine** — per-task partner + DIY/free option with disclosure.
4. **Funding commission pipeline** — funding-ready clients, Ray-approved path, commission tracked
   (never auto-applied).

## Safety

Pricing/bank figures are internal market-research estimates to validate, not live offers. No client
is charged. SmartCredit: no password storage/scraping/auto-login. DocuPost: shell only, no sending.
Client Vault: not_connected_by_design. Level 3 high-risk actions remain blocked. Client-facing
recommendations remain approval-gated. Hermes uses sanitized signals only.

CRM evaluation (Twenty/Relaticle/Atomic/Open Mercato/NextCRM/crm-logic) remains deferred — see
[NEXUS_FUTURE_CRM_EVALUATION_POLICY.md](NEXUS_FUTURE_CRM_EVALUATION_POLICY.md).
