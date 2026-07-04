# GoClearOnline Domain Setup Status

- Netlify primary domain: `goclearonline.cc` (Ray-confirmed).
- `www.goclearonline.cc`: redirects to primary; read-only HTTP check confirmed.
- HTTPS: enabled; read-only HTTPS checks returned 200.
- Desired QR URL: `https://goclearonline.cc/got-funding/`.
- QR generator: `scripts/generate_got_funding_qr.swift`; override with `GOCLEAR_QR_URL` only if the canonical URL changes.

Verification:

```bash
curl -I https://goclearonline.cc/got-funding/
curl -L https://goclearonline.cc/got-funding/ | head -40
```

Shirt printing is safe only after the teaser, QR scan on two phones, synthetic Netlify capture, and deletion are verified.
