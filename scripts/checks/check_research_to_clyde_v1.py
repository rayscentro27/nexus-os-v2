#!/usr/bin/env python3
from pathlib import Path
R=Path(__file__).resolve().parents[2]
m=(R/'supabase/migrations/20260715150000_research_to_clyde_v1.sql').read_text()+(R/'supabase/migrations/20260715151000_research_to_clyde_rls_hardening.sql').read_text()
engine=(R/'src/lib/researchToClydeEngine.ts').read_text();ui=(R/'src/pages/client/WorldClassClientPortal.jsx').read_text();admin=(R/'src/components/CreditSpecialistWorkbench.jsx').read_text();worker=(R/'scripts/credit/parse_uploaded_credit_report.py').read_text();alpha=(R/'netlify/functions/alpha-url-review.mjs').read_text()
for table in ('credit_strategy_versions','credit_strategy_matches','credit_strategy_client_selections','credit_strategy_selection_history','credit_strategy_evidence_links','credit_strategy_drafts','credit_strategy_exceptions','research_strategy_audit_events'):
 assert f'create table if not exists public.{table}' in m and f'alter table public.{table} enable row level security' in m
for phrase in ('approval_state=\'approved\'','retired_at is null','tenant_memberships','client_documents d','nexus_is_active_admin') : assert phrase in m
assert 'match_credit_strategies(comparison, approved_versions)' in worker and 'credit_strategy_matches' in worker
assert all(x in engine for x in ('classifyResearchClaim','rankApprovedStrategies','buildStructuredClydeGuidance','validateStrategyDraft','generateSafeStrategyDraft','evaluateResearchToClydeException'))
assert all(x in ui for x in ('Nexus detected:','Question only you can answer:','Upload evidence securely','Save and return later'))
assert all(x in admin for x in ('Research Sources','Claims','Versioned Strategies','Genuine Exceptions','governStrategy'))
assert all(x in alpha for x in ('validateAlphaReviewUrl','credentials_not_allowed','host_not_allowed','protocol_not_allowed'))
assert 'SUPABASE_SERVICE_ROLE_KEY' not in ''.join((R/p).read_text() for p in ['src/lib/researchToClydeEngine.ts','src/pages/client/WorldClassClientPortal.jsx','src/components/CreditSpecialistWorkbench.jsx'])
assert 'docupost' not in engine.lower() and 'mailCreated:false' in engine
print('PASS: governed research-to-Clyde v1, RLS boundaries, approved-only matching, safe drafts, evidence, UI, Alpha boundary, and no mail')
