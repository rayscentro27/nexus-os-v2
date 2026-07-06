# GoClear Browser Verification

**Date**: 2026-07-06

---

## Automated Browser Testing

**Status**: NOT AVAILABLE

No Playwright, Cypress, or other browser test tooling is configured in this repo.

## Manual Test Checklist

### Prerequisites
1. Dev server running: `npm run dev`
2. Supabase configured: `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` in `.env`
3. Browser open at `http://localhost:5173`

### Test 1: Landing Page
| Step | Expected | How to Verify |
|------|----------|---------------|
| Visit `/goclear` | Landing page loads | Hero, features, steps, promo visible |
| Click "Sign Up" | Navigates to `/goclear/signup` | URL changes |
| Click "Login" | Navigates to `/goclear/login` | URL changes |

### Test 2: Signup Flow
| Step | Expected | How to Verify |
|------|----------|---------------|
| Visit `/goclear/signup` | Form loads | All fields visible |
| Leave fields empty, click submit | Validation errors | Required field errors |
| Enter mismatched passwords | "Passwords do not match" | Error message |
| Enter weak password | Password requirements shown | Checklist items |
| Enter valid data, check ToS | Button enables | Can submit |
| Submit with valid data | "Check Your Email" page | Confirmation message |
| **If Supabase not configured** | Warning shown | "Supabase not configured" message |

### Test 3: Login Flow
| Step | Expected | How to Verify |
|------|----------|---------------|
| Visit `/goclear/login` | Form loads | Email + password fields |
| Enter wrong credentials | Error message | "Invalid login credentials" |
| Enter correct credentials | Redirect to `/client` | URL changes to `/client` |
| Click "Forgot password?" | Reset form shown | Email-only form |
| Submit reset with valid email | Success message | "If this email is registered…" |
| **If Supabase not configured** | Warning shown | "Supabase not configured" message |

### Test 4: Session Persistence
| Step | Expected | How to Verify |
|------|----------|---------------|
| Login successfully | Redirect to `/client` | URL is `/client` |
| Refresh page | Session persists | Still on `/client`, not redirected to login |
| Close browser, reopen | Session persists | Navigate to `/client` directly |
| Check localStorage | Supabase session exists | `sb-*` key in localStorage |

### Test 5: Client Portal Access
| Step | Expected | How to Verify |
|------|----------|---------------|
| Visit `/client` without login | Shows portal (NO auth gate) | Mock data visible |
| Login, then visit `/client` | Shows portal | Same mock data |
| Click journey steps | Navigation works | URL changes, content updates |
| Click "Request Review" | Navigates to review page | URL changes |

### Test 6: Console/Network
| Step | Expected | How to Verify |
|------|----------|---------------|
| Open browser console | No errors | Clean console |
| Open Network tab | No 401/403 errors | Expected requests only |
| Check CORS | No CORS errors | Supabase URL allowed |

## Expected Supabase Dashboard Verification

1. **Authentication → Users**: New user appears after signup
2. **Authentication → Users → User**: `raw_user_meta_data` contains `full_name`, `business_name`
3. **Authentication → Logs**: Login/signup events logged
4. **Database → Tables**: No `tenant_memberships` row (no trigger)
5. **Database → RLS**: Policies exist but are DRAFT

## Known Issues (will be found during testing)

1. `/client` accessible without login (no auth gate)
2. No profile/membership row created on signup
3. Client portal shows mock data regardless of user
4. No logout button in client portal

## Status: MANUAL TEST REQUIRED

Automated testing not available. Manual checklist provided above.
