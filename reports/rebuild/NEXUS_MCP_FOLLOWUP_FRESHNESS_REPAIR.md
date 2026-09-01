# Nexus MCP follow-up freshness repair

Root cause: native turns did not receive a generic volatile-resource contract
unless an explicit resource obligation had already been inferred. Consequently
Hermes could treat a prior Nexus answer as sufficient for a later current-state
question. The repair adds one generic freshness statement to the profile-local
runtime context and strengthens the MCP tool descriptions. No reviews-specific
route or classifier was added.

Required live two-turn Hermes proof remains pending because the local Hermes
provider environment failed before model execution (`openai` import/runtime
environment inconsistency). No readiness claim is made from static tests.
