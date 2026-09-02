# WP9F Oracle Hermes forensic audit

Baseline: `218a7c853a93195c24cf66b11cc419a7ecf9b228`; WP9 state at start and
end: `RETRY_NIGHT_1`.

Real Oracle evidence:

- `nexus-hermes-0206` is running, created 2026-08-29, image digest
  `sha256:e3f4f0679f15556d5e09369cc36bf1074351b2d37bdd672dae593dfd07495180`.
- Image label revision is `5fc308a70719a83cccdbba4c0e39c23f5a8239d5`.
- In-container package/version command reports Hermes Agent `0.20.6`
  (2026.8.27), upstream `5fc308a7`.
- No other Hermes image/container was present; no stopped staging container
  remained after probes.
- Existing unit: `~/.config/containers/systemd/nexus-hermes-0206.container`;
  rootless Podman, host network, 4 GiB memory, no CPU quota, `/opt/data`
  bound to the existing `nexus-hermes-0206-cert` data directory.
- Environment names were inspected without values. No secret was printed.

Conclusion: `ORACLE_HERMES_0_20_6_STATE=PROVEN_ACTIVE_RUNTIME`.
