# Hermes Route Regression Audit

Generated: 2026-07-01 20:18 America/Phoenix
Baseline: `ec73bf5654d8748616966354e604f3ae3a3760ca`

The seven-message transcript contains two mechanism regressions:

1. **Approvals inventory fell to fallback.** The domain classifier recognized `approval` and `approve`, but not plural `approvals`; there was no protected live-record intent precheck before advisor routes.
2. **Selection implementation did not create advisory continuity.** Number 3 resolved correctly, but `memory_followup/selection_implementation` was omitted from advisory-producing routes. The follow-up marker family also omitted “do you think it will work.”

Trading, trace/Supabase capability, business-opportunity retrieval, and numbered selection routes behaved as expected. The patch target is therefore the priority precheck and advisory write/eligibility path, not a router rebuild.
