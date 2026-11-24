# Nexus Repository Governor Contract

All autonomous coding agents working in this repository must use `python3 scripts/ops/nexus_safe_git.py` for staging and commits.

- Read `configs/nexus_repository_policy.yaml` before editing or staging.
- Stage explicit repository-relative paths with `nexus_safe_git.py add path...`; never use `git add .`, `git add -A`, `git add -u`, or directory-wide staging.
- Keep one subsystem per commit. The installed pre-commit hook rejects cross-subsystem commits and local runtime/data, credentials, generated artifacts, caches, certification, and archives.
- Before a high-impact operation, record a checkpoint with `nexus_safe_git.py checkpoint SUBSYSTEM path...`.
- Do not use `git clean`, `git reset --hard`, broad restore/checkout, mass deletion, or force push. The wrapper blocks destructive Git commands; owner approval is interactive and does not override the pre-commit content boundary.
- Keep runtime state and Research knowledge in their designated local/durable systems; do not move or ignore them to make Git status clean.
- If the guard rejects a path, stop and resolve ownership with the repository owner instead of bypassing the hook.

## NEXUS_GIT_REMOTE_SYNC_POLICY_R1

For every completed scoped unit of accepted work, in Research, Creative, Marketing, Workflow, Hermes adapters, Trading, GoClear, Admin, Systems, or any other Nexus subsystem:

1. Run the focused tests for the unit.
2. Stage explicit paths and create a scoped commit through `nexus_safe_git.py`; let the repository guard and pre-commit hook pass.
3. Push the commit or branch to its configured remote without force-pushing.
4. Fetch the remote and verify the exact commit SHA is reachable from the intended remote branch.
5. Only then begin the next accepted unit of work.

Completion reporting must distinguish local code from canonical remote state. Record `SCOPED_COMMIT_CREATED=YES`, `REMOTE_PUSH_ATTEMPTED=YES`, and `REMOTE_SHA_VERIFIED=YES` only when each condition is true. If a push cannot complete, report `REMOTE_SYNC_PENDING=YES`; do not describe the work as fully checkpointed or canonical. The commit must be pushed and its remote SHA verified before the next accepted unit begins.

An intentionally local-only commit must be explicitly recorded with `LOCAL_ONLY_INTENTIONAL=YES` and a `LOCAL_ONLY_REASON`. Otherwise, local-only commits are not considered canonical.

For upstream reconciliation when a development worktree is dirty, preserve it and use a separate clean integration worktree. Fetch first, merge the exact fetched `origin/main` normally, preserve both histories, resolve conflicts deliberately, commit through the guard, and push without force. A merge-guard exception is limited to conflict-free integration branches merging the exact fetched `origin/main`; sensitive-path, secret, file-size, and deletion checks remain active.
