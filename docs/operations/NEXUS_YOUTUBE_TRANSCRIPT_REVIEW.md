# Nexus YouTube Transcript Review

`scripts/research/youtube_transcript_review.py` reviews one explicit YouTube URL or one local transcript file.

Command:

```bash
python3 scripts/research/youtube_transcript_review.py --input-file tests/fixtures/research/sample_youtube_transcript.txt --dry-run --no-external-ai --json
```

It does not scrape channels, download media, run yt-dlp, start a scheduler, or use external AI.

Scores:

- money potential
- GoClear/Apex relevance
- SEO potential
- affiliate potential
- content potential
- implementation difficulty
- compliance risk
- urgency
- uniqueness
- testability
- overall score

Routing: Opportunity Lab, SEO / Marketing, Creative Studio, GoClear Revenue Hub, Ops & Improvements, Trading Lab paper-only, or Ray review when risky.
