# Clyde Chat Drawer Repair

- Chat with Clyde routes to Resources by default: `False`
- In-page Clyde drawer exists: `True`
- External model calls from frontend: `False`

## Behavior

- The Clyde button opens an in-page drawer with page context, suggested questions, top recommended actions, and a disabled live-chat input state.
- Suggested questions can show guidance without leaving the page.
- Recommended actions route only when clicked.
- `Request human review` routes to `/client/request-review` as an explicit CTA.
