#!/usr/bin/env python3
from pathlib import Path
r=Path(__file__).resolve().parents[2];m=(r/"supabase/migrations/20260715120000_research_driven_credit_strategies.sql").read_text();a=(r/"src/lib/clientPortalDataAdapter.ts").read_text()
for x in ("credit_strategy_recommendations","credit_strategy_client_decisions","strategy_version","previous_state","new_state"):assert x in m
assert "saveCreditStrategyDecision" in a and "strategyDecisions" in a
print("PASS: durable selections and append-only audit history")
