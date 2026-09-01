# Current versus history information architecture

`PERSISTED` does not mean `CURRENT`. A current capability result must contain
only records eligible for present operational use. Historical counts and
research decisions remain durable, but belong to historical analysis rather
than the current opportunity answer envelope.

The 8,510 value means accumulated research candidates evaluated. It does not
mean current opportunities. Prior session history may still be used when Ray
asks historical questions or asks why a current state differs from an earlier
state. It must not silently establish present state.

The current opportunity adapter now separates these concerns by omitting the
historical accumulator from the current result while leaving the source ledger
unchanged. This permits current and historical reasoning to coexist without a
global ban on historical discussion.
