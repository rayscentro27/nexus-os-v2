# Google final integrated preflight

Focused Hermes-native verification passes for the repaired Gmail path:

* Turn A returns the real five-item bounded set.
* Turn B does not perform broad Gmail discovery and selects a linked thread
  object from Turn A.
* Turn C performs a real `gmail_read_thread` using the preserved thread ID.
* Calendar and Gmail reads remain read-only and bounded.
* Casual, Nexus, Calendar, and Gmail resource boundaries remain available.

Focused regression suite: 45 passed.

One earlier live probe showed duplicate Gmail search messages during Turn A;
this is retained as an observability/efficiency follow-up and is not allowed
to redefine the result-set referent. Real-world certification still requires
Ray’s final Telegram test.
