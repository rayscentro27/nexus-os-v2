# WP9J blocker ownership

The actual blocker discovered in this campaign was profile-scoped API
authentication/provider configuration. It was diagnosed and repaired through
the existing Oracle service without requesting a new credential:

1. profile API key absent from the profile secret scope;
2. profile key copied from the container's existing API secret source;
3. profile provider key hash differed from canonical Oracle OpenRouter key;
4. provider key reconciled to `/opt/data/.env` source;
5. existing service restarted once;
6. profile model request returned HTTP 200 and the exact sentinel.

`HERMES_BLOCKER_OWNERSHIP=NOT_PROVEN_REAL_HERMES_FLOW`

The repair itself is real infrastructure evidence, but it was performed by
the bounded operator procedure, not selected by Oracle Nova.

