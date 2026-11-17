# Nexus Repository Governor Contract

All autonomous coding agents working in this repository must use `python3 scripts/ops/nexus_safe_git.py` for staging and commits.

- Read `configs/nexus_repository_policy.yaml` before editing or staging.
- Stage explicit repository-relative paths with `nexus_safe_git.py add path...`; never use `git add .`, `git add -A`, `git add -u`, or directory-wide staging.
- Keep one subsystem per commit. The installed pre-commit hook rejects cross-subsystem commits and local runtime/data, credentials, generated artifacts, caches, certification, and archives.
- Before a high-impact operation, record a checkpoint with `nexus_safe_git.py checkpoint SUBSYSTEM path...`.
- Do not use `git clean`, `git reset --hard`, broad restore/checkout, mass deletion, or force push. The wrapper blocks destructive Git commands; owner approval is interactive and does not override the pre-commit content boundary.
- Keep runtime state and Research knowledge in their designated local/durable systems; do not move or ignore them to make Git status clean.
- If the guard rejects a path, stop and resolve ownership with the repository owner instead of bypassing the hook.
