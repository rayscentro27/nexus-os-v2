# Nexus Jarvis Voice Feedback Plan

Full voice is not implemented in this pass. The architecture is prepared for a future Hermes/Jarvis voice layer.

## Future Voice Commands

- review top report
- explain why an item scored high
- approve campaign
- request changes
- move item to a department
- generate next test
- reject idea
- capture preference
- compare paper-only trading strategies

## Safety Boundary

Voice feedback may create internal memory, reports, drafts, and task requests.

Voice approval must still pass through explicit approval gates for:

- publish
- send
- contact
- spend
- live trading or broker execution
- persistent scheduler activation
- production changes
- sensitive/private data in external tools

## Future Architecture

1. Speech-to-text captures Ray's command.
2. Hermes classifies it as internal feedback, research request, draft request, or approval-gated execution.
3. Internal feedback is stored as Hermes decision memory.
4. Approval-gated execution creates an Approval Desk item.
5. No action leaves Nexus until Ray approval is recorded and the runner gate allows it.

## Ray Review Queue Voice Path

Future voice commands should be able to say:

- "What needs my decision?"
- "Approve this for prep only."
- "Request changes."
- "Park this."
- "Move this to Creative Studio."
- "Create the formal approval item."

Voice should never publish, send, trade, deploy, or activate a scheduler directly.
