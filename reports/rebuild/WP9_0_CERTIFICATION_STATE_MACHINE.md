# WP9.0 Certification State Machine

The durable state file is `data/runtime/wp9_certification_state.json` and starts
at `PENDING_NIGHT_1`. Runtime states are `PENDING_NIGHT_1`, `PENDING_NIGHT_2`,
`PENDING_NIGHT_3`, `CERTIFIED`, `FAILED`, and `BLOCKED`. This implementation run
does not advance a night from a manual test and does not claim three-night
certification.

WP9_CERTIFICATION_STATE_MACHINE=PASS
WP9_CERTIFICATION_STATE_PERSISTENCE=PASS
WP9_AUTOMATIC_NIGHT_EVALUATION=DESIGN_PASS_PENDING_SCHEDULE
WP9_NIGHT_SUCCESS_CONTRACT=PASS_DESIGN
WP9_THREE_NIGHT_CERTIFICATION=PENDING
WP9_CODEX_NOT_RUNTIME=PASS
