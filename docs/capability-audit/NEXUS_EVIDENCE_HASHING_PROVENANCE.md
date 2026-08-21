# Evidence Hashing and Provenance

`source_hash` identifies acquired source bytes/content. `material_hash` identifies normalized meaningful evidence. Normalization uses stable line endings and removes volatile trailing whitespace; execution timestamps, receipt IDs, paths, and worker metrics are not part of material identity.

Every artifact records original reference, source type, display name or requested/final URL, content type, retrieval time, adapter/version, worker type, status, classification, and execution timestamps. Receipts reference the artifact and handoff and retain the hashes and duplicate result.

The pilot proves same content is duplicate/no-change equivalent, renamed same-content files are content duplicates, and meaningful fixture changes produce new material hashes.
