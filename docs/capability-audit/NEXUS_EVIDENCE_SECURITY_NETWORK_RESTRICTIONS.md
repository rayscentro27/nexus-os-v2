# Evidence Ingestion Security Boundaries

Local ingestion is allowlist-based and fail-closed. Environment files, runtime configuration, credential/secret directories, symlinks, non-regular files, unsupported files, and oversized sources are rejected.

Web ingestion is public-only. It does not receive credentials or cookies and cannot submit forms or perform external mutations. DNS-resolved addresses and redirect destinations are checked against private, loopback, link-local, reserved, multicast, unspecified, localhost, and cloud metadata destinations. A blocked source is recorded rather than bypassed.

The adapters have no arbitrary shell interface, no financial authority, no external messaging authority, no approval mutation, and no access to certified scheduler processes. Sensitive classification is recorded; this pilot used only public/synthetic evidence.
