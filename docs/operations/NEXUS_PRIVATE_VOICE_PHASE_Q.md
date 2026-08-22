# Nexus Private Voice Foundation — Phase Q

Status: `PARTIAL` — private local STT is implemented and smoke-tested; a
consented operator recording and authenticated browser-to-Mac transport are
not available in this certification environment.

## Boundary

Phase Q adds push-to-talk speech input only:

`admin capture → bounded voice adapter → local whisper.cpp → existing Hermes`

It does not add TTS, continuous listening, wake-word detection, WebRTC,
avatar rendering, or a public audio API. Voice uses the same Hermes and
governance path as typed input, so it gains no additional authority.

The existing Jarvis voice plan and `hermesVoiceReadyRenderer` were reused.
Hermes returns the normal screen response and the existing voice-ready text
from the same canonical response.

## whisper.cpp gate

The official upstream is [whisper.cpp](https://github.com/ggml-org/whisper.cpp),
tag `v1.9.1`, commit `f049fff95a089aa9969deb009cdd4892b3e74916` in the local
pilot checkout. Its official [license](https://github.com/ggml-org/whisper.cpp/blob/master/LICENSE)
is MIT. The project documents Apple Silicon, Accelerate, Metal, and Core ML
support in its upstream README. The current pilot host is Intel `x86_64`
macOS 12.7.6, so Apple Silicon performance is not claimed.

The runtime is isolated under `tools/voice/` and ignored by Git:

- binary: `tools/voice/runtime/whisper.cpp/build/bin/whisper-cli`
- model: `tools/voice/models/ggml-base.en.bin`
- temporary audio: `tools/voice/audio/`

The selected pilot model is `base.en` (approximately 141 MB), downloaded with
the upstream model helper from the reviewed
[whisper.cpp model source](https://huggingface.co/ggerganov/whisper.cpp).
The observed model hash is
`a03779c86df3323075f5e796cb2ce5029f00ec8869eee3fdfb897afe36c6d002`.
OpenAI’s upstream Whisper repository and model terms are MIT; model files are
never committed to this repository.

The local build completed with CMake Release mode. The host detected Metal
and Accelerate during configuration, but this Intel pilot is recorded as a
CPU/Accelerate smoke path; no Apple Silicon or GPU latency claim is made.

## Canonical contracts and limits

The adapter emits:

- `nexus.voice-input.v1`
- `nexus.voice-transcript.v1`

Audio is limited to 30 seconds and 10 MB, with a preferred duration of 15
seconds or less. One channel is expected. The request requires an explicit
consent state, bounded source, session identity, and
`external_action_performed=false`.

Raw audio is written only to a temporary file, passed to the fixed local
`whisper-cli` binary, and deleted by the temporary-directory lifecycle. Raw
audio is not placed in canonical state, reports, Mission Control, Hermes
memory, Alpha, Supabase, or Git. The transcript retains metadata only;
confidence remains null unless the provider supplies a genuine confidence
value.

## Local adapter and transport

The fixed adapter is `scripts/nexus_agent_platform/voice/local_stt.py`.
`scripts/nexus_agent_platform/voice/local_server.py` provides an optional
localhost-only endpoint at `127.0.0.1:8789/v1/voice/transcribe` with a bounded
body and optional `NEXUS_VOICE_LOCAL_TOKEN`. It exposes only
`voice.transcribe`; it is not a generic file, shell, model, or RPC endpoint.

No authenticated admin-portal-to-Mac Mini bridge was found in the existing
infrastructure. The browser component therefore fails closed when
`VITE_NEXUS_VOICE_ENDPOINT` is absent. It does not expose the Mac Mini or
invent a tunnel. The certified transport state is:

`ADMIN_TRANSPORT=LOCAL_ONLY`

`ADMIN_BROWSER_VOICE_CERTIFICATION=NOT_AVAILABLE`

The browser push-to-talk component is present in the existing admin Hermes
surface and uses `getUserMedia`/`MediaRecorder`, but live browser certification
requires a real authenticated transport and session.

## Smoke certification

The upstream JFK sample WAV was used as a clearly labeled runtime smoke test,
not as a consented Ray/operator recording. whisper.cpp produced the real
speech transcript:

> And so my fellow Americans, ask not what your country can do for you, ask
> what you can do for your country.

The sample duration was 11,000 ms; a warm local-server run took approximately
7.7 seconds. This proves the fixed local binary/model path and transcript
contract. It does not satisfy the missing consented human-operator sample, so
the final gate remains `PRIVATE_VOICE_STT_READY=PARTIAL` until such a sample
is supplied and run.

## Hermes, safety, and failure isolation

Voice transcripts enter the existing Hermes router. Safe questions such as
today’s priorities, approvals, revenue truth, growth readiness, creative
state, and creative-history queries use canonical systems. “Publish this
campaign”, charge, send, trade, and similar requests remain blocked or
approval-gated exactly as typed input. “Approve it” without an unambiguous
target returns clarification rather than mutating approval state.

If local STT is unavailable, Hermes text, Mission Control, Business Active
Operator, and Creative Studio remain available. Mission Control exposes Voice
as an optional integration with provider/model, retention, transport, and
last-error state; core health impact is `NONE`.

TTS, continuous voice, WebRTC, wake words, and avatars remain deferred.
