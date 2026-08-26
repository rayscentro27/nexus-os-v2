# Overnight Autonomy Campaign V1

The overnight campaign is a bounded priority overlay consumed by the existing
Phase 15 scheduler. It does not create a scheduler, approve releases, deploy,
trade, contact clients, or synthesize human evidence.

Hermes uses a fact-only decision trace with layers for input, authority,
intent, evidence, deterministic/model routing, specialist handoff, optional
zero-authority critique, approval, execution, verification, and response.
The Python Telegram operator and browser Workroom brain remain separate
surfaces, but production actions still use the governed action/release
contracts. The Python trace is the canonical overnight evidence contract.

Model roles are deterministic-first. Status and runtime truth use local
logic; research uses the existing Alpha path; source changes use Builder/Codex;
the Integrity Critic is unavailable unless a governed provider is configured.
Critic inputs must be sanitized and critic output has no action authority.

`IDEA:` and `/ideas` use the append-only Idea Inbox. Capturing an idea creates
no mission, work order, approval, deployment, or research execution.

The campaign state is `data/runtime/nexus_overnight_campaign.json`. It records
`EXISTING_PHASE15_ONLY`, `TRUE_GATES_ONLY`, and `production_mutation: NO`.
Morning reporting reads persisted portfolio, certification, and Idea Inbox
evidence and distinguishes missing evidence from completion.
