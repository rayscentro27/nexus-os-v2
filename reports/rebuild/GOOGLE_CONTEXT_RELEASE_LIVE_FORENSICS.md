# Live context release forensics

The live business turn occurred after a Calendar read and was answered with an
unrequested “no meetings” statement. Its sidecar showed Calendar as the last
resource record, demonstrating that global last-resource state was being used
as a continuing subject. This was a resource-context boundary defect, not a
Nova profile restriction.

The repair makes referent continuity explicit and clears `active_referent` when
a turn has neither a resource execution nor an object continuation. Historical
records remain available for audit and explanation but no longer select the
active resource for unrelated turns.

The post-repair process-equivalent business test cleared the prior Gmail
referent correctly, but the native model still voluntarily selected a Nexus
opportunities read. This is a remaining model-native resource-selection issue,
not persisted Calendar/Gmail context injection. Suppressing it would require a
new routing or behavioral restriction, which is outside this campaign’s allowed
scope.
