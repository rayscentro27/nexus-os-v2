# Hermes Live Transcript Routing Audit

Baseline: `948ac6e79cd62fcb1128bf75840299c7f8825ec4`

All nine Ray messages in the supplied live transcript were audited before routing logic was changed. None produced the required mechanism-level result.

The critical failure is priority. “Last response” was interpreted as the last ranked business item before source/trace intent was recognized, so Funding Application Prep Sprint leaked into a trace question. That polluted the next domain trace. Other source variants were not classified at all. “Are you using Supabase” fell through a narrow Supabase capability pattern and matched the overly broad model phrase “are you using.”

Trading used one generic Level 4 response for listing and recommendation sub-intents. It neither enumerated repository-backed strategies nor stated when recommendation evidence was insufficient. The first follow-up omitted “trading,” and the router failed to inherit the immediately preceding trading topic.

The money question missed narrow monetization patterns, including natural “most money” wording and the transcript typo “30 says.” The internal general-domain diagnostic then escaped as the final answer.

Required fix: central trace priority immediately after safety, semantic trace/source classification, last-normal-trace targeting, dedicated trading and revenue reasoners, same-domain continuation inference, and a final guard preventing internal diagnostics from becoming normal answers.
