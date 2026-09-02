# WP9B1 Creative test root cause

The territory test exited immediately. The real-render test stalled in the
Python Playwright CLI subprocess after Chromium rendered the first `file://`
screenshot. A direct Python Playwright API test exited cleanly. The fix changes
only `creative/department.py`'s screenshot helper to use
`sync_playwright()`, an explicit browser/context lifecycle, and `browser.close()`
in `finally`.

Evidence: `scripts/nexus_agent_platform/tests/test_creative_department.py`
now exits `2 passed in 26.84s`.
