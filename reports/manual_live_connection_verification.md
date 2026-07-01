# Manual Live Connection Verification

**Date:** 2026-06-30
**How to verify each live connection path**

---

## 1. Ray Review — Live Supabase Persistence

### Steps:
1. Open `/#rayreview` in the live app
2. Look at the toolbar: you should see a source label
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

## 2. Hermes — Live Supabase Context

### Steps:
1. Open the Hermes chat panel (Workroom or inline drawer)
2. Type: `can you check Supabase`
3. Look at the response — it should either:
   - Show live data from Supabase tables (if connected + authenticated)
   - Show honest "Supabase not configured" or "No auth session" message
4. Type: `what approvals are pending`
5. Look for live data or honest fallback
6. Type: `what tables can you see`
7. Should list accessible tables or say Supabase not available
8. Type: `did my approval persist`
9. Should reference Supabase or localStorage source

### What to report:
- Response for "can you check Supabase": ___________
- Response shows live data: yes/no
- Response for "what approvals are pending": ___________
- Source label visible: ___________

---

## 3. Hermes — Web Search

### Steps:
1. In Hermes chat, type: `can you search the internet`
2. Look at the response:
   - If `VITE_HERMES_SEARCH_ENABLED=true`: should say search is available
   - If not enabled: should say "cannot search the internet" and offer to create research task
3. Type: `search the internet for AI news`
4. If enabled: should return search results with citations
5. If not enabled: should say endpoint not configured

### What to report:
- Response for "can you search the internet": ___________
- Search actually works: yes/no
- VITE_HERMES_SEARCH_ENABLED value: ___________

---

## 4. Research Engine — Supabase Write Proof

### Steps:
1. Open `/#research` in the sidebar
2. Look at the source label at the top
   - "Live Supabase" means data loaded from `research_sources` or `task_requests`
   - "Static snapshot" means data from `researchEngineData.js`
3. Check the candidate count
4. In terminal, check if launchd is running:
   ```bash
   launchctl list | grep nexus
   ```
5. Check last run timestamp in `reports/runtime/continuous_loop_history.jsonl`
6. Check if Supabase has research rows:
   ```bash
   # In Supabase SQL editor (safe read-only):
   SELECT count(*) FROM research_sources;
   SELECT count(*) FROM task_requests WHERE task_type = 'research_candidate';
   ```

### What to report:
- Source label on research page: ___________
- Candidate count: ___________
- launchd running: yes/no
- Last continuous loop run: ___________
- research_sources row count: ___________
- research_candidate task_requests count: ___________

---

## 5. Reports / CLI / Settings — Actionability

### Steps:
1. Open `/#reports`
2. Click any report row — should open details with summary, source, timestamp
3. Look for source labels: "static snapshot" or "live Supabase"
4. Open `/#cli`
5. Click any command row — should show details, copy button, safety explanation
6. Open `/#settings`
7. Click any setting — should show connection state, not silently toggle

### What to report:
- Reports show details on click: yes/no
- Reports have source labels: yes/no
- CLI commands show details: yes/no
- Settings show connection state: yes/no

---

## 6. System Health

### Steps:
1. Open `/#health`
2. Look at health items — each should show:
   - Component name
   - Status (ok/partial/failed)
   - Source label (static or live)
3. Click any item for details

### What to report:
- Health items have source labels: yes/no
- Items show details on click: yes/no

---

## 7. Quick Verification Checklist

| Check | Expected | Actual |
|-------|----------|--------|
| `/#rayreview` source label visible | Yes | |
| Ray Review receipt shows Supabase table | If live | |
| Approved card persists after reload | If Supabase live | |
| Approved card persists after localStorage clear | If Supabase live | |
| Hermes "can you check Supabase" answer | Honest | |
| Hermes "can you search the internet" answer | Honest | |
| Research page source label visible | Yes | |
| `launchctl list \| grep nexus` shows agents | Yes | |
| Reports page has source labels | Yes | |
| CLI page has source labels | Yes | |
| Settings page shows connection state | Yes | |
| Health page has source labels | Yes | |
