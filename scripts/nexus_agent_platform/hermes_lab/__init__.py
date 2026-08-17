"""Hermes compatibility lab helpers.

The lab is intentionally isolated from production Hermes, Telegram, and
client-facing behavior. It probes the upstream Hermes checkout through a
temporary HERMES_HOME and uses the local deterministic Nexus capability
registry for read-only status synthesis.
"""

from .upstream_compatibility import (
    UpstreamHermesCompatibilityLab,
    build_upstream_compatibility_report,
    run_upstream_compatibility_lab,
    write_upstream_compatibility_report,
)

__all__ = [
    "UpstreamHermesCompatibilityLab",
    "build_upstream_compatibility_report",
    "run_upstream_compatibility_lab",
    "write_upstream_compatibility_report",
]
