# Gmail live search semantics

The captured live searches were materially different operations. The first
attention search returned the July 31 Google Alert result; the later “newer”
search returned an August 20–21 set. The latter is a freshness recheck and is
not evidence that the first result was stale or malformed. The runner preserves
the executed query in the MCP result and bounded receipt; no global Gmail query
was introduced.

Object follow-ups use the persisted result set. Explicit freshness requests
perform a new Gmail search and replace the active Gmail result-set referent.
