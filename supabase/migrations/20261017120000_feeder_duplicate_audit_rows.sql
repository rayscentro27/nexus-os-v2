-- Keep duplicate detections as auditable BLOCKED source rows; application-level
-- idempotency and the detection worker prevent processing them twice.
drop index if exists public.nexus_feeder_source_url_uq;
drop index if exists public.nexus_feeder_content_hash_uq;
