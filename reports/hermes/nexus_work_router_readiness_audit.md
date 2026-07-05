# Nexus Work Router Readiness Audit

**Generated**: 2026-07-05

---

## Work Router Architecture

### Intent Classification
- `src/lib/hermesIntentClassifier.ts` — Classifies user intent
- `src/lib/hermesIntent.ts` — Intent definitions
- `src/lib/hermesIntentFrame.ts` — Intent framing

### Routing Layers
1. **Priority Router** (`hermesPriorityRouter.ts`) — Routes by priority
2. **Tool Router** (`hermesToolRouter.ts`) — Routes to tools/capabilities
3. **Action Resolver** (`hermesActionResolver.ts`) — Resolves specific actions
4. **Response Router** (`hermesResponseRouter.ts`) — Routes responses
5. **Dual Brain Router** (`hermesDualBrainRouter.ts`) — Routes between Alpha/Hermes

### Intent Types Supported
| Intent | Router | Status |
|--------|--------|--------|
| Research query | Intent classifier | Built |
| Process execution | Tool router | Built |
| Status check | Status router | Built |
| Ray Review request | Review router | Built |
| Department action | Department router | Built |
| Trading query | Trading reasoner | Built |
| Client query | Client adapter | Built |
| Marketing query | Marketing router | Built |

---

## Readiness Assessment

| Component | Score | Status |
|-----------|-------|--------|
| Intent classification | 65 | Built, needs testing |
| Priority routing | 55 | Built, needs live data |
| Tool routing | 50 | Built, no real tools |
| Action resolution | 45 | Built, no real actions |
| Response routing | 55 | Built, needs testing |
| Dual brain routing | 60 | Built, needs testing |
| **Overall** | **55** | |

---

## Missing Components

| Component | Impact | Priority |
|-----------|--------|----------|
| Real process registry | Cannot dispatch to real processes | HIGH |
| Live capability status | Cannot route based on real status | HIGH |
| Real Ray Review items | Cannot create review requests | HIGH |
| Live system health | Cannot route based on system state | MEDIUM |
| Department process execution | Cannot execute department actions | MEDIUM |

---

## Recommendation for Prompt 2

1. Build real process registry (connect to actual scripts/processes)
2. Wire capability status to live data
3. Create real Ray Review items from router
4. Test routing with real user prompts
5. Connect to live system health
6. Build department-specific action execution
