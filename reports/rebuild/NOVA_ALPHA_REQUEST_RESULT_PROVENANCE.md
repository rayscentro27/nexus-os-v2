# Alpha Request/Result Provenance

The native Alpha tool result now preserves:

`request_id` → `job_id` (`research_job_id`) → `result_id` (`receipt_id`) → `artifact_id` (`research_pack_ref`), plus objective, status, completion, findings/pack, and provenance.

A canonical-worker development run produced a fresh linked chain:

- request: `alpha_req_76b985700d364be59cb489abca5ad9b9`
- job: `alpha-research-a5a0d4a0d5554962`
- result/receipt: `alpha-receipt-beba2305d97a46d7`
- artifact: `alpha-pack:alpha-research-a5a0d4a0d5554962`

These are development evidence identifiers only; no Telegram certification was run.
