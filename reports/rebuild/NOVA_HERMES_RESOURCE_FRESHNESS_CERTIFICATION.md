# Nova Hermes resource freshness certification

Each shadow turn receives a unique turn ID. Tool messages are parsed for actual
request/result/receipt/artifact identifiers when present and indexed as
`resource_results`. Prior records remain historical context but are explicitly
marked `current_for_turn=false` before the next turn.

Fresh Alpha linkage remains preferred through the Hermes session and active
turn context. The sidecar is correlation metadata only; it is not an evidence
database. Historical results can be requested as history and cannot silently
become the current result.
