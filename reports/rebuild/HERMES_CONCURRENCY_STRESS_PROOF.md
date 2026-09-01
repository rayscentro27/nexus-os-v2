# Concurrency stress proof

The deterministic harness acquired a same-chat lock, started a competing
acquisition, verified the contender remained blocked, released the owner, and
verified the contender acquired the lock. A dead-owner lock was recovered.

Results: TURN1 before TURN2 before TURN3 is enforced by the lock boundary;
same-session state cannot be processed concurrently through this path; separate
sessions remain eligible for concurrent processing. Focused tests passed,
including progress-only rejection and MCP/currentness regressions.
