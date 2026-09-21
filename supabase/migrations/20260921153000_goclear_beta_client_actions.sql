-- Client-safe action RPCs for the closure path. They keep writes narrow and
-- tenant-scoped while preserving the existing client_tasks work semantics.
begin;

drop policy if exists goclear_upload_receipts_own_insert on public.goclear_upload_receipts;
create policy goclear_upload_receipts_own_insert on public.goclear_upload_receipts for insert to authenticated with check (exists (select 1 from public.tenant_memberships tm where tm.client_id = goclear_upload_receipts.client_id and tm.tenant_id = goclear_upload_receipts.tenant_id and tm.user_id = auth.uid() and tm.role = 'client'));

drop policy if exists goclear_clyde_receipts_own_insert on public.goclear_clyde_receipts;
create policy goclear_clyde_receipts_own_insert on public.goclear_clyde_receipts for insert to authenticated with check (exists (select 1 from public.tenant_memberships tm where tm.client_id = goclear_clyde_receipts.client_id and tm.user_id = auth.uid() and tm.role = 'client'));

drop policy if exists goclear_client_reports_own_insert on public.goclear_client_reports;
create policy goclear_client_reports_own_insert on public.goclear_client_reports for insert to authenticated with check (exists (select 1 from public.tenant_memberships tm where tm.client_id = goclear_client_reports.client_id and tm.tenant_id = goclear_client_reports.tenant_id and tm.user_id = auth.uid() and tm.role = 'client'));

create or replace function public.goclear_create_review_request(
  p_tenant_id text,
  p_client_id text,
  p_title text default 'GoClear readiness review requested',
  p_notes text default null,
  p_readiness_snapshot jsonb default '{}'::jsonb
) returns public.client_tasks
language plpgsql security definer set search_path = public
as $$
declare result_row public.client_tasks;
begin
  if not exists (select 1 from public.tenant_memberships tm where tm.tenant_id=p_tenant_id and tm.client_id=p_client_id and tm.user_id=auth.uid() and tm.role='client') then
    raise exception 'client_context_required';
  end if;
  insert into public.client_tasks(id, tenant_id, client_id, title, summary, category, status, priority, client_visible, approval_required, source, payload)
  values (gen_random_uuid()::text, p_tenant_id, p_client_id, left(coalesce(p_title,'GoClear readiness review requested'),200), left(coalesce(p_notes,''),4000), 'review_request', 'pending_admin_review', 'high', true, true, 'goclear_friends_beta', jsonb_build_object('readiness_snapshot',p_readiness_snapshot,'notes',p_notes,'requested_by',auth.uid(),'department_owner','credit_funding','customer_response_required',true))
  returning * into result_row;
  return result_row;
end;
$$;
revoke all on function public.goclear_create_review_request(text,text,text,text,jsonb) from public;
grant execute on function public.goclear_create_review_request(text,text,text,text,jsonb) to authenticated;

commit;
