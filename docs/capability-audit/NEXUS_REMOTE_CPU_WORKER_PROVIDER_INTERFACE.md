# Provider Interface

`RemoteWorkerProvider` separates Nexus job semantics from transport/provider details. Its methods are `submit(job)`, `get_status(job_id)`, `cancel(job_id)`, and `health()`.

The repository includes an in-process contract provider for tests and an HTTP provider adapter. Provider-specific fields remain in the adapter/result metadata; the canonical request is `nexus.remote-job.v1` and result is `nexus.remote-result.v1`.

A future OCI, AWS, GCP, Modal, or self-hosted container adapter must implement this interface without changing evidence hashes, provenance, tenant semantics, receipt correlation, or Nexus authority.
