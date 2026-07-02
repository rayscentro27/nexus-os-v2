# Hermes Source Authority Contract

**Date:** 2026-07-02
**Module:** `src/lib/hermesSourceAuthority.ts`
**Status:** Implemented and verified

---

## Purpose

Every Hermes answer should be traceable to a source level. The source authority contract defines the priority ladder of data sources for each business domain, so that:

1. Hermes knows which source to prefer for a given domain
2. The user can see which source was used
3. The voice-ready response can include source provenance
4. The trace/provenance system has structured source data

---

## Source Authority Ladder

Each domain has an ordered list of source levels, from highest priority to lowest:

| Source Level | Label | Meaning |
|---|---|---|
| `live_supabase` | "I used live Supabase data." | Direct database read, authenticated and RLS-checked |
| `latest_report` | "I used the latest local report." | Pre-generated report file from the last audit/run |
| `local_registry` | "I used the local registry." | Hardcoded or file-based registry (agents, settings, tools) |
| `static_context` | "I used static Nexus context because live and report data were not available." | Embedded static data (offer definitions, business context) |
| `page_context` | "I used page metadata passed by the UI." | Current page ID, section, URL from the chat surface |
| `local_trace` | "I used the last routing trace." | Previous answer's routing trace for provenance questions |
| `general_reasoning` | "I used general reasoning." | No Nexus data; plain reasoning or common knowledge |
| `unknown` | "The source is unverified." | No source identified |

---

## Domain Ladders

| Domain | Source Priority |
|---|---|
| `business_opportunities` | live_supabase → latest_report → static_context → unknown |
| `approvals` | live_supabase → latest_report → static_context → unknown |
| `clients` | live_supabase → latest_report → unknown |
| `monetization` | live_supabase → latest_report → static_context → unknown |
| `research` | live_supabase → latest_report → local_registry → unknown |
| `trading` | latest_report → local_registry → unknown |
| `credit_funding` | live_supabase → latest_report → static_context → unknown |
| `nexus_product_build` | local_registry → static_context → unknown |
| `system_health` | live_supabase → latest_report → local_registry → unknown |
| `reports` | local_registry → latest_report → unknown |
| `ray_review` | live_supabase → latest_report → unknown |
| `current_page` | page_context → unknown |
| `specialist_agents` | local_registry → unknown |
| `trace` | local_trace → unknown |
| `general_conversation` | general_reasoning → unknown |
| `external_info` | unknown |

---

## API

```typescript
getSourceAuthorityForDomain(domain: IntentDomain): SourceAuthorityEntry
```
Returns the source authority entry for a domain, including the ordered source levels and a human-readable label.

```typescript
getSourceAuthorityLabel(level: SourceLevel): string
```
Returns a human-readable label for a source level, suitable for inclusion in responses and voice-ready output.

---

## Integration

- **Pipeline:** `hermesBrainPipeline.ts` uses source authority to determine which source was used and to include provenance in responses
- **Voice-ready:** `hermesVoiceReadyRenderer.ts` extracts the source label for plain-answer output
- **Business opportunity review:** `hermesBusinessOpportunityReview.ts` uses source authority to set the session source and verification status
- **Trace:** `hermesTraceQuestionHandler.ts` uses source information from the routing trace, which aligns with the source authority ladder

---

## Remaining Weaknesses

1. **Static context is unverified** — when `static_context` is used, the verification status is `unverified`; a freshness indicator would improve trust
2. **No source staleness tracking** — the contract does not track when a source was last refreshed; a timestamp per source level would help
3. **Live Supabase failures are not distinguished from RLS blocks** — both produce `unknown` or `static_context` fallback; a `supabase_blocked` level could differentiate
