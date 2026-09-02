# WP9E remote browser evidence

Real bounded probe: existing `opc@161.153.40.41` → Podman container
`nexus-hermes-0206` → Playwright-managed Chromium headless shell.

- Public URL: `https://example.com` (non-sensitive)
- DOM/title and H1 extraction: PASS in the container
- Screenshot: PASS, 1280×720 PNG
- Screenshot SHA-256: `bc7cf1f419af36be6d190e8559333b0915d7fc0ec66c41414bdb22b65932e4d2`
- Remote temporary file was copied to the repo evidence directory and removed
- Existing host/container processes were not restarted

This proves browser execution and artifact return, not authenticated profile
browsing. The proof image is [oracle-browser-proof.png](../runtime/wp9e/oracle-browser-proof.png).
