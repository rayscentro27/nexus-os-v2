# WP9.1 Night 1 Forensic Audit

Window: 2026-09-01 19:00 through 2026-09-02 07:00, America/Phoenix.

## Scheduler and cycles

The single launchd job `com.nexus.wp9-company-cycle` produced one autonomous
company-cycle trigger at 20:00 local: `wp9-20260902T030000Z-be889fce76`.
Launchd evidence is `reports/runtime/wp9/company_cycle_launchd.log`; the
process completed at 20:00:16 local-equivalent UTC 03:00:16 with exit code 0.
The 06:00 launchd invocation also ran the morning-report branch at
2026-09-02T13:00:00Z. It was not a company-cycle trigger.

Manual/setup cycles and transport tests in the window were retained as
separate evidence and are not counted as autonomous scheduled work:
`021941`, `021958`, `022535`, and `030352` UTC cycle records were manual.

## Scheduled work-order forensics

The real scheduled cycle invoked six internal work orders:

| Department | Result | Evidence/output |
|---|---|---|
| Nova | COMPLETED | cycle-state assessment |
| Finance | COMPLETED | Finance preflight/postrun and ledger receipt |
| Alpha | NO_MEANINGFUL_WORK | no new evidence; no artifact claimed |
| Creative | COMPLETED | internal creative queue/report output |
| Growth | FAILED | launchd environment lacked `PYTHONPATH` |
| Trading | COMPLETED | bounded paper/research readiness output; no orders |

The scheduled cycle persisted start, preflight, completion, Finance receipts,
and company rollup. Cash was `$0.00`; compute was `9.471` minutes; storage,
free-credit, quota, and replacement-cost values were recorded according to
the existing actual/unknown policy. No publication, payment, ad spend, client
mutation, or live trading occurred.

The Growth failure was diagnosed and repaired by adding the repository scripts
directory to the production subprocess `PYTHONPATH`. A subsequent bounded
manual recovery completed Growth without duplicating side effects. This does
not turn the original scheduled cycle into a perfect night; it is recorded as
failure/recovery evidence.

## Certification decision

The 06:00 report artifact and email receipt exist, but the email provider
receipt says only `PROVIDER_QUEUED`; inbox delivery was not confirmed. The
original report also contained placeholder-level content rather than an
executive account of the night. Night 1 therefore requires retry and is not
retroactively marked PASS. Durable state was corrected to `RETRY_NIGHT_1`.
