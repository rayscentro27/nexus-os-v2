# Nova → Nexus Hermes Operations Map

Nova is the human-facing coordinator. Nexus Hermes/Operations is the governed
command boundary.

Nova may read operational state, explain results, recommend work, and submit a
bounded request. Submission is not execution.

```text
Nova request → Nexus intake → TruthKernel validation → assignment/queue
             → execution → verification → receipt → Nova explanation
```

Supported acknowledgement states are `RECEIVED`, `ASSIGNED`, `QUEUED`,
`STARTED`, `COMPLETED`, `BLOCKED`, `REJECTED`, and `FAILED`. The current
implementation guarantees a typed `RECEIVED` acknowledgement for bounded Nexus
intake; later states depend on Nexus processing evidence.

Nova cannot directly execute or mutate Nexus operations. Approval pass-through
is context submission only; Nexus independently validates the approval.
