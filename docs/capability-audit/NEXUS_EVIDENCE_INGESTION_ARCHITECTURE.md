# Nexus Evidence Ingestion Pilot

Phase H adds a bounded capability adapter for document and public-web evidence acquisition.

`Nexus evidence request -> isolated adapter -> normalized evidence -> hashes/provenance -> intake handoff -> receipt -> Mission Control visibility`

The worker is `scripts/nexus_agent_platform/evidence_ingestion.py`. It is invoked once as a Python module and is not a scheduler, research brain, work-order store, approval authority, or Mission Control producer.

MarkItDown handles approved local fixtures/files. Crawl4AI handles one public URL at shallow depth when its browser dependency is available. Both run as `MAC_MINI_ISOLATED_WORKER`; the request/result envelope is transport-neutral for a future remote CPU worker.

The pilot deliberately does not activate Alpha, broaden Hermes authority, provision cloud infrastructure, or add a second research database.
