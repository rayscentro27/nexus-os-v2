# Google Hermes integrated preflight

## Result

The read-only Google MCP foundation is integrated with the current Hermes-native
Nova runtime and is ready for Ray’s real Telegram test, subject to the explicit
boundary that real-world certification has not been performed here.

## Verified

* Gmail search, message read, and thread read passed against the authorized
  account.
* Calendar search, event read, and availability passed against the authorized
  account using the existing `calendar.events` grant.
* Hermes discovery and invocation passed for exactly six Google read tools.
* Google tools were unused on ordinary conversational probes.
* Calendar and Gmail context released on unrelated reasoning turns.
* Nexus→Google and Google→Nexus transitions remained available.
* Nexus+Calendar and Nexus+Gmail mixed-resource probes selected and synthesized
  both resources.
* Google results remained read-only, bounded, provenance-bearing, and were not
  forwarded automatically to Web or Alpha.
* Focused regression suite: 45 passed.

## Known observation

One Gmail model exchange requested a same-turn search more than once during
continuation. It does not change correctness or authority, but should be
addressed separately if the project requires strict one-read-per-turn
efficiency. It is not hidden in this report.

## Boundary

`GOOGLE_MCP_REAL_WORLD_CERTIFIED=NO`; Ray must perform the final Telegram test.
