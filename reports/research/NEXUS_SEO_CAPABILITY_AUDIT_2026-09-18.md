# Nexus SEO Capability Audit — 2026-09-18

Audit scope: executable capability fit for Nexus Research, Marketing, Creative,
Hermes, and MCP. No SEO project was installed, authenticated, deployed, or
connected to GoClear.

## Executive decision

The repositories are complementary rather than interchangeable.

`iannuttall/seo` is the better first capability for owned-site evidence: local
technical crawling, Google Search Console, Google Analytics, structured reports,
CLI automation, and a compact local MCP surface. Its research-provider adapters
are optional.

`every-app/open-seo` is a broader SEO platform and MCP product for keyword,
SERP, competitor, backlink, rank-tracking, site-audit, and AI-visibility work.
Its useful market data depends on DataForSEO, and self-hosting adds a Docker or
Cloudflare application boundary. It is a plausible second capability for paid
market intelligence, not a replacement for Last30Days or owned-site Search
Console evidence.

Recommended architecture: use both for different roles, with
`iannuttall/seo` as the first read-only local SEO evidence target and OpenSEO as
an optional separately governed market-data capability. Do not integrate either
until the first adapter is approved and pinned.

## Repository evidence

### iannuttall/seo

```text
REPO=https://github.com/iannuttall/seo
COMMIT=52f10012021131c2405cddfb976d583a6af3b490
VERSION=0.2.40
LICENSE=Apache-2.0
CLASSIFICATION=AGENT_SKILL + CLI_TOOL + MCP_SERVER + TypeScript library
NODE_REQUIREMENT=>=22.19.0
STARS=519
FORKS=40
OPEN_ISSUES=0 at audit time
COMMITS=644 repository history entries shown by GitHub
LATEST_COMMIT=2026-08-31; repository pushed 2026-09-06
```

The project exposes an `seo` executable, an MCP export, a provider SDK, JSON
reports, packaged agent skills, and a local crawl path that does not require
sign-in. Its README documents Search Console and Analytics connections plus
optional DataForSEO, Semrush, and Ahrefs research providers.

Maintenance and documentation are strong for a young project: active recent
commits, CI/security files, tests, stable command help, and explicit evidence
boundaries. The primary operational risk is its Node 22+ runtime and local
OAuth/keychain state, not an inherent architectural mismatch.

### every-app/open-seo

```text
REPO=https://github.com/every-app/open-seo
COMMIT=b076099fe25568b2acd43b3a9ec8d30fc31653a2
VERSION=0.1.9 (private application package)
LICENSE=MIT
CLASSIFICATION=SEO_PLATFORM + WEB_APP + MCP_SERVER + AGENT_SKILLS + self-hosted service
STARS=19,203
FORKS=2,471
OPEN_ISSUES=176
OPEN_PULL_REQUESTS=96
COMMITS=559 repository history entries shown by GitHub
LATEST_COMMIT=2026-09-18
```

OpenSEO exposes an MCP endpoint/configuration, agent skills, a React/TypeScript
web application, Docker self-hosting, and Cloudflare deployment paths. The
repository is highly active and has a large community signal, but the larger
application and external-data boundary create more operational surface than
the first Nexus-owned-site adapter needs.

## Capability matrix

| Capability | iannuttall/seo | every-app/open-seo |
|---|---|---|
| Technical crawl/site audit | YES, local | YES |
| Keyword discovery | YES, provider-backed or imported data | YES, DataForSEO-backed |
| Search volume/KD/CPC | REQUIRES_PROVIDER or import | REQUIRES_DATAFORSEO |
| SERP retrieval | YES via provider/extensions | YES via DataForSEO |
| SERP feature analysis | PARTIAL/REPORT-DEPENDENT | PARTIAL/YES through SERP workflows |
| Competitor analysis/gaps | YES | YES |
| Backlinks | YES via providers/imports | YES via DataForSEO |
| Rank tracking | YES | YES |
| Search Console | YES, OAuth | OPTIONAL, OAuth |
| GA4 | YES, OAuth | OPTIONAL/integration-dependent |
| Core Web Vitals/performance | PARTIAL through crawl/Lighthouse | PARTIAL/site-audit dependent |
| Local SEO | YES/partial reports | YES, local skills/tools |
| Content decay/CTR/cannibalization | PARTIAL through GSC/report workflows | PARTIAL; verify exact report support before use |
| Content briefs/search intent | YES through reports/skills | YES through skills/MCP |
| AI-search visibility | YES, provider-indexed/live observation reports | YES, AI visibility workflow |
| MCP | YES, local MCP server | YES, hosted/self-hosted MCP |
| Agent skills | YES | YES |
| CLI | YES, `seo` | NO standalone equivalent; service/MCP/UI |
| Structured JSON | YES | YES through MCP/API/report contracts |
| Scheduled automation | YES, scripts/CI/local jobs | YES, service/background deployment |
| Data-provider dependence | Optional for research; first-party GSC is separate | Required for SEO market data |
| Founder-mode deployment | Low/medium | Medium/high |
| Security fit | Good with local read-only boundary | Good only with auth, secret, telemetry, and exposure controls |

## Provider and cost boundary

### iannuttall/seo

| Provider | Required? | Cost/boundary | Enables |
|---|---|---|---|
| Local crawler/Lighthouse | No external key | local compute | technical audit, metadata, links, performance |
| Google Search Console | Optional | Google OAuth, no SEO-provider credit | owned impressions, clicks, positions, pages |
| Google Analytics | Optional | Google OAuth | traffic/analytics context |
| DataForSEO | Optional | paid usage | keyword/SERP/domain/competitor/link evidence |
| Semrush | Optional | paid API | provider market/ranking data |
| Ahrefs | Optional | paid API | provider market/backlink data |

Minimum useful setup is local crawl plus JSON output. A useful search-demand
setup requires one approved paid provider or imported exports. Exact monthly
cost is usage/provider-plan dependent and was not invented here.

### every-app/open-seo

| Provider | Required? | Cost/boundary | Enables |
|---|---|---|---|
| DataForSEO | Required for SEO data | pay-as-you-go; docs state $1 trial credit and $50 minimum top-up | keyword, SERP, rank, competitor, backlink data |
| Google Search Console | Optional | OAuth and encrypted token storage | owned search performance and inspection |
| Google Analytics | Optional | OAuth | analytics context |
| OpenRouter | Optional | model/provider cost | SAM/in-app AI features |
| Docker/Cloudflare | Self-hosting requirement | local compute or Cloudflare resources | service deployment/MCP access |
| Hosted OpenSEO | Optional | README states $10/month hosted subscription | managed service/MCP |

Self-hosted OpenSEO also documents local-no-auth Docker mode, a warning to put
it behind a private/authenticated boundary, and anonymous telemetry unless
disabled. DataForSEO credentials are the main cost and lock-in risk.

## Agent/MCP fit

```text
IANNUTTALL_MCP=YES_LOCAL_MCP_EXPORT
IANNUTTALL_CLI=YES
IANNUTTALL_STRUCTURED_OUTPUT=YES
IANNUTTALL_HERMES_COMPATIBILITY=GOOD_VIA_LOCAL_MCP_OR_CLI_BRIDGE
IANNUTTALL_NEXUS_ADAPTER_DIFFICULTY=LOW_TO_MEDIUM

OPEN_SEO_MCP=YES_HOSTED_OR_SELF_HOSTED
OPEN_SEO_CLI=NO_STANDALONE_PRIMARY_CLI_PROVEN
OPEN_SEO_STRUCTURED_OUTPUT=YES_MCP/API_REPORTS
OPEN_SEO_HERMES_COMPATIBILITY=GOOD_VIA_MCP_BUT_AUTH/SERVICE_BOUNDARY_REQUIRED
OPEN_SEO_NEXUS_ADAPTER_DIFFICULTY=MEDIUM
```

The clean first integration is:

```text
Hermes → Nexus read-only SEO adapter/MCP → pinned iannuttall/seo CLI/MCP
```

The later market-data option is:

```text
Research/Marketing → governed OpenSEO MCP → DataForSEO → evidence store
```

Neither path should write keywords, publish content, mutate rankings, or save
provider data without an explicit governed action.

## Last30Days and current Nexus overlap

```text
LAST30DAYS=recent human conversations, complaints, questions, engagement,
           social momentum, emerging customer problems

SEO=search demand, keyword metrics, SERPs, ranking/competitor evidence,
    owned-site performance, technical crawl, AI-visibility observations
```

Last30Days should discover the human problem; SEO should measure whether that
problem has searchable demand, what language ranks, which competitors appear,
and whether GoClear owns relevant search evidence. Search volume is not proof of
customer truth, and social engagement is not search volume.

Current Nexus already has a manual CSV keyword scout, deterministic opportunity
scoring, SEO opportunity reports, and an SEO director skill. The current
worktree/history did not contain a proven integrated `sushantkarn/SEO-engine`
runtime; its role is therefore `NOT_PRESENT_IN_CURRENT_RUNTIME / NO_ACTIVE
CAPABILITY`. Existing code should be retained as an implementation utility and
not treated as live provider-backed SEO intelligence.

## Lightweight probes

```text
IANNUTTALL_PROBE=PARTIAL_PASS
  npm registry metadata confirmed seo@0.2.40, Apache-2.0, Node >=22.19, and seo CLI bin.
  transient npm execution probe timed out in this environment; no package was
  installed into Nexus and no production state changed.

OPEN_SEO_PROBE=PASS_STATIC_CAPABILITY
  repository MCP config exposes https://app.openseo.so/mcp;
  keyword-research skill exposes research_keywords, get_keyword_metrics,
  get_ranked_keywords, get_search_console_performance, get_serp_results;
  no live MCP call, credentials, Docker service, or provider request was made.
```

## Resource and security fit

`iannuttall/seo` fits the Intel Mac mini and Oracle fallback best as a bounded
CLI/MCP process. It needs Node 22 and local browser/network access for crawl;
OAuth/provider access should be isolated and read-only.

OpenSEO is compatible with both hosts through Docker or Cloudflare, but is a
larger service with database/storage, auth, secrets, DataForSEO, optional
OpenRouter, and telemetry controls. Docker local-noauth must never be exposed
publicly without the documented private/authenticated reverse-proxy boundary.
Client PII should not enter either provider path unless an approved data policy
and provider contract exists.

## Role recommendation and next implementation

```text
RECOMMENDED_SEO_ARCHITECTURE=USE_BOTH_FOR_DIFFERENT_ROLES
RECOMMENDED_PRIMARY_SEO_CAPABILITY=iannuttall/seo for owned-site technical/GSC/GA4 evidence
RECOMMENDED_SECONDARY_SEO_CAPABILITY=OpenSEO for optional DataForSEO market/SERP/backlink/AI visibility
RECOMMENDED_NEXT_IMPLEMENTATION=pin iannuttall/seo and build a read-only JSON adapter
```

The next implementation should be a small local read-only probe/adapter for
`seo report --url` and, only after review, Search Console report ingestion. It
should persist bounded evidence into the existing Research stores and expose
source/provider provenance. OpenSEO should remain an audit-approved future
secondary capability until DataForSEO budget, auth, self-hosting, and telemetry
decisions are explicit.

## Audit status

```text
SEO_CAPABILITY_AUDIT_STATUS=PASS_REAL_AUDIT_NO_INSTALL
INTEGRATION_DECISION=ROLE_SEPARATED_NOT_YET_DEPLOYED
```

Sources reviewed: repository READMEs, package metadata, licenses, MCP config,
agent skill contracts, self-hosting/provider documentation, GitHub API metadata,
and current Nexus SEO code/reports. Official repository evidence:

- https://github.com/iannuttall/seo
- https://github.com/every-app/open-seo
- https://raw.githubusercontent.com/iannuttall/seo/main/package.json
- https://raw.githubusercontent.com/every-app/open-seo/main/.agents/skills/keyword-research/SKILL.md
