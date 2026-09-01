# Cross-process referent forensics

Live evidence showed Gmail search snapshots were persisted with message and
thread IDs. Turn C could still retrieve the original thread, while Turn B and
Turn E lost the bounded result-set subject. The common cause was not absent
storage; it was selecting the last resource record rather than the active
resource referent. Thread linkage therefore survived through a narrower linked
object path while result-set selection was contaminated by later resource
history.

The new `active_referent` record stores resource, capability, source turn, and
request ID. It is hydrated before `turn_requirements`; the bounded object
snapshot remains in `resource_referent_links`.
