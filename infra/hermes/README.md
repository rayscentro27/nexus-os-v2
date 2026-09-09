# Nexus Hermes 0.20.6 workstation

This is the durable ARM64 toolchain layer for the live Oracle Hermes image.
It intentionally uses the certified upstream digest and preserves the
upstream entrypoint and `/opt/data` volume. Build with Podman on Oracle:

```sh
podman build --arch arm64 \
  -f infra/hermes/Containerfile.hermes-workstation \
  -t nexus-hermes-0206-workstation:r15.4 .
```

The Quadlet must continue to mount the existing protected `/opt/data` state and
Oracle-side auth environment. Recreate the container only through the normal
Quadlet/service procedure after validating the built image. The image pins the
live certified Hermes digest and the following tool versions:

- Debian ARM64: `gh`, `jq`, `fd-find` (exposed as `fd`)
- npm: OpenCode `1.18.29`, Supabase `2.117.0`, Netlify `27.5.1`, Playwright `1.62.0`

Browser binaries are intentionally not downloaded in the image layer: the
Oracle runtime must certify the approved Playwright browser cache separately,
because Chromium is large and its cache is not part of Hermes state.

Credentials are deliberately not copied into the image. CLI auth, if any,
must remain in the established protected runtime mounts.
