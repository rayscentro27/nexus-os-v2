# WP8.3 Business Loop Recovery Proof

Loop `loop_67890646218d45579e9ab7a6b3a67d02` is persisted in governed
`loop_state`, and idea, work orders, research references, metrics, opportunity,
launch candidate, outcomes, and receipts are append-only reloadable records.

The focused persistence test reloads the final `WAITING_REVIEW` state and checks
receipt references and terminal work-order states. The dependency policy is
fail-closed: unavailable research becomes `WAITING_DEPENDENCY`, not fabricated
research, and bounded restoration may resume eligible work. This campaign did
not claim a machine reboot; process-faithful persistence was tested.

