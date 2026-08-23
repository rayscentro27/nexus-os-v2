# Nexus Product Evolution Loop

Status: operational pilot orchestration layer. It is not a scheduler, agent
brain, approval system, work-order store, or deployment authority.

## Purpose

Ray supplies a bounded product outcome. Nexus then runs a contract-driven
research, build, test, browser-evaluation, critic, repair, regression, and
reporting sequence over the existing certified systems.

## Mission contract

Each mission records: goal, user-visible outcome, acceptance criteria, locked
systems, allowed files, capability candidates, security boundaries, license
requirements, cost ceiling, cycle limit (1–5), deployment policy, and human-only
gates. The reusable implementation is `scripts/nexus_product_evolution/loop.py`.

Callbacks are explicit stage adapters. The loop does not execute arbitrary
shell, choose a new model, create a scheduler, or bypass approvals. If an
existing governed work order is appropriate, the mission may reference it;
mission receipts remain evidence of orchestration, not a new canonical store.

## Bounded repair

Each cycle runs only the stages supplied by the mission. A failed stage is
classified, fingerprinted, and offered once to a repair callback. Identical
failures are not retried indefinitely. The default maximum is five cycles.
The loop stops with `PASS`, `PARTIAL` for a genuine human/credential/approval
blocker, or `FAIL` for an unresolved implementation/unknown failure.

Failure classes: `IMPLEMENTATION_BUG`, `ENVIRONMENT_BLOCKER`,
`CREDENTIAL_BLOCKER`, `PROVIDER_BLOCKER`, `LICENSE_BLOCKER`,
`CAPACITY_BLOCKER`, `HUMAN_HARDWARE_TEST_REQUIRED`, `APPROVAL_REQUIRED`, and
`UNKNOWN`.

## Critic gate

The critic receives the contract and stage evidence. Mission critics score
completion, friction/clicks, hierarchy, viewport, responsive behavior,
accessibility, errors/empty states, truthfulness, security, performance,
regression safety, design consistency, mobile use, and agent boundaries.
Screenshots and interaction traces are preferred evidence where browser
automation is available. A click budget is a hard acceptance criterion.

## Reporting and deployment

Telegram is a reporting channel only and uses the existing certified Hermes
bot. It receives start, milestone, blocker, and final summaries; tokens and
private content are never printed. Production deployment remains subject to
the repository's existing governance and rollback policy. Preview-first is
the default.

Future invocation shape:

```text
goal: Reduce first-login client onboarding friction
surface: Client Portal
acceptance: next step visible in 5 seconds; no fake metrics; mobile tests pass
constraints: preserve tenant isolation; max 3 cycles; preview first
```

