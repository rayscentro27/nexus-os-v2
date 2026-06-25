# Nexus — Hermes Chat Persistence & Scroll

## Problem
Hermes chat reset when navigating away from Command Center (the component unmounts on tab switch),
and long chats stretched the whole page instead of scrolling inside the panel.

## Persistence
`src/lib/hermesChatStore.ts` (localStorage):
- `nexus_hermes_chat_history` — last 50 messages.
- `nexus_hermes_mode` — current Hermes mode.
- **Sensitive text is never persisted** — `saveMessages` drops any message that trips
  `containsSensitive` (firewall belt). No secrets / customer data stored.

`CommandCenter` lazy-initializes `messages`/`mode` from the store and writes back on change
(`useEffect`). Switching tabs / reloading no longer resets the conversation. Conversation /
Report Reader / Task Request behavior unchanged.

## Scroll
The Hermes card is a flex column with bounded height (`min(64vh,720px)`); the message list is
`flex:1; overflow-y:auto`; the composer is pinned (`flex-shrink:0`) at the bottom and stays visible.
A `chatEndRef` auto-scrolls to the latest message. The page no longer grows from chat volume; mobile
stacks cleanly.

## Approval authority copy
Header + footer now state: "Hermes can recommend, but Ray approves risky actions." and
"No publish/send/trade/deploy without your approval."
