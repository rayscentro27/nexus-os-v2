# Oracle Hermes Deployment Attempt — 2026-08-29

`DEPLOYMENT_GATE=HG-WP2-B-ORACLE-HERMES-DEPLOY-20260829-05`
`GATE_VERIFICATION=PASS`
`API_KEY_PREEXISTED=YES`
`API_KEY_CREATED_THIS_RUN=NO`
`CONTAINER_CREATED=YES`
`CONTAINER_START=SUPERVISOR_STARTED_THEN_EXITED_137`
`CONTAINER_ROLLBACK=YES`
`ORACLE_HERMES_INSTALLED=NO`
`ORACLE_HERMES_RUNNING=NO`

The exact replacement command was executed without `--cpus=2`. The official
pinned ARM64 image was present and the container was created with host
networking, the approved memory limit, the isolated `/opt/data` mount, and no
privileged mode. The image setup phase initialized state and bundled skills,
then the supervised gateway exited with status 137 before opening port 8642.

No host OOM, kernel OOM event, memory pressure, or swap pressure was observed.
The exact cause of the exit-137 shutdown is therefore not proven by this
attempt. No Hermes API/auth/provider/runtime certification was claimed. The
failed container was removed under the gate rollback; isolated data/config and
the protected API-key file were preserved. Ollama and SearXNG remained healthy.

No public listener, bridge, Telegram action, Active Operator action, or
existing-service restart occurred. The approved gate must not be retried until
the startup condition is diagnosed and a new exact gate is approved.
