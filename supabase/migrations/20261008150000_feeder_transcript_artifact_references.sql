-- Keep large public-source transcript bodies in the local Nexus artifact store.
-- Existing transcript_or_extract values are deliberately preserved for legacy
-- analysis fallback; this migration performs no destructive data movement.
alter table public.nexus_feeder_sources
  add column if not exists transcript_storage_class text,
  add column if not exists transcript_ref text,
  add column if not exists transcript_sha256 text,
  add column if not exists transcript_char_count bigint,
  add column if not exists transcript_byte_count bigint,
  add column if not exists transcript_summary text,
  add column if not exists transcript_available boolean;

comment on column public.nexus_feeder_sources.transcript_ref is
  'Nexus-local artifact reference; never a transcript body or credential.';
comment on column public.nexus_feeder_sources.transcript_or_extract is
  'Legacy source text retained for compatibility. New YouTube intake stores bodies locally.';
