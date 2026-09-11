# Nexus durable continuation protocol

The canonical resume state is `state/nexus_continuation/ACTIVE.json`. It is
repository-backed, nonsecret, and must be updated before a voluntary stop.

Use:

```sh
python3 scripts/continue_nexus.py
```

The operator phrase is `CONTINUE NEXUS`. A new session loads the checkpoint,
then checks live runtime state before acting. `scripts/continue_nexus.py
self-test` proves checkpoint persistence and reload without changing active
work.

Each checkpoint carries the current objective, last verified action, changed
files, tests, deployments, failure/root cause, next machine action, Ray queue,
external boundaries, and resume point. Secrets and tokens are prohibited.

Before committing a task, stage only the task files and this checkpoint. Never
use `git add .`, reset, clean, or restore unrelated work.
