# Nexus Overnight Research Audit — 2026-09-19

## Window and runtime

- Audit window: `2026-09-18T23:09:33.015771+00:00` through
  `2026-09-19T13:13:39.678200+00:00`.
- Runtime owner: `com.nexus.continuous-loop`.
- Runtime was active under the existing daemon; no duplicate runtime was
  created.
- Heartbeat at the end of the audit was `ACTIVE`, `REAL`, with
  `resume_without_manual_restart=true`.
- The exact process start time is not persisted by launchd, so uptime is
  reported as the observed audit duration: approximately 14h 04m.

## What actually ran

The Research execution ledger recorded 131 bounded execution IDs in the
window. The ledger contained 911 lifecycle records because each execution
records queued, claimed, running, source-selected, evidence-ready, and
completed transitions.

- Jobs started: 131
- Jobs completed: 115 terminal completions in the ledger window
- Retryable failures: 16
- Blocked-external jobs: 0 terminal blocks in this window
- Productive audits: 15 hourly audits in the persisted session report
- Self-resume events: recurring `CONTINUE_INCOMPLETE_OBJECTIVE` checkpoints
- Stalls/recoveries: no runtime stop; source-level retryable failures were
  isolated and the daemon continued

The work was not uniformly valuable. There were 67 full processed results,
48 unchanged duplicates, 16 retryable failures, and 4 insufficient-source
outcomes. The queue ended with 10 complete, 3 monitoring, and 14 retryable
items before the CRJ repair added new bounded candidates.

## Lane results

- Customer demand: no new deduplicated `research_needs` record was created in
  this exact window. This is a material gap, not a success claim.
- Funding/Clyde: SBA/funding sources were refreshed and processed, but no new
  decision-grade Clyde handoff was created in the window.
- SEO: 19 SEO-mode processing records; the governed SEO lane produced stored
  evidence and refresh output.
- GitHub/capability: 24 GitHub-oriented processing records across GitHub and
  platform-capability lanes; these were mostly source refreshes and did not
  produce a new qualified monetization route in this window.
- Monetization: no new deduplicated monetization opportunity record in the
  exact window.
- YouTube: the persisted audits show four canonical channels represented and
  checked as a scheduled set; one video pipeline artifact had a transcript.
  Caption/media restrictions remain item-level blockers, especially for
  Stedman. No channel failure stopped other lanes.

## Alpha and handoffs

Two Alpha evaluations were recorded in the window and both were `REJECTED`.
There were no new Research v2 Alpha reviews or Research v2 department
handoffs in the exact window. Rejection was not treated as Research failure,
but the outputs did not advance to a department result during this audit.

## CRJ repair

Root cause: a topic/entity research objective was serialized as
`source_type=RESEARCH_OBJECTIVE` with an empty `source_url`, then routed to the
URL-only `research_document_pipeline.web_page` processor. It failed with
`unknown url type: ''`.

Repair: the existing queue now preserves bounded `source_candidates`, and the
existing Research worker selects a real public candidate for objective-level
work. Four public CRJ candidates were discovered through the existing
Research acquisition boundary. Two completed successfully:

- `crj-goclear-capability-research-v1:crj-home` → package
  `package_3a72678b46c54f8469de`
- `crj-goclear-capability-research-v1:crj-automation` → package
  `package_acbe0a7c18e4f9d98282`

Two bounded candidates remain queued. The parent objective is `WAITING`, not
falsely complete. Alpha handoff is pending the existing Alpha consumer; no
manual CRJ analysis was substituted.

## Value assessment

`OVERNIGHT_RESEARCH_VALUE=LOW` for company advancement, with `MEDIUM`
surveillance value. Nexus saved time on source refresh, SEO monitoring,
YouTube checks, and duplicate suppression. It did not produce enough new
customer-demand, monetization, Clyde, or Alpha-routed intelligence to call the
overnight period highly productive.

Non-productive patterns:

- repeated unchanged-source processing;
- scheduled items reaching evidence storage without Alpha invocation;
- retryable source failures without immediate objective-aware rerouting;
- the CRJ empty-source serialization defect;
- queue state that could report healthy while no new customer need was formed.

Dropped handoffs: no new department handoff was created in the exact window.
Repeat failures: 16 retryable execution failures, plus the CRJ source defect.

## Next action

Continue the queued CRJ candidates through the existing Research worker, then
allow Alpha to review the completed evidence. Keep customer-demand discovery
and monetization lanes active; do not treat process uptime or duplicate
suppression as sufficient productivity.
