# Research Room v1 (shadow)

Research Room is an isolated conversation engine. It does not replace the
production Research worker and does not own production objective routing.

## Reused Nexus components

- LangGraph 1.2.x is already installed. The room uses LangGraph `StateGraph`
  for conditional participant routing; each `ResearchRoomWorker` invocation
  executes one participant and returns.
- Nexus also exposes `adapters/graph_adapter.py` and `state_adapter.py`; the
  graph adapter is a synchronous compatibility wrapper whose fallback walks
  registered nodes in order. The room needs conditional routing, so it uses
  the already-installed LangGraph API directly rather than its linear fallback.
- Existing provider surfaces include the Hermes agent/graph, canonical
  `LlmGatewayAdapter` / `model_router` path, and local/offline after-action
  review selection. `AdvisorRouter` accepts those clients by injection and
  does not call a model unless a connected client is supplied.
- Existing read-only Supabase access and durable job APIs exist. The room's
  default proof store is local JSON and includes its own idempotent one-turn
  outbox; the optional `SupabaseCaseStore` targets only the separate
  `research_room_cases` table defined by `schema.sql` and is disabled unless
  explicitly enabled. It does not write production queue tables.
- Existing Research source adapters cover public web / source acquisition,
  YouTube transcript handling, and optional NotebookLM. `SourceTools` gives
  the room an ordered method fallback interface; NotebookLM is not invoked by
  the current shadow proof.
- Existing department handoff implementation persists real assignments. The
  room deliberately uses `PROPOSED_HANDOFF` instead and never calls it.

## Storage and safety

Each case, room message, question, finding, answer, and proposed handoff lives
in one case document under `data/research_room_shadow/cases`. A room turn also
records a deterministic, idempotent local outbox job. JSON replacement is
atomic. The included case runner does not enable Supabase storage. No
production table, queue, dispatcher, objective, or handoff is used by the
included case runner.

## Entry points

`entry.open_manual_shadow` is enabled for tests and local shadow runs.
`entry.youtube_event_shadow` is intentionally inactive. No automatic watcher
is registered.

## Current limitations

The TradingView proof uses current public web search result content and cited
independent public sources; it does not download or execute the Pine source or
run a backtest. The YouTube proof uses the repository's existing local
transcript fixture. Advisor responses in the three proofs are deterministic
fixtures, not model output. Hermes/OpenRouter adapters are provider-neutral
injection boundaries; ChatGPT is exposed as an unavailable connector boundary
until the actual connector is supplied.
