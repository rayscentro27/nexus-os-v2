#!/usr/bin/env python3
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[2]; migration=(root/'supabase/migrations/20260714120000_funding_readiness_system_reviews.sql').read_text(); worker=(root/'scripts/credit/parse_uploaded_credit_report.py').read_text()
terms=['credit_report_system_reviews','funding_impact_items','utilization_actions','specialist_exceptions','client_visible','enable row level security','nexus_is_active_admin','System review created','verified_reviews']
for term in terms: print(('PASS' if term in migration+worker else 'FAIL')+': '+term)
sys.exit(0 if all(t in migration+worker for t in terms) and 'disable row level security' not in migration.lower() else 1)
