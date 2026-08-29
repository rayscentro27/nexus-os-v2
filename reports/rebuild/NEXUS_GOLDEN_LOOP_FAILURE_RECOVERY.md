# Golden Loop Failure / Recovery — 2026-08-29

Verified fail-closed cases include invalid/PII-like bridge context, malformed
bridge responses, bridge timeout/unavailable state, and executor non-zero
exit/missing output. The Python wrapper records `FAILED`, never marks a run
verified, and retains TruthKernel evidence.

The Hermes review blocker received three materially distinct corrections:
toolset minimization, isolated worker-provider routing, and bounded-token
review requests. The scoped OpenRouter route then completed the worker canary
and the real golden loop. Existing fail-closed tests cover invalid context,
malformed responses, bridge timeout/unavailable state, and executor failure;
no failure path invents success or bypasses Nexus authority.

A fresh synthetic reviewer-failure run also returned `FAIL_CLOSED` / `FAILED`
and emitted a non-success receipt; it did not mark the run verified.
