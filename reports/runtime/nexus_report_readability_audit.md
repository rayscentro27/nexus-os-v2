# Nexus Report Readability Audit

**Generated**: 2026-07-05

---

## Readability Dimensions

| Dimension | Description |
|-----------|-------------|
| Readable by Ray | Human-readable markdown, clear language |
| Readable by Alpha | Machine-parseable, structured data |
| Readable by Nexus Hermes | Machine-parseable, structured data |
| Has summary | Executive summary or overview section |
| Has evidence | References to source files, data, proofs |
| Has timestamp | When the report was generated |
| Has source files | Lists files used to generate report |
| Has status | Current status of the subject |
| Has next action | Recommended next step |
| Has blockers | Known blockers or issues |
| Has activation mode | OBSERVE/DRY_RUN/SANDBOX_TEST/APPROVED_LIVE |

---

## Report Readiness by Directory

### reports/runtime/
| Dimension | Score | Notes |
|-----------|-------|-------|
| Readable by Ray | 70 | Markdown available, some JSON-heavy |
| Readable by Alpha | 80 | Machine-readable JSON |
| Readable by Hermes | 80 | Machine-readable JSON |
| Has summary | 60 | Varies by report |
| Has evidence | 70 | References included |
| Has timestamp | 90 | Most have generated_at |
| Has source files | 50 | Not always listed |
| Has status | 40 | Not always included |
| Has next action | 30 | Rarely included |
| Has blockers | 20 | Rarely included |
| Has activation mode | 10 | Not standard yet |

### reports/manual_publish/
| Dimension | Score | Notes |
|-----------|-------|-------|
| Readable by Ray | 90 | Human-readable markdown |
| Readable by Alpha | 70 | Structured but narrative |
| Readable by Hermes | 70 | Structured but narrative |
| Has summary | 80 | Most have summaries |
| Has evidence | 80 | References included |
| Has timestamp | 90 | Most have timestamps |
| Has source files | 70 | Often listed |
| Has status | 60 | Often included |
| Has next action | 40 | Sometimes included |
| Has blockers | 30 | Sometimes included |
| Has activation mode | 0 | Not included |

### reports/alpha/ & reports/hermes_alpha/
| Dimension | Score | Notes |
|-----------|-------|-------|
| Readable by Ray | 85 | Well-structured markdown |
| Readable by Alpha | 75 | Structured data |
| Readable by Hermes | 75 | Structured data |
| Has summary | 80 | Most have summaries |
| Has evidence | 85 | Good references |
| Has timestamp | 85 | Most have timestamps |
| Has source files | 80 | Well-referenced |
| Has status | 70 | Often included |
| Has next action | 50 | Often included |
| Has blockers | 40 | Sometimes included |
| Has activation mode | 20 | Sometimes included |

---

## Overall Readiness

| Dimension | Average Score |
|-----------|--------------|
| Readable by Ray | 82 |
| Readable by Alpha | 75 |
| Readable by Hermes | 75 |
| Has summary | 73 |
| Has evidence | 78 |
| Has timestamp | 88 |
| Has source files | 67 |
| Has status | 57 |
| Has next action | 40 |
| Has blockers | 30 |
| Has activation mode | 10 |

---

## Key Gap

Reports are **well-structured and timestamped** but lack:
- **Activation mode** (only 10% have it)
- **Next action** (only 40% have it)
- **Blockers** (only 30% have it)

These fields are critical for Hermes routing and Alpha analysis.

---

## Recommendation for Prompt 2

1. Add activation_mode to all reports
2. Add next_action to all reports
3. Add blockers to all reports
4. Create report template with standard fields
5. Wire reports to Alpha/Hermes research inbox
