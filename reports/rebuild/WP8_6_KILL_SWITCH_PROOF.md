# Practice Kill Switch

Kill-switch state is persisted at `data/runtime/oanda_practice_kill_switch.json`; RiskEngine checks it before every entry. Restart reads the same state, so an active switch cannot silently re-enable Practice entries. Existing-position handling is explicit and broker reconciliation remains required.
