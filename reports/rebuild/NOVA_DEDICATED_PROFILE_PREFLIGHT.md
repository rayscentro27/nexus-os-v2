# Dedicated profile preflight

Native sequence: 10/10 turns responded, zero tools, zero report headings, and
no evidence-validator suppression. Greetings, disagreement, topic closure,
general knowledge, and business reasoning all used the native Hermes path.

Resource regression: Tesla 4 calls (2 search, 2 retrieval), Nexus 2 reads,
Alpha 1 call; all produced responses.

Action separation remains governed: discussion does not authorize a mutation.
Focused evidence, delivery, and governed-operation tests passed. The combined
test suite had one pre-existing unrelated assertion failure because
`submit_alpha_request` is present in the governed-intent set while its older
test expectation omits it.
