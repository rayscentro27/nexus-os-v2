# Nexus Operating Dashboard Blueprint

**Generated**: 2026-07-05

---

## Recommended Future Sections

### 1. Today Overview
- Current date/time
- Active processes count
- Pending Ray Review items
- System health summary
- Last 24h activity count

### 2. Revenue/Funnel Status
- Got Funding form submissions (last 7d)
- Lead capture count
- Conversion rate
- Active funnels
- Revenue this month

### 3. Lead Capture
- New leads (today/week/month)
- Lead source breakdown
- Follow-up status
- Lead quality scores

### 4. Process Runs
- Active processes
- Completed today
- Failed/blocked
- Next scheduled run
- Process health indicators

### 5. System Health
- Supabase connection status
- Edge function status
- Netlify function status
- External connector status
- Error rate (last 24h)

### 6. Alpha Brain Status
- Last analysis run
- Opportunities in queue
- Research items processed
- Cost estimate (tokens/credits)
- Provider status

### 7. Nexus Hermes Recommendations
- Top 3 recommended actions
- Blocked items needing Ray decision
- Process optimization suggestions
- Risk alerts

### 8. Ray Review/Approvals
- Pending items count
- Urgent items
- Recently approved
- Recently rejected
- Average review time

### 9. Research Opportunities
- New items (today/week)
- Score distribution
- Top opportunities by score
- Research sources active

### 10. Client Portal Readiness
- Active clients
- Completion rates
- Blocked clients
- Average readiness score

### 11. Automation Modes
- Active schedulers
- Last run times
- Failed runs
- Upcoming scheduled runs

### 12. Connector Status
- Supabase: connected/disconnected
- Resend: configured/unconfigured
- Stripe: configured/unconfigured
- Oanda: connected/disconnected
- Meta: connected/disconnected
- YouTube: configured/unconfigured

### 13. Next Recommended Actions
- Top 3 actions for Ray
- Priority ranking
- Estimated effort
- Dependencies

---

## Layout Recommendation

```
┌─────────────────────────────────────────────────────┐
│  TODAY OVERVIEW           │  SYSTEM HEALTH          │
│  - Active processes: 12   │  - Supabase: ✓          │
│  - Pending reviews: 3     │  - Netlify: ✓           │
│  - Last 24h: 45 runs      │  - Connectors: 4/6     │
├───────────────────────────┼─────────────────────────┤
│  REVENUE/FUNNEL           │  RAY REVIEW             │
│  - Leads today: 2         │  - Pending: 3           │
│  - Conversion: 12%        │  - Urgent: 1            │
│  - Revenue: $0            │  - Avg time: 2h         │
├───────────────────────────┼─────────────────────────┤
│  PROCESS RUNS             │  ALPHA BRAIN            │
│  - Active: 5              │  - Last run: 2h ago     │
│  - Completed: 38          │  - Queue: 12            │
│  - Failed: 0              │  - Cost: $0.05          │
├───────────────────────────┼─────────────────────────┤
│  RESEARCH                 │  CLIENT PORTAL          │
│  - New today: 8           │  - Active: 1            │
│  - Top score: 85          │  - Readiness: 45%       │
│  - Sources: 5             │  - Blocked: 0           │
├───────────────────────────┼─────────────────────────┤
│  NEXT ACTIONS             │  HERMES RECOMMENDATIONS │
│  1. Verify Supabase live  │  1. Run research cycle   │
│  2. Test email sending    │  2. Review opportunities │
│  3. Connect Command Ctr   │  3. Update client data   │
└───────────────────────────┴─────────────────────────┘
```

---

## Implementation Notes

- Use existing components where possible
- Connect to live Supabase data
- Add auto-refresh (30s intervals)
- Mobile responsive (stack sections)
- Dark mode support (existing CSS variables)
- Graceful degradation if data unavailable
