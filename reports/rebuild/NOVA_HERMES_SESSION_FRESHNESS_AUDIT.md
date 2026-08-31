# Hermes Shadow Session Freshness Audit

## Repair

Each shadow turn now receives a unique `turn_id`. The shadow keeps a small
session sidecar containing only non-sensitive correlation metadata: latest turn,
prompt preview, tools used, and linked Alpha request/result identifiers. Tool
results also remain in Hermes's same session conversation for native
continuation.

The prompt contract explicitly requires current conversational referents and
linked request/result IDs to outrank unrelated historical artifacts.

## Results

In a sequential session, Nexus read → Alpha challenge → Research follow-up,
Hermes returned the fresh Alpha result and its six-source research receipt on
the challenge turn. The follow-up still queried Nexus repeatedly instead of
cleanly selecting the stored Alpha artifact, so continuity is improved but not
fully proven.

```text
FRESH_RESULT_PRECEDENCE=YES for linked Alpha result
STALE_RESULT_MAY_BE_CONTEXT=YES
STALE_RESULT_MAY_IMPERSONATE_CURRENT=NO by correlation contract
SESSION_REFERENT_CONTINUITY=PARTIAL
```

No historical session or live Nova memory was migrated or deleted.

