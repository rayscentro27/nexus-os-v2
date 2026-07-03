# Alpha Research File Adapter Validation Report

Foundation validation covers allowed directories, extensions, size bounds, sensitive path segments, route mapping, evidence quality, and immutable cloned metadata.

Expected accepted fixtures: local Markdown/JSON/TXT/CSV metadata within approved roots, under 1 MB. Expected rejection examples: `.env`, `.pem`, `.sql`, `.db`, archives/executables, oversized files, path traversal/outside roots, and paths marked client/private/secret/credential/production.

Routing checks cover opportunity, affiliate, landing, newsletter, social, trading, general research, and risky-execution-to-Ray-Review-draft behavior. Tests confirm no prohibited adapter is touched.

Status: foundation implemented; real file content ingestion not implemented or claimed.
