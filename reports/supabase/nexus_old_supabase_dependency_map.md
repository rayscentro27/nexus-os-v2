# Nexus Old Supabase Dependency Map

**Generated**: 2026-07-05

---

## Executive Summary

Nexus OS v2 has **no active code dependencies on an old/legacy Supabase project**. The only legacy Supabase reference (`ygqglfbhxiumqdisauar.supabase.co`) exists in historical audit reports under `reports/hermes_alpha/`, not in any active source code, configuration, or script.

---

## Legacy References Found

| File | Reference | Context | Active? |
|------|-----------|---------|---------|
| `reports/hermes_alpha/alpha_audit_conclusions.md` | `ygqglfbhxiumqdisauar.supabase.co` | Historical audit documenting old project | No |
| `reports/hermes_alpha/alpha_legacy_nexus_folder_audit.md` | `ygqglfbhxiumqdisauar.supabase.co` | Legacy folder audit | No |
| `reports/hermes_alpha/alpha_existing_asset_inventory.json` | `ygqglfbhxiumqdisauar.supabase.co` | Asset inventory referencing old project | No |
| `reports/hermes_alpha/alpha_existing_system_process_cli_audit.md` | `ygqglfbhxiumqdisauar.supabase.co` | System process audit | No |
| `scripts/ops/test_hermes_chat_live_model.py` | `{PROJECT_REF}.supabase.co` (dynamic) | Test script using dynamic project ref | No (test only) |

---

## Active Code Supabase References

All active code references point to environment variables (`VITE_SUPABASE_URL`, `SUPABASE_URL`) which are set in `.env` to the current v2 project. No hardcoded legacy URLs exist in active code.

---

## Recommendation

- **No redirect needed**: Active code already points to current v2 project via env vars
- **Legacy reports**: Can be archived or left as historical documentation
- **Old Supabase data**: If data migration from the old project is needed, it would be a separate initiative (not a code dependency)
- **Prompt 2**: No action required for old Supabase dependency removal
