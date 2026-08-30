# Nova Public Search to Nexus Misroute Trace

## Observed message

“Search the internet for current credit repair affiliate programs” was answered with a statement about failure to retrieve current Nexus state.

## Current source-level trace

The current five-layer graph builds an information plan for this request with:

- domain: `PUBLIC_BUSINESS_RESEARCH`
- information needed: `GENERAL_REASONING`, `PUBLIC_WEB_SEARCH`, `PUBLIC_WEB_RETRIEVAL`
- pre-route: `model_first`
- broker mode: descriptive-only

The current pre-model boundary therefore does not force a Nexus-state lookup for this request in the inspected source path. The explicit operational-control branch is separate and applies only when an operational control object is resolved.

## What is proven and what is not

| Item | Result |
|---|---|
| Public-search semantic plan exists | YES, source-level/runtime state build |
| Nexus was selected by current deterministic pre-router | NOT PROVEN |
| `get_live_capability_status` ran in Telegram | NOT PROVEN |
| Web provider was selected in Telegram | NOT PROVEN |
| A capability envelope was dispatched in Telegram | NOT PROVEN |
| Raw provider error was recorded | NO; receipts lack provider metadata |
| Stale conversation contained negative external-access beliefs | YES |

## Forensic conclusion

The response cannot honestly be attributed to a current deterministic Nexus-first branch from the available evidence. The strongest evidence-backed explanation is that the ephemeral Telegram worker fed stale refusal turns to the model and/or fell through a path whose capability invocation was not instrumented. The absence of capability telemetry prevents distinguishing stale-model reproduction from a hidden runtime fallback in the historical cycle.

## Required follow-up (not performed)

The remediation campaign should add correlation-safe, secret-free fields for graph entrypoint, prompt/profile version, capability request, dispatcher result, provider, and model continuation. Then run the same prompt in a fresh session after a controlled worker reload. Only that test can prove whether the current source-level `model_first` plan reaches web search rather than a legacy fallback.
