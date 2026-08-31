# Hermes Nova per-turn resource contract

The shadow runtime now records a turn-scoped contract separately from
conversation memory. Explicitly named resources are obligations for the
current turn; prior results cannot silently satisfy them. Hermes remains the
semantic selector and continues through its native tool loop.

The contract records the objective, required resources, executed resources, and
missing resources. If an obligation is missing, the same Hermes session gets a
bounded continuation request. No question router, phrase-specific answer, or
automatic refusal was added.

Current-turn examples:

- `Using Nexus and current outside information ...` requires `NEXUS` and
  `PUBLIC_WEB`.
- `What did Research find?` may reuse a correlated current Alpha result.
- Ordinary questions have no resource obligation.

Canonical-worker fixture 990204 executed Nexus, public web search, and page
retrieval in one shadow turn; its receipt contains the contract and evidence
state.
