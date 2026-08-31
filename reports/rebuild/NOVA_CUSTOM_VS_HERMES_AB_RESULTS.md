# Nova Custom vs Hermes Shadow A/B Results

| Prompt class | Current custom path | Hermes shadow path | Result |
|---|---|---|---|
| Simple conversation | Existing Nova graph/OpenRouter | Same Nova SOUL through Hermes | PASS: natural answer, no tool |
| Self-contained recommendation | Custom model call | Hermes native model call | PASS: selected Option C with rationale |
| Current web research | Custom envelope/shared capability | Hermes native web tool | PARTIAL: tool executed; Brave returned HTTP 402 |
| Nexus capability read | Custom shared capability | Bounded Hermes Nexus read adapter | PASS: registry returned with provenance |
| Alpha challenge | Custom Alpha intake | Bounded Hermes adapter | PASS: Alpha execution/receipt/result returned |
| Multi-resource strategy | Custom continuation | Hermes native continuation | PARTIAL: Nexus succeeded; web provider failed |

Additional native delegation probe: Hermes `delegate_task` executed and its
child result returned to Nova's same reasoning context. This proves generic
Hermes delegation, not durable Alpha lifecycle parity.

The comparison must use the same model baseline and must record tool execution,
evidence, recommendation, failures, leakage, continuity, and custom/native path.
This document intentionally does not claim shadow parity or cutover readiness;
web provider repair and full Telegram-equivalent A/B proof remain outstanding.
