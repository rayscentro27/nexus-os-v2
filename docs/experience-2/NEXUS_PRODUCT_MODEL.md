# Nexus Product Model

**Status:** proposed product model; not production implementation

## The central distinction

**Nexus is the operating system. Hermes, Nova, and Alpha are agents inside it.** The product is not “Hermes with tabs.” Nexus coordinates attention, work, evidence, artifacts, approvals, and system truth while preserving agent boundaries.

## User mental model

Ray should be able to answer five questions from the front door:

- What matters now?
- What is Nexus doing?
- What needs me?
- Who should I talk to?
- What has Nexus produced?

Internal concepts such as schedulers, adapters, health probes, and engines remain implementation details unless Ray opens System or a work trace.

## Proposed primary navigation

1. **Command** — attention, priorities, changes, escalations, and a global Ask Nexus composer.
2. **Work** — all active, waiting, completed, failed, and approval-gated work presented over canonical sources.
3. **Agents** — Hermes, Nova, Alpha, roles, conversations, current work, and outputs.
4. **Business** — Clients, Credit & Funding, Revenue, Opportunities, and Growth.
5. **Studio** — Research, Creative, Campaigns, Artifacts, and Reports.
6. **System** — Mission Control, Workers, Integrations, Costs, Runtime, and Diagnostics.

The six labels are user outcomes, not backend ownership boundaries.

## Product objects

| Object | Meaning | Canonical source rule |
| --- | --- | --- |
| Attention item | A reason Ray may need to act or decide | Existing approvals, Ray Review, escalation, or operating context |
| Work item | A unit of unattended or assisted Nexus work | Presentation over Active Operator, Work Orders, Mission Control, reports, receipts, and approvals |
| Agent thread | A conversation with one selected agent | Existing Hermes, Nova, or Alpha conversation path; never cross-routed |
| Artifact | A report, research result, creative output, plan, or receipt | Existing engine/output source; unknown stays unknown |
| Evidence | A source, observation, or receipt supporting a claim | Existing evidence and report contracts |
| Decision | A human choice with explicit consequence | Ray Review/approval path |
| Capability | What Nexus can currently do | Mission Control and runtime truth |

## Command

Command is not a monitoring dashboard. It is a prioritized briefing with four zones: Needs You, Today, Working Now, and Business. Every card names its source and next step. An unavailable source renders `UNKNOWN`, `NOT_CONNECTED`, `NOT_AVAILABLE`, or `MEASUREMENT_PENDING`.

## Work

Work consolidates the human view of unattended activity. It does not create a new work database. Filters are Needs You, Running, Scheduled, Completed, Failed, Approvals, and All. Selecting an item opens a thread containing the timeline, evidence, receipts, next step, and authority boundary.

## Agents

Agents are presented as three distinct colleagues in one operating system:

- **Hermes:** operator / COO / chief of staff. “What should we do, what is blocked, and what needs approval?”
- **Nova:** strategic adviser / critic. “What are we missing, and what would you challenge?”
- **Alpha:** research / evidence / market intelligence. “What can we verify, compare, and learn?”

## Business, Studio, and System

Business is organized around the company journey, not internal workflow stages. Studio is organized around outputs. System is where technical truth lives, with Mission Control remaining canonical and diagnostic detail progressively disclosed.

## Product decisions

1. **One conversation shell?** Yes. Share composer, thread layout, voice states, attachments, context, and artifact presentation. Keep agent endpoints, prompts, memory, tools, and authority separate.
2. **Selected agent persistence?** Persist per Admin session and page context, defaulting to Hermes when no explicit selection exists. Never persist selection into a client session.
3. **Ask Nexus default?** Yes, Ask Nexus defaults to Hermes because Hermes is the operating interface; the selector makes Nova and Alpha deliberate choices.
4. **Page context?** Pass a removable, visible context envelope: route, entity type/id, selected artifact, and approved summary. The selected agent may decline or request more context.
5. **Handoffs?** Show an explicit handoff event: “Hermes asked Alpha to research X” with reason, source, receiving agent, and returned artifact. A handoff is not a brain merge.
6. **Ray Review in Work?** Yes. Ray Review becomes a Needs You filter and work-thread state, while its existing approval source remains canonical.
7. **Mission Control standalone?** Yes, under System. It is important but not the front door.
8. **Command vs Work?** Command is a curated attention brief; Work is the complete operational queue and history.
9. **Primary sidebar?** Command, Work, Agents, Business, Studio, System.
10. **Never in primary sidebar?** Raw probes, CLI/tool registry, tester screens, individual workflow stages, model/provider details, legacy report variants, and implementation phases.
11. **Mobile Admin?** A compact bottom/rail navigation for the six areas; Command and Work prioritize one decision per viewport; diagnostics use drawers.
12. **Voice location?** In the universal composer and available to all three agents, with the same private STT and review-before-send contract.
13. **Attachments?** One attachment affordance in the composer, with agent-specific validation and a visible context chip; Alpha handles evidence, Hermes handles approved operating context, Nova receives only approved strategic material.
14. **Artifacts?** Inline preview cards in threads plus an Artifact drawer; never bury the only copy in a chat transcript.
15. **Unattended work noise?** Summarize by consequence and change. Show new failures/escalations immediately, collapse healthy repetition into one heartbeat, and let Ray expand the trace.

## Non-negotiable boundaries

No parallel health, revenue, approval, priority, memory, or agent brain is introduced by the product model. Voice remains input only. Publishing, external sends, charges, funding submission, and funded trading retain existing governance.
