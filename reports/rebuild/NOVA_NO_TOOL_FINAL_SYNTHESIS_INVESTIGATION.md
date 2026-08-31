# Nova No-Tool Final Synthesis Investigation

## Checkpoint

`HEAD=38bc36a`; `origin/main=38bc36a`. The implementation files have no diff from the checkpoint. The worktree has unrelated generated/runtime changes. `FILES_CHANGED=1` referred to the last commit, which changed only the validator; it did not describe the full campaign history.

## Captured failing preflight

`USER_MESSAGE=What should I work on first today?`

`TOOLS_EXECUTED=0`

`RAW_HERMES_RESPONSE=` the model returned a broad priority list centered on monetization, client-portal stability, trading research, and affiliate/content work.

`FINAL_PRESENTATION_RESPONSE=` “Today, prioritize stabilizing the client portal and reviewing the affiliate content systems. Focusing on these areas can enhance user experience and retention, which are essential for driving recurring revenue. Additionally, optimizing affiliate strategies may uncover valuable revenue streams.” It then added four task bullets, “initiate a stability check,” and an offer to pull data or run checks.

`VALIDATOR_RESULT=` the prior validator accepted the draft; after the validator tightening, an equivalent run was correctly marked invalid for `currentness_not_proven` / attribution risk.

`REPAIR_ATTEMPTED=YES`

`REPAIRED_RESPONSE=` a later bounded presentation attempt still contained procedural prioritization and revenue language.

`DELIVERABLE_RESPONSE=` the preflight response above was not accepted as certification evidence.

Responsible phrases included “essential for driving recurring revenue” and “valuable revenue streams” (`MODEL_JUDGMENT_FRAMED_AS_FACT` / `UNSUPPORTED_EVIDENCE`), “current state ... hasn't been verified recently” followed by “initiate a stability check” (`PROCEDURAL_OVERREACH`), and “If you're ready, I can assist ... running system checks” (`UNNECESSARY_NEXT_ACTION`).

## Prompt precedence and cause

`SYSTEM/HERMES → NOVA SOUL → RESOURCE GUIDANCE → TURN CONTEXT → FINAL SYNTHESIS → VALIDATOR/REPAIR → TELEGRAM`.

The SOUL previously combined conversational identity with a substantive-operator directive to form an initial view, seek missing evidence, challenge the first conclusion, recommend, and end with a useful next move. Resource guidance correctly allowed reasoning first, but still emphasized recommendations for business prioritization. The final presentation prompt required answer-first reasons and a useful next move, while the validator detected defects only after drafting. This over-constrained ordinary business turns toward operator workflow prose.

The repair narrows SOUL and presentation guidance to: reason naturally, seek resources only when material, express unsupported business/current claims as qualified judgment, and stop naturally. The validator now fails closed if bounded repair cannot produce a valid response.
