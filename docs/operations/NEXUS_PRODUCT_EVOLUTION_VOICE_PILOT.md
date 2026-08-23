# Product Evolution Pilot: Voice Assistant

Status: `PARTIAL` pending genuine human microphone/wake verification and Nova
Cloudflare Access session verification.

## Contract

Outcome: Ray can turn Voice Listening on, say `Hey Nexus`, `Hey Nova`, or
`Hey Alpha`, and receive a response in the selected agent's active thread.

Acceptance: one-click Quick Voice; no second stop click; no manual Send in
Quick mode; local/private STT; automatic silence finalization; wake routing;
active-thread reuse; missing-thread creation; review mode retained; raw audio
deleted; Hermes/Nova/Alpha and governance remain separate.

Locked systems: Phase Q final-file path, local whisper.cpp, Cloudflare Access,
Nova graph/Telegram, Alpha route, canonical Hermes route, multi-chat and
multi-window state. Allowed surfaces are the global Admin Voice control,
agent dispatch adapter, tests, and operational docs.

## Architecture decision

The pilot uses the smallest reversible local design: browser `getUserMedia`
plus an `AudioContext` RMS voice-activity gate, bounded `MediaRecorder`
capture, cumulative private preview snapshots, and the existing final-file
local whisper.cpp route for authoritative text. Silence is 1.1 seconds and a
session is capped at 30 seconds. Wake routing happens from the authoritative
local transcript, so the pilot does not claim a separate always-running
keyword model. No cloud speech or wake provider is used.

Quick Voice automatically finalizes and dispatches. Review Before Send remains
available in the existing precision composer. An active pointer is maintained
per agent; a voice `new chat` command creates a new ID. A bounded 20-second
follow-up window reuses the same agent/thread when present.

## Research gate

Evaluated on 2026-08-23: whisper.cpp (reuse), sherpa-onnx keyword spotting
(WATCH), and browser/local VAD (ADOPT for pilot). sherpa-onnx supports custom
keyword spotting, but official issue evidence leaves commercial licensing for
specific pretrained models unresolved and recent issue activity includes
macOS arm64 keyword/streaming concerns. No new dependency or model was
adopted. This keeps recurring cost at `$0` and preserves rollback to Phase Q.

## Pilot critic and repair

Automated tests cover wake phrase mapping, no cloud `SpeechRecognition`, local
AudioContext ownership, bounded silence, active-thread dispatch, and source
integration. Typecheck, build, focused UI tests, and Phase Q Python tests pass.
The Nova browser transport was diagnosed: the localhost adapter, CORS, tunnel,
canonical graph, provider, and model work; a browser without a Cloudflare
Access session receives a redirect. The frontend now reports an explicit
“Nova Access authentication required” action instead of generic `Failed to
fetch`. Access remains Admin-only.

Remaining human gate: Ray must authenticate the Nova hostname in the same
authorized identity session and test real microphone/wake behavior. Synthetic
fixtures are not human certification.

