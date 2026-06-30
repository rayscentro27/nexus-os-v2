# Nexus Tool Access Registry

Generated: 2026-06-30T00:05:19.138503+00:00

- ok: true
- status: tool_access_validated
- tools_validated: 42
- default_deny_external: true
- blocked_command_rules: 8
- external_action_performed: false

## Safety policy

- **version:** 1
- **global_blocked_commands:** ["stripe --live", "supabase db reset --linked", "supabase db push --include-all", "oanda live order", "yt-dlp video download", "yt-dlp audio download", "git add .env", "service role in frontend"]
- **approval_required_actions:** ["external writes", "payments confirmation", "email sending", "social publishing", "database insertion", "trading orders", "permanent scheduler installation"]
- **default_external_action_allowed:** False
