# Nexus Not Good Enough — Action Plan

**Generated**: 2026-07-05
**Current Score**: 76/100 (PARTIAL_ACTIVE)
**Target Score**: 88/100 (ACTIVE_WITH_BLOCKERS)

---

## Priority Actions

### 1. Add Telegram Env Vars (+5 points)
**File**: `.env`
```
TELEGRAM_BOT_TOKEN=<from @BotFather>
TELEGRAM_ADMIN_CHAT_ID=<Ray's chat ID>
```
**Impact**: Telegram becomes live operator console

### 2. Verify Supabase via Browser (+5 points)
**Steps**:
1. Open app in browser
2. DevTools → Network tab
3. Navigate to page with Supabase queries
4. Verify 200 responses
5. Update report

**Impact**: Supabase classification moves to VERIFIED_BROWSER_READS

### 3. Build Client Portal Premium Shell (+10 points)
**Scope**:
- Premium no-scroll desktop layout
- Top navigation
- Hermes Guidance panel
- Rounded white cards, blue/teal accents
- Guided journey steps
- Resources/Affiliates section

**Impact**: Client Portal moves from 50 to 80+

### 4. Add Stripe Test-Mode Keys (+5 points)
**File**: `.env`
```
STRIPE_SECRET_KEY=<from Stripe dashboard, test mode>
STRIPE_WEBHOOK_SECRET=<from Stripe dashboard, test mode>
VITE_STRIPE_PUBLISHABLE_KEY=<from Stripe dashboard, test mode>
STRIPE_TEST_MODE=true
```
**Impact**: Paywall foundation active

### 5. Build NotebookLM Import Parser (+2 points)
**Scope**: Parse NotebookLM export bundles
**Impact**: Research pipeline complete

---

## Timeline

| Action | Estimated Effort | Dependencies |
|--------|-----------------|-------------|
| Telegram env | 5 minutes | @BotFather bot creation |
| Supabase verify | 10 minutes | Browser access |
| Client Portal shell | 2-4 hours | Design decisions |
| Stripe keys | 5 minutes | Stripe account |
| NotebookLM parser | 1-2 hours | None |

---

## Projected Score After Actions

| Category | Current | After | Change |
|----------|---------|-------|--------|
| Telegram | 80 | 85 | +5 |
| Supabase | 70 | 75 | +5 |
| Client Portal | 50 | 80 | +30 |
| Paywall | 30 | 60 | +30 |
| Research | 60 | 62 | +2 |
| **Overall** | **76** | **88** | **+12** |
