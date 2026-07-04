# Alpha Conversation Naturalness Fix

- Greetings use `Date.now()`/browser-local time instead of a report snapshot.
- A morning phrase sent in the afternoon receives the current afternoon greeting.
- “How did you sleep?” and “favorite card” receive direct natural answers without pretending Alpha is human.
- Business questions receive a useful first analysis before optional clarification.
- Current questions never claim live facts when Search Mode is off or the connector fails.
- “Where did that answer come from?” points Ray to the response trace.
