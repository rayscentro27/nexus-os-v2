# Alpha Environment Key Inventory

**Generated**: 2026-07-04

---

## Files Searched

### Current Project (~/nexus-os-v2)
| File | Status |
|------|--------|
| `.env` | Found |
| `.env.local` | Found |
| `.env.production` | Not found |
| `.env.netlify` | Not found |
| `netlify/.env` | Not found |
| `netlify/functions/.env` | Not found |

### Legacy Project (~/nexus-ai)
| File | Status |
|------|--------|
| `.env` | Found |
| `.env.local` | Not found |
| `.env.production` | Not found |
| Workflow `.env` files | 10 found (research_ingestion, trading_analyst, etc.) |

---

## Allowlisted Key Inventory

| Key | Current .env | Current .env.local | Legacy .env | Conflict? |
|-----|-------------|-------------------|-------------|-----------|
| OPENROUTER_API_KEY | Found, non-empty | Not found | Found, non-empty | Same value — no conflict |
| GROQ_API_KEY | Not found | Not found | Found, non-empty | No conflict (missing in current) |
| NOUS_API_KEY | Not found | Not found | Not found | Not found anywhere |
| ALPHA_OPENROUTER_MODEL | Not found | Not found | Not found | Not found anywhere |
| ALPHA_GROQ_MODEL | Not found | Not found | Not found | Not found anywhere |
| ALPHA_NOUS_MODEL | Not found | Not found | Not found | Not found anywhere |
| ALPHA_DEFAULT_PROVIDER | Not found | Not found | Not found | Not found anywhere |
| ALPHA_PROVIDER_MODE | Not found | Not found | Not found | Not found anywhere |
| ALPHA_MAX_HOSTED_CALLS_PER_DAY | Not found | Not found | Not found | Not found anywhere |
| ALPHA_REQUIRE_DEEP_APPROVAL | Not found | Not found | Not found | Not found anywhere |

---

## Notes

- OPENROUTER_API_KEY has the same value in both current and legacy .env — no conflict.
- GROQ_API_KEY exists only in legacy .env — will import from legacy.
- NOUS_API_KEY not found anywhere — skipped.
- All ALPHA_* config keys need to be created with defaults.
- Values are NEVER printed in this report.
