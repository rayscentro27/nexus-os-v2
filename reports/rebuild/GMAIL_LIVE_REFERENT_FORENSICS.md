# Gmail live referent forensics

The reproduced real-account sequence established the original failure and the
repair evidence. Turn A returned five bounded Gmail objects. Before the repair,
Turn B performed a new `gmail_search`, returned a different five-message set,
and Turn C therefore lacked a reliable thread target.

The current sequence preserves the A result set as a bounded sidecar snapshot.
Turn B now resolves the existing Gmail object and selects a thread read rather
than a discovery search. Turn C receives the selected thread ID and completes a
real `gmail_read_thread` call.

The distinction is now explicit: object follow-ups use linked result metadata;
questions asking for newer/new/changed mail remain fresh Gmail reads. No Gmail
write capability or Nova behavior restriction was added.
