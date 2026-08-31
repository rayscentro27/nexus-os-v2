# Hermes Primary Preflight

## Canonical worker proof

Controlled fixture updates were sent through the canonical worker processing
path with Telegram delivery replaced by an in-process capture. No Telegram
API message was sent.

The complete 11-turn sequence completed with nonempty Hermes responses:

1. general reasoning
2. affiliate web research
3. Tesla current research
4. Nexus read
5. Nexus plus web synthesis
6. Alpha challenge
7. Alpha result reuse
8. three-option comparison
9. winner selection
10. first-option referent
11. cross-referent comparison

Primary runtime was Hermes for all turns. Custom was not invoked as primary.

## Results

`GENERAL=PASS`, `WEB=PASS`, `CURRENTNESS=PASS`, `NEXUS=PASS`,
`MULTI_RESOURCE=PASS`, `ALPHA=PASS`, `ALPHA_REUSE=PASS`, `REFERENTS=PASS`,
`RECOMMENDATION=PASS`, and `FALSE_EVIDENCE_CLAIMS=0`.

The Hermes session used a stable production namespace of the form
`nova-telegram-primary-{chat_id}`. The test used an isolated fixture chat, so
Ray's historical custom session was not imported.
