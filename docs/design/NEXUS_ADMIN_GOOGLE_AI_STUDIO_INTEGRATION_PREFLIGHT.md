# Nexus Admin Google AI Studio Integration Preflight

Complete this checklist before integrating the Google AI Studio Admin Portal. Do not integrate Admin UI in the same change as the preflight standard.

- [ ] Preserve the original Google AI Studio source package unchanged.
- [ ] Identify and record the source package Tailwind/runtime version.
- [ ] Run the package against the Nexus Tailwind 4 frontend baseline; do not reintroduce Tailwind 3 compatibility assumptions.
- [ ] Create a unique isolated visual namespace/root.
- [ ] Generate and verify scoped CSS before connecting live data.
- [ ] Capture approved baseline screenshots for desktop and mobile.
- [ ] Connect auth, data, actions, and routing without changing visual component hierarchy.
- [ ] Compare the local rendered structure and computed styles against the baseline.
- [ ] Compare the production rendered structure and computed styles against the baseline after deployment.
- [ ] Require visual acceptance for geometry, spacing, typography, colors, and responsive behavior before connecting live data.
- [ ] Do not declare PASS from source hashes or a successful build alone.
- [ ] Confirm Nova's right rail, avatar, and voice layout remain exactly as approved.
- [ ] Verify no CSS leakage into the client portal or other Nexus surfaces.
- [ ] Verify preview, live, empty, and partial-data states preserve the same shell.
