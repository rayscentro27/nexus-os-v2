# Nexus Department Registry Audit

**Generated**: 2026-07-05

---

## Department Registry

### 1. Command Center
| Field | Value |
|-------|-------|
| department_id | `command_center` |
| purpose | Central operating dashboard and navigation |
| existing files | `Shell.tsx`, `MissionControl.tsx`, `NexusAdminUI.jsx` |
| activation_status | OBSERVE (mock data) |
| available processes | Navigation, tab switching |
| missing processes | Live data aggregation, real status |
| data sources | Local data files (mock) |
| approvals needed | None |
| Prompt 2 buildout | Connect to live data sources |

### 2. Alpha Strategy Brain
| Field | Value |
|-------|-------|
| department_id | `alpha_strategy` |
| purpose | Strategy, research, opportunity scoring |
| existing files | `src/hermes/alpha/` (25+ files) |
| activation_status | SANDBOX_TEST |
| available processes | Scoring, URL review, research intake |
| missing processes | Live data, real research intake |
| data sources | Local files, env vars |
| approvals needed | Ray review for live actions |
| Prompt 2 buildout | Connect to live research data |

### 3. Nexus Hermes Operations Brain
| Field | Value |
|-------|-------|
| department_id | `nexus_hermes` |
| purpose | Operations, routing, process dispatch |
| existing files | `src/hermes/nexus/` (11 files), `src/lib/hermes*.ts` (60+ files) |
| activation_status | SANDBOX_TEST |
| available processes | Intent classification, routing, status |
| missing processes | Real process execution, live data |
| data sources | Local files, Supabase (read) |
| approvals needed | Ray review for live actions |
| Prompt 2 buildout | Connect to real process registry |

### 4. App Department
| Field | Value |
|-------|-------|
| department_id | `app` |
| purpose | Nexus OS2 UI and client portal |
| existing files | `src/components/`, `src/pages/`, `src/app/` |
| activation_status | OBSERVE (mock data) |
| available processes | UI rendering, routing |
| missing processes | Live data loading, real interactions |
| data sources | Local data files (mock) |
| approvals needed | None |
| Prompt 2 buildout | Replace mock data with live sources |

### 5. Landing Page Department
| Field | Value |
|-------|-------|
| department_id | `landing_pages` |
| purpose | Marketing landing pages and funnels |
| existing files | Got Funding page, QR generator |
| activation_status | APPROVED_LIVE (Got Funding) |
| available processes | Page rendering, form submission |
| missing processes | Other landing pages |
| data sources | Netlify, local assets |
| approvals needed | None for Got Funding |
| Prompt 2 buildout | Build additional landing pages |

### 6. Client Portal Department
| Field | Value |
|-------|-------|
| department_id | `client_portal` |
| purpose | Client-facing portal and guided journey |
| existing files | `src/components/client/`, `src/pages/client/` |
| activation_status | OBSERVE (placeholder) |
| available processes | Page rendering, navigation |
| missing processes | Real data, form submissions, document upload |
| data sources | Local data files (mock) |
| approvals needed | None |
| Prompt 2 buildout | Build guided journey with real data |

### 7. Credit Readiness Department
| Field | Value |
|-------|-------|
| department_id | `credit_readiness` |
| purpose | Credit profile, utilization, repair |
| existing files | `src/data/creditFundingData.js` (mock) |
| activation_status | OBSERVE (placeholder) |
| available processes | None (mock only) |
| missing processes | Credit analysis, utilization calc, dispute generation |
| data sources | Local data files (mock) |
| approvals needed | Ray review for dispute letters |
| Prompt 2 buildout | Build credit analysis engine |

### 8. Business Setup Department
| Field | Value |
|-------|-------|
| department_id | `business_setup` |
| purpose | Business profile, bankability, setup |
| existing files | Migration `20260629090000` |
| activation_status | OBSERVE (schema only) |
| available processes | None |
| missing processes | Business profile form, bankability scoring |
| data sources | Supabase (schema defined) |
| approvals needed | None |
| Prompt 2 buildout | Build business profile form |

### 9. Funding/Grant Department
| Field | Value |
|-------|-------|
| department_id | `funding_grants` |
| purpose | Funding readiness, grant research |
| existing files | Migration `20260629095450`, seed data |
| activation_status | OBSERVE (schema only) |
| available processes | None |
| missing processes | Funding scoring, grant research, application drafts |
| data sources | Supabase (schema defined), local seeds |
| approvals needed | Ray review for applications |
| Prompt 2 buildout | Build funding readiness dashboard |

### 10. Research Department
| Field | Value |
|-------|-------|
| department_id | `research` |
| purpose | Research intake, scoring, reporting |
| existing files | `scripts/research/`, `configs/research_*.json` |
| activation_status | DRY_RUN |
| available processes | Research scripts, scoring |
| missing processes | Live data pipeline, UI integration |
| data sources | Local files, YouTube API |
| approvals needed | None for research |
| Prompt 2 buildout | Connect to live data, add UI |

### 11. YouTube Research Department
| Field | Value |
|-------|-------|
| department_id | `youtube_research` |
| purpose | YouTube channel/video research |
| existing files | `data/cache/youtube/`, `scripts/research/` |
| activation_status | DRY_RUN |
| available processes | Metadata caching, research scripts |
| missing processes | Live API integration, transcript processing |
| data sources | YouTube API (key present) |
| approvals needed | None |
| Prompt 2 buildout | Connect to live API |

### 12. NotebookLM Department
| Field | Value |
|-------|-------|
| department_id | `notebooklm` |
| purpose | NotebookLM export/import |
| existing files | `data/exports/notebooklm/`, configs |
| activation_status | OBSERVE |
| available processes | Export generation |
| missing processes | Import parsing, UI integration |
| data sources | Local files |
| approvals needed | None |
| Prompt 2 buildout | Build import parser |

### 13. Marketing Department
| Field | Value |
|-------|-------|
| department_id | `marketing` |
| purpose | Marketing drafts, content, campaigns |
| existing files | `src/hermes/nexus/marketingAssetStudio.ts`, drafts |
| activation_status | DRY_RUN |
| available processes | Draft generation |
| missing processes | Publishing, analytics |
| data sources | Local files |
| approvals needed | Ray review for publishing |
| Prompt 2 buildout | Connect to publishing pipeline |

### 14. Affiliate Department
| Field | Value |
|-------|-------|
| department_id | `affiliate` |
| purpose | Affiliate links, tracking, payouts |
| existing files | `configs/offer_registry.json`, `src/lib/affiliateOpportunityTracker.ts` |
| activation_status | OBSERVE (config only) |
| available processes | None |
| missing processes | Link generation, tracking, payout calculation |
| data sources | Config files |
| approvals needed | None |
| Prompt 2 buildout | Build affiliate tracking |

### 15. Email Department
| Field | Value |
|-------|-------|
| department_id | `email` |
| purpose | Email sending via Resend |
| existing files | `RESEND_API_KEY` in `.env` |
| activation_status | DRY_RUN |
| available processes | Email sending (untested) |
| missing processes | Template management, analytics |
| data sources | Resend API |
| approvals needed | None for transactional |
| Prompt 2 buildout | Test email sending |

### 16. Social/Video Department
| Field | Value |
|-------|-------|
| department_id | `social_video` |
| purpose | Social media posting, video content |
| existing files | Meta tokens, social scripts |
| activation_status | DRY_RUN |
| available processes | Meta posting (untested) |
| missing processes | TikTok, video editing, analytics |
| data sources | Meta API |
| approvals needed | Ray review for posting |
| Prompt 2 buildout | Test social posting |

### 17. Trading Department
| Field | Value |
|-------|-------|
| department_id | `trading` |
| purpose | Trading research, demo trading |
| existing files | `scripts/trading/`, OANDA config |
| activation_status | SANDBOX_TEST |
| available processes | Demo trading, research |
| missing processes | Live trading (blocked by design) |
| data sources | OANDA API (demo) |
| approvals needed | Ray review for live |
| Prompt 2 buildout | Test demo trading |

### 18. Billing/Referral Department
| Field | Value |
|-------|-------|
| department_id | `billing_referral` |
| purpose | Stripe billing, referrals |
| existing files | `configs/stripe_product_registry.json` |
| activation_status | OBSERVE (config only) |
| available processes | None |
| missing processes | Checkout, subscriptions, referrals |
| data sources | Stripe (keys in recovered env) |
| approvals needed | None for test mode |
| Prompt 2 buildout | Build checkout flow |

### 19. System Health Department
| Field | Value |
|-------|-------|
| department_id | `system_health` |
| purpose | System monitoring, status |
| existing files | `src/components/SystemHealthPanel.jsx`, `src/data/systemHealthData.js` |
| activation_status | OBSERVE (mock data) |
| available processes | Status display (mock) |
| missing processes | Live monitoring, alerting |
| data sources | Local data files (mock) |
| approvals needed | None |
| Prompt 2 buildout | Connect to live Supabase |

### 20. Ray Review Department
| Field | Value |
|-------|-------|
| department_id | `ray_review` |
| purpose | Review queue, approvals |
| existing files | `src/components/RayReviewCenter.jsx`, `src/lib/rayReviewQueue.ts` |
| activation_status | OBSERVE (mock data) |
| available processes | Review display (mock) |
| missing processes | Real review items, approval flow |
| data sources | Local data files (mock) |
| approvals needed | Ray review |
| Prompt 2 buildout | Connect to real review items |
