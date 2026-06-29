# Today Continuous Ops Activation

Generated: 2026-06-29T16:42:16.543997+00:00

- ok: true
- status: bounded_internal_running
- started: true
- tmux_session: nexus_today_ops
- command: python3 scripts/activation/run_nexus_continuous_loop.py --interval-minutes 30 --max-cycles 8 --json --safe-internal --local-only --feedback-enabled
- heartbeat_path: reports/runtime/continuous_loop_status_latest.json
- stop_command: tmux kill-session -t nexus_today_ops
- external_action_performed: false

## Will do

- safe internal activation
- feedback intake
- reports/exports
- Hermes brief
- heartbeat

## Will not do

- publish
- send messages
- contact clients/bureaus/lenders
- insert live Supabase data
- place trades
- spend money
