# Nova Live Prompt Assembly Audit

Controlled source-level context assemblies were built for four sanitized questions with empty chat memory. The active system prompt was identical across all four cases:

- active SOUL hash: `f68d256eee70b2f2`
- system length: 1,637 characters
- profile: embedded `SOUL`, agent `hermes_nova`
- model: `openai/gpt-4o-mini`

## Normalized prompt inputs

### General

`What is an affiliate program?`

`question_type=GENERAL_CONVERSATION`, `pre_route=model_first`, no company context. The user message included an information plan, the full descriptive resource catalog, reasoning abilities, and capability protocol because the current builder constructs a plan for this turn. No capability result was injected.

### Recommendation

`Find three affiliate programs for GoClear and recommend the best one.`

`question_type=ADVISORY`, `pre_route=model_first`, company context injected. The model received the plan, catalog, reasoning abilities, capability protocol, bounded company context, and no verified capability result.

### Current public information

`What is Tesla doing right now?`

`question_type=GENERAL_CONVERSATION`, `pre_route=model_first`, no company context. The plan identified `PUBLIC_COMPANY_RESEARCH` and requested general reasoning, public search, and public retrieval. No web evidence was injected before generation.

### Nexus

`Check Nexus and tell me what capability could make money.`

`question_type=GENERAL_CONVERSATION`, `pre_route=model_first`, company context injected. The plan identified Nexus operations and public business research; the catalog included Nexus, web, Alpha, company data, and action descriptors. No Nexus result was injected before generation.

The model request protocol accepts `PUBLIC_WEB_SEARCH`, `PUBLIC_WEB_RETRIEVAL`, `ALPHA_RESEARCH`, `CAPABILITY_STATUS`, `NEXUS_READ`, and `NEXUS_CAPABILITY_MAP`. Resource catalog data is descriptive; it does not itself prove execution.
