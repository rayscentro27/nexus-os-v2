-- Nexus OS v2 — Client Document Upload Storage. ADDITIVE ONLY.
-- Creates a private storage bucket with RLS policies for client document uploads.

-- Create private bucket for client documents
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'client-documents',
  'client-documents',
  false,
  10485760, -- 10MB limit
  array['application/pdf', 'image/jpeg', 'image/png', 'image/heic', 'text/plain', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
)
on conflict (id) do nothing;

-- Policy: Authenticated users can upload to their own folder
create policy "client_documents_upload_own"
on storage.objects
for insert
to authenticated
with check (
  bucket_id = 'client-documents'
  and (storage.foldername(name))[1] = auth.uid()::text
);

-- Policy: Authenticated users can read their own files
create policy "client_documents_read_own"
on storage.objects
for select
to authenticated
using (
  bucket_id = 'client-documents'
  and (storage.foldername(name))[1] = auth.uid()::text
);

-- Policy: Admins can read all client files
create policy "client_documents_read_admin"
on storage.objects
for select
to authenticated
using (
  bucket_id = 'client-documents'
  and public.nexus_is_active_admin()
);

-- Policy: Admins can delete files (for review workflow)
create policy "client_documents_delete_admin"
on storage.objects
for delete
to authenticated
using (
  bucket_id = 'client-documents'
  and public.nexus_is_active_admin()
);
