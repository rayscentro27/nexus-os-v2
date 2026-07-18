# Client Route Replacement Matrix

| Route | Legacy Wrapper Found | Duplicate UI Found | Replacement Completed | Data Preserved | Browser Verified |
|---|---|---|---|---|---|
| `/client/credit-profile` | Yes | Yes | PASS | PASS | PASS local preview |
| `/client/credit-utilization` | Yes | Yes | PASS | PASS | PASS by shared Credit workspace |
| `/client/account-details` | Yes | Yes | PASS | PASS | PASS by shared Credit workspace |
| `/client/credit-repair-journey` | Yes | Yes | PASS | PASS | PASS by shared Credit workspace |
| `/client/dispute-review` | Yes | Yes | PASS | PASS | PASS by shared Credit workspace |
| `/client/business-journey` | Yes | Yes | PASS | PASS | PASS local preview |
| `/client/business-setup` | Yes | Yes | PASS | PASS | PASS by shared Business workspace |
| `/client/business-bankability` | Yes | Yes | PASS | PASS | PASS by shared Business workspace |
| `/client/business-credit` | Yes | Yes | PASS | PASS | PASS by shared Business workspace |
| `/client/recommendations` | Resources reuse | Partial | PASS | PASS | PASS local preview |
| `/client/documents` | Shared wrapper | Potential duplicate | PASS | PASS | NOT RUN authenticated |
| `/client/funding-readiness` | Shared wrapper | Potential duplicate | PASS | PASS | NOT RUN authenticated |
| `/client/resources` | Shared wrapper | Potential duplicate | PASS | PASS | NOT RUN authenticated |
| `/client/request-review` | Shared wrapper | Potential duplicate | PASS | PASS | NOT RUN authenticated |

Notes: all routes now render `{panel}` directly inside `.wc-pageHost`. Legacy shared wrappers remain available as source files but are not route wrappers in `WorldClassClientPortal`.
