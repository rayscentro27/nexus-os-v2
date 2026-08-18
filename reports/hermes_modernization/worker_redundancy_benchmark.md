# Worker Redundancy Benchmark — Phase 13B Continuation

- Primary: Codex `AVAILABLE`
- Secondary: OpenCode `AVAILABLE`, model `opencode/mimo-v2.5-free`
- Deterministic fallback: Local worker `AVAILABLE`
- MiMo: `INSTALLED_UNPROVEN`
- Kilo: `INSTALLED_UNPROVEN`
- OpenHands: `NOT_INSTALLED`

Routing proof: Codex unavailable → OpenCode for a compatible certified task; Codex and OpenCode unavailable → local worker only for compatible deterministic tasks. Verification remains mandatory and worker self-report cannot produce PASS. Production routing was unchanged.

OpenCode telemetry: duration approximately 13 seconds, input/output/cache tokens UNKNOWN from supplied JSON evidence, provider cost $0. A local recheck timed out at 30 seconds; this did not override the successful explicit manual probe.
