# Protected Credential Discovery

Credentials were discovered by variable-name presence only. No values were printed, copied, committed, or included in reports.

| Credential | Status | Source Category | Recovery Needed |
|---|---|---|---|
| E2E_PERSONA_A_EMAIL | configured | ignored E2E env file | no |
| E2E_PERSONA_A_PASSWORD | configured | ignored E2E env file | no |
| E2E_PERSONA_B_EMAIL | configured | ignored E2E env file | no |
| E2E_PERSONA_B_PASSWORD | configured | ignored E2E env file | no |
| E2E_PERSONA_C_EMAIL | configured | ignored E2E env file | no |
| E2E_PERSONA_C_PASSWORD | configured | ignored E2E env file | no |
| E2E_ADMIN_EMAIL | configured | ignored E2E env file | no |
| E2E_ADMIN_PASSWORD | configured | ignored E2E env file | no |
| VITE_SUPABASE_URL | configured | ignored base env file | no |
| VITE_SUPABASE_ANON_KEY | configured | ignored base env file | no |
| SUPABASE_SERVICE_ROLE_KEY | configured | ignored base env file, server-side scripts only | no |
| STRIPE_MODE | missing in active shell | owner-deferred live configuration | no live action |

Result: PASS. Synthetic credentials were available securely. No reprovisioning was required.
