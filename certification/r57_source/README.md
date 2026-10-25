# R57 governor ordering certification inputs

R57 composes the byte-verified R56 deployable release (artifact SHA pinned in
`contract.json`) and adds exactly one additive Supabase migration. The migration
is based on the immediately preceding applied R56-era RPC definition; its
certification test checks the SQL transformation so request, response-byte,
cost, policy, and idempotency behavior cannot drift as part of this fix.

The isolated GitHub PostgreSQL service installs a minimal table contract, applies
the migration, and exercises empty, valid, expired, mixed, idempotent, repeat
reconciliation, and concurrent reservation scenarios. It does not connect to or
mutate production Supabase.

The terminal job records in the incident showed that reservations can remain
ACTIVE until TTL cleanup after cancellation. R57 does not add terminal-job
lookups to the governor RPC: the diagnosed canary failure was that expired rows
were counted before expiry cleanup. The function now reconciles expiry first;
terminal reservation lifecycle cleanup remains an independent follow-up.
