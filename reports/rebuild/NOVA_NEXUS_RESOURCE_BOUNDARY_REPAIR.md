# Nova/Nexus Resource Boundary Repair

## Trace-backed change

1. `turn_requirements` no longer carries the latest Nexus capability into every
   later prompt. It exposes a referent only for a generic anaphoric or volatile
   continuation.
2. Session assistant history is retained, but resource-backed entries are
   labeled as continuity/history and not current operational truth.
3. Legacy unlabeled entries are conservatively labeled as prior conversation
   context rather than promoted to a resource result.
4. Ordinary no-tool turns no longer mark prior resource receipts as valid for the
   current turn. Explicit result-reuse follow-ups retain structured linkage.
5. New sidecar turns record `source_type`, `resource_domains`, and `turn_id`.

No Nexus business logic, Nova profile, global SOUL, model/provider, or Telegram
delivery behavior was changed.

## Result

The clean-session control and Nexus-then-casual harness both produced natural
casual responses with zero Nexus calls. Explicit Nexus reentry still produced a
fresh blocker read. This is a context boundary, not a conversational ban.
