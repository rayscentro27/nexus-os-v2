# WP9F Hermes version reconciliation

Mac local package: `0.14.0`, git `cea87d9139044870752aafdcdf9ca253049ae175`.
Oracle running package: `0.20.6`, release date 2026-08-27, commit
`5fc308a70719a83cccdbba4c0e39c23f5a8239d5`.

The WP9E `0.17.0` value was stale upstream lookup evidence, not Oracle runtime
evidence. Official upstream releases visible now include v0.18.2 (2026-07-07);
the Oracle image contains a later v0.20.6 build. The package version, release
date, CLI output, image label and running container all agree. Current official
release-page visibility is not treated as proof that a newer release than the
Oracle image exists.

`VERSION_RECONCILIATION=MAC_BEHIND;ORACLE_0_20_6_PROVEN;UPSTREAM_PAGE_NOT_SHOWING_NEWER_THAN_ORACLE_IMAGE`.
Recommendation: retain Oracle 0.20.6 as a proven worker and stage any Mac
upgrade separately.
