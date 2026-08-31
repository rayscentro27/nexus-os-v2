# Alpha Correlation Root Cause

The shadow Alpha adapter returned the governed envelope’s nested `data.job`, `data.pack`, and `data.receipt`, but the direct execute path did not expose a request ID, normalized result ID, or artifact ID at the top level. The shadow parser consequently recorded `NULL` identifiers.

Repair: the existing Alpha execute lifecycle now creates one request correlation ID, carries it with the existing research job, and exposes the existing receipt and research-pack references as result/artifact identity. The shadow parser reads both the governed envelope and nested Alpha objects.
