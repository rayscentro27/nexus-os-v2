# Nexus Engineering Git Closure Policy V1

Every Codex, OpenCode, or Kilo engineering task that modifies production source follows this closure contract:

`IMPLEMENT → TEST → DIFF REVIEW → WORKSTREAM CLASSIFICATION → COMMIT → PUSH OR EXPLICIT HOLD → DEPLOY IF APPLICABLE → LIVE VERIFY IF APPLICABLE → RECEIPT`

The required final fields are:

```text
CODE_CHANGE_STATUS=
COMMIT_SHA=
PUSH_STATUS=
DEPLOYMENT_STATUS=
LIVE_VERIFICATION_STATUS=
```

If no production code changed, use `CODE_CHANGE_STATUS=NO_CODE_CHANGE` and still report whether documentation, tests, or configuration changed.

Workstream commits must use `scripts/nexus_agent_platform/workstream_git_closure.py`. Its default inspection/plan commands are read-only. `commit` and `push` are explicit separate actions. Broad staging (`git add .` and `git add -A`) is prohibited.

Runtime state, caches, locks, local browser/provider profiles, credential/session files, temporary artifacts, and generated status output are not commit candidates by default. A clean isolated worktree based on the remote branch is the preferred path when the active worktree contains unrelated local commits or dirty work.

No task is complete until it ends in one of:

- `COMMITTED_AND_PUSHED`
- `COMMITTED_NOT_PUSHED_WITH_REASON`
- `LOCAL_ONLY_WITH_REASON`

For production-facing changes, also report:

- `DEPLOYED_AND_VERIFIED`
- `NOT_DEPLOYED_WITH_REASON`
