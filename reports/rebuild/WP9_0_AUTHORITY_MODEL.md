# WP9.0 Authority Model

The cycle authority is `INTERNAL_ONLY` with zero new paid spend. Payments, bank
transfers, subscriptions, ad spend, social publishing, outreach, client
production mutation, and live trading are false in every cycle receipt.

The global kill switch is `configs/wp9_scheduler.json`:
set `kill_switch.active` to `true` to fail closed. Department switches are in
the same file under `departments.<NAME>.enabled`. These controls are not loaded
into launchd until the email gate is resolved.

WP9_AUTHORITY_BOUNDARY=PASS
WP9_ZERO_NEW_SPEND_POLICY=PASS
WP9_GLOBAL_KILL_SWITCH=PASS
WP9_DEPARTMENT_DISABLE_SWITCHES=PASS
WP9_ORACLE_NOT_CORE_DEPENDENCY=PASS
WP9_OMNIROUTE_STATUS=REFERENCE_ONLY
