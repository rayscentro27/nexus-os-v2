# Gmail same-turn semantic dedupe final proof

Campaign: `HG-WP7.1-GMAIL-SAME-TURN-SEMANTIC-DEDUPE-FINAL-COMPLETION-20260901-01`

## Scope and baseline

The repository baseline was `85367b4`; `origin/main` was the same commit at
audit time. Existing unrelated worktree changes were preserved. The only
implementation change for this campaign is in
[`scripts/nova/nova_hermes_shadow.py`](../../scripts/nova/nova_hermes_shadow.py),
plus the deterministic execution-layer tests in
[`scripts/nova/test_nova_google_same_turn_dedupe.py`](../../scripts/nova/test_nova_google_same_turn_dedupe.py).

## Evidence of the defect

The prior real Gmail run recorded multiple `gmail_search` tool messages for one
user turn and did not retain normalized arguments. That was insufficient to
distinguish duplicate discovery from legitimate distinct searches. The current
instrumentation now records, per bounded turn:

- root `turn_id` (including bounded Hermes continuation task IDs collapsed to
  the user turn);
- tool name and call sequence;
- normalized-argument fingerprint and Gmail semantic-query fingerprint;
- `EXECUTE`, `REUSED_SUCCESS`, `RETRY_AFTER_FAILURE`, or no-turn-ID decision;
- whether the external dispatch actually ran.

The result is emitted in existing bounded latency/trace metadata and the local
session sidecar. No email body or secret is added.

## Repair

The previous handler-level wrapper was replaced by a wrapper at the existing
Hermes registry dispatch boundary. The key is:

`(root_user_turn_id, tool_name, normalized_arguments)`

For Gmail discovery, normalized arguments contain only the case-folded,
trimmed query. `max_results` is a result bound, not a different mailbox
semantic request. Only successful results are cached. Errors are never cached,
so the existing bounded retry behavior remains possible. Different user turns
remain isolated by the turn component of the key.

This is generic resource execution behavior, not Gmail prompt/routing logic.

## Deterministic proof

Using a fake registry dispatch with the same production wrapper:

| Case | Model requests | External executions | Result |
|---|---:|---:|---|
| equivalent `is:unread` requests, including `-evidence` continuation | 2 | 1 | second result `REUSED_SUCCESS` |
| `is:unread` and `from:supabase.com` in one turn | 2 | 2 | both distinct searches execute |
| first equivalent call fails, second succeeds, third repeats | 3 | 2 | failure not cached; later success reused |
| same query on two different turns | 2 | 2 | no cross-turn reuse |

Test result: `20 passed` for the dedupe and evidence-contract tests. The
broader focused Nova regression set passed with `27 passed`.

## Integrated evidence

The previously captured canonical Gmail A/B/C run showed that the linked-result
repair remained intact: A returned the bounded Gmail set, B selected a linked
thread without broad discovery, and C read the linked thread successfully.
The latest local run used an already-populated session and therefore followed a
prior Gmail object; it is not used as a fresh-discovery count. A fresh-session
attempt was unable to discover the local MCP children because the existing
Hermes environment cancelled both configured MCP child connections. That is an
environment/runtime availability issue, not evidence against the dedupe key,
and no MCP path or credential change was made in this campaign.

## Contract status

- `GMAIL_CALL_ARGUMENT_CORRELATION_VISIBLE=YES`
- `SEMANTICALLY_DUPLICATE_SAME_TURN_SEARCHES_EXECUTED_ONCE=YES`
- `SEMANTICALLY_DISTINCT_SAME_TURN_SEARCHES_ALLOWED=YES`
- `FAILED_CALL_DEDUPE_BEHAVIOR=SAFE`
- `CROSS_TURN_VOLATILE_REUSE=NO`
- `NEW_NOVA_BEHAVIORAL_RESTRICTIONS_ADDED=0`
- `GOOGLE_SECRET_REDACTION=PASS`
- `TRACE_DATA_MINIMIZATION=PASS`
- `NO_COT_CAPTURE=PASS`

The implementation is ready for Ray’s short final Telegram retest. Google
real-world certification remains intentionally unclaimed until that test.
