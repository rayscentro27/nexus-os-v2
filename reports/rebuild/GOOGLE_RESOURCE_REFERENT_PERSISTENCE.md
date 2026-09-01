# Google resource referent persistence

Referent state is persisted in the existing per-session shadow sidecar. A
bounded `resource_referent_links` map retains the latest object-bearing result
set independently of the rolling `resource_results` index. Stored fields are
IDs, positions/order, bounded labels/subject/title/snippet metadata, source
turn, request ID, fingerprint, creation time, and currentness. Full email
bodies are not persisted for referents.

Writes now use a temporary file, flush/fsync, and atomic replace. This prevents
the next Telegram worker from reading a truncated JSON sidecar.
