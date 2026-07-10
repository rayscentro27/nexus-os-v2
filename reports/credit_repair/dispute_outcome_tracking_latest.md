# Dispute Outcome Tracking

Outcome table added: `credit_dispute_outcomes`

## Tracked Fields

- Case
- Report item
- Strategy
- Letter option
- Round number
- Sent date
- Response due date
- Response received date
- Result
- Bureau/furnisher
- Notes
- Next recommended action

## Deterministic Next Actions

- Deleted: mark success and track option used.
- Corrected/updated: reassess funding readiness impact.
- Verified: consider method of verification, furnisher dispute, or stronger evidence.
- No response: prepare follow-up or escalation review.
- Client evidence needed: request document upload.
- Needs escalation: specialist reviews next-round posture.
- Not sent: keep item in review until approved.
