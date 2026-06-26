# Nexus Ray Review Queue

- generated_at: 2026-06-26T16:30:12.628069+00:00
- dry_run: True
- ok: True
- publish_send_trade_deploy: false
- scheduler_started: false
- external_ai_called: false

## Counts
- candidates_scanned: 55
- qualifies: 25
- skipped_autonomous_or_other: 12
- duplicates: 0
- created: 0
- failed: 0

## Top Recommendations
- medium / connector_setup: Enable one Facebook GoClear/Apex test post — Review this connector setup before any execution path.
- medium / social_post: Approve manual publish package: GoClear Credit Readiness — Facebook post — manual package — Review this social post before any execution path.
- medium / campaign_publish: IG: readiness before applying — Review this campaign publish before any execution path.
- medium / email_send: Carousel: the bankability stack — Review this email send before any execution path.
- medium / email_send: Lead magnet: Funding Readiness Checklist — Review this email send before any execution path.
- medium / social_post: Approve sample Facebook readiness post — Review this social post before any execution path.
- medium / campaign_publish: Review sample creative brief before drafting assets — Review this campaign publish before any execution path.
- medium / social_post: Approve first Facebook publish test after Day 3 — Review this social post before any execution path.
- medium / social_post: Approve first Facebook publish test after Day 3 — Review this social post before any execution path.
- urgent / scheduler_activation: GoClear revenue signal: Approval decision: Enable one Facebook GoClear/Apex test post — Review this scheduler activation before any execution path.

## Verification

- `build_ray_review_queue.py` dry-run: passed.
- `generate_ray_review_report.py` dry-run: passed; 10 pending decisions in the report, including 1 urgent, 8 campaign/send decisions, 1 scheduler decision, and 1 connector decision.
- `capture_ray_decision.py` dry-run: passed; 0 live updates.
- `npm run build`: passed.
- `npm run nexus:watch`: passed; email send false, broker connection false, scheduler not started.

## Live Run

The optional live queue build was not run. No `ray_review_item` rows were created in this pass.

## Next Recommendation

Run the builder in dry-run mode after the next weekly research report, then create a bounded live queue only if the candidates are true decisions.
