-- Nexus OS v2 — Client Document Metadata Client Self-Insert RLS
-- Additive only. Allows authenticated clients to insert their own document metadata
-- rows through the standard anon client, without service role.

create policy "client_documents_client_insert_own"
  on public.client_documents
  for insert
  to authenticated
  with check (
    exists (
      select 1 from public.tenant_memberships tm
      where tm.user_id = auth.uid()
        and tm.role = 'client'
        and tm.tenant_id = client_documents.tenant_id
        and tm.client_id = client_documents.client_id
    )
    and client_documents.client_visible = true
    and client_documents.approval_required = true
    and client_documents.source = 'client_portal_upload'
  );
