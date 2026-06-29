# Resend 403 Diagnosis

Generated: 2026-06-29T23:02:46.034991+00:00

- ok: true
- status: resend_403_diagnosed_configuration_and_permission_blocker
- api_key_present: true
- http_status: 403
- provider_error_category: HTTPError
- local_code_bug_likely: false
- email_sent: false
- raw_key_included: false
- external_action_performed: false

## Likely causes

- API key is accepted by the endpoint but lacks domain-list permission, is restricted, revoked, or belongs to a different Resend account/project.
- Configured sender domain is goclearonline.cc, which does not match the intended goclearonline.com domain.
- Sender-domain verification cannot be proven with the current key/configuration.
