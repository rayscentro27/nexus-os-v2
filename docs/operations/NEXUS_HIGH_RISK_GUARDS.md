# Nexus High-Risk Guards

Level 3 (blocked / high-risk) actions default to **blocked**. A guard may only be lifted by a
separate design doc, explicit Ray approval, proof plan, rollback plan, hard guard tests, and a
safety contract.

- **Registry:** `src/config/nexusHighRiskGuards.ts` (Python mirror: `scripts/automation/automation_model.py`).
- **Verifier:** `scripts/automation/verify_high_risk_guards.py`.
- **Reports:** `reports/runtime/high_risk_guards_latest.json`, `reports/manual_publish/high_risk_guards_latest.md`.

## Blocked actions

`live_trade`, `broker_order`, `funded_account_execution`, `auto_executor_exposure`,
`payment_charge`, `payment_refund`, `ad_spend_activation`, `production_deploy`, `rls_weaken`,
`destructive_db_write`, `secret_print`, `env_commit`, `broad_scrape`, `youtube_media_download`,
`external_ai_sensitive_data`, `bulk_send`, `spam_automation`, `client_data_exposure`,
`tenant_isolation_bypass`.

## Verify (dry-run)

```
python3 scripts/automation/verify_high_risk_guards.py --dry-run --json
```

The verifier confirms each action classifies as `blocked_high_risk`, that a guard exists, proof of
the blocked default, files checked where feasible, and the next recommended hardening. It fails if
any high-risk action is not blocked.
