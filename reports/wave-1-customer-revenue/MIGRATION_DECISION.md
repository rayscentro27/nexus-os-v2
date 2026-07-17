# Migration Decision

Generated: 2026-07-17T18:58:18Z

| Migration | Decision | Remote Status | Evidence |
| --- | --- | --- | --- |
| `20260715200000_tester_invitation_system.sql` | DEFER | Local migration ID not present remotely, but required tables already exist remotely. | `supabase migration list`; remote table probes for `tester_invitations`, `payment_pilot_controls`, `invitation_events`, `invite_email_drafts`. |
| `20260716120000_enable_pilot_controls.sql` | DEFER | Local migration ID not present remotely, but singleton pilot controls already match Wave 1 required safe state. | Remote `payment_pilot_controls` has invitations/test purchases enabled; controlled live/public live/hidden pilot disabled. |

## Rationale

The remote schema contains newer objects/columns than the local local-only invitation migration, including columns used by current application code. Applying either local migration blindly would risk history drift or stale check constraints. No migration was applied in this sprint.
