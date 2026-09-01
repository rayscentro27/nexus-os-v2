# Broker Execution Journal

The runtime writes bounded JSONL execution records under `reports/runtime/oanda_practice_execution_journal.jsonl` and governed `trading_journal` records. Records include strategy/version, experiment, intent identity, instrument, direction, units, tier, broker order/fill/trade IDs, status, stops/targets, and timestamps; no bodies, tokens, or unnecessary account data are stored.
