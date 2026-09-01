# Gmail thread follow-up repair

The defect was below Nova reasoning: the prior result snapshot was present in
the session sidecar but was not included in the native-turn context. Hermes
therefore treated “Which one looks most important?” as a new discovery task.

Repair:

* classify Google MCP records as the `GOOGLE` resource family;
* distinguish `OBJECT` referent follow-ups from `CURRENT_RECHECK` requests;
* expose bounded linked objects for object follow-ups;
* keep Gmail item/thread reads available for additional detail while excluding
  broad discovery search from an object-only continuation.

The repair does not alter Nova’s profile, personality, or conversational
constitution.
