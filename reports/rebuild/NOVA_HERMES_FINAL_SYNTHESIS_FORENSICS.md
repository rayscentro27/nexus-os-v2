# Hermes Nova final synthesis forensics

Campaign: HG-WP6.5-NOVA-HERMES-PRIMARY-FINAL-SYNTHESIS-AND-COMMUNICATION-OWNERSHIP-REPAIR-20260831-01  
Baseline: 0580e10  
Implementation commit: pending final commit

## Path

The canonical native path is `nova_telegram_worker._run_hermes_primary()` → the Hermes subprocess `run_shadow()` → the native `AIAgent` draft. The draft is stored in `result["final_response"]`; the worker applies `_response_integrity()` and sends that text once through `tg_send_message()`.

The final synthesis entrypoint is the existing Hermes result path, followed by the new tool-disabled `_final_presentation_prompt()` pass in `scripts/nova/nova_hermes_shadow.py`. `claim_feedback()` is the final validation entrypoint. Telegram text comes from the final presentation result, not a tool payload.

The defect was precedence and ownership: native tool/Alpha continuations produced report-shaped prose, and the worker forwarded it directly. The repair makes Nova explicitly rewrite the internal draft, supplies authoritative current-turn execution state, performs bounded claim correction without another resource call, and validates currentness assertions introduced by the final prose. Internal receipts retain evidence state, provenance, and Alpha identifiers.

No runtime/provider/model selection or custom-Nova path was changed.
