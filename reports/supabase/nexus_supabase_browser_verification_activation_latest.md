# Nexus Supabase — Browser Verification Activation

**Generated**: 2026-07-05
**Phase**: G

## Status: ENV_PRESENT_BROWSER_EXPECTED_BROWSER_CHECK_REQUIRED

## Env Key Status

| Key | Present | Frontend Safe |
|-----|---------|---------------|
| VITE_SUPABASE_URL | YES | YES |
| VITE_SUPABASE_ANON_KEY | YES | YES |
| SUPABASE_URL | YES | Server-only |
| SUPABASE_SERVICE_ROLE_KEY | YES | Server-only (NOT in frontend) |

## Client Configuration

- File: `src/lib/supabaseClient.ts`
- `isSupabaseConfigured`: boolean (checks VITE_ keys)
- Frontend uses VITE_ keys only
- Service role key NOT in frontend

## Browser Verification Steps for Ray

### Step 1: Start Dev Server
```bash
cd ~/nexus-os-v2 && npm run dev
```

### Step 2: Open Browser
Navigate to: `http://localhost:5173`

### Step 3: Open DevTools
- Chrome: Cmd+Option+I → Network tab
- Safari: Develop → Show Web Inspector → Network tab

### Step 4: Navigate to Client Portal
Go to: `http://localhost:5173/client`

### Step 5: Check Network Requests
Filter by: your Supabase URL (from VITE_SUPABASE_URL)

Expected results:
- 200 OK = Supabase connected, anon key works
- 401 Unauthorized = anon key needs regeneration
- 403 Forbidden = RLS policy blocking (expected for unauthenticated)
- Network error = Supabase project may be paused

### Step 6: What to Look For
- Requests to `*.supabase.co` appearing in Network tab
- Response codes (200, 401, 403 are all valid — they prove connection works)
- No CORS errors in Console

### Step 7: Screenshot Checkpoints
1. Network tab showing Supabase requests
2. Response code for at least one request
3. Console tab (no red CORS errors)

## What 401/403 Means
- 401: Anon key is invalid or expired → regenerate in Supabase dashboard
- 403: RLS policy denying access → expected for unauthenticated users
- Both 401 and 403 PROVE the connection works (request reached Supabase)

## Final Status After Ray Completes Steps
- If requests appear: VERIFIED_BROWSER_READS
- If no requests appear: VERIFIED_BROWSER_ENV_ONLY
- If CORS errors: BLOCKED_WITH_REASON
