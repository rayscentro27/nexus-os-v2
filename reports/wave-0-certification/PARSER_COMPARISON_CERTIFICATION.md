# Parser Comparison Certification

Date: 2026-07-17

## Parser Fixture Contract

Command:

```bash
python3 scripts/checks/check_authenticated_parser_fixtures.py
```

Result:

- Exit code: 0.
- Status: PASS.

Evidence summary:

- 5 synthetic records parsed.
- Bureau set: Experian, Equifax, TransUnion.
- Canonical account group sizes: `[1,1,3]`.
- Balance mismatch detected.
- Account status mismatch detected.

## Parser Save/Load Shape

Command:

```bash
python3 scripts/checks/check_parser_result_save_load_shape.py
```

Result:

- Exit code: 0.
- Status: PASS.

Evidence summary:

- Worker sends raw JSON objects for JSONB columns.
- Worker verifies saved row counts.
- Frontend loader handles double-encoded fallback.
- Workflow reads account, inquiry, negative candidate, structured draft, suggestion, bureau, utilization, warning, and personal info fields.
- No fake OCR claims.
- No auto-letter creation.
- No auto-DocuPost send.
- Migration JSONB columns match expected shape.

## Non-Causal Outcome Checker

Command:

```bash
python3 scripts/checks/check_outcome_analytics.py
```

Result:

- Exit code: 0.
- Status: PASS.

Evidence summary:

- Non-causal policy is present.
- Bounded comparison model exists.
- Additive migration exists.
- Client output sources do not contain blocked causal/guarantee phrases.

## Synthetic Persona A Replay

Command:

```bash
python3 scripts/testers/replay_synthetic_credit_case.py --persona a --full
```

Result:

- Exit code: 0.
- Status: PASS.

Sanitized summary:

- Documents: 21 visible under synthetic scope after prior/reused certification state.
- Parser results: 3.
- Canonical accounts: 3.
- Recommendations: 2.
- Strategy matches: 2.
- Drafts: 1.
- Decisions: 12.
- Exceptions: 0.
- Comparison runs: 1.
- Readiness history: 1.
- Active jobs: 0.

Parser and Comparison Gate: PASS.
