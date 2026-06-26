# Nexus SEO Keyword Scout

`scripts/research/seo_keyword_scout.py` imports manually reviewed keyword CSV files.

Command:

```bash
python3 scripts/research/seo_keyword_scout.py --input-file reports/seo/keyword_imports/sample_keywords.csv --dry-run --json
```

No paid keyword API is required in this pass. The safe import folder is `reports/seo/keyword_imports/`.

Fields: `keyword`, `topic_cluster`, `search_intent`, `difficulty_estimate`, `cpc_estimate`, `affiliate_relevance`, `GoClear_relevance`, `content_type_recommendation`, `funnel_stage`, `target_offer`, `priority_score`, `source`, `proof_source`, and `notes`.
