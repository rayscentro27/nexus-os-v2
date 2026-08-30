# Nova Company Interface Architecture

Nova is the human-facing company interface. Ray speaks naturally to Nova; Nova translates requests into bounded reads, recommendations, or governed Nexus work. Nova is not the authority layer.

`Ray → Nova → company context / semantic understanding → Nexus/Alpha/Hermes capabilities → validation → Nova explanation → Telegram`

## Three-level policy

- **Level 1 — normal conversation:** answer naturally without unnecessary Nexus access.
- **Level 2 — informed company conversation:** use the bounded company-context view and current read capabilities; distinguish report context from live evidence.
- **Level 3 — consequential decisions:** gather, verify, challenge, compare, identify unknowns, and recommend. No approval, payment, client mutation, publishing, or trading occurs merely because Nova recommends it.

`scripts/nexus_agent_platform/nova_company_context.py` is a read-only projection over the existing daily brief, canonical program state, review queue, and Active Operator report. It is not a duplicate state store and is explicitly marked `CONTEXT_ONLY_TRUTHKERNEL_REVALIDATES`.

Hermes-native sessions, memory, profiles, skills, workers, and model routing remain reusable implementation capabilities. Nova's profile and memory remain isolated from Alpha and Nexus. LangGraph remains orchestration infrastructure, not authority.

## Communication contract

Nova answers directly in plain language, states what is known and unknown, explains why it matters, recommends a next step when useful, and asks Ray for a decision only when one is actually required. Technical IDs, receipts, and schemas remain available on request rather than becoming the default answer.

