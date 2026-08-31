# Hermes Reasoning Feature Audit

## Reasoning effort

The installed source supports model-family/provider-specific reasoning fields in
some adapters, but no single generic `reasoning_effort` setting was proven as a
stable Hermes 0.20.6 contract for every provider and model. Therefore:

```text
HERMES_REASONING_EFFORT=NOT_PROVEN_AS_GENERIC_RUNTIME_FEATURE
```

Nova should not gain a new custom “reasoning layer” merely to emulate this.
If a later pilot uses a model/provider that supports effort tiers, it should be
an adapter-level option:

- simple conversation: normal/low provider-supported effort
- business recommendation: stronger effort where supported
- consequential economics: stronger model or explicit approved review

The model and evidence loop, not a deterministic question router, should choose
the level. Cost must be checked before invocation.

## Multi-model / MoA

The installed repository contains delegation/toolset references involving MoA,
but the audit did not prove a native primary-agent ensemble configuration with a
defined aggregator, reference models, or cost policy. Status:

```text
HERMES_MOA=NOT_PROVEN_FOR_NOVA
```

It may be evaluated later for high-value opportunity ranking or contradictory
evidence, but must remain optional and must not be mandatory for ordinary Nova
answers.

## Grounding and truth

Hermes has web extraction, browser, tool-result, and session infrastructure. The
audit found no Hermes-native equivalent to Nexus TruthKernel's governed source,
freshness, certification, receipt, and contradiction contract. Hermes can carry
evidence; Nexus must continue to validate Nexus-controlled facts and governed
actions.

## Native reasoning fit

Hermes's native loop improves execution mechanics, not Nova's business judgment
by itself. Nova's SOUL, business context, and recommendation behavior must stay
explicit. The safe target is: native tool continuation behind the same Nova
identity, with Nexus-specific policy wrapped at the capability boundary.

