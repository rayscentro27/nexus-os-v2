# Dispute Review World-Class Shell

- `/client/dispute-review` uses world-class shell: `True`
- Legacy green/client shell restored: `False`
- Main client-facing guidance uses Clyde / GoClear language: `True`
- Hermes Guidance shown as the main client panel: `False`

## DocuPost Safety

- Auto-send: `False`
- Specialist/client approval required: `True`
- Letter preview action visible: `True`
- Request edits action visible: `True`
- Approve letter action visible: `True`
- Authorize/send request action visible only as an approval-gated request: `True`

## Notes

- The page reuses `loadCreditRepairJourney`, `clientApproveLetter`, and `createDocuPostSendRequest`.
- Supporting dispute documents can be uploaded inline through the shared inline requirement component.
