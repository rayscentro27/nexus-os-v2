# Hermes Memory Overmatch Trace — Before Fix

The exact baseline flow was executed against commit `62241f2` before routing logic was changed.

The business list and recommendation worked. “So number 3…” resolved the correct entity but incorrectly reported Level 4 because the number-reference detector was anchored to the beginning of the message.

The failure was reproduced for both casual questions and trading. Each message selected Level 4 because the detector treated the existence of any conversation memory as sufficient context. The Level 4 default answer then returned the `$97 Credit & Funding Readiness Review` recommendation without an explicit reference or domain match.

The standalone audit correctly detected the topic changes, rejected memory, and showed that neither a casual override nor a trading-domain override existed in the live pipeline.

Root cause: stale memory did not directly resolve the selected item through Level 3; instead, memory made the generic Level 4 default eligible, and Level 4’s fallback was hardwired to the business recommendation. The smallest correct patch is therefore the activation/topic boundary plus the Level 4 domain answer builder—not phrase-specific casual commands.
