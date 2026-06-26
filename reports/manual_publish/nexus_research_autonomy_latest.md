# Nexus Research Autonomy + Reporting + Hermes Memory

Generated: 2026-06-26

## Summary

Nexus now documents and implements the split between autonomous internal research and approval-gated execution.

Internal research/scoring/routing/reporting can run without asking Ray to approve every item. Publishing, sending, contacting, spending, live trading, scheduler activation, production changes, and sensitive external-tool use remain approval-gated.

## Added

- `src/config/nexusResearchAutonomyPolicy.ts`
- `src/config/hermesDecisionMemory.ts`
- `src/lib/hermesDecisionMemory.ts`
- `src/lib/nexusResearchReports.ts`
- `scripts/research/generate_weekly_research_report.py`
- `scripts/research/generate_department_top_report.py`
- `scripts/research/capture_ray_feedback.py`

## Approval Policy

`src/config/nexusActionPolicy.ts` now treats `needs_review` as internal review, not an automatic Approvals item. Only hard execution triggers force approval.

Research enrichment now preserves risk flags and internal review notes while keeping `approval_required=false` for internal research cards.

## Command Center

Command Center now shows:

- internal research count
- approval-needed count
- top report count
- research autonomy status copy

## Verification Commands

```bash
python3 scripts/research/generate_weekly_research_report.py --dry-run --limit 10 --no-external-ai --json
python3 scripts/research/generate_department_top_report.py --department youtube_transcripts --dry-run --limit 10 --no-external-ai --json
python3 scripts/research/capture_ray_feedback.py --dry-run --feedback "Prioritize business funding videos that can become GoClear SEO content." --no-external-ai --json
```

## Dry-Run Results

- Weekly research report: passed, 9 source reports, 27 items considered, 10 top items, 0 created.
- Department top report: passed, 2 source reports, 4 items considered, 4 top items, 0 created.
- Ray feedback capture: passed, 1 memory candidate, 0 created.
- `npm run build`: passed.
- `npm run nexus:watch`: passed.

## Safety

- Scheduler activation: disabled.
- Publish/send/trade/deploy: not performed.
- External AI: not used.
- Live campaign execution: not performed.
- Broker execution: blocked.

## Next Recommendation

Add the Ray Review Queue so Ray sees only true decision items: campaign approval, scheduler approval, outbound contact/send/publish, production change, sensitive external-tool use, and trading execution requests.
