# Nova Live Capability Execution

Campaign: HG-WP6.5-NOVA-LIVE-CAPABILITY-EXECUTION-WEB-ALPHA-AND-FALLBACK-COMPLETION-20260830-01

The existing five-node graph was preserved. Before this repair, the broker
only described resources and `_generate_response` called the model once; no
model-selected capability request could execute. The repair adds an optional,
bounded request envelope within `generate_response`, validates it through the
broker, invokes the shared adapter, and calls Nova once more with the result.

Development proof: `public_web_search` returned six real Bing HTML results for
`Tesla strategy 2026` after SearXNG refused the connection and Brave returned
HTTP 402. `public_web_retrieval` read Microsoft’s public site (HTTP 200,
bounded content). Alpha’s bounded onboarding request executed through the same
search path, produced a research pack/report/receipt, and returned the pack to
the caller. These are development proofs, not Telegram E2E certification.

The Alpha request is explicitly read-only research. No payment, publishing,
client mutation, or Nexus direct execution was enabled.
