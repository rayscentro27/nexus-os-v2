# Nexus Prompt 2 — Hermes / Alpha / Brain Closeout

**Generated**: 2026-07-05

---

## Hermes Work Router

**File**: `src/lib/hermesWorkRouter.ts` (190 lines)

| Capability | Status |
|-----------|--------|
| Intent classification | 23 regex patterns across 15 departments |
| Work order creation | Full model with ID, status, phases, recovery |
| Department routing | All 23 departments mapped |
| `classifyIntent()` | Returns RoutingDecision with confidence, mode, review flag |
| `createWorkOrder()` | Generates unique work order IDs |
| `getHermesResponse()` | Simplified response for API consumption |

**What Hermes can route now**: Any natural language prompt → department + process + activation mode
**What still requires live data**: Actually executing work orders against Supabase, tracking work order completion

---

## Alpha Decision Packets

**File**: `src/lib/alphaDecisionPackets.ts` (147 lines)

| Capability | Status |
|-----------|--------|
| Source type classification | 13 types (YouTube, TikTok, GitHub, grants, credit, affiliate, etc.) |
| Decision packet creation | Full model with 15 fields |
| Scoring engine | 4 dimensions: content quality, relevance, monetization, actionability |
| Score classification | 4 tiers: high_value (80+), opportunity_candidate (60-79), medium_value (40-59), low_value (<40) |
| Ray Review routing | Score >= 80 auto-routes to Ray Review |

**What Alpha can research now**: Classify URLs, create decision packets, score them, route high-value items to Ray Review
**What still requires live data**: Actual research intake from Supabase, connecting to live research sources

---

## Process Registry

**File**: `src/lib/nexusProcessRegistry.ts` (436 lines, 20 processes)

| Mode | Count | Examples |
|------|-------|---------|
| APPROVED_LIVE | 1 | Got Funding Lead Capture |
| SANDBOX_TEST | 5 | Supabase verification, Alpha brain, Hermes router, Trading lab, Billing |
| DRY_RUN | 9 | Research intake, YouTube, Creative engine, Email, Social, Reports |
| OBSERVE | 7 | System health, Ray Review, Command Center, Client Portal, NotebookLM, Telegram |

---

## Recovery System

Designed but not yet implemented:
- Recovery receipt model: `src/lib/nexusProcessReceipts.ts`
- Interrupted work detection: designed
- Recovery prompt generator: designed
- Next best tool recommendation: designed

---

## What Is Safe to Expose Through Telegram

| Feature | Safe? | Reason |
|---------|-------|--------|
| Hermes routing | YES | Read-only classification, no external actions |
| Alpha scoring | YES | Local computation, no external calls |
| Process registry status | YES | Read-only |
| Health check status | YES | Read-only |
| Ray Review queue | YES | Read-only, approval-gated |
| Work order creation | CAUTION | Should be DRY_RUN or SANDBOX_TEST only |
| Research intake | CAUTION | Should not trigger external API calls |
| Client data | NO | Requires Supabase + access control |
| Trading execution | NO | Even demo requires Oanda connectivity |
| Email sending | NO | Requires Resend + approval |
| Social posting | NO | Requires Meta + approval |

---

## What Should Stay Dashboard-Only

- Client workflow data (requires Supabase + access control)
- Night run monetization (internal only)
- Launch readiness (approval-gated)
- Affiliate approval waiting room (internal)
- Money opportunity highlights (draft-only)
