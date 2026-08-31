# Conversational final-response contract

Normal Telegram output is Nova-owned prose: answer first, recommendation early, two to four key reasons, meaningful uncertainty, and an optional useful next move. The default is two to five compact paragraphs or an opening paragraph plus at most four short bullets.

Tools provide evidence; Alpha provides research; Nexus provides state; web provides outside information. None is copied as the answer. Schema labels and report headings are excluded from ordinary conversation. Formal report, audit, status, certification, and detailed evidence requests may remain structured through model judgment.

Current/trend claims require current evidence or are rewritten as qualified judgment. A completed retrieval is presented as completed; stale planning text cannot override the current execution receipt. Alpha findings are interpreted into Nova's own agree/disagree decision.

Implementation: `_final_presentation_prompt()` plus bounded post-presentation claim correction. No phrase-specific answer router or canned answer was added.
