# Nexus Research — Data Classification Policy

**Generated**: 2026-07-04
**Status**: DRAFT — NOT APPROVED — NOT LIVE

---

## Data Classification Levels

### Level 1: Public
- Published blog posts (none currently)
- Public marketing materials (none currently)

### Level 2: Internal
- Nexus Research seed artifacts (unverified)
- Adapter processing results
- Internal test runner outputs
- Readiness report drafts
- Ray Review queue items
- Administrative configuration

### Level 3: Confidential
- Real client PII (not yet connected)
- Real credit report data (not yet connected)
- Real financial account data (not yet connected)
- Service role keys (never store)
- API keys (never store)

### Level 4: Restricted
- Passwords (never store)
- SSNs (never store)
- Credit card numbers (never store)
- Bank account numbers (never store)

---

## Storage Rules

| Classification | Supabase | Local | Notes |
|---------------|----------|-------|-------|
| Level 1: Public | Allowed | Allowed | No restrictions |
| Level 2: Internal | After approval | Allowed | Requires Ray Review approval for Supabase |
| Level 3: Confidential | Never (current phase) | Never (current phase) | Until security workflow approved |
| Level 4: Restricted | Never | Never | Never store in any system |

---

## Nexus Research Data Classification

| Data Type | Level | Supabase (Future) | Local |
|----------|-------|-------------------|-------|
| Seed artifacts | Internal | After approval | Allowed |
| Adapter results | Internal | After approval | Allowed |
| Test profiles (hypothetical) | Internal | Optional | Allowed |
| Readiness reports | Internal | After approval | Allowed |
| Ray Review queue | Internal | After approval | Allowed |
| Real client PII | Confidential | Blocked | Blocked |
| Real credit data | Confidential | Blocked | Blocked |
| Service role keys | Restricted | Never | Never |
| API keys | Restricted | Never | Never |

---

## Access Control

| Role | Level 1 | Level 2 | Level 3 | Level 4 |
|------|---------|---------|---------|---------|
| Anonymous | Read | No access | No access | No access |
| Authenticated user | Read | Own tenant only | No access | No access |
| Admin (service role) | Read | Read/Write | Read (audit only) | Never |

---

## Retention Policy

| Data Type | Retention | Deletion |
|----------|-----------|----------|
| Seed artifacts | Indefinite (internal) | Manual cleanup |
| Adapter results | Indefinite (internal) | Manual cleanup |
| Test outputs | 90 days | Auto-cleanup |
| Readiness reports | 90 days | Auto-cleanup |
| Audit logs | 1 year | Archive then delete |

---

## Encryption

- All Supabase data encrypted at rest (default)
- All connections use TLS
- No additional encryption required for Level 2 data
- Level 3+ data requires additional encryption (not yet implemented)
