"""Context module init."""

from nexus_agent_platform.context.resolver import (
    load_context,
    save_context,
    update_active_context,
    get_active_context,
    clear_context,
)

__all__ = ["load_context", "save_context", "update_active_context", "get_active_context", "clear_context"]
