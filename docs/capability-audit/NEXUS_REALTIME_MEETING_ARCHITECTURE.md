# Nexus Real-Time Meeting Architecture

This is research only. Nexus must not join a meeting or connect a meeting bot
as part of this audit.

## Required pipeline

`meeting adapter → consent/authentication → audio ingress → streaming STT → turn manager → Hermes context retrieval → policy/approval classification → streaming TTS → optional avatar/media egress → transcript/notes → governed follow-up work → receipt`.

## Integration choices

- **Google Meet / Zoom official APIs:** preferred when they provide permitted
  bot/media access; scopes and tenant consent must be narrow.
- **Browser WebRTC:** fallback for visual participation, but higher fragility,
  browser security risk, and evidence burden.
- **Virtual audio/video devices:** isolated media worker only; never expose raw
  host devices to arbitrary tool code.

## Non-negotiable controls

- Explicit meeting-level consent and visible Nexus identity.
- No joining, speaking, recording, or follow-up without the appropriate
  authorization state.
- Participant/transcript privacy classification and retention policy.
- Prompt injection resistance: meeting content is untrusted input.
- External messages and action items become governed drafts/work orders.
- Full turn, tool, approval, and output receipts without storing unnecessary raw
  audio/video.

## Placement

The control plane and approvals stay in Nexus. Media transport and rendering
belong in a remote or isolated worker. STT can be local for sensitive meetings;
streaming TTS/avatar is likely managed or remote GPU. A provider outage must
degrade to text notes and a post-meeting work order, not fail the autonomy
stack.
