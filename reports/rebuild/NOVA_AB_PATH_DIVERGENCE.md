# Nova A/B Path Divergence

Campaign: `HG-WP6.5-NOVA-CONVERSATIONAL-CORE-VS-OUTER-LAYERS-AUDIT-20260830-01`

## Shared path

Both prompt classes enter the same authorized Telegram worker and Nova graph.
The decisive difference is semantic capability classification after utility
handling and before context/model synthesis.

## Path A: conversational

Examples: “What do you think about Tesla?” and “Do you know any affiliate
programs?”

`_capability_gate` records no forced capability, `_build_context` remains
lightweight unless company terms are present, and the model receives the
question plus bounded session history. The model can answer from general
knowledge and conversational context.

## Path B: current/research

Examples: “Look into Tesla’s current strategy” and “Find a low-cost affiliate
opportunity.”

`classify_company_question` marks research/analytical intent and
`classify_question_domains` marks public research. `_capability_gate` selects
`public_web_search` before synthesis. The adapter loads the existing Hermes web
search provider chain. The latest durable search receipts show that chain
ended with provider `none` and `all_providers_failed`; the resulting tool
failure becomes the dominant answer limitation.

## Comparison matrix

| Field | A | B |
|---|---|---|
| Model receives full user wording | yes | yes, with forced capability result |
| Model chooses tools | no tool needed | no; deterministic gate chooses first tool |
| Source forced before model | no | public web search |
| Tool failure can dominate answer | no | yes |
| Nexus required by intent | no | no, but adapter is Nexus-owned |
| Truth validation | post-response/general | post-response plus capability result |
| Correct architecture | preserve | replace pre-model shell with model-led planning over allowlist |

## Important limit

The receipts prove provider-chain failure, not the precise network or
credential sub-cause. A future implementation campaign should add non-secret
provider diagnostics and an authorized fallback attempt, then perform fresh
real Telegram A/B testing.
