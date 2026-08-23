# Admin Information Architecture

**Status:** proposed IA; production routes remain unchanged in this phase

## Primary shell

The future shell has six primary destinations:

```text
NEXUS
├── Command
├── Work
├── Agents
├── Business
├── Studio
└── System
```

The current 26 direct items are moved behind these destinations or become diagnostic-only. The shell should communicate one operating model, not the repository’s component tree.

## Command

Command is the landing page and should fit in one desktop viewport at normal density.

```text
Greeting + system-level truth
Needs You        Today                 Working Now
Business snapshot / truth states
Recent Nexus activity and escalations
Global Ask Nexus composer
```

Cards are ranked by attention, not by data source. “All critical systems healthy” is shown only when Mission Control supports that claim.

## Work

Secondary navigation: `Needs You · Running · Scheduled · Completed · Failed · Approvals · All`.

The list is a compact queue. The detail view is a work thread with timeline, evidence, receipts, artifact links, and approved actions. The user can ask an agent about the selected item without losing the work context.

## Agents

Secondary navigation: `All agents · Hermes · Nova · Alpha · Recent outputs`.

The hub opens with three role cards and current work. Each agent detail has:

- role and authority boundary;
- current work and recent outputs;
- selected context;
- conversation history;
- one shared composer with the agent selected.

## Business

Secondary navigation: `Overview · Clients · Credit & Funding · Revenue · Opportunities · Growth`.

Business uses contextual tabs and journey links. Credit, funding readiness, business foundation, and bankability become related stages rather than separate top-level destinations.

## Studio

Secondary navigation: `Research · Creative · Campaigns · Artifacts · Reports`.

Studio is output-oriented. Alpha research and Creative Intelligence are represented through work, evidence, and artifacts rather than exposed as internal engines.

## System

Secondary navigation: `Mission Control · Workers · Integrations · Costs · Runtime · Diagnostics`.

System is the honest technical layer. It shows healthy/degraded/deferred/not connected states and links to source evidence. It does not compete with Command for attention.

## Global interaction

The persistent desktop shell includes a compact Ask Nexus bar. On an agent page it expands into the universal composer. On Business, Studio, or Work it includes a removable page-context chip. The user always sees which agent is selected.

## Route strategy

During cutover, existing `/admin#...` hashes remain compatibility targets. The new shell maps them into the six conceptual areas first, then canonical routes can be changed after browser review. No route is deleted during the design phase.

## Responsive behavior

- Desktop: 240px rail, content max-width 1440px, two-column detail layouts.
- Tablet: collapsible rail and persistent context drawer.
- Phone: Command/Work/Agents become a bottom navigation; secondary tabs scroll horizontally; evidence and diagnostics open as drawers; composer remains thumb-reachable.

## Truth states

Every surface has designed states for `LOADING`, `EMPTY`, `UNKNOWN`, `NOT_CONNECTED`, `NOT_AVAILABLE`, `MEASUREMENT_PENDING`, and `ERROR`. Missing source data is never rendered as zero.
