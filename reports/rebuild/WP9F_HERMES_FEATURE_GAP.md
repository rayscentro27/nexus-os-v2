# WP9F Hermes feature gap

| Capability | Mac 0.14.0 | Oracle 0.20.6 | Decision |
|---|---|---|---|
| Browser | local Playwright evidence | container Chromium/browser surface | Oracle for bounded heavy browser |
| MCP/skills/tools | existing Nexus route | CLI surfaces listed in real help | stage adapter before cutover |
| Delegation/model | not benchmarked | not model-tested here | unproven |
| Sessions/memory | existing local runtime | isolated data mount exists | do not merge state automatically |
| Security | Mac control plane | rootless, host network, 4 GiB limit | preserve trust boundary |

The new Oracle version is valuable as a worker candidate, but no feature delta
was used to justify production migration. Authenticated browser value remains
`UNKNOWN` without a dedicated approved profile.
