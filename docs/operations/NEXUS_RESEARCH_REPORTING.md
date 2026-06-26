# Nexus Research Reporting

Research reporting is internal and approval-free. Reports prepare Hermes and Ray for strategic decisions without publishing, sending, trading, deploying, or scheduling anything.

## Weekly Report

Command:

```bash
python3 scripts/research/generate_weekly_research_report.py --dry-run --limit 10 --no-external-ai --json
```

Inputs:

- watched resource reports
- YouTube transcript review reports
- research scout reports
- affiliate opportunity reports
- SEO keyword reports
- SEO-to-affiliate content plans
- research-to-experiment reports
- content opportunity reports
- content test reports

Output:

- `reports/runtime/weekly_research_report_latest.json`
- `reports/manual_publish/weekly_research_report_latest.md`

## Department Top-N Report

Command:

```bash
python3 scripts/research/generate_department_top_report.py --department youtube_transcripts --dry-run --limit 10 --no-external-ai --json
```

Supported department/source groups include:

- `youtube_transcripts`
- `seo_marketing`
- `affiliate`
- `experiments`
- `goclear`
- `trading`

Each report includes top items, counts, and a suggested Hermes prompt.

## YouTube Research Report

Command:

```bash
python3 scripts/research/generate_youtube_research_report.py --dry-run --limit 10 --no-external-ai --json
```

This report summarizes watched YouTube candidates, channel opportunity quality, GoClear content opportunities, SEO/affiliate ideas, AI/automation ideas, and paper-only trading ideas.

## Ask Hermes About This Report

Reports include `hermes_context.suggested_prompt` so Ray can ask:

- "What direction should we take?"
- "Why did these score high?"
- "Which angle should we test next?"
- "Which item should move to Creative Studio?"

Hermes can advise and prepare drafts, but outbound execution remains approval-gated.
