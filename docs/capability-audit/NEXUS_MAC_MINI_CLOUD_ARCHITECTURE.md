# Nexus Mac Mini / Cloud Architecture

## Recommendation

The Mac Mini should become the **founder/private control plane plus a small
isolated worker**, not the entire future Nexus platform and not a permanent
GPU farm.

```text
NEXUS CORE / MAC MINI CONTROL PLANE
        │ governed job
        ▼
   WORKER ROUTER
   ├── Mac Mini isolated CPU/private worker
   ├── remote CPU worker
   ├── remote GPU worker
   └── managed capability API
        │ normalized result
        ▼
 receipt → Mission Control → Ray review where required
```

## Mac Mini role

**Excellent:** Hermes, approvals, work orders, Mission Control, private state,
small deterministic transforms, MarkItDown, cached retrieval, whisper.cpp for
private short audio, development, and local adapters.

**Possible but isolated:** small browser jobs, small embeddings, light research
batching, and paper-only trading analytics.

**Poor:** persistent GPU image/video/avatar generation, large model serving,
high-concurrency browser fleets, 10–100 tenant workloads, and any service that
could starve certified launchd jobs.

## Scale transitions

- **GoClear today:** Mac Mini control plane plus local/private workers is viable.
- **10 businesses:** add a remote CPU worker plane, tenant-aware queues,
  externalized object storage, per-tenant quotas, and fleet observability.
- **100 businesses:** control plane becomes a multi-tenant service; Mac Mini is
  an optional founder node/private edge worker. GPU becomes an on-demand pool.

## Privacy placement

Credit reports, client documents, credentials, and sensitive financial records
remain local-required until encryption, tenant isolation, deletion, and audit
contracts are proven. Public research, anonymized text, and approved creative
assets may use cloud workers. No worker receives broad Supabase or filesystem
access.

## Commercial architecture consequence

Business configuration belongs in Nexus Core. Workers receive a scoped business
and capability context; they do not own business policy. This preserves one
platform while allowing different businesses to select different adapters,
brands, offers, workflows, and integrations.
