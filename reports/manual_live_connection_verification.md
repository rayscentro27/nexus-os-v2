# Manual Live Connection Verification

**Date:** 2026-07-01
**How to verify each live connection path**

---

## 1. Ray Review — Live Supabase Persistence

### Steps:
1. Open `/#rayreview` in the live app
2. Look at the SourceBanner at the top — you should see a source label
   - If "Live Supabase" — cards are loaded from `task_requests` table
   - If "Static snapshot" — Supabase has 0 ray_review_item rows (using fallback)
3. Note the card count and source label
4. Click any card's **Approve** button
5. Watch for the receipt toast — it should show:
   - `Source: live_supabase` if persisted to Supabase
   - `Source: local_only` if localStorage only
6. **Reload the page**
7. Check if the approved card still shows as approved
   - If Supabase live: YES (persisted server-side)
   - If static fallback: NO (localStorage may be cleared)
8. Open browser DevTools → Application → Local Storage
9. Find key `nexus-ray-review-decisions-v2`
10. Clear it manually
11. Reload the page
12. If Supabase live: approved card should STILL show approved
13. If static fallback: approved card will revert to pending

### What to report:
- Source label shown: ___________
- Card count: ___________
- Receipt source: ___________
- Persisted after reload: yes/no
- Persisted after localStorage clear: yes/no

---

## 2. Business Opportunities — Live-First Loading

### Steps:
1. Open `/#opportunity` in the sidebar
2. Look at the SourceBanner at the top — should show:
   - "Live Supabase" — data loaded from `business_opportunities` table
   - "Static snapshot" — Supabase has 0 rows, using bundled `businessOpportunitiesData.js`
   - "Mismatch" — UI has static items but Supabase is empty (expected until seeded)
3. Note the opportunity count
4. Click any opportunity row — detail drawer should open
5. Check the "Data source" field in the drawer — should match the banner
6. Click "Ask Hermes" — Hermes should reference the same data source
7. Type in Hermes: "Is the Business Opportunities page live or static?"
8. Hermes should explain the source (via `hermesSourceReasoner`)

### What to report:
- SourceBanner label: ___________
- Opportunity count: ___________
- Detail drawer data source: ___________
- Hermes response on source: ___________

---

## 3. Research Engine — Live-First Loading

### Steps:
1. Open `/#research` in the sidebar
2. Look at the SourceBanner at the top
3. Note the candidate count and source label
4. Click any candidate row — detail drawer should show data source
5. In Hermes, type: "Compare the Research Engine page data to Supabase"
6. Hermes should explain any mismatch

### What to report:
- SourceBanner label: ___________
- Candidate count: ___________
- Detail drawer data source: ___________
- Hermes comparison response: ___________

---

## 4. Monetization — Live-First Loading

### Steps:
1. Open `/#monetization` in the sidebar
2. Look at the SourceBanner at the top
3. Note the offer count and source label
4. Click any offer row — detail drawer should show data source
5. In Hermes, type: "Is the Monetization page live or static?"
6. Hermes should explain the source

### What to report:
- SourceBanner label: ___________
- Offer count: ___________
- Detail drawer data source: ___________
- Hermes response: ___________

---

## 5. Clients — Live-First Loading

### Steps:
1. Open `/#clients` in the sidebar
2. Look at the SourceBanner at the top
3. Note the client count and source label
4. Click the client row (Julius Erving) — detail drawer should show data source
5. In Hermes, type: "Is the Clients page live or static?"
6. Hermes should explain the source

### What to report:
- SourceBanner label: ___________
- Client count: ___________
- Detail drawer data source: ___________
- Hermes response: ___________

---

## 6. Hermes — Source Reasoning

### Steps:
1. Open the Hermes chat panel (Workroom or inline drawer)
2. Type: "Is this live or static?"
   - Should explain current page source
3. Type: "Why does this page show data but Supabase says none?"
   - Should explain split-brain if applicable
4. Type: "Compare page data to Supabase"
   - Should compare current section's page data vs Supabase
5. Type: "Which sections are live?"
   - Should list all loaded sections and their status
6. Type: "What do we need to sync?"
   - Should explain seed requirements

### What to report:
- "Is this live or static?" response: ___________
- "Why does this page show data?" response: ___________
- "Compare page to Supabase" response: ___________
- "Which sections are live?" response: ___________
- "What do we need to sync?" response: ___________

---

## 7. Hermes — Live Supabase Context

### Steps:
1. In Hermes chat, type: "can you check Supabase"
2. Look at the response — it should either:
   - Show live data from Supabase tables (if connected + authenticated)
   - Show honest "Supabase not configured" or "No auth session" message
3. Type: "what approvals are pending"
4. Look for live data or honest fallback
5. Type: "did my approval persist"
6. Should reference Supabase or localStorage source

### What to report:
- Response for "can you check Supabase": ___________
- Response shows live data: yes/no
- Response for "what approvals are pending": ___________
- Source label visible: ___________

---

## 8. Hermes — Web Search

### Steps:
1. In Hermes chat, type: "can you search the internet"
2. Look at the response:
   - If `VITE_HERMES_SEARCH_ENABLED=true`: should say search is available
   - If not enabled: should say "cannot search the internet" and offer to create research task
3. Type: "search the internet for AI news"
4. If enabled: should return search results with citations
5. If not enabled: should say endpoint not configured

### What to report:
- Response for "can you search the internet": ___________
- Search actually works: yes/no
- VITE_HERMES_SEARCH_ENABLED value: ___________

---

## 9. Quick Verification Checklist

| Check | Expected | Actual |
|-------|----------|--------|
| `/#rayreview` SourceBanner visible | Yes | |
| Ray Review receipt shows Supabase table | If live | |
| Approved card persists after reload | If Supabase live | |
| Approved card persists after localStorage clear | If Supabase live | |
| `/#opportunity` SourceBanner visible | Yes | |
| Business Opportunities detail shows data source | Yes | |
| `/#research` SourceBanner visible | Yes | |
| Research Engine detail shows data source | Yes | |
| `/#monetization` SourceBanner visible | Yes | |
| Monetization detail shows data source | Yes | |
| `/#clients` SourceBanner visible | Yes | |
| Clients detail shows data source | Yes | |
| Hermes "Is this live or static?" honest | Yes | |
| Hermes "Compare page to Supabase" explains mismatch | Yes | |
| Hermes "Which sections are live?" lists status | Yes | |
| Hermes "can you check Supabase" answer | Honest | |
| Hermes "can you search the internet" answer | Honest | |

---

## 10. Split-Brain Detection

### Steps:
1. Open any section (e.g., `/#opportunity`)
2. If SourceBanner shows "Static snapshot" or "Mismatch":
   - The UI has bundled static data
   - Supabase has 0 rows for that table
   - This is expected until the seed plan is executed
3. Ask Hermes: "Why does this page show data but Supabase says none?"
4. Hermes should explain:
   - The page reads from a bundled data file
   - Supabase has no live rows
   - The fix is to seed the table or wire the page
5. Ask Hermes: "What do we need to sync?"
6. Hermes should reference `reports/static_to_supabase_seed_plan.md`

### What to report:
- SourceBanner shows mismatch: yes/no
- Hermes explains split-brain: yes/no
- Hermes references seed plan: yes/no
