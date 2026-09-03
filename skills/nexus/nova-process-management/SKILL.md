---
name: nexus-nova-process-management
version: 1.0.0
owner: nexus
status: ACTIVE_INTERNAL
---

# Purpose

Maintain continuity for multi-step executive requests across short Hermes turns.

# Procedure

1. Link the request to the existing Nexus objective when one exists.
2. Persist the parent question, current stage, result, next action, and review
   trigger in the bounded Nova process index.
3. Resume from the persisted stage after a worker/session boundary.
4. On failure, classify the method failure, preserve the parent process, and use
   an approved alternate path when available.
5. Escalate only the exact human-only or approval boundary.

# Boundary

This skill records process continuity; Nexus remains the durable objective and
work-order owner.
