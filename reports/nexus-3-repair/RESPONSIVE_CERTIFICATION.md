# Responsive Certification

Local production preview tested:

| Viewport | Credit | Business | Recommendations | Horizontal Overflow |
|---|---|---|---|---|
| Desktop 1920x1080 | PASS | PASS | PASS | PASS |
| Tablet 820x1180 | PASS | PASS | PASS | PASS |
| Mobile 390x844 | PASS | PASS | PASS | PASS |

Observed repair:

- the non-interactive hero overlay was intercepting sidebar clicks during browser testing;
- repaired by disabling pointer events on `.wc-n3HeroShade` and `.wc-n3HeroContent` and giving the sidebar a stacking context;
- retest passed.
