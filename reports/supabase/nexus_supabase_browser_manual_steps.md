# Nexus Supabase — Manual Browser Verification Steps

**Generated**: 2026-07-05

## Quick Verification (2 minutes)

1. `cd ~/nexus-os-v2 && npm run dev`
2. Open `http://localhost:5173/client`
3. Open DevTools → Network tab
4. Look for requests to `*.supabase.co`
5. Check response codes (200/401/403 = connected)

## What You're Proving
- Frontend can reach Supabase
- Anon key is valid
- RLS policies are active
- No CORS issues

## If It Works
Supabase is live for reads. Writes need migration approval.
