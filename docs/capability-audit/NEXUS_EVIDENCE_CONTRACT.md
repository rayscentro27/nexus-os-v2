# Nexus Evidence Contract

The canonical schema identifier is `nexus.evidence.v1` with deterministic normalization `nexus.evidence.normalization.v1`.

Artifacts contain source identity and provenance, source and material SHA-256 hashes, adapter/version, normalized content, safety classification, execution timing, tenant context, and bounded status. Receipts contain references and hashes rather than duplicating large content. The intake handoff is append-only JSONL at the capability runtime boundary and is consumed by existing Nexus intake/research paths.

The transport-neutral request envelope contains `job_id`, `capability`, `adapter`, `source`, policy, limits, tenant context, and `requested_at`. A future remote worker can return the same artifact/result semantics without changing Nexus authority.

Statuses include `SUCCESS`, `DUPLICATE`, `NO_CHANGE`, `UNSUPPORTED_FORMAT`, `INVALID_PATH`, `BLOCKED_PATH`, `PRIVATE_NETWORK_BLOCKED`, `REDIRECT_BLOCKED`, `TIMEOUT`, `CONTENT_EMPTY`, `DEPENDENCY_UNAVAILABLE`, and bounded source/conversion errors.
