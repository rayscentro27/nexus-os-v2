# Alpha Netlify Environment Import Plan

**Generated**: 2026-07-04

---

## Import Set (key names only — no values)

### Will Set
| Key | Source |
|-----|--------|
| OPENROUTER_API_KEY | Current project `.env` |
| GROQ_API_KEY | Legacy project `~/nexus-ai/.env` |
| ALPHA_OPENROUTER_MODEL | Default: `openrouter/auto` |
| ALPHA_GROQ_MODEL | Default: `llama-3.3-70b-versatile` |
| ALPHA_DEFAULT_PROVIDER | Default: `openrouter` |
| ALPHA_PROVIDER_MODE | Default: `hosted` |
| ALPHA_MAX_HOSTED_CALLS_PER_DAY | Default: `50` |
| ALPHA_REQUIRE_DEEP_APPROVAL | Default: `false` |

### Skipped
| Key | Reason |
|-----|--------|
| NOUS_API_KEY | Not found in any .env file |
| ALPHA_NOUS_MODEL | Not found, no default needed (Nous not configured) |
| SUPABASE_SERVICE_ROLE_KEY | Not on allowlist — requires separate Ray approval |
| OANDA_API_KEY | Not on allowlist |
| STRIPE_SECRET_KEY | Not on allowlist |
| RESEND_API_KEY | Not on allowlist |
| META_ACCESS_TOKEN | Not on allowlist |

---

## Priority Rules Applied

1. Current project value used for OPENROUTER_API_KEY (same as legacy — no conflict)
2. Legacy value used for GROQ_API_KEY (not in current project)
3. Empty/missing keys skipped (NOUS_API_KEY)
4. Non-allowlisted keys skipped
5. Config defaults applied for ALPHA_* settings
