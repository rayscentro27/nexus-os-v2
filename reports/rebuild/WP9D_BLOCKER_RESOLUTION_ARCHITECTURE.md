# WP9D blocker resolution architecture

`scripts/nexus_agent_platform/wp9d_capabilities.py` introduces a canonical,
appendable blocker state with typed causes, bounded recovery attempts,
verification evidence, human checkpoints, and durable resume state. A blocker
is no longer represented only as a report line. Recovery is explicit:
DETECT → DIAGNOSE → bounded attempt → VERIFY → RESOLVED or human checkpoint.

The state file is atomically replaced to prevent readers observing partial or
concatenated JSON. No scheduler or certification file is used by this layer.
