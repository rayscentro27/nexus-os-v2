# Nexus Hermes Agent Certification

Generated: 2026-07-21

## Result

`NEXUS_HERMES_FAILED`

## What Passed

- Hosted OpenRouter model invoked for ordinary conversation.
- Recent visible history was transmitted.
- Tool-free ordinary conversation passed.
- Tool-free writing passed.
- Client aggregate smoke passed through `get_client_aggregate`.
- Native tool-call architecture outperformed the legacy/default route in the comparison sample.
- No frontend deployment was attempted after holdout failure.

## What Failed

The 100-turn holdout scored 73%. Current private Nexus facts and governed drafts still need more reliable tool selection before Ray-only production activation.

The failure is architectural rather than a single phrase issue: native `gpt-4o-mini` tool choice is too conservative with the current tool definitions and context. It often answers from safe static context instead of calling the required current-data tool.

## Decision

Do not merge or deploy the Ray-only frontend.
