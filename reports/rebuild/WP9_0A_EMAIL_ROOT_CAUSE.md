# WP9.0A Email Root Cause

The direct Resend path used the configured key and verified sender domain, but
the send endpoint returned HTTP 403 with provider/upstream code 1010. Resend's
read-only `/domains` request returned HTTP 200 and showed `goclearonline.cc`
verified, so the failure was not proven to be a missing domain.

The existing Supabase `send-client-email` function was called incorrectly in the
previous probe: it requires a real authenticated Supabase user JWT and the
template payload (`to`, `template`, `subject`, `data`). A service-role JWT is not
a user session for the function's `auth.getUser()` check, producing HTTP 401.

Using the already-provisioned synthetic admin account and anon-key login returned
HTTP 200 with a user session. The corrected function request then returned HTTP
200 with provider ID `c704ce11-8c8e-43ae-b979-e9dc7f9ec86c`.

EMAIL_TRANSPORT_ROOT_CAUSE_AUDIT=PASS
EMAIL_EXISTING_AUTH_DISCOVERY=PASS
RESEND_403_ROOT_CAUSE=NETWORK_OR_UPSTREAM_WAF_RESTRICTION_CODE_1010_NOT_DOMAIN_PROVEN
SUPABASE_EMAIL_401_ROOT_CAUSE=WRONG_AUTH_CONTEXT_SERVICE_ROLE_IS_NOT_USER_JWT_AND_LEGACY_PAYLOAD
