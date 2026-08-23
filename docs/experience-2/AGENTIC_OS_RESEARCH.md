# Nexus Experience 2.0 — Agentic OS Research

**Status:** design research only; no production UI changes
**Access date:** 2026-08-22

## Research frame

The question is not “which dashboard should Nexus resemble?” It is: **how should a human operate a team of agents while retaining attention, context, evidence, and approval control?** The review focused on first-party product and documentation sources and extracted interaction principles rather than visual copies.

## Benchmarks

| Product | Primary source | Useful signal |
| --- | --- | --- |
| OpenAI ChatGPT Workspace Agents / ChatGPT agent | [Workspace agents](https://openai.com/index/introducing-workspace-agents-in-chatgpt/), [ChatGPT agent](https://openai.com/index/introducing-chatgpt-agent/) | Shared agents, long-running work, tools, approvals, and user interruption inside a familiar composer. |
| Microsoft Copilot Studio | [Product documentation](https://learn.microsoft.com/microsoft-copilot-studio), [multi-agent patterns](https://learn.microsoft.com/en-us/microsoft-copilot-studio/guidance/multi-agent-patterns) | Connected agents remain separate in orchestration, tools, and knowledge; flows and human review are first-class. |
| Relevance AI | [Workforces](https://relevanceai.com/docs/get-started/core-concepts/workforces) | Specialized agents are composed visually, with explicit handoffs and a team/workforce mental model. |
| CrewAI | [CrewAI documentation](https://docs.crewai.com/) | Crews and flows make role, process, state, and observability distinct concepts. |
| n8n | [Advanced AI documentation](https://docs.n8n.io/advanced-ai/) | Agent work is represented as inspectable workflow/tool steps rather than opaque chat magic. |
| Salesforce Agentforce | [Agentforce overview](https://www.salesforce.com/agentforce/how-it-works/), [security model](https://help.salesforce.com/s/articleView?id=005315874&language=en_US&type=1) | Role, knowledge, actions, guardrails, channels, permissions, and auditability define an agent contract. |
| Google Vertex AI Agent Builder | [Agent Builder documentation](https://docs.cloud.google.com/agent-builder) | Build, scale, and govern agents as a platform concern; operational detail can remain behind a controlled layer. |

## Comparative findings

### OpenAI: work starts in the composer, not a control panel

- **Navigation:** Agents are discoverable from a workspace sidebar, while the active task remains in a conversation/work surface.
- **Agent interaction:** A shared interaction surface can move between ordinary conversation, research, and action. The mode/tool choice is visible at the point of use.
- **Work:** Long-running tasks and outputs are more important than implementation logs. Interrupt, stop, and permission moments preserve user control.
- **Human-in-the-loop:** Consequential steps ask for permission rather than silently completing them.
- **Context and artifacts:** Files, connected sources, and generated reports are attached to the work thread.
- **What Nexus should learn:** Put “what should happen next?” beside the composer and make work resumable.
- **What Nexus should not copy:** A general-purpose agent mode cannot define Nexus’s narrower authority or operating truth.

### Microsoft Copilot Studio: connected agents are a system, not one brain

- **Navigation:** Builder, knowledge, tools, flows, testing, and publishing are separate concerns; users do not need every concern in the daily operating view.
- **Agent interaction:** Connected agents retain their own orchestration, tools, and knowledge while sharing bounded conversation context.
- **Work and approvals:** Flows can invoke agents and include human review steps.
- **Observability:** Configuration and testing are available without turning the front door into a telemetry dashboard.
- **What Nexus should learn:** Show role boundaries and handoffs explicitly; model context transfer as an inspectable event.
- **What Nexus should not copy:** A low-code builder hierarchy would expose too much internal machinery to Ray’s daily work.

### Relevance AI: workforce and handoff are visible concepts

- **Navigation:** A workforce groups specialized agents around an outcome.
- **Agent interaction:** A visual canvas connects agents; a right-side detail surface configures the selected specialist.
- **Work:** Multi-step work is decomposed into specialist steps and handoffs.
- **What Nexus should learn:** A work item can show “who is doing what next” without presenting each agent as a separate product.
- **What Nexus should not copy:** A canvas-first authoring model would make Nexus feel like an automation builder instead of an executive operating surface.

### CrewAI: process and observability belong behind the operating layer

- **Navigation:** Agents, crews, flows, tasks, and traces form a platform model.
- **Agent interaction:** Roles, goals, tools, and task sequencing are explicit.
- **Work:** The process graph is useful when diagnosing a run, but not as the first screen for a human decision.
- **What Nexus should learn:** Separate the work outcome from the technical trace; expose the trace through a detail drawer.
- **What Nexus should not copy:** Crew/task vocabulary as the primary navigation; Ray needs priorities, decisions, and outputs.

### n8n: inspectable automation beats magical claims

- **Navigation:** Workflows and executions are discoverable, with technical detail available for debugging.
- **Agent interaction:** AI nodes, tools, memory, and human review are connected in a visible flow.
- **Work:** Execution status and failed steps are concrete and recoverable.
- **What Nexus should learn:** Every “Nexus is working” statement needs a status, receipt, source, and next step.
- **What Nexus should not copy:** Node-builder density as the default business experience.

### Salesforce Agentforce: role, action, guardrail, and trust are one contract

- **Navigation:** Agents are embedded in CRM work; the user does not leave the business context to ask for assistance.
- **Agent interaction:** Agent roles, knowledge, actions, channels, and guardrails are defined separately.
- **Human-in-the-loop and observability:** Permissions, action boundaries, trust controls, and event logs make consequential behavior reviewable.
- **What Nexus should learn:** A visible agent identity must be paired with a visible authority boundary and evidence source.
- **What Nexus should not copy:** CRM-specific action breadth; Nexus’s agents are advisory or governed by design.

### Google Agent Builder: platform governance is a secondary layer

- **Navigation:** Development, deployment, scaling, and governance are platform capabilities rather than daily operator destinations.
- **Work:** The product framing supports production agents without requiring every runtime concept in the primary experience.
- **What Nexus should learn:** Keep Mission Control under System and expose operational truth when needed.
- **What Nexus should not copy:** Cloud-platform terminology as the language of Ray’s business decisions.

## Cross-benchmark principles

1. **Outcome before taxonomy:** Command answers what matters; System answers why the machinery is healthy.
2. **One operating shell, separate agents:** Hermes, Nova, and Alpha can share composer mechanics while retaining separate brains, memory, tools, and authority.
3. **Work is a first-class object:** Running, waiting, completed, failed, approval-required, evidence, and receipts need a common presentation model.
4. **Approval is a state, not a modal surprise:** Needs Ray belongs in Command and Work, with the approval boundary visible in the work thread.
5. **Context is explicit and removable:** Show page/context chips and sources; never imply more context than is actually passed.
6. **Observability is progressive disclosure:** The first view is human-readable; traces, heartbeats, and logs live in detail views.
7. **Artifacts are outcomes:** Reports, research, creative, plans, and receipts belong beside the conversation that produced them.
8. **Voice is a shared input capability:** Microphone and transcript review belong to the universal composer, not to one agent brand.
9. **Mobile prioritizes attention:** Needs You, one next step, and the active thread survive; dense diagnostics move behind drawers.
10. **Truthful absence is a product state:** Unknown, pending, not connected, and measurement pending must be designed, not replaced with zeros.

## Client portal research principles

The benchmark lesson from contemporary financial onboarding and document-led portals is to make the next action concrete, keep progress visible, and let evidence be supplied in context. GoClear should explain readiness factors without implying loan approval, use category-specific inline upload, show review states, and reveal complexity progressively on mobile.

## Nexus conclusion

Nexus should feel like a calm operating room for a founder: attention is curated, work is traceable, agents are distinct colleagues, and the system is honest about what is known. The visual identity should be confident and information-dense without becoming a developer console.
