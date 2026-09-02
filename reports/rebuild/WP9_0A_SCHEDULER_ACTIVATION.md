# WP9.0A Scheduler Activation

After the authenticated email and generated-report tests passed, the existing
canonical plist was installed at the user's LaunchAgents location:
`com.nexus.wp9-company-cycle.plist`.

Native launchd evidence:

- label: `com.nexus.wp9-company-cycle`
- state: loaded / not running between calendar events
- program: `/usr/local/bin/python3`
- entrypoint: `scripts/wp9_company_scheduler.py --scheduled`
- schedule: 20:00 local company cycle and 06:00 local morning report
- last exit: never exited at activation time

Temporary observability is configured for three nights. The first real calendar
trigger occurred at 20:00 local and produced cycle
`wp9-20260902T030000Z-be889fce76` with `scheduled=true`, durable start/preflight/
completion receipts, Finance rollup, and launchd exit code 0. Growth initially
failed because launchd lacked the repository Python path; Finance recorded that
failure, and the corrected bounded recovery run completed Growth successfully.
Alpha truthfully recorded `NO_MEANINGFUL_WORK`.

WP9_IMPLEMENTATION_READY=YES
WP9_CANONICAL_SCHEDULER_INSTALLED=YES
WP9_CANONICAL_SCHEDULER_LOADED=PASS
WP9_TEMPORARY_OBSERVABILITY_ACTIVATED=YES
CERTIFICATION_STATE=PENDING_NIGHT_1
WP9_FIRST_REAL_SCHEDULED_TRIGGER=PASS
WP9_FIRST_REAL_SCHEDULED_CYCLE=PASS_WITH_RECORDED_FAILURE_AND_RECOVERY
WP9_REAL_SCHEDULED_SIDE_EFFECT=PASS
WP9_UNATTENDED_EVIDENCE=PASS_FIRST_SCHEDULED_CYCLE
