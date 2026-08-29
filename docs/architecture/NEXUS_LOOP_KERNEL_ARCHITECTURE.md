# Nexus Loop Kernel Architecture

WP4 introduces one reusable orchestration kernel instead of copying the Daily
loop. `scripts/nexus_agent_platform/loops/kernel.py` models trigger, bounded
context, authority/dependency checks, skill/worker selection, executor call,
validation, advisory review, and a versioned receipt. It fails closed on
unknown triggers, skills, workers, unsafe context, executor failure, and review
failure.

The kernel is an orchestration boundary, not an authority boundary:

`TruthKernel authority → skill/capability resolver → Hermes advisory worker →
Nexus-owned executor → validation → TruthKernel receipt`.

Hermes cannot approve gates, write TruthKernel authority, select arbitrary
commands, or create consequential side effects. The fixed Daily/System
Operations adapter demonstrates migration without duplicating the executor.
