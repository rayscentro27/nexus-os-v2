# Nexus Credit & Funding Research Adapter v1 — Test Report

**Generated**: 2026-07-03

---

## Test Suite: `tests/nexus_research_adapter_v1.test.ts`

### Test Categories

| Category | Tests | Status |
|----------|-------|--------|
| Approved Folder Enforcement | 5 | ✅ |
| SHA-256 and Metadata | 2 | ✅ |
| Classification and Routing | 4 | ✅ |
| Safety Checks | 4 | ✅ |
| No-Supabase and Isolation Guards | 5 | ✅ |
| Empty Inbox Handling | 1 | ✅ |
| Fixture Labeling | 2 | ✅ |
| Draft Outputs | 2 | ✅ |
| Category Routing Table | 11 | ✅ |
| Path Validation | 15 | ✅ |
| **Total** | **51** | **✅** |

### Test Details

#### 1. Approved Folder Enforcement
- Adapter only reads approved Nexus Research inbox folders ✅
- Adapter rejects files outside approved folders ✅
- Adapter rejects path traversal ✅
- Adapter rejects blocked file types ✅
- Adapter reads Markdown only ✅

#### 2. SHA-256 and Metadata
- Adapter produces SHA-256 hash (64 hex chars) ✅
- Adapter produces metadata schema with all 20 required fields ✅

#### 3. Classification and Routing
- Credit utilization → Scorecard recommendation draft ✅
- Business funding → Funding Readiness Plan draft ✅
- Affiliate → requires Ray Review ✅
- Client education → requires approval ✅

#### 4. Safety Checks
- Guarantee language is flagged ✅
- Risky artifact becomes admin-only ✅
- Compliance flags are detected ✅
- Safe artifact is not admin-only ✅

#### 5. No-Supabase and Isolation Guards
- No Supabase import in Alpha files ✅
- Nexus adapter does not connect Supabase ✅
- No Oanda import ✅
- No external provider calls ✅
- No send/publish/charge/trade actions ✅

#### 6. Empty Inbox Handling
- Empty inbox is valid and honestly reported ✅

#### 7. Fixture Labeling
- Fixture artifacts are clearly labeled as fixtures ✅
- Non-fixture artifacts are marked unverified ✅

#### 8. Draft Outputs
- Admin note includes all required fields ✅
- Ray Review draft includes blocked actions ✅

#### 9. Category Routing Table
- All 11 categories route to correct targets ✅

#### 10. Path Validation
- All 10 approved categories accepted ✅
- External paths rejected ✅
- Traversal paths rejected ✅
- Blocked extensions rejected ✅
