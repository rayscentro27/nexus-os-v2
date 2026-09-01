# Gmail result-set correlation

Each Gmail read record retains a bounded ordered snapshot with message ID and
thread ID. The snapshot is attached to the resource-backed exchange and is
passed to native Hermes only for an anaphoric follow-up. Full message bodies are
not retained in the referent envelope.

Observed repaired flow:

`gmail_search` → five-item ordered set → object follow-up → linked first item →
`gmail_read_thread(thread_id)`.

The selected item belongs to Turn A’s set. A later explicit freshness query
replaces the active Gmail result-set referent; the older set remains historical
context only.
