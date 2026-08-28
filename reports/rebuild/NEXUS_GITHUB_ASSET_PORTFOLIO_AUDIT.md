# Nexus V2 GitHub Asset Portfolio Audit — Sprint 0 WP0-C

## Access evidence

The authenticated GitHub CLI account was available for read-only repository
listing. No repository was cloned, changed, deployed, or written during this
audit. The accessible portfolio included the current repository and related
Nexus/client/financial/site candidates.

## Candidate inventory

| Repository | Observable purpose | Initial disposition | Evidence limit |
|---|---|---|---|
| `nexus-os-v2` | Current Nexus operating system | REFERENCE / CANONICAL CANDIDATE | This is the current working tree; full capability truth remains the Sprint 0 census/audit |
| `nexuslive` | Nexus-related live application | INSPECT BEFORE IMPORT | Name/description alone does not prove working or deployable |
| `nexus-mobile` | Nexus mobile app; credit/funding platform | INSPECT BEFORE WRAP | Likely client-delivery overlap; requires code/history/security review |
| `AAAANexusCRM`, `AANexurRay`, `AGetNexus`, `NexusFinal` | CRM iterations | ARCHIVE CANDIDATES / INSPECT | Multiple generations imply duplication and possible stale implementations |
| `nexus-financial-os`, `FinalVersion1.1` | Financial systems | INSPECT BEFORE IMPORT | Financial safety and data lineage require deeper review |
| `site-boost-suite` | SEO/site tooling | INSPECT BEFORE WRAP | Potential research/marketing overlap; no operational claim made |
| `credit-cascade-portal` | Credit/client portal | INSPECT BEFORE WRAP | Potential core-business overlap; no production mutation performed |

Read-only metadata confirmed during this checkpoint:

- `nexuslive`: Python, public, main branch, not archived; source review still pending.
- `nexus-mobile`: TypeScript, public, default branch `feature/nexus-mobile-app`, not archived; source review still pending.
- `AAAANexusCRM`: TypeScript, private, default branch `integrate-aistudio-local`, not archived; source review still pending.
- `nexus-financial-os`: private, main branch, not archived; language metadata was null, so source review is required.
- `site-boost-suite`: TypeScript, private, main branch, not archived; source review still pending.
- `credit-cascade-portal`: TypeScript, private, main branch, not archived; source review still pending.

These metadata facts establish candidate existence and recency only. They do
not establish working, tested, deployable, secure, or reusable behavior.
| `gala-rsvp-demo`, `phxweather`, `weather`, `nba-gpt-api` | Demo or domain-specific apps | REFERENCE / IGNORE PENDING PURPOSE | Not enough evidence of Nexus reuse value |

## Decision rule

Before new capability work, compare: existing working Nexus Python, these
repositories, native Hermes capabilities, mature open source, then custom
implementation. Repository names and descriptions are discovery evidence only;
they are not proof of working, tested, secure, or deployable assets.

## Current WP0-C status

**IN_PROGRESS.** The portfolio is inventoried at the repository-list level.
Per-repository source/history/test/deployability review is the next safe
action. No import or merge is authorized by this package.

## Safety

No credentials, tokens, private repository contents, client PII, or generated
secrets are included here.
