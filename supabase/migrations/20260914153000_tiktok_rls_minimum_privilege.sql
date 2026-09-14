-- Harden an already-created TikTok persistence schema without exposing token
-- ciphertext to authenticated client sessions.
drop policy if exists "tiktok connections owner read" on public.nexus_tiktok_connections;
create policy "tiktok connections owner read" on public.nexus_tiktok_connections
  for select to authenticated
  using (user_id = auth.uid() and exists (
    select 1 from public.tenant_memberships tm
    where tm.user_id = auth.uid()
      and tm.tenant_id = nexus_tiktok_connections.tenant_id
  ));

revoke all on public.nexus_tiktok_connections from anon, authenticated;
grant select (id, user_id, tenant_id, open_id, access_token_expires_at,
  refresh_token_expires_at, scopes, status, created_at, updated_at, revoked_at)
  on public.nexus_tiktok_connections to authenticated;

drop policy if exists "tiktok receipts owner read" on public.nexus_tiktok_post_receipts;
create policy "tiktok receipts owner read" on public.nexus_tiktok_post_receipts
  for select to authenticated
  using (user_id = auth.uid() and exists (
    select 1 from public.tenant_memberships tm
    where tm.user_id = auth.uid()
      and tm.tenant_id = nexus_tiktok_post_receipts.tenant_id
  ));

revoke all on public.nexus_tiktok_post_receipts from anon, authenticated;
grant select on public.nexus_tiktok_post_receipts to authenticated;
