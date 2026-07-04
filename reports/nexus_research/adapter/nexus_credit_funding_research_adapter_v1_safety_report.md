# Nexus Credit & Funding Research Adapter v1 — Safety Report

**Generated**: 2026-07-03

---

## Safety Architecture

### Hard Rules Enforced

| Rule | Status |
|------|--------|
| No Supabase connection (Alpha) | ✅ Enforced |
| No Supabase connection (Nexus) | ✅ Enforced |
| No client data access | ✅ Enforced |
| No external API calls | ✅ Enforced |
| No production mutation | ✅ Enforced |
| No fake research created | ✅ Enforced |
| All output draft-only | ✅ Enforced |
| All client-facing requires Ray Review | ✅ Enforced |
| No send/publish/charge/trade actions | ✅ Enforced |

### Guarantee Language Detection

The adapter flags these patterns:

| Pattern | Detected | Action |
|---------|----------|--------|
| "guaranteed approval" | Yes | Flag + admin-only |
| "guaranteed funding" | Yes | Flag + admin-only |
| "guaranteed deletion" | Yes | Flag + admin-only |
| "guaranteed score increase" | Yes | Flag + admin-only |
| "no credit check" | Yes | Flag + admin-only |
| "instant approval" | Yes | Flag + admin-only |
| "remove all negatives" | Yes | Flag + admin-only |
| "bypass underwriting" | Yes | Flag + admin-only |
| "fake business address" | Yes | Flag + admin-only |
| "tradeline manipulation" | Yes | Flag + admin-only |
| "illegal dispute" | Yes | Flag + admin-only |
| "submit application automatically" | Yes | Flag + admin-only |
| "send letter automatically" | Yes | Flag + admin-only |
| "apply for loan automatically" | Yes | Flag + admin-only |
| "charge client automatically" | Yes | Flag + admin-only |
| "publish this" | Yes | Flag + admin-only |
| "email this" | Yes | Flag + admin-only |
| "ignore approval" | Yes | Flag + admin-only |
| "bypass Ray Review" | Yes | Flag + admin-only |
| "100% approval/funding" | Yes | Flag + admin-only |

### Compliance Flag Detection

| Flag | Trigger |
|------|---------|
| FCRA | Content mentions FCRA |
| FDCPA | Content mentions FDCPA |
| FTC disclosure | Content mentions FTC |
| Potential legal advice | Content mentions "legal advice" |
| Potential tax advice | Content mentions "tax advice" |
| Potential financial advice | Content mentions "financial advice" |

### Output Safety

| Output Type | Gate | Safety |
|-------------|------|--------|
| Admin notes | Level 1 | Admin-only, no client exposure |
| Ray Review drafts | Level 3 | Requires Ray approval |
| Client education drafts | Level 3 | Requires Ray approval, marked "DRAFT" |
| Client-facing content | Level 3 | Blocked until approved |

### Blocked Actions (Always Blocked)

| Action | Status |
|--------|--------|
| Automated dispute sending | Blocked |
| Direct lender applications | Blocked |
| Funding approval guarantees | Blocked |
| Credit score guarantees | Blocked |
| Automated email/SMS | Blocked |
| Social publishing | Blocked |
| Payment collection | Blocked |
| Live API connections | Blocked |
| Client data exposure | Blocked |
| Legal advice without license | Blocked |
