# Nexus Department Workspace UI

The department workspace is NotebookLM-inspired:

- Left panel: department projects, sources, assets, jobs, or work items.
- Middle panel: selected project summary plus contextual Hermes advisor/chat.
- Right panel: department function buttons and generated outputs/proof.

Desktop uses three columns with internal panel scrolling. Mobile stacks project list, selected project, then actions.

## Components

- `DepartmentWorkspace`
- `DepartmentProjectList`
- `DepartmentProjectSummary`
- `HermesAdvisorWorkspace`
- `DepartmentActionStudio`
- `DepartmentOutputPanel`

## Refactored Tabs

- Source Intake.
- Opportunity Lab.
- Design Library.
- Creative Studio.
- SEO / Marketing.
- Ops & Improvements.
- Agent Jobs.
- Command Center executive overview.

## Source Intake

Manual paste is instant: "Add Source / Research Now" saves a `research_sources` row immediately. Enrichment can happen later through safe task requests. The visible UI says "Saved. Summary/enrichment pending" rather than "queued and unavailable."

## Right-Side Actions

Actions include Analyze, Create Report, Send to Creative, Send to Opportunity Lab, Send to Design Library, Create Task, Request More Research, Generate Summary, Generate Slide Deck, Generate Social Draft, Mark Research Only, Park, Reject, and Approve/Queue only when required.

Disconnected actions are disabled and described as not connected yet. Risky actions create approvals.
