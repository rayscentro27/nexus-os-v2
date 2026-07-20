# Nexus Worktree And Release Policy

Generated: 2026-07-20T16:57:31.444Z

1. No new feature wave begins in a dirty main worktree.
2. Every wave gets a dedicated branch or Git worktree created from the intended production baseline.
3. Generated caches and runtime artifacts follow an explicit ignore and retention policy; do not silently mix them with source changes.
4. Every wave ends committed, pushed, deployed, and classified as passed, failed, or blocked.
5. No unexplained source changes remain on main.
6. Overlapping changes are reviewed at hunk level before staging.
7. Production acceptance is performed against the deployed commit, not localhost.
8. WIP work is stored in named branches or isolated worktrees, not mixed on main.

## Release Gate

Before a wave starts, verify branch, HEAD, origin/main, deployment baseline, and dirty status. If dirty paths exist, classify them and create an isolated worktree before implementation.

## Staging Rule

Use explicit filename staging only. Never use bulk staging in a mixed worktree. Generated reports may be committed only when they are required release evidence.
