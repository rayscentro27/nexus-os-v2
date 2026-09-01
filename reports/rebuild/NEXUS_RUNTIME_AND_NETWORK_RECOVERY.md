# Runtime and Network Recovery

Runtime recovery is bootstrap → dependency inspection → state restore →
unfinished-work reconciliation → duplicate protection → resume → verify →
receipt. Network recovery is detect → wait external work → reconnect with
bounded attempts → refresh volatile state → resume → verify. Dependency state
contains no secret values and uses CONNECTED/DEGRADED/DISCONNECTED/RECONNECTING.

