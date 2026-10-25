"""CEO Reporting Standard formatter.

Renders agent results in the required format:
  headline conclusion → working → needs attention → changed →
  recommendation → action required → Phoenix time → optional detail
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

PHOENIX_OFFSET = -7  # UTC offset for Phoenix, AZ


def _phoenix_time() -> str:
    utc = datetime.now(timezone.utc)
    phoenix = utc.replace(second=0, microsecond=0)
    from datetime import timedelta
    phoenix = phoenix + timedelta(hours=PHOENIX_OFFSET)
    return phoenix.strftime("%I:%M %p MT")


def format_ceo_report(
    headline: str,
    working: str = "",
    needs_attention: str = "",
    changed: str = "",
    recommendation: str = "",
    action_required: str = "",
    detail: Optional[str] = None,
    agent_id: str = "",
) -> str:
    """Format a response using the CEO Reporting Standard."""
    lines = [f"**{headline}**"]

    if working:
        lines.append(f"\nWorking: {working}")
    if needs_attention:
        lines.append(f"\nNeeds Attention: {needs_attention}")
    if changed:
        lines.append(f"\nChanged: {changed}")
    if recommendation:
        lines.append(f"\nRecommendation: {recommendation}")
    if action_required:
        lines.append(f"\nAction Required: {action_required}")

    lines.append(f"\nPhoenix: {_phoenix_time()}")

    if detail:
        lines.append(f"\nDetail:\n{detail}")

    return "\n".join(lines)


def format_research_summary(
    topic: str,
    key_findings: list[str],
    sources: list[str],
    recommendation: str = "",
    agent_id: str = "",
) -> str:
    """Format a research summary using the CEO Reporting Standard."""
    headline = f"Research: {topic}"
    findings_text = "\n".join(f"• {f}" for f in key_findings)
    sources_text = "\n".join(f"• {s}" for s in sources)

    detail = f"Key Findings:\n{findings_text}\n\nSources:\n{sources_text}"

    return format_ceo_report(
        headline=headline,
        working="Research completed",
        recommendation=recommendation,
        detail=detail,
        agent_id=agent_id,
    )
