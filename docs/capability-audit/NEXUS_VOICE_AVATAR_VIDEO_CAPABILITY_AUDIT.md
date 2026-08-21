# Nexus Voice, Avatar, and Video Capability Audit

## Separation of concerns

Hermes remains intelligence, policy, governance, and authority. Voice and
avatar systems are interfaces or renderers. They may not become operators.

## Recommendations

| Capability | Recommendation | Disposition | Location |
|---|---|---|---|
| STT | whisper.cpp local/private pilot; managed streaming only when latency wins | PILOT | Mac Mini isolated worker / hybrid |
| TTS | compare a managed streaming API with a consented local model | WATCH | Hybrid |
| Real-time voice | WebRTC/audio session adapter with Hermes turn state | WATCH | Managed media plane + Nexus adapter |
| Async avatar | evaluate one provider/model per use case; require identity consent | WATCH | Remote GPU or managed API |
| Real-time avatar | separate streaming renderer and media gateway | DEFER | Remote GPU / managed media |
| Video generation | isolated on-demand GPU; model/license review per asset | DEFER | Remote GPU |
| Video editing | Remotion for programmatic templates; OpenCut variants only as research | PILOT later | Remote CPU render worker |
| Video meeting | architecture only; official APIs/browser media plane | DEFER | Hybrid |

whisper.cpp is attractive for privacy because its project documents Apple
Silicon/Metal support and offline operation. Remotion is strong for React-based
programmatic composition, but its project warns that some commercial uses need
a company license. Coqui TTS is not a default recommendation: repository
activity and model/voice rights need a fresh legal and quality review.

## Consent and safety

Voice cloning, avatar likeness, and meeting participation require recorded
consent, identity policy, watermark/attribution policy where applicable,
disclosure to participants, retention limits, and human review for external
communications. Raw audio/video should not enter long-term Nexus logs by
default.

## Failure isolation

Audio capture, TTS, avatar rendering, video generation, and meeting media must
run outside the core process. A renderer outage becomes a bounded optional
failure; Hermes and Mission Control remain usable in text mode.
