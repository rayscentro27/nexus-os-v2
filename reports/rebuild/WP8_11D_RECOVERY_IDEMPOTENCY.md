# WP8.11D Recovery and Idempotency

Media ingestion is keyed by asset/source/type/version and returns
`DUPLICATE_SUPPRESSED` on rerun. Object keys are deterministic, and source
masters remain intact when derivative generation or remote configuration is
unavailable. Review IDs are deterministic over asset, decision, feedback, and
reviewer; review and learning records are immutable.

Model routing records provider failure and returns an explicit blocked state;
it does not loop indefinitely. Missing objects return a failed `head` result
without deleting the source.

`CREATIVE_MEDIA_RECOVERY=PASS`
`CREATIVE_MEDIA_IDEMPOTENCY=PASS`
`CREATIVE_STORAGE_FAILURE_FALLBACK=PASS`
`SECONDARY_ROUTE_USED_OR_BOUNDED_BLOCK=PASS`
`LOCAL_STAGING_PRESERVED=PASS`
`REMOTE_SYNC_PENDING=PASS`

