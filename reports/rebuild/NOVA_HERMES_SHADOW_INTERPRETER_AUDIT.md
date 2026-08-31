# Nova Hermes Shadow Interpreter Audit

Campaign: `HG-WP6.5-NOVA-HERMES-TELEGRAM-SHADOW-RUNTIME-PARITY-AND-FANOUT-REPAIR-20260831-01`

The canonical Nova worker uses `.venv-agent-platform/bin/python3`, Python 3.14.5. In that environment `import openai` and `import run_agent` both fail. The existing Hermes environment uses `/Users/raymonddavis/.hermes/hermes-agent/venv/bin/python`, Python 3.11.15; `openai` and Hermes `run_agent.py` import successfully. No dependency was installed or modified.

| Environment | Python | OpenAI | Hermes runtime | Result |
|---|---:|---|---|---|
| Agent platform | 3.14.5 | MISSING | MISSING | unsuitable for shadow |
| Hermes venv | 3.11.15 | PASS | PASS | supported shadow runtime |

Selected strategy: **Option B** — keep the canonical primary worker in its current environment and invoke the existing Hermes runner through a bounded subprocess. This preserves primary dependency risk and provides rollback by disabling the existing A/B flag.

No secrets are copied into the child environment. The child receives the protected runtime-env path and secret-free update/message correlation values, then loads provider credentials itself.
