# Duplicate Order Protection

Signal IDs are persisted and rejected on repeat. Order intents use deterministic identity and the journal is checked before submission. Broker state is reconciled at startup and before entries. This prevents duplicate execution across scheduler overlap/restart for known identities; an ambiguous lost-response branch remains a future injected integration test.
