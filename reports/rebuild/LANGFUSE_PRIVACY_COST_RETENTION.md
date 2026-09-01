# Langfuse privacy, cost, and retention

Tracing uses the existing redaction adapter: identifiers are hashed, secrets,
tokens, credentials, email, phone, SSN, and sensitive document fields are
redacted. Text is bounded. Local runtime traces are ignored by Git.

Recommended retention: normal success 7–14 days; failures and unsupported
claims 30 days; high-cost traces 30 days; debug traces 72 hours; sensitive
traces metadata-only and 24 hours. Do not enable unlimited retention.
