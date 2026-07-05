# Nexus YouTube Researcher Audit

**Generated**: 2026-07-05

---

## YouTube Research Infrastructure

### Data Files
| Location | Contents | Status |
|----------|----------|--------|
| `data/cache/youtube/api_metadata/` | 5 channel/video JSON files | Cached, not live |
| `data/cache/youtube/ytdlp_metadata/` | 5 yt-dlp extracted files | Cached, not live |
| `data/sources/youtube_transcripts/approved/` | Empty | No transcripts imported |
| `data/sources/youtube_transcripts/pending/` | 1 template file | Template only |
| `configs/youtube_engine_registry.json` | Engine config | Read-only |
| `configs/youtube_research_channels.json` | Channel watchlist | Read-only |
| `configs/youtube_source_targets.json` | Source targets | Read-only |
| `configs/youtube_quota_policy.json` | Quota policy | Read-only |

### Scripts
| Script | Purpose | Status |
|--------|---------|--------|
| `scripts/research/` (20+ files) | YouTube research operations | DRY_RUN capable |
| `scripts/activation/` | YouTube activation scripts | DRY_RUN capable |

### Reports
| Report | Location | Status |
|--------|----------|--------|
| YouTube research status | `reports/manual_publish/youtube_research_*.md` | Auto-generated |
| Cache status | `reports/manual_publish/` | Auto-generated |
| API connector audit | `reports/manual_publish/` | Auto-generated |
| Research scoring | `reports/manual_publish/` | Auto-generated |

---

## Watched Channels
From `data/cache/youtube/api_metadata/`:
1. Alec Delpuech
2. Credit Plug
3. Michael Ionita
4. Stedman Waiters
5. Video zbAmmnMh5ew (specific video)

---

## Transcript Availability
- **Approved transcripts**: None (empty directory)
- **Pending transcripts**: 1 template file
- **Status**: No real transcripts have been imported

---

## Scoring Logic
- `configs/research_scoring_policy.json` defines scoring rules
- Alpha scoring engine: `src/hermes/alpha/alphaScoring.ts`
- Research scoring exists but not connected to live YouTube data

---

## Data Flow
```
YouTube API (YOUTUBE_API_KEY)
  → data/cache/youtube/api_metadata/
  → scripts/research/ (processing)
  → reports/manual_publish/ (reports)
  → reports/runtime/ (JSON data)
  → Nexus OS2 UI (research panel) [NOT CONNECTED]
  → Alpha brain (research inbox) [NOT CONNECTED]
  → Nexus Hermes (research route) [NOT CONNECTED]
```

---

## Nexus OS2 UI Visibility
- Research panel exists in navigation (`nexusNavigationConfig.js`)
- `ResearchEnginePanel.jsx` component exists
- Data source: `src/data/researchEngineData.js` (static/mock)
- **Verdict**: UI exists but shows mock data, not live YouTube research

## Alpha Visibility
- `src/hermes/alpha/alphaResearchFileAdapter.ts` exists
- Research inbox directory: `hermes_alpha/research_inbox/youtube/` (empty README)
- **Verdict**: Foundation exists but no live data flows to Alpha

## Nexus Hermes Visibility
- Research route exists in Hermes intent classifier
- `src/hermes/nexus/nexusResearchAdapter.ts` exists
- **Verdict**: Routing exists but no live data connection

---

## Classification
- **Activation Mode**: DRY_RUN
- **Score**: 55/100
- **Issue**: YouTube API key present, scripts exist, but no live data pipeline connected to UI/Alpha/Hermes
- **Next Action**: Test YouTube API call, verify cache population, connect to research panel
