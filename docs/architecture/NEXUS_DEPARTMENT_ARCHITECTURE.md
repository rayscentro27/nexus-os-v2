# Nexus Department Architecture

WP5 formalizes departments as responsibility boundaries, not AI personas.
`data/runtime/nexus_department_registry.json` is the canonical map from a
department to its bounded workers, skills, loops, capabilities, execution
targets, model policies, data classes, and review policy.

The resolution path is deterministic after intent interpretation:

`Telegram identity → intent → department → certified loop → skill → worker → capability → execution target → executor → validation → TruthKernel receipt`.

TruthKernel and Nexus remain authoritative. Hermes may interpret or review;
it cannot approve gates, create authority, or replace verified operational
state. Active Operator remains paused.
