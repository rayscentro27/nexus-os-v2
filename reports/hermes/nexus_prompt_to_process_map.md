# Nexus Prompt-to-Process Map

**Generated**: 2026-07-05

---

## Current Routing Structure

### Prompt → Intent → Route → Process

| Prompt Pattern | Intent | Route | Process | Status |
|---------------|--------|-------|---------|--------|
| "Research [topic]" | research_query | research_route | YouTube researcher / research scripts | DRY_RUN |
| "Check system health" | status_check | health_route | System Health panel | OBSERVE (mock) |
| "Review [item]" | review_request | review_route | Ray Review queue | OBSERVE (mock) |
| "Run [process]" | process_execution | tool_route | Nexus runner / scripts | SANDBOX_TEST |
| "What's the status?" | status_query | status_route | Status components | OBSERVE (mock) |
| "Help with [client]" | client_query | client_route | Client portal | OBSERVE (mock) |
| "Trade [strategy]" | trading_query | trading_route | Trading lab | SANDBOX_TEST |
| "Send [email]" | communication | email_route | Resend integration | DRY_RUN |
| "Post [content]" | social_post | social_route | Meta integration | DRY_RUN |
| "Create [draft]" | content_creation | creative_route | Marketing studio | DRY_RUN |

---

## Routing Readiness by Department

| Department | Routes Defined | Real Processes | Ready? |
|-----------|---------------|----------------|--------|
| Research | Yes | Scripts exist | Partial |
| System Health | Yes | Panel exists (mock) | No |
| Ray Review | Yes | Queue exists (mock) | No |
| Operations | Yes | Scripts exist | Partial |
| Client | Yes | Portal exists (mock) | No |
| Trading | Yes | Lab exists | Partial |
| Email | Yes | Resend configured | Partial |
| Social | Yes | Meta configured | Partial |
| Creative | Yes | Studio exists | Partial |
| Marketing | Yes | Drafts exist | Partial |

---

## Gap Analysis

| Gap | Impact | Fix |
|-----|--------|-----|
| No real process registry | Cannot dispatch to actual processes | Build in Prompt 2 |
| Mock data in all routes | Routing works but outputs are fake | Connect to live data |
| No real Ray Review items | Cannot create review requests | Build in Prompt 2 |
| No live capability status | Cannot route based on real status | Connect to Supabase |
| No department execution | Cannot execute department actions | Build in Prompt 2 |

---

## Recommendation for Prompt 2

1. Build real process registry (map prompts to actual scripts)
2. Connect all routes to live data sources
3. Wire Ray Review creation to real items
4. Test end-to-end routing with real prompts
5. Add feedback loop (process results → routing improvements)
