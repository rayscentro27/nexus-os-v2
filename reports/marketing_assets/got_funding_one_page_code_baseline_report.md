# Got Funding One-Page Code Baseline Report

The Got Funding page is implemented as real static HTML/CSS in both supported entry points:

- `public/got-funding/index.html`
- `public/got-funding.html`

The files are byte-for-byte identical. A base URL keeps local image paths valid from either route. The implementation uses a dark navy/gold system, Manrope headings/buttons, Inter body copy, a local business-success hero, and the local preparation-road image.

The static Netlify form remains active with POST, form name, hidden form-name, honeypot, required lead fields, consent checkbox, and `/got-funding/thanks.html` action. It contains no Supabase or email-send integration.

Compliance language states that GoClear is not a lender, the form is not a loan application, and outcomes are not guaranteed.

Verification: 63 focused Got Funding tests passed and the production build passed.
