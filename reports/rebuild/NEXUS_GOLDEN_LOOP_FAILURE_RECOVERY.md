# Golden Loop Failure / Recovery — 2026-08-29

Verified fail-closed cases include invalid/PII-like bridge context, malformed
bridge responses, bridge timeout/unavailable state, and executor non-zero
exit/missing output. The Python wrapper records `FAILED`, never marks a run
verified, and retains TruthKernel evidence.

The Hermes review blocker received three materially distinct corrections:
toolset minimization, isolated worker-provider routing, and bounded-token
review requests. All failed without authority expansion. Per WP3 anti-loop
policy, this signature is `INSTALLATION_OR_INTEGRATION_STALLED` until a
compatible already-authorized tool-capable/provider route is available.
