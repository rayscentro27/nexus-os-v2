# WP8.11C Nova Voice

The Hermes TTS implementation was audited. It supports local NeuTTS,
KittenTTS, and Piper handlers, but the canonical Hermes environment does not
have those optional Python packages or a configured Nova voice provider. The
existing WP8.11B WAV is a synthetic composition-tone placeholder, not Nova
narration.

- `NOVA_EXISTING_VOICE_PATH_AUDITED=YES`
- `NOVA_VOICE_STATUS=NOT_CONFIGURED`
- `REAL_NOVA_AUDIO=BLOCKED`
- `NOVA_AUDIO_ARTIFACT=NONE`

No provider was enrolled or purchased. A future proof must generate a new
short audio file through a configured lawful local/provider path and record its
codec, duration, voice configuration, and receipt.

