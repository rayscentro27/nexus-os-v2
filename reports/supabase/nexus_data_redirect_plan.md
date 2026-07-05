# Nexus Data Redirect Plan

**Generated**: 2026-07-05

---

## Executive Summary

No data redirects are needed. All active Nexus OS v2 code paths use environment variables that point to the current v2 Supabase project. There are no hardcoded legacy Supabase URLs in active code.

---

## Current Data Flow

```
Frontend (browser)
  └─ src/lib/supabaseClient.ts
       └─ VITE_SUPABASE_URL + VITE_SUPABASE_ANON_KEY
            └─ Current Nexus OS v2 Supabase project

Server-side (Python scripts)
  └─ SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY
       └─ Current Nexus OS v2 Supabase project

Edge Functions (Deno)
  └─ Run inside Supabase runtime
       └─ Current project by deployment

Netlify Functions
  └─ No Supabase dependency (Alpha provider/search/url-review)
```

---

## Redirect Requirements

| Source | Target | Needed? | Reason |
|--------|--------|---------|--------|
| Old `ygqglfbhxiumqdisauar.supabase.co` | Current v2 project | No | Not referenced in active code |
| Frontend env vars | Current v2 | Already done | `.env` contains current values |
| Server env vars | Current v2 | Already done | `.env` contains current values |
| Edge functions | Current v2 | N/A | Deployed to current project |

---

## If Old Data Migration Is Needed (Future)

If Ray wants to migrate data from the old Supabase project to the current v2:

1. Export data from old project via Supabase dashboard or CLI
2. Map old table names to new schema (77 tables defined)
3. Use `scripts/supabase/seed_static_data_to_supabase.py` pattern for bulk import
4. Verify RLS policies allow the imported data
5. Test with `supabase` CLI locally before production push

**This is a separate initiative and not required for Prompt 2 activation.**

---

## Recommendation

- **Prompt 2**: No data redirect work needed
- **Future**: If old Supabase project data is valuable, create a dedicated migration script
- **Current state**: All data paths are clean and point to v2
