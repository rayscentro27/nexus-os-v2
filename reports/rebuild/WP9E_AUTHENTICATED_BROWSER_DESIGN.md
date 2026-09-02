# WP9E authenticated browser design

`AUTHENTICATED_ORACLE_BROWSER_ARCHITECTURE=PASS_DESIGN`.

Use service API/OAuth first, then a dedicated Nexus browser profile. Do not
copy Ray's everyday browser profile. A headed intervention, if needed, must
be private/tunneled/authenticated, temporary, consent-gated for password/MFA/
OAuth, and disabled after the checkpoint. The profile is a convenience
boundary, not a security-isolation boundary.

No authenticated proof was attempted because no dedicated approved test
profile/session was identified. `AUTHENTICATED_ORACLE_BROWSER_REAL_PROOF=
WAITING_RAY_AUTH`.
