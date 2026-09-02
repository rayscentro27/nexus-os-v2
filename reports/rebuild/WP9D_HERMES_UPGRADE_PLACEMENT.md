# WP9D Hermes upgrade placement

The current Hermes executable is present at `~/.local/bin/hermes`, but a stable
version string and latest upstream version were not established without
starting an interactive/runtime process. They remain `UNKNOWN`, not guessed.

Recommended path: retain current Mac control-plane Hermes, stage any candidate
runtime on an existing Oracle worker only after a bounded compatibility test,
then run adapter/regression tests before any production cutover. No production
Hermes replacement or scheduler change was made.
