# Nexus Approval Policy

Nexus separates autonomous internal work from approval-gated execution.

## No Approval Required

- watched-resource checks after Ray approves the resource
- transcript review
- research scoring
- SEO keyword scoring
- affiliate opportunity scoring
- internal routing
- internal experiment cards
- internal reports
- Hermes internal recommendations
- paper-only trading research

## Ray Review Queue

Ray Review Queue is for decisions. It is used when Ray should choose direction, request changes, park an item, or create a formal approval item.

Examples:

- campaign is ready for approval
- scheduler is ready to activate
- connector setup needs a decision
- high-value revenue choice needs Ray direction

## Formal Approvals

Formal Approvals are required before execution:

- publish
- send
- contact lead/client
- spend money
- launch ads
- live trade or broker execution
- enable persistent scheduler
- production change
- sensitive/private data in external tools

Approving a Ray Review Queue item does not bypass formal execution gates unless a specific approval path is implemented and active.

## Automation Levels

See [NEXUS_AUTOMATION_LEVELS.md](NEXUS_AUTOMATION_LEVELS.md). Helpers in
`src/config/nexusActionPolicy.ts`:

- **Level 1 (autonomous):** no approval row. Never create approvals for research, scoring, routing,
  internal reports, watched-resource updates, transcript reviews, paper-only trading research, or
  Hermes internal recommendations.
- **Level 2 (approval-gated):** create an approval row ONLY when execution-ready
  (`shouldCreateApprovalRow(action, executionReady)`). Covers publish-ready campaigns, send-ready
  messages, client-contact actions, scheduler activation, connector activation, production change,
  spend request.
- **Level 3 (blocked):** no direct execution approval (`isBlockedFromDirectApproval`). Live
  trading, broker execution, raw `auto_executor`, payment modification, destructive DB actions, and
  external AI on sensitive data require a separate contract/design review first.
