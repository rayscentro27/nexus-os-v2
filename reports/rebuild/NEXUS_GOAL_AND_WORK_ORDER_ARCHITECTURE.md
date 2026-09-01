# Goal and Work-Order Architecture

`build_goal()` implements company/department/initiative-compatible goal
hierarchy fields. `build_work_order()` implements goal, initiative, loop,
owner, inputs, authority, approval, budgets, lifecycle timestamps, result and
receipt references, metrics, next action, return-to-Nova, and deterministic
idempotency key. Existing governed work-order execution remains canonical.

