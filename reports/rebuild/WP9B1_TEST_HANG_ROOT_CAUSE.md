# WP9B1 Creative test root cause

The territory test exited immediately. The real-render test stalled in the
Python Playwright CLI subprocess after Chromium rendered the first `file://`
screenshot. The final fix changes only `creative/department.py`'s screenshot
helper to call the repository-local `scripts/creative/playwright_screenshot.mjs`
Node API runner with explicit context/browser teardown. This preserves real
Chromium rendering while avoiding the leaking Python 3.14 Playwright driver.

Evidence: `scripts/nexus_agent_platform/tests/test_creative_department.py`
now exits `2 passed in 26.84s`.
