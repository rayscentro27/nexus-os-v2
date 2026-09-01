# WP8.11D Creative Review Studio

`src/components/CreativeReviewStudio.jsx` is the canonical review surface and
is wired into the Studio route of the active admin experience and the legacy
admin route. It loads `public/creative-library/index.json`, renders thumbnails
or posters, opens review proxies inline, shows provenance/territory/version,
supports comparison state, and records internal decision state in the UI.

The backend receipt contract is implemented by `media_library.review()`:
REQUEST_REVISION, APPROVE, REJECT, and ARCHIVE create immutable review and
learning records; approval never triggers publication and rejection retains the
asset. A duplicate approval was re-run and returned `DUPLICATE_SUPPRESSED`.

Admin browser access is authentication-gated in this environment, so the
authenticated production UI screenshot was not claimed as a full E2E proof.
The unauthenticated public route correctly showed the admin-access guard. The
production build and component wiring passed.

