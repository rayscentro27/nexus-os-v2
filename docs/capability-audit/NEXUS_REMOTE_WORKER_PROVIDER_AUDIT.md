# Nexus Remote Worker Provider Audit

## Provider categories

| Category | Best use | Strength | Limitation | Disposition |
|---|---|---|---|---|
| AWS/GCP/Azure CPU | durable services, private networking, queues, databases | broad primitives and enterprise controls | operational complexity and cost | WATCH / provider adapters |
| AWS Lambda / equivalent | short deterministic transforms and event jobs | pay-per-use; ARM option; no server management | duration/runtime limits, not browser/GPU | ADAPT |
| Coolify on a VPS | small persistent CPU workers and internal services | self-hosted, portable deployment convenience | operator owns server/update/HA | WATCH |
| RunPod | burst GPU jobs and inference | Pods, Serverless, Clusters; broad GPU inventory | availability, data/network and cost variability | PILOT later |
| Modal | containerized burst inference and jobs | developer-friendly serverless GPU/CPU model | provider coupling and usage billing | PILOT later |
| Vast.ai | low-cost burst GPU experiments | marketplace pricing | heterogeneous hosts and stronger trust/isolation burden | WATCH |
| Lambda Labs | predictable GPU instances | simpler dedicated GPU model | availability/region tradeoffs | WATCH |
| Paperspace/current equivalents | managed notebooks/GPU | accessible experimentation | product/platform coupling | WATCH |

Coolify explicitly describes itself as self-hosted PaaS that still requires the
customer's server; its current pricing separates a free self-hosted control
plane from a paid managed control plane. AWS Lambda bills requests and
GB-seconds, making it appropriate for short jobs rather than long browser or
GPU sessions. RunPod separates Pods, Serverless, and Clusters, supporting a
future provider adapter rather than a single hard-coded deployment path.

## Provider-portable contract

The worker router should select a provider using capability, sensitivity,
latency, cost ceiling, queue depth, tenant policy, region, and provider health.
The job envelope must be provider-neutral. Provider-specific IDs, logs, and
costs remain adapter metadata. Results are normalized before they enter Nexus.

## Security boundary

Workers get short-lived scoped credentials, signed job references, network
egress policy, resource/time limits, and no arbitrary Nexus shell. PII is
blocked by default from public or marketplace workers. A failed provider is a
degraded optional capability, not a core-runtime failure.

## Recommended sequence

1. Define the job/result/receipt contract with local fixture workers.
2. Pilot one CPU worker with public, non-sensitive document/crawl data.
3. Add a burst GPU adapter only for non-sensitive generated assets.
4. Add provider failover and cost accounting after measured utilization.
