-- Tighten client writes to approved, visible, same-tenant strategy and evidence records.
drop policy if exists credit_strategy_selections_client_insert on public.credit_strategy_client_selections;
create policy credit_strategy_selections_client_insert on public.credit_strategy_client_selections for insert to authenticated with check (
 actor='client'
 and exists(select 1 from public.tenant_memberships tm where tm.user_id=auth.uid() and tm.tenant_id=credit_strategy_client_selections.tenant_id and tm.client_id=credit_strategy_client_selections.client_id)
 and exists(select 1 from public.credit_strategy_versions v where v.strategy_id=credit_strategy_client_selections.strategy_id and v.version=credit_strategy_client_selections.strategy_version and v.approval_state='approved' and v.retired_at is null)
 and exists(select 1 from public.credit_strategy_matches m where m.id=credit_strategy_client_selections.match_id and m.tenant_id=credit_strategy_client_selections.tenant_id and m.client_id=credit_strategy_client_selections.client_id and m.report_id=credit_strategy_client_selections.report_id and m.strategy_id=credit_strategy_client_selections.strategy_id and m.strategy_version=credit_strategy_client_selections.strategy_version and m.client_visible)
);
drop policy if exists credit_strategy_history_client_insert on public.credit_strategy_selection_history;
create policy credit_strategy_history_client_insert on public.credit_strategy_selection_history for insert to authenticated with check (
 exists(select 1 from public.tenant_memberships tm where tm.user_id=auth.uid() and tm.tenant_id=credit_strategy_selection_history.tenant_id and tm.client_id=credit_strategy_selection_history.client_id)
 and exists(select 1 from public.credit_strategy_client_selections s where s.id=credit_strategy_selection_history.selection_id and s.tenant_id=credit_strategy_selection_history.tenant_id and s.client_id=credit_strategy_selection_history.client_id)
);
drop policy if exists credit_strategy_evidence_client_insert on public.credit_strategy_evidence_links;
create policy credit_strategy_evidence_client_insert on public.credit_strategy_evidence_links for insert to authenticated with check (
 exists(select 1 from public.tenant_memberships tm where tm.user_id=auth.uid() and tm.tenant_id=credit_strategy_evidence_links.tenant_id and tm.client_id=credit_strategy_evidence_links.client_id)
 and exists(select 1 from public.credit_strategy_client_selections s where s.id=credit_strategy_evidence_links.selection_id and s.tenant_id=credit_strategy_evidence_links.tenant_id and s.client_id=credit_strategy_evidence_links.client_id)
 and exists(select 1 from public.client_documents d where d.id=credit_strategy_evidence_links.document_id and d.tenant_id=credit_strategy_evidence_links.tenant_id and d.client_id=credit_strategy_evidence_links.client_id)
);
