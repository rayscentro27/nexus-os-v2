update public.pulse_notebook_templates
set prompt_body = $prompt$
PURPOSE: Analyze a current trend cluster using evidence in this notebook. Keep observed facts, calculated values, and AI inferences separate. Never invent search volume, growth, audience demographics, product sales, pricing, active affiliate terms, or commercial results. Do not approve a business, campaign, spend, purchase, or publication.

SOURCE BUNDLE TO REVIEW: public-search discovery; Google Trends and trend pages; source videos/posts; creator examples and public comments; Google News/news context; related queries and topics; cross-platform matches; official affiliate offers and terms; TikTok Shop products where accessible; merchandise options and Printify catalog matches; competitor campaigns and landing pages; prior Nexus campaign results when relevant.

QUESTIONNAIRE:
1. What is trending? Include exact topic, keywords, title, source URL and platform.
2. When did the trend begin? Separate first observed date from source publication date.
3. Is it accelerating, stable, decelerating, or unknown? State the observations and time window.
4. Which platforms confirm the signal?
5. What is the strongest evidence and its source-quality class?
6. Who is the audience? Separate evidence from hypothesis.
7. Why are people engaging?
8. What emotional driver is involved?
9. What curiosity mechanism is involved?
10. What hooks repeat across independent sources?
11. What content formats repeat?
12. What visual patterns repeat?
13. Is the trend creator-specific?
14. Is it portable across creators?
15. Is it platform-specific?
16. Is it cross-platform?
17. What is the saturation level and supporting evidence?
18. What is the expected lifespan and confidence?
19. What products are being sold around it? Cite current evidence.
20. What affiliate programs match? Use UNVERIFIED until the official program and terms are checked.
21. What TikTok Shop products match? Use UNVERIFIED unless current listing evidence is available.
22. What Printify merchandise opportunities match? Verify catalog blueprint/provider/variant; do not create a product.
23. What digital products match?
24. What services match?
25. What lead-generation opportunities match?
26. Can Nexus respond before the trend decays? State the operational dependency.
27. What could be prepared within 24 hours?
28. What could be prepared within 72 hours?
29. Does this warrant a Business Opportunity feeder handoff?
30. Does this warrant a Rapid Campaign marketing review?
31. Does this warrant a Rapid Merch Campaign review?
32. What evidence would invalidate the opportunity?
33. What should Pulse monitor next and when?

For each important claim use SOURCE_CLAIM, CROSS_SUPPORTED, VERIFIED, CONTRADICTED, or RESEARCH_REQUIRED. Do not treat repeated creator/blog claims as independent verification. Public search summaries, YouTube, blogs, forums, Reddit and social posts are DISCOVERY_ONLY until independently verified. Import or cite sources only when relevant, public-safe, and non-duplicate.

OUTPUT:
TREND_SUMMARY=
EVIDENCE_SUMMARY=
AUDIENCE_SUMMARY=
VIRAL_MECHANISM=
COMMERCIAL_MATCHES=
AFFILIATE_MATCHES=
MERCH_MATCHES=
RISKS=
RECOMMENDED_ROUTE=BUSINESS_OPPORTUNITY/RAPID_CAMPAIGN/RAPID_MERCH_CAMPAIGN/INTELLIGENCE_ONLY/WATCH
URGENCY=
CONFIDENCE=
NEXT_RECHECK=
$prompt$,
updated_at=now()
where template_id='TREND_INTELLIGENCE_V1';
