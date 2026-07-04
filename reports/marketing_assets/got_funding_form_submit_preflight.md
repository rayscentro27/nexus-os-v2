# Got Funding Form Submit Preflight

- Starting commit: `d46919e add Alpha URL review connector foundation`
- Form action: `/got-funding/thanks.html`
- Form name: `goclear-got-funding`
- Hidden form-name input: present
- Honeypot: present as `bot-field`
- Consent field: present with compliance language
- Thank-you files exist:
  - `public/got-funding/thanks.html`
  - `public/got-funding/thanks/index.html`
  - Build output exists for both thank-you files.

Likely cause:
- The visible form is missing the `netlify` form detection attribute.
- The browser is submitting directly to `/got-funding/thanks.html`; Netlify does not capture a POST aimed at a static thank-you path, so it returns 404.
- Add JS submit fallback to avoid direct POST to the thank-you URL.
