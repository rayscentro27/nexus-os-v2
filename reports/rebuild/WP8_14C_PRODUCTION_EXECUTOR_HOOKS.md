# WP8.14C Production executor hooks

The canonical `scripts/nexus_agent_platform/governed/engine.py:execute_approved_work_order` boundary now calls Finance preflight before transition to execution and Finance postrun after success, timeout, exception, or repair failure. Finance failure blocks execution; postrun is idempotent by work-order/attempt receipt. The existing governed test path proved a real work order produced both Finance records. Department-specific loops remain parent-bound to this executor boundary.
