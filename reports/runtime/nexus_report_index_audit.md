# Nexus Report Index Audit

**Generated**: 2026-07-05

---

## Report Directories

| Directory | Files | Types | Latest Date |
|-----------|-------|-------|-------------|
| `reports/runtime/` | 577 | JSON, MD | 2026-07-05 |
| `reports/manual_publish/` | 496 | MD | 2026-07-04 |
| `reports/hermes_alpha/` | 42 | MD, JSON | 2026-07-03 |
| `reports/alpha/` | 36 | MD | 2026-07-03 |
| `reports/operations/` | 31 | MD, JSON | 2026-07-03 |
| `reports/hermes_brain/` | 28 | MD | 2026-07-02 |
| `reports/marketing_assets/` | 24 | MD | 2026-07-02 |
| `reports/nexus_readiness/` | 17 | MD | 2026-07-01 |
| `reports/nexus_research/` | ~50 | MD, JSON | 2026-07-03 |
| `reports/activation/` | 19 | MD, JSON | 2026-07-01 |
| `reports/goclear_activation/` | 4 | MD | 2026-07-01 |
| `reports/auth/` | 3 | MD | 2026-06-30 |
| `reports/deployment/` | 2 | MD | 2026-06-30 |
| Root reports | ~70 | MD, JSON | 2026-07-04 |
| **Total** | **~1,620** | | |

---

## Latest Useful Reports by Category

### Operations
| Report | Path | Purpose |
|--------|------|---------|
| Operating cycle | `reports/manual_publish/daily_operating_cycle_latest.md` | Daily ops status |
| Evening closeout | `reports/manual_publish/evening_closeout_cycle_latest.md` | End of day |
| Operations status | `reports/nexus_operations_status_latest.md` | System status |
| Connector registry | `reports/operations/nexus_connector_registry_latest.json` | Connector status |

### Research
| Report | Path | Purpose |
|--------|------|---------|
| Research to money | `reports/manual_publish/research_to_money_pipeline_latest.md` | Research pipeline |
| YouTube research | `reports/manual_publish/youtube_research_*.md` | YouTube status |
| NotebookLM | `reports/manual_publish/notebooklm_*.md` | NotebookLM status |

### Alpha/Hermes
| Report | Path | Purpose |
|--------|------|---------|
| Second brain index | `reports/hermes_second_brain_index_latest.json` | 400-item index |
| Alpha audit | `reports/hermes_alpha/alpha_audit_conclusions.md` | Alpha status |
| Hermes routing | `reports/hermes_brain_routing_rebuild_latest.md` | Routing status |

### Client Portal
| Report | Path | Purpose |
|--------|------|---------|
| Client portal build | `reports/manual_publish/client_portal_backend_build_latest.md` | Backend status |
| Client portal safety | `reports/manual_publish/client_portal_safety_latest.md` | Safety status |

### Trading
| Report | Path | Purpose |
|--------|------|---------|
| Trading activation | `reports/manual_publish/trading_activation_latest.md` | Trading status |
| Oanda audit | `reports/manual_publish/oanda_vibe_trading_audit_latest.md` | Oanda status |

---

## Report Readiness for Alpha/Hermes

| Report Type | Alpha Readable? | Hermes Readable? | Has Summary? | Has Evidence? |
|-------------|----------------|------------------|--------------|---------------|
| Runtime JSON | Yes | Yes | Varies | Yes |
| Manual publish MD | Yes | Yes | Yes | Yes |
| Hermes brain MD | Yes | Yes | Yes | Yes |
| Marketing assets MD | Yes | Yes | Yes | Yes |
| Activation MD/JSON | Yes | Yes | Yes | Yes |

---

## Recommendation for Prompt 2

1. Create unified report index (machine-readable)
2. Add timestamps to all reports
3. Add status fields to all reports
4. Add next_action fields to all reports
5. Wire reports to Alpha/Hermes research inbox
6. Add report freshness scoring
