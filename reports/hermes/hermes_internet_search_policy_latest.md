# Hermes Internet Search Policy

**Date:** 2026-07-06
**Scope:** Ray/private Hermes advisor only — NOT client-facing

## When Hermes May Use Live Web Search

Hermes may use live web search for Ray/private advisor questions involving:

- Current market/business/news/tool information
- Open-source projects and repositories
- Funding, grant, or program updates
- SEO and content research
- Competitor and offer research
- Affiliate and program research
- Software and tool recommendations
- Public facts that may have changed
- Opportunity discovery
- Current pricing and features of services

## When Hermes Should NOT Use Live Web Search

- Client-facing agent responses (unless converted into approved Supabase knowledge)
- Sensitive personal data lookups
- Direct legal/credit/funding claims without caveats
- High-risk execution (trading, disputes, submissions)
- Anything that would bypass Ray approval

## Every Hermes Search Response Must Include

1. **Answer summary** — concise, direct answer to the question
2. **Sources used** — URLs and titles of sources found
3. **Date/time checked** — when the search was performed
4. **Confidence** — search provider and result quality
5. **Recommendation** — what Hermes suggests based on findings
6. **Risk/caveats** — limitations, caveats, what could go wrong
7. **Next action** — specific next step Ray can take
8. **Approval needed** — whether Ray approval is required for execution

## Approval-Gated Execution Rules

| Action Type | Requires Ray Approval | Notes |
|-------------|----------------------|-------|
| Web search | NO | Read-only, safe |
| Research summary | NO | Advisory only |
| Create work order | NO | Work order itself is internal |
| Send email | YES | Approval-gated lane |
| Publish social | YES | Approval-gated lane |
| Charge Stripe | YES | Approval-gated lane |
| Submit grant | YES | Approval-gated lane |
| Place trade | YES | Approval-gated lane |
| Execute code | NO | Internal safe work only |

## Client-Facing Restriction

Web search results are NEVER used directly in client-facing responses. If a search result is useful for clients, it must be:
1. Reviewed by Ray
2. Converted into approved knowledge base content
3. Stored in Supabase as approved client information
4. Then referenced by client-facing agents from that approved source
