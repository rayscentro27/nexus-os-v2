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

Temporary observability is configured for three nights. Certification state is
durable at `PENDING_NIGHT_1`. No scheduled trigger was observed during the
short activation-session polling window; no scheduled proof is claimed.

WP9_IMPLEMENTATION_READY=YES
WP9_CANONICAL_SCHEDULER_INSTALLED=YES
WP9_CANONICAL_SCHEDULER_LOADED=PASS
WP9_TEMPORARY_OBSERVABILITY_ACTIVATED=YES
CERTIFICATION_STATE=PENDING_NIGHT_1
WP9_FIRST_REAL_SCHEDULED_TRIGGER=PENDING
