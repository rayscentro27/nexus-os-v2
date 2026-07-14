#!/usr/bin/env python3
from pathlib import Path
r=Path(__file__).resolve().parents[2];c=(r/"src/lib/creditStrategyCatalog.ts").read_text();m=(r/"supabase/migrations/20260715120000_research_driven_credit_strategies.sql").read_text()
assert c.count("s('")>=25 and "approved_for_tool_use" in c and "approved_for_education" in c
assert "credit_strategy_sources" in m and "credit_strategy_claims" in m and "credit_strategy_definitions" in m
assert "discovered','under_review','conditionally_approved','approved_for_education','approved_for_tool_use','rejected','retired" in m
print("PASS: controlled reusable strategy research library")
