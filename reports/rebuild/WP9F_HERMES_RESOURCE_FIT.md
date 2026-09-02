# WP9F Hermes resource fit

Oracle measured capacity: 4 aarch64 vCPU, 22 GiB RAM, 5 GiB swap (unused),
7.5 GiB root free. Existing Hermes container memory limit is 4 GiB; observed
container stats were about 204 MiB / 4 GiB and 0.28% CPU at idle. The ephemeral
version/startup/shutdown proof completed in about 5.1 seconds.

`ORACLE_HERMES_RESOURCE_FIT=GOOD` for bounded browser/research/control-worker
use. Disk is the constraint: 25% free remains, so logs, profiles and artifacts
need rotation. GPU is not present/proven; generative GPU work remains out of
scope.
