# WP9P Final Report

## Executive Result

`WP9P=PARTIAL`. The historical Oracle 2/10 failure was not reproduced in the
current bounded bridge window: the existing Oracle Hermes 0.20.6 route returned
20/20 valid sentinel responses. Direct Mac OpenRouter also returned 5/5. This
is strong comparative evidence, but it does not prove that the earlier
model-driven MCP/specialist path is permanently reliable, because the bridge
probe is an OpenAI-compatible advisory request rather than a full Hermes tool
loop. Telegram was deliberately not changed.

## Starting State

START_HEAD=`5cde38bb916b41284210aacae1e4a65cb0745e99`
ORIGIN_MAIN_HEAD=`5cde38bb916b41284210aacae1e4a65cb0745e99`
BRANCH=`main`
WORKTREE_ENTRY_COUNT_BEFORE=574
WP9_CERTIFICATION_STATE_BEFORE=`RETRY_NIGHT_1`

The working tree contained 574 entries, including unrelated reports and
runtime receipts. They were not staged or modified for WP9P.

## Exact Failing Execution Path

Historical path: Nexus `OracleHermesBridge` on the Mac control plane → loopback
SSH forward `127.0.0.1:18642` → Oracle Hermes 0.20.6 API → OpenRouter →
`openai/gpt-4o-mini` → non-streaming JSON response → bridge result extraction.
The bridge uses `httpx.request`, a caller timeout, `stream=false`, and at most
one transient retry. WP9O failures were `ReadTimeout` while reading the
upstream Hermes/OpenRouter result.

Current Oracle container evidence: `nexus-hermes-0206` is running from the
existing NousResearch image digest; it has a 4 GiB memory limit and no CPU
quota (`NanoCpus=0`). Its logs still report that `nova_nexus` is skipped as a
secondary API profile while multiplex mode is enabled. A bounded CLI probe
using the profile returned generic W-9 content, not Nexus state. This means
profile canonicality remains unresolved even though the API bridge returned
valid sentinel responses.

## Network Latency Decomposition

Mac direct OpenRouter `curl -w` probes, same model and non-streaming sentinel:

| Run | DNS | Connect | TLS | TTFB | Total |
|---:|---:|---:|---:|---:|---:|
| 1 | 0.004s | 0.024s | 0.049s | 1.065s | 1.309s |
| 2 | 0.003s | 0.026s | 0.059s | 0.846s | 1.069s |
| 3 | 0.002s | 0.021s | 0.045s | 1.091s | 1.351s |

Oracle Hermes bridge probes cannot expose provider DNS/TCP/TLS separately
through its API response. Their end-to-end Mac→tunnel→Hermes→provider timing
was 3.799–9.320s for the first five probes and 1.188–8.756s in the 20-run
window. All 20 completed before the 20s per-attempt bound. The dominant
historical signal remains upstream response-read latency, not Mac DNS/TLS.

## Mac vs Oracle A/B

`MAC_ORACLE_AB=PASS_REAL`. Same model, provider, sentinel prompt, and bounded
request policy were used.

| Host/path | Runs | Valid | Success | Observed timing |
|---|---:|---:|---:|---|
| Mac direct OpenRouter | 5 | 5 | 100% | 1.069–13.239s; median approximately 1.4s |
| Oracle Hermes bridge | 5 | 5 | 100% | 3.799–9.320s; median approximately 5.2s |

The direct Mac route is faster in this sample. The Oracle route adds Hermes
and tunnel overhead, but the sample does not reproduce WP9O's 90s timeout
pattern. Classification: `INCONCLUSIVE_FOR_PERMANENT_ROOT_CAUSE`, with a
current measured advantage for Mac direct provider access.

## Provider / Model Comparison

The only zero-new-spend route tested in this package was the already authorized
OpenRouter `openai/gpt-4o-mini` route. No additional model was invoked because
the available OpenRouter alternatives could create metered usage and the
mission forbids new spend. The current route was valid in both five-run A/B
and 20-run Oracle bridge samples.

## OpenRouter Analysis

Mac direct responses identified the selected upstream as `Azure`. Oracle
Hermes responses exposed the model but not provider metadata. No evidence in
the bounded current sample proves a changing upstream provider, fallback loop,
or rate-limit response. Historical failures remain consistent with variable
upstream queue/TTFB behavior, but cannot be narrowed further from the current
Hermes API boundary.

## HTTP Client Analysis

The Nexus bridge creates a fresh `httpx` request for each call, uses
non-streaming mode, and has a bounded caller timeout. It has one retry only for
transient read/connect errors. No speculative pooling, IPv6, proxy, or timeout
inflation change was made. The current code fails closed and records
`bridge_attempts` on successful and failed responses.

## Root Cause

`UPSTREAM_ORACLE_OPENROUTER_READ_LATENCY` remains the best evidence-backed
historical classification. Current 20/20 success means it is intermittent or
environment/provider-state dependent, not continuously active. The separate
Oracle profile binding warning is a real configuration/canonicality defect and
must be repaired before claiming a production Nova route.

## Production Routing Decision

Do not promote Oracle as the primary production execution path from this
package. For interactive reliability, measured evidence currently favors the
Mac direct OpenRouter path. Oracle remains a useful bounded worker/fallback
candidate, but requires a fresh full Hermes tool-loop certification after its
profile binding is corrected. No routing cutover was performed.

## Repair Implemented

No speculative networking repair was committed. The existing WP9O bounded
one-retry/attempt-provenance behavior was exercised and verified. The measured
result did not justify changing client pooling, timeout, provider, or model.

## 20-Run Reliability Certification

The 20-run bounded Oracle bridge certification completed `20/20` valid
sentinels, `0` timeouts, and `0` retries. Median observed duration was
`4.646s`; maximum was `8.756s`. This is `RAW_PRIMARY_SUCCESS=20/20` for the
tested advisory bridge route and `USER_VISIBLE_SUCCESS=20/20` for that route.
It is not certification of the full model-driven single-tool/MCP route.

## Failover Proof

`FAILOVER_RECOVERY=NOT_RUN`. WP9P did not induce an Oracle outage or alter the
Telegram runtime. No failover claim is made.

## Session Continuity

`SESSION_CONTINUITY=NOT_RUN`. The bridge probe has no persistent conversational
session contract; a successful stateless response cannot prove continuity.

## Tests

- Oracle bridge, WP9D, and WP9E focused tests: `17 passed`.
- Real Mac direct OpenRouter A/B: `5/5` valid.
- Real Oracle Hermes bridge A/B: `5/5` valid.
- Real Oracle Hermes bridge bounded reliability: `20/20` valid.
- Canonical build: `PASS_EXIT_0` (Tailwind completed after a bounded wait;
  Vite produced the production bundle).

## Secret Scan

`PASS` for intended WP9P artifacts; no credential values were printed or
written to the report.

## Git

Only this WP9P report is intended for commit. Existing unrelated worktree
entries were preserved.

IMPLEMENTATION_HEAD=`5cde38bb916b41284210aacae1e4a65cb0745e99`
REPORT_COMMIT=`RECORDED_AFTER_COMMIT`
VERIFIED_ORIGIN_MAIN_AFTER_REPORT=`RECORDED_AFTER_PUSH`
PUSHED=`YES`
WORKTREE_ENTRY_COUNT_AFTER=575
UNRELATED_EXISTING_CHANGES_PRESERVED=YES

Git commit self-reference is impossible: the final report's own content
changes its commit hash. The finalization procedure records the commit that
introduced the report and a subsequent verified origin head after final report
metadata is committed.

## Remaining WP9 Blockers

1. Full model-driven Oracle Hermes tool-loop reliability remains unproven.
2. Oracle `nova_nexus` profile canonical binding emits a multiplex warning and
   the CLI probe did not demonstrate Nexus context.
3. Session continuity and real failover/recovery remain unproven.
4. Telegram cutover and human-originated Telegram proof remain intentionally
   out of scope for WP9P.

## Final Status

WP9P=PARTIAL
ROOT_CAUSE=UPSTREAM_ORACLE_OPENROUTER_READ_LATENCY_INTERMITTENT_CURRENT_WINDOW_NOT_REPRODUCED
MAC_SUCCESS_RATE=5/5 (100%)
ORACLE_SUCCESS_RATE=5/5 A/B; 20/20 bounded bridge certification
SELECTED_PRIMARY_HOST=MAC_CONTROL_PLANE
SELECTED_PRIMARY_PROVIDER=OPENROUTER
SELECTED_PRIMARY_MODEL=openai/gpt-4o-mini
FALLBACK_CONFIGURED=NO
RAW_PRIMARY_SUCCESS=20/20 (tested Oracle bridge route)
USER_VISIBLE_SUCCESS=20/20 (tested Oracle bridge route)
SINGLE_TOOL_RELIABILITY=FAIL_FULL_TOOL_LOOP_NOT_PROVEN
FAILOVER_RECOVERY=NOT_RUN
SESSION_CONTINUITY=NOT_RUN
TELEGRAM_READY=NO
TELEGRAM_CUTOVER=NO
WP9=RETRY_NIGHT_1
