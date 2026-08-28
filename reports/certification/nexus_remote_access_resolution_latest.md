# Nexus Remote-Aware Access Resolution

This redacted report records access location, not credential values.

| Capability | Access state | Execution location | Resolution | Local secret required |
|---|---|---|---|---:|
| `voice.transport` | `AVAILABLE_REMOTE_NETLIFY` | Netlify server | same-origin `/.netlify/functions/voice-relay` | No |
| `model.groq` | `AVAILABLE_REMOTE_NETLIFY` | Netlify server | `/.netlify/functions/alpha-provider` | No |
| `model.openrouter` | `AVAILABLE_REMOTE_NETLIFY` | Netlify server | `/.netlify/functions/alpha-provider` | No |
| `google.workspace` | `AVAILABLE_LOCAL` | Mac Keychain/runtime | existing local OAuth path | No new secret |

Voice browser components now use the same-origin relay unconditionally. Cloudflare
Access credentials remain server-side Netlify configuration; no `VITE_` copy or
local credential provisioning was performed. Groq remains remote-configured and
was not copied locally. Provider health is `CONFIGURED_UNTESTED` in this audit;
no paid model call was made.

Active Operator remains paused. No production deployment, email, social action,
payment, credential rotation, or trading action occurred.
