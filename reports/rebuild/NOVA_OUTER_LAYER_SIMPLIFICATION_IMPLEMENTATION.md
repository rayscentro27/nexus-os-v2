# Nova Outer-Layer Simplification Implementation

Campaign: `HG-WP6.5-NOVA-OUTER-LAYER-SIMPLIFICATION-CAPABILITY-BROKER-AND-MODEL-LED-PLANNING-20260830-01`

Baseline: `0f435fa`

## Before/after

Before: seven graph nodes plus deterministic capability/source wrappers:
`classify_intent`, `handle_utility`, `capability_gate`, `build_context`,
`generate_response`, `validate_output`, `compose_output`.

After: five graph nodes. Classification and utility handling are internal
operations of `pre_model_boundary`; ordinary advisory/research questions no
longer execute a forced source before model reasoning. A compact broker plan is
provided to the model. Factual company reads and strict governed commands keep
their existing authority boundary.

This is a structural simplification, not real Telegram certification. Public
web live provider health and full Alpha execution remain to be proven through
fresh real-world tests.
