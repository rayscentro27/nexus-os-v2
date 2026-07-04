# Got Funding Desktop No-Scroll Verification

## Desktop behavior

- Root page height: `100dvh`
- Root page overflow: hidden
- Body overflow: hidden
- Compact grid rows: top bar, 42vh hero, 23vh preparation, 20vh form/fit section, remaining footer
- Local hero and road imagery are rendered through CSS backgrounds.

## Mobile and tablet behavior

At widths of 1100px and below, the page switches to auto height and visible scrolling. Content grids collapse and the form remains reachable.

## Build verification

The production build contains:

- `dist/got-funding/index.html`
- `dist/got-funding.html`
- `dist/got-funding/thanks.html`
- `dist/got-funding/thanks/index.html`
- both local image assets

The QR asset still targets `https://goclearonline.cc/got-funding/`.

The CSS guarantees a one-viewport desktop container. Final visual fit can still vary at unusually short desktop viewport heights or with browser zoom/font overrides; those cases should be checked on Ray's target display after deployment.
