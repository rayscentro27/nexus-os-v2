# Nexus Kaggle ASR worker payload

This directory contains the minimal GPU worker payload for a later bounded
Kaggle certification. It is intentionally not a scheduler, FIFO, source
registry, or second Supabase system.

The Mac acquires and normalizes audio, then supplies it as a private Kaggle
input artifact. The notebook transcribes it and emits
`/kaggle/working/nexus_asr_receipt.json`. The existing Nexus worker adapter
retrieves that receipt; the Mac-side canonical ingestion path writes and
read-verifies Supabase using the shared `MEDIA_ASR` contract.

Required input environment values are non-secret job metadata only:

- `NEXUS_JOB_ID`
- `NEXUS_QUEUE_SEQUENCE`
- `NEXUS_VIDEO_ID`
- `NEXUS_AUDIO_PATH` (defaults to `/kaggle/input/nexus-asr-audio/audio.wav`)

The notebook does not receive Supabase credentials. This keeps Supabase as
central durable state without exposing a service credential to a transient
GPU notebook. Kaggle API credentials remain in the approved local Keychain /
CLI path and are never committed here.

The existing `KaggleAdapter` remains the submission/status/output transport.
This payload is not production routing and must not be activated until a real
ASR canary, receipt retrieval, canonical write, and readback have succeeded.
