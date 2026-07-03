# Alpha Research File Adapter Contract

`AlphaResearchFileAdapter` accepts metadata for local reports, NotebookLM exports, YouTube metadata, transcripts, manual notes, strategy notes, opportunity reports, and marketing research. Phase 1 validates path/type and returns cloned metadata; it does not read files automatically.

Allowed roots: `reports/`, `data/exports/notebooklm/`, and `data/sources/youtube_transcripts/`. Block paths suggesting client data, environment/secrets, credentials, service keys, or production material. Future reads require size/type limits, canonical-path containment, hash, UTF-8/text parsing, prompt-injection labeling, provenance, license/terms, and explicit sensitivity/routing.

Blocked capabilities: Supabase/database access, Nexus client context, credentials, production data, broker execution, live/funded trading, email, publish, charge, or mutation. Adapter evidence never becomes source authority and is not automatically promoted to memory.
