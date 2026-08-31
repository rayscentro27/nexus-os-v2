# Alpha Referent Continuity Proof

Sequential shadow session:

1. `Check Nexus and tell me which capability you would use first to make money.`
2. `Have Research challenge your recommendation.`
3. `What did Research find, and did it change your recommendation?`

Turn 1 performed bounded Nexus reads and produced a recommendation. Turn 2
resolved “your recommendation” to the immediately preceding session context,
called `alpha_challenge_shadow`, executed Alpha, and returned a fresh Alpha
receipt/result. Turn 3 had access to the fresh Alpha result, but the model also
made additional Nexus reads and did not cleanly limit itself to the linked
artifact.

```text
ALPHA_EXECUTION=YES
FRESH_ALPHA_RESULT_RETURN=YES
REFERENT_RESOLUTION=YES
FINAL_FRESHNESS_DISCIPLINE=PARTIAL
```

