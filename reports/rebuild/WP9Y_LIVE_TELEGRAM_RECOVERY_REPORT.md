# WP9Y Live Telegram Recovery Report

## Executive Result

The real WP9X human update was found in the Nova bot queue and was accepted by
the Mac worker.  It created mission `nova_20260903T003008_590357326`, reached
the Oracle path, and then remained incomplete.  The worker was left resident
as a `--once` process, preventing normal launchd interval recovery.  The
accepted mission was resumed using its original update ID and canonical
session, and one outbound Telegram response was accepted with message ID
`1152`.

The repair adds bounded outer supervision to the launchd runner and resumes
recent `AUTHORIZED` missions that have no delivery record.  No Telegram token,
bot identity, polling configuration, or second responder was introduced.

## Human Event Evidence

- `HUMAN_MESSAGE_FOUND=YES`
- `TELEGRAM_UPDATE_ID=590357326`
- Human sender/chat: allowlisted Ray identity, chat `1288928049`.
- Telegram Bot API showed the exact token-bearing message pending for
  `@HermesNova27bot`; no webhook was configured.
- The worker log recorded the exact incoming token at
  `2026-09-03T00:30:00.492206Z`.
- Mission record persisted the full message and `AUTHORIZED` state at
  `2026-09-03T00:30:15.787544Z`.
- No prior delivery record existed before recovery.

## T1-T20 Trace

| Stage | Result | Evidence |
|---|---|---|
| T1 Telegram update exists | PASS_REAL | Bot API pending update `590357326`; exact token matched |
| T2 Mac poller received it | PASS_REAL | `nova_telegram.log` incoming record |
| T3 authorization passed | PASS_REAL | persisted mission status `AUTHORIZED` |
| T4 dedup accepted it | PASS_REAL | no prior delivery record; mission created |
| T5 session mapping resolved | PASS_REAL | canonical session `nova-telegram-primary-1288928049` |
| T6 oracle selector chosen | PASS_REAL | WP9X selector and Oracle branch in worker |
| T7 bridge invoked | PASS_REAL | Oracle adapter resumed with original request ID |
| T8 SSH connection established | PASS_REAL | recovered adapter completed against Oracle |
| T9 Podman target reached | PASS_REAL | adapter target is `nexus-hermes-0206`; recovered result returned |
| T10 Hermes 0.20.6 invoked | PASS_REAL | recovered runtime envelope |
| T11 nova_nexus loaded | PASS_REAL | recovered runtime envelope |
| T12 model request began | PASS_REAL | real MCP/system-health telemetry |
| T13 tool activity completed | PASS_REAL | system-health and business-state telemetry completed |
| T14 Hermes final text returned | FAIL on original attempt; PASS_REAL on resume | original process had no completion; resumed adapter returned in 23,969 ms |
| T15 bridge parsed response | PASS_REAL | structured adapter result |
| T16 worker received response | PASS_REAL | recovery process received `SUCCEEDED` |
| T17 executive formatting completed | PASS_REAL | bounded Telegram response envelope |
| T18 outbound send attempted | PASS_REAL | delivery record attempt 1 |
| T19 Telegram API accepted response | PASS_REAL | delivery state `DELIVERED`, message ID `1152` |
| T20 Ray-visible response produced | UNKNOWN | API acceptance is proven; visual client receipt is not observable programmatically |

`FIRST_FAILED_STAGE=T14` for the original processing attempt.  The practical
root cause was an unbounded resident one-shot lifecycle around an incomplete
Oracle execution, combined with no startup resume for an already-accepted
mission.

## First Failed Stage

`T14` — the original worker never returned a final Oracle response envelope.
The mission remained `AUTHORIZED`, with no delivery record and the offset still
at `590357325`.

## Root Cause

`ORACLE_EXECUTION_DID_NOT_COMPLETE_BEFORE_WORKER_RECOVERY_AND_ACCEPTED_MISSION_HAD_NO_RESUME_PATH`.

Evidence distinguishes this from Telegram authorization or an absent event:
the message was accepted, real MCP activity occurred, but no Hermes completion,
delivery, or offset advancement followed.  The live `--once` process remained
resident under launchd.  A fresh bounded adapter invocation completed the same
request successfully in 23,969 ms.

## Repair

1. Added `_resume_authorized_missions()` to
   `scripts/nova/nova_telegram_worker.py`. It resumes only recent persisted
   `AUTHORIZED` missions without a delivery record, reuses the original update
   ID/mission/session identity, and routes through the existing worker path.
2. Added a 300-second outer deadline to
   `scripts/ops/run_nova_with_runtime_env.sh` using the existing Perl runtime
   available on macOS. This keeps launchd supervision effective when an inner
   network/library call fails to honor its timeout.
3. Recovered the original accepted mission; no new inbound Telegram event was
   fabricated and no second response was sent.

## Original Event Recovery

`ORIGINAL_HUMAN_EVENT_RECOVERABLE=YES`

`ORIGINAL_HUMAN_EVENT_RESUMED=YES`

The mission was durably present with the original message, update ID, chat,
user, and correlation ID.  Recovery produced one delivery record and one
Telegram message ID (`1152`).

## Oracle Runtime Identity

- Host: ORACLE
- Hermes: 0.20.6
- Profile: `nova_nexus`
- Provider/model: OpenRouter / `openai/gpt-4o-mini`
- MCP activity: real Nexus system-health and business-state reads

## Session / Dedup

The resumed invocation reused `nova-telegram-primary-1288928049` and request
identity `telegram-590357326`.  The original mission had no prior delivery;
the resulting delivery record is terminal `DELIVERED` with one attempt and one
message ID.  No duplicate tool, specialist, or Telegram response was observed.

## Live Telegram Response

Telegram accepted the outbound response at approximately
`2026-09-03T00:41:37Z`.  The response included current system health, the
highest-priority queued Voice repair item, Alpha availability, and a verified
Oracle runtime footer.

The model prose also contained an incorrect local Python-version statement and
was not fully reliable about Finance availability.  Therefore executive
quality is not certified as fully passing even though the runtime envelope and
outbound delivery were correct.

## Executive Response Quality

`LIVE_RESPONSE_EXECUTIVE_QUALITY=FAIL` due to the contradictory runtime-version
sentence in the model-generated text.  The response was mobile-sized and did
not expose secrets or schema dumps, but the contradiction requires a later
formatter/provenance-quality repair before a final WP9 quality certification.

## Regression

- Original human event: received, authorized, resumed, delivered once.
- Oracle response: `SUCCEEDED`, 23,969 ms on resumed execution.
- Delivery: `DELIVERED`, Telegram message ID `1152`, one attempt.
- Worker lifecycle repair: bounded 300-second outer deadline plus persisted
  accepted-mission resume.
- Existing WP9X direct bridge and runtime evidence remain intact.

## Security

No secrets were printed.  Existing token references and SSH key paths were not
changed.  No bot API call was used to fabricate inbound traffic.

## Git

The report and narrowly scoped worker/runner repair are the only intended WP9Y
changes.  Unrelated pre-existing worktree entries were preserved.

## Remaining External Blockers

Programmatic evidence proves Telegram API acceptance, but cannot prove that Ray
visually opened the Telegram client.  The generated response also needs a
small provenance-quality correction before claiming perfect executive answer
quality.  No additional human message is required to recover the original
accepted event.

## Final Status

`WP9Y=PARTIAL_HUMAN_ACTION_REQUIRED`

The real human event completed through Oracle Hermes and Telegram delivery, but
strict certification remains partial because visual receipt is not observable
from the runtime and the generated text contained a contradictory version
claim.  WP9 remains `RETRY_NIGHT_1`.
