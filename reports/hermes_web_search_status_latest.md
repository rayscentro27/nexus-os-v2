# Hermes Web Search Status Report

**Generated:** 2026-07-01

## Status: Not Configured

| Field | Value |
|-------|-------|
| Edge Function Exists | Yes |
| Deployed | No |
| Env Configured | No |
| VITE_HERMES_SEARCH_ENABLED | Not set |
| OPENROUTER_API_KEY | Present |
| Status | not_configured |

## Capabilities

- Web search: not_configured
- Hermes can search: No
- Hermes can fallback to static: Yes

## Blockers

1. VITE_HERMES_SEARCH_ENABLED not set in .env
2. hermes-search Edge Function exists but not deployed
3. No search API key configured in frontend

## Next Actions

1. Set VITE_HERMES_SEARCH_ENABLED=true in .env if search is desired
2. Deploy hermes-search Edge Function if safe and keys are present
3. Label as "not configured" in UI until deployed

## Notes

Web search is not configured. Hermes falls back to local context for research questions. Do not deploy hermes-search without verifying env keys are safe.
