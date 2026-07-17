# Build Diagnostic

Date: 2026-07-17

## Command Discovery

- TypeScript command: `npm run typecheck` -> `tsc --noEmit`
- Production build command: `npm run build` -> `tsc --noEmit && vite build`
- Vite config: `vite.config.ts`
- TypeScript config: `tsconfig.json`
- Build metadata: generated from env/git in `vite.config.ts`; no external service call.
- Vite plugins: local Alpha/static bridge for dev server only plus React plugin.

## TypeScript Certification

Command:

```bash
npm run typecheck
```

Final result:

- Start: 2026-07-17T17:55:15Z
- End: 2026-07-17T17:55:48Z
- Exit code: 0
- Status: PASS

## Production Build Certification

Command:

```bash
npm run build
```

Final result:

- Start: 2026-07-17T17:56:01Z
- End: 2026-07-17T17:56:28Z
- Exit code: 0
- Status: PASS
- Vite version: 5.4.21
- Modules transformed: 1,822
- Output path: `dist/`
- Main assets:
  - `dist/index.html`
  - `dist/assets/index-BYba2NKk.css`
  - `dist/assets/index-C_IbqEHI.js`
  - `dist/assets/creditReportParserToCaseEngine-DuETIo3S.js`

Warnings:

- `creditRepairWorkflow.ts` is both dynamically and statically imported, so dynamic import will not split it into a separate chunk.
- Main JS chunk is larger than 500 kB after minification.

Build delay diagnosis:

- Independent build did not stall.
- The previous stall was not reproduced.
- Playwright webServer currently chains `npm run build && npm run preview`, causing each browser run to rebuild. This is slow but not a hang.

## Unit Test Script Repair

Problem:

- `npm test` originally ran `vitest run --exclude tests/e2e/**`.
- In zsh, the unquoted glob expanded to E2E filenames, causing Vitest to filter to E2E files and then report "No test files found."

Repair:

- `package.json` now uses `vitest run --exclude 'tests/e2e/**'`.

Verification:

```bash
npm test
```

- Test files: 83 passed.
- Tests: 1,389 passed.
- Exit code: 0.

## Build Gate

Production Build: PASS.
