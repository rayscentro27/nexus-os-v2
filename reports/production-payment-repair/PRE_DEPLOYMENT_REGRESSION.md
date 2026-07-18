# Pre-Deployment Regression

## Status

PASS for non-live regression.

## Evidence

- `npm run typecheck`: PASS
- `npm run build`: PASS; 1822 modules transformed; known chunk-size and dynamic-import warnings
- `npx vitest run tests/revenue_activation.test.ts`: PASS, 12/12

## Current Gate

Regression should be rerun after live configuration is entered during Nexus 3.0 and before any live payment.
