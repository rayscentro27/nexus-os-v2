# WP8.14 Resource Ledger

The ledger records provider, resource type, department, work order/initiative references, starting/consumed/remaining balance, unit, cash cost, estimated replacement cost, scarcity, measurement source, confidence, and timestamps. Cost receipts are idempotent by `receipt_id`; revenue receipts are idempotent by the same contract.

Current bounded inventory recorded from existing Nexus evidence: Creative's WP8.11E Hermes route has four recorded invocations at $0 actual cash cost; available quota/credit is `UNKNOWN`. A governed WP8.13 API probe is recorded at $0 actual. Oracle, Supabase, Netlify, GPU, email, and research-provider billing balances are not fabricated when no current bill/quota receipt is available.
