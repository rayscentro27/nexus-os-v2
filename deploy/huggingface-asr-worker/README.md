---
title: Nexus ASR Worker
emoji: 🎙️
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 6.0.0
app_file: app.py
---

# Nexus Hugging Face ASR worker

This is a stateless secondary `MEDIA_ASR` worker. It is not a queue, scheduler,
source selector, or Research decision-maker. The universal Research FIFO remains
the only work source.

Flow:

```text
Mac acquires audio → authenticated multipart request → normalize → faster-whisper
→ return transcript receipt → optional canonical Supabase write/readback → delete temp media
```

The Space uses a minimal Gradio interface and exposes the Gradio API endpoint
for `transcribe`. The existing Nexus worker token is checked from the
`X-Nexus-Worker-Token` request header when supplied by an API caller. The
private Space boundary remains the primary access control.

Required Space secrets:

- `NEXUS_WORKER_TOKEN`
- `SUPABASE_URL`
- `SUPABASE_WORKER_KEY` (narrowly scoped worker credential)

Optional:

- `HF_TOKEN` only if private model access is needed
- `ASR_MODEL` (default `tiny.en`)

The first certification sends audio acquired by the Mac. The Space does not
download YouTube media or become permanent media storage. Supabase persistence
is downstream-owned by Nexus so an already-ingested source is not duplicated.
