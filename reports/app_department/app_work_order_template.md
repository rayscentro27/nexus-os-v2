# App Work Order Template

**Generated:** 2026-07-05  
**Status:** Template Ready

---

## App Information

| Field | Value |
|-------|-------|
| **App Name** | `[APP_NAME]` |
| **Version** | `[VERSION]` |
| **Priority** | `[P0/P1/P2]` |
| **Owner** | `[OWNER]` |
| **Created** | `[DATE]` |

---

## Idea Summary

**Problem Statement:**  
`[What problem does this app solve?]`

**Target User:**  
`[Who is this for?]`

**Success Metrics:**  
- `[Metric 1]`
- `[Metric 2]`
- `[Metric 3]`

---

## Requirements

### Functional Requirements
1. `[FR-001]` — `[Description]`
2. `[FR-002]` — `[Description]`
3. `[FR-003]` — `[Description]`

### Non-Functional Requirements
1. `[NFR-001]` — `[Performance / Security / Scalability]`
2. `[NFR-002]` — `[Description]`

### Constraints
- `[Constraint 1 — budget, timeline, tech stack]`
- `[Constraint 2]`

---

## UI / Page Spec

### Pages
- `[PAGE-001]` — `[Name]` — `[Route]` — `[Description]`
- `[PAGE-002]` — `[Name]` — `[Route]` — `[Description]`

### Components
- `[COMP-001]` — `[Name]` — `[Props]` — `[State]`
- `[COMP-002]` — `[Name]` — `[Props]` — `[State]`

### State Management
- `[STATE-001]` — `[Slice]` — `[Shape]` — `[Source]`

---

## Data Model

### Tables
- `[TABLE-001]` — `[Name]` — `[Columns]` — `[RLS Policy]`
- `[TABLE-002]` — `[Name]` — `[Columns]` — `[RLS Policy]`

### API Surface
- `[ENDPOINT-001]` — `[Method]` — `[Path]` — `[Auth]`
- `[ENDPOINT-002]` — `[Method]` — `[Path]` — `[Auth]`

---

## Prototype

### File List
```
src/apps/[app-name]/
  ├── index.tsx
  ├── pages/
  │   ├── [page].tsx
  │   └── [page].tsx
  ├── components/
  │   ├── [component].tsx
  │   └── [component].tsx
  ├── hooks/
  │   └── use[Hook].ts
  ├── types/
  │   └── index.ts
  └── tests/
      ├── [test].test.ts
      └── [test].test.ts
```

### Routing
| Route | Page | Auth |
|-------|------|------|
| `/[app]/[page]` | `[Page Component]` | `[yes/no]` |

---

## Test Plan

### Unit Tests
- `[TEST-001]` — `[What it tests]` — `[Expected result]`
- `[TEST-002]` — `[What it tests]` — `[Expected result]`

### Integration Tests
- `[INT-001]` — `[What it tests]` — `[Expected result]`

### Manual QA Checklist
- [ ] `[QA-001]` — `[Manual check]`
- [ ] `[QA-002]` — `[Manual check]`

---

## Recovery Notes

- **Last Known Good State:** `[STATE]`
- **Error Context:** `[ERROR]`
- **Retry Instructions:** `[INSTRUCTIONS]`

---

## Sign-Off

- [ ] Requirements reviewed
- [ ] Specs approved
- [ ] Data model validated
- [ ] Prototype built
- [ ] Tests passing
- [ ] Ray Review complete
