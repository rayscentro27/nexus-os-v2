# No-Docker RLS Verification Plan

Generated: 2026-06-29T23:04:14.223451+00:00

- ok: true
- status: no_docker_sql_editor_path_ready
- docker_required: false
- target_project: iqjwgpnujbeoyaeuwehj
- read_only: true
- ray_review_card: Approve no-Docker RLS SQL verification in Supabase SQL Editor.
- database_write_performed: false
- external_action_performed: false

## Steps

- Open Supabase project iqjwgpnujbeoyaeuwehj → SQL Editor.
- Paste the generated read-only RLS verification packet.
- Confirm every expected table has relrowsecurity=true.
- Review policy roles, commands, permissive mode, qual and with_check expressions.
- Reject any anon/public policy or unconditional true policy.
- Save/export results without secrets and rerun the insert gate.
