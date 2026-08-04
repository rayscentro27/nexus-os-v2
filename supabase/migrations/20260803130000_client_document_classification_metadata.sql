-- Add post-upload document classification metadata.
-- Additive only: preserves existing document rows and upload storage policies.

alter table public.client_documents
  add column if not exists classification_status text,
  add column if not exists classification_confidence numeric,
  add column if not exists classification_basis jsonb not null default '{}'::jsonb,
  add column if not exists classified_category text,
  add column if not exists review_state text;

create index if not exists client_documents_classification_status_idx
  on public.client_documents(tenant_id, client_id, classification_status, updated_at desc);
