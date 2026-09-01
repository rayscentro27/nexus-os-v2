# Google final Telegram-equivalent preflight

## Results

- Cross-process persistence: implemented and covered by atomic sidecar writes.
- Active referent selection: fixed generically; active resource outranks later
  unrelated resource history.
- Real process-equivalent A→B check: PASS. A performed one external Gmail
  search despite three equivalent model requests; B, in a separate runner
  process, hydrated the persisted five-item result set and performed only
  object reads, with no new discovery search.
- Real process-equivalent D→E check: PASS. D performed one fresh external
  Gmail search; E used the resulting set and performed one linked thread read,
  with no new discovery search.
- Context release: the persisted Gmail referent was cleared before an unrelated
  business turn. The native model nevertheless selected one Nexus opportunity
  read; this remaining selection issue is not a lost Google snapshot and was
  not suppressed with a phrase router.
- The B response selected objects from A’s five-item set. It was verbose, but
  the result-set and object linkage were correct; response style is outside
  this campaign’s scope.
- Gmail object continuity: covered by the existing linked snapshot tests and
  the new active-referent ordering test.
- Volatile recheck boundary: preserved; new turns still receive new turn IDs
  and explicit newer queries still execute fresh reads.
- No Nova profile/SOUL, phrase routing, Gmail command mode, or new behavioral
  restriction was added.
- Focused Nova tests: `28 passed`.
- Google MCP tests: `4 passed`.

The real-world Google certification boundary remains with Ray’s final Telegram
retest. No real-world certification is claimed here; the unrelated-turn
resource-selection issue remains a separate trace-backed blocker.
