# First 3 Tester Smoke Test Checklist

**Generated:** 2026-07-07

## Tester-Side Steps

- [ ] 1. Visit https://goclearonline.cc/client/login
- [ ] 2. Log in as tester (email + password)
- [ ] 3. Confirm dashboard loads
- [ ] 4. Confirm name/status/current step displays
- [ ] 5. Confirm tasks list loads
- [ ] 6. Confirm document requirements load
- [ ] 7. Confirm readiness scores load
- [ ] 8. Confirm Hermes guidance panel loads
- [ ] 9. Confirm no admin login appears on client portal
- [ ] 10. Confirm mobile layout is usable (resize browser)

## Admin-Side Steps

- [ ] 1. Visit https://goclearonline.cc/admin
- [ ] 2. Log in as admin
- [ ] 3. Navigate to Clients panel
- [ ] 4. Find tester in list
- [ ] 5. Click tester to open detail drawer
- [ ] 6. Review readiness score
- [ ] 7. Review document metadata
- [ ] 8. Review credit workflow items
- [ ] 9. Review business funding requirements
- [ ] 10. Confirm guidance is approved/client-safe
- [ ] 11. Verify storage files section shows uploaded files
- [ ] 12. Add admin note and confirm save

## Edge Cases to Test

- [ ] Login with wrong password → shows error
- [ ] Access /client/dashboard without login → redirects to /client/login
- [ ] Access /admin without login → shows admin login
- [ ] Upload document → confirm progress + success
- [ ] Preview mode → confirm demo banner + no auth required

## Expected Results

- Dashboard loads within 2 seconds
- All data sections populate
- No console errors
- No raw database errors shown to user
- Mobile layout stacks properly
