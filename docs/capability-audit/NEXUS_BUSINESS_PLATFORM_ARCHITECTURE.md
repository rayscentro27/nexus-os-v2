# Nexus Business Platform Architecture

## Target model

```text
Nexus Core
  → Business Configuration Layer
    → GoClear Business #1
    → Business #2
    → reusable business templates
  → commercial Nexus platform
```

## Core reusable components

Continuous Loop, Active Operator, Recovery Check, Hermes, Mission Control,
governance, approvals, work orders, receipts, health/freshness semantics,
research intake, memory interfaces, model routing, worker adapters, secrets
boundaries, tenant policy, and reporting are Nexus Core candidates.

## Business configuration

The configuration layer must declare business identity, brand, products,
services, offers, workflows, departments, knowledge sources, policies,
approval limits, integrations, revenue models, channels, client journeys,
operator personality, voice/avatar preferences, reporting, and role
definitions. Configuration must be data and policy, not a fork of Nexus Core.

## Separate from core

GoClear offers, credit/funding workflows, client-specific fields, local service
journeys, brand assets, partner catalogs, and business-specific legal/approval
rules belong in a tenant/business package. They must not be hard-coded into
autonomy, health, or worker authority.

## Readiness

**PARTIAL — not ready for template abstraction yet.** The control plane is
strong and GoClear is a valid proving ground. A second-business pilot needs:

1. versioned business configuration schema;
2. tenant-scoped state and receipts;
3. per-tenant secret and worker quotas;
4. capability enablement matrix;
5. data-class and retention policy;
6. migration/rollback support;
7. cross-business Mission Control without data leakage;
8. cost and usage attribution.

## Commercial path

Potential products include Nexus OS subscriptions, setup/templates, managed AI
operations, research/intelligence, creative/marketing services, voice/avatar
upgrades, and custom integrations. No external project should become a hidden
dependency that forces every tenant onto one vendor or one execution model.
