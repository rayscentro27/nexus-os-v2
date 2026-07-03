# Alpha Research File Adapter Allowed Sources

Allowed directories:

- `reports/hermes_alpha/`
- `reports/manual_publish/`
- `data/exports/notebooklm/`
- `data/sources/notebooklm_exports/`
- `data/sources/youtube_transcripts/`
- `hermes_alpha/evaluations/fixtures/`

Allowed extensions: `.md`, `.txt`, `.json`, `.csv`. Maximum size: 1,000,000 bytes.

Rejected types include environment/key/certificate/database/SQL/executable/archive files. Paths containing client, secret, credential, service-role, production, or private markers are rejected. Canonical filesystem containment, content parsing, hashes, prompt-injection scanning, and provenance checks remain next-phase requirements before real reads.
