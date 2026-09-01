# Google currentness and history

Google tools are declared volatile read capabilities. Calendar and Gmail
results include `fetched_at`, source, query/window, item count, request ID, and
read-only status. Conversation history identifies a referent but does not
substitute for a fresh Google read when the user asks about current/new/changed
state.

The Calendar “today” and “next meeting” probes performed fresh Calendar reads.
The Gmail thread follow-up used the linked thread identifier and the newer
current mailbox query path remained available. Historical message/event
context is bounded and distinct from current state.

The historical query split is preserved by the existing adapter contract:
historical questions may request a historical window; present-tense questions
use an explicit current window or mailbox query. No Google write capability is
registered.
