# Nexus Existing Repo Tool Queue Audit

**Generated**: 2026-07-03

---

## Tools Available in nexus-os-v2

### Build Tools
| Tool | Version | Purpose |
|------|---------|---------|
| TypeScript | 5.8.3 | Type checking |
| Vite | 6.3.5 | Build/bundle |
| Vitest | 3.2.1 | Testing |
| ESLint | 9.28.0 | Linting |
| Prettier | 3.5.3 | Formatting |

### Runtime Tools
| Tool | Version | Purpose |
|------|---------|---------|
| Node.js | 22.22.3 | Runtime |
| React | 19.1.0 | UI framework |
| Supabase JS | 2.49.1 | Database client |
| Tailwind CSS | 4.1.7 | Styling |

### AI/ML Tools
| Tool | Version | Purpose |
|------|---------|---------|
| Ollama | 0.14.0 | Local LLM |
| Groq SDK | 3.3.0 | Cloud LLM |
| OpenAI SDK | 5.3.0 | Cloud LLM |
| Anthropic SDK | 0.51.0 | Cloud LLM |

### Integration Tools
| Tool | Purpose | Status |
|------|---------|--------|
| Supabase client | Database | Configured |
| Stripe SDK | Payments | Test mode |
| Resend | Email | Blocked (403) |
| Cloudflare | Tunnel | Active |
| YouTube API | Content | Cached |

---

## Tools NOT Available

| Tool | Status | Notes |
|------|--------|-------|
| Claude Code CLI | Not installed | opencode used instead |
| Docker | Not installed | No containerization |
| Terraform | Not installed | No IaC |
| Grafana | Not installed | No monitoring dashboards |
| Prometheus | Not installed | No metrics collection |

---

## Queue / Job Systems

| System | Location | Status |
|--------|----------|--------|
| Hermes Brain Pipeline | `src/lib/hermesBrainPipeline.ts` | Active in nexus-os-v2 |
| Nexus Research Worker | `~/nexus-ai/services/nexus-research-worker/` | launchd job exists |
| Nexus Orchestrator | `~/nexus-ai/services/nexus-orchestrator/` | launchd job exists |
| Mac Mini Worker | `~/mac-mini-worker/` | launchd job exists |
| Operations Scheduler | `~/nexus-ai/operations_center/scheduler.py` | launchd job exists |

---

## Recommendations

1. **Use existing tools**: Supabase, Groq, Ollama, Vite, Vitest — all configured and working
2. **Do not add new dependencies** unless absolutely necessary
3. **Reuse queue patterns** from nexus-ai research worker for Hermes Alpha content jobs
4. **Leverage existing Cloudflare tunnel** for Hermes gateway exposure
