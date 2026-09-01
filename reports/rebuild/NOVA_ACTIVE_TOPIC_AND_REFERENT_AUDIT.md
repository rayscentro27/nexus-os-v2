# Nova Active Topic and Referent Audit

Before the repair, the active Nexus capability was effectively session-scoped:
`prior_records` always supplied `referent_capability`, even when the new prompt
contained no anaphoric continuation. This conflated referent continuity with
resource routing.

Examples proven by code and live traces:

- `good morning` received Nexus referent scope despite no referent.
- `my favorite is hazelnut` received the same inherited scope.
- `Which of those are still active?` correctly remains eligible for referent
  continuation because it contains an anaphoric/current-state continuation.

The repair makes referent capability available only when a generic continuation
signal is present (`that`, `those`, `it`, `they`, `still`, `active`, and related
forms). It does not name or route specific questions.

`REFERENT_CONTEXT=allowed`; `UNRELATED_RESOURCE_DOMAIN=non-authoritative`.
