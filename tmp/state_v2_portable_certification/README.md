# Portable Research State v2 Certification Bundle

Run from this directory with a compatible Python 3.11+ interpreter:

```sh
python3 runner.py
```

The runner creates a temporary isolated certification root and executes exactly
the 25 existing State v2 contract functions. It
uses a tiny local pytest-API shim for `raises`, `fail`, `monkeypatch`, and
`tmp_path`; it performs no test discovery. SQLite and Python standard library
are the only runtime requirements. Production Supabase is replaced by an
offline adapter that rejects network use. No credentials, production state,
legacy ledger, Phase 5 live state, or provider executable is included.

The included Phase 5 file is a lineage fixture only. It is not a live case.
