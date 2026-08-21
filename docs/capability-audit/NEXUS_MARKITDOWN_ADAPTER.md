# MarkItDown Adapter

The MarkItDown adapter accepts one explicitly supplied regular file under an approved intake root. The pilot allowlist is TXT, Markdown, HTML, PDF, DOCX, XLSX, and PPTX where the installed converter supports the format. It rejects symlinks, traversal/out-of-root paths, blocked environment/credential paths, unsupported formats, and oversized sources.

Conversion is local and bounded by a worker timeout and output limit. Source bytes produce `source_hash`; normalized line-ending/trailing-whitespace-stable content produces `material_hash`. Repeated unchanged content is reported as `DUPLICATE`; meaningful content changes produce a new material identity.

Canonical invocation:

```text
PYTHONPATH=. /tmp/nexus-evidence-venv.<id>/bin/python -m scripts.nexus_agent_platform.evidence_ingestion --file <approved-file> --allowed-root <approved-root> --root <runtime-root>
```

The pilot used synthetic non-sensitive fixtures only. No client files or external processing were used.
