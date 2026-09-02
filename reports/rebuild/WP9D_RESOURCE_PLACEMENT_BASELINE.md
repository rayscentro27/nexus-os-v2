# WP9D resource placement baseline

Measured local Mac baseline: x86_64, macOS 12.7.6, 4 CPUs, approximately 8 GiB
RAM, Python 3.14.5, Node v22.22.3, root volume approximately 658 GiB free.
No suitable local GPU evidence was found. Small bounded control-plane work is
appropriate on the Mac; GPU/high-memory work should be placed on an existing
remote worker or remain approval-gated.

Oracle resource values were not available from the current local evidence and
remain `UNKNOWN`; no remote probe or service restart was performed. Placement
records distinguish `MAC_CONTROL_PLANE`, `ORACLE_FREE_WORKER`,
`REMOTE_GPU_OPTIONAL`, and `NOT_FEASIBLE`.
