# Alpha Ray Review / Nexus Bridge Contract

Alpha may create draft proposals, recommendation reports, opportunity scorecards, marketing drafts, trading research/backtest plans, risk reviews, and suggested Nexus tasks.

Alpha may not save/write an approval, approve itself, submit a Nexus task, mutate production data, publish, send, charge, trade, access clients, or bypass Ray Review.

Required proposal fields: artifact ID/version/hash, fixture/real-source label, objective, lane, sources, assumptions, confidence, score, recommendation, risk, requested decision, proposed destination, prohibited actions, expiration/freshness, and creator timestamp.

Artifacts are immutable after review begins. Revisions create a new version/hash. Phase 1 state is `conversation_draft_only`, `saved: false`, `submitted: false`, and `externalActionAuthorized: false`.

A future handoff to Nexus Hermes contains only the approved immutable artifact and Ray receipt. It never includes Alpha memory, provider credentials, untrusted instructions, client data, or executable external commands. Supabase remains disconnected because Phase 1 proves proposal quality and safety before any persistence/queue adapter exists.
