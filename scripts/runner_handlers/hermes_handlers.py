"""Hermes / intake handlers.

Hermes is Ray's PRIVATE advisor: it can classify a command, queue an allowlisted follow-up
job, and create an approval when a risky/public action is requested — but it NEVER publishes,
sends, trades, deploys, or calls a live model here. Plain-language response, no fake work.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # for agent_policy
from ._base import sb, ok, run_script
import agent_policy  # noqa: E402

# Categories that are risky/public → require an approval, never executed by Hermes.
RISKY = {
    "social_publish_request": "publish_social",
    "send_telegram": "send_telegram",
    "send_email": "send_email",
    "trade": "trade",
    "deploy": "deploy",
}
# Category → allowlisted follow-up job type Hermes may queue (safe, non-publishing).
JOB_FOR = {
    "creative_request": "creative_generate_assets",
    "monetization_review": "monetization_review",
    "opportunity_research": "niche_research",
    "niche_research": "niche_research",
    "trading_research": "niche_research",
    "ops_diagnostic": "ops_diagnostic",
    "system_status": "system_status",
}


def _affirm(t: str, pattern: str) -> bool:
    """Match an action pattern only when it's NOT negated (e.g. 'do not publish')."""
    if not re.search(pattern, t):
        return False
    neg = r"(do not|don'?t|never|no|without)\s+(\w+\s+){0,2}?(publish|post|send|trade|deploy|email)"
    return not re.search(neg, t)


def classify(text: str) -> str:
    t = (text or "").lower()
    # Explicit safe-research intent wins over an action keyword buried in a 'do not X' clause.
    if re.search(r"niche", t) and not _affirm(t, r"\b(publish|post (it|this|to)|go live)\b"): return "niche_research"
    if _affirm(t, r"\b(publish|post (it|this|to)|go live)\b"): return "social_publish_request"
    if _affirm(t, r"telegram|war ?room|message me"): return "send_telegram"
    if _affirm(t, r"\bemail\b"): return "send_email"
    if _affirm(t, r"\b(buy|sell|execute (a )?trade|place (a )?trade)\b"): return "trade"
    if _affirm(t, r"deploy|ship to prod"): return "deploy"
    if re.search(r"niche", t): return "niche_research"
    if re.search(r"trad(e|ing).*(research|strategy|backtest)|strategy", t): return "trading_research"
    if re.search(r"opportunit|repo|video|idea", t): return "opportunity_research"
    if re.search(r"money|monetiz|revenue|offer", t): return "monetization_review"
    if re.search(r"creativ|campaign|content|caption|reel|post idea", t): return "creative_request"
    if re.search(r"seo|keyword|search console", t): return "seo_recommendation"
    if re.search(r"status|health|what'?s going on|summary", t): return "system_status"
    if re.search(r"ops|incident|broken|fail", t): return "ops_diagnostic"
    return "unknown"


def command_ack(job, ctx) -> dict:
    cmd = (job.get("input") or {}).get("command", "")
    agent = agent_policy.load_agent("hermes_advisor") or {}
    category = classify(cmd)
    queued_job, approval = None, None
    did_not = ["publish anything", "send Telegram", "trade", "deploy", "call a live model"]

    # Transcript/idea intake → deterministic intake review (Day 8).
    INTAKE_RX = (r"transcript|process this (video|idea)|where does this fit|what should nexus do with|"
                 r"is this (useful|a trading idea|hype)|extract the service opportunity")
    intake_request = bool(re.search(INTAKE_RX, cmd.lower())) and category not in RISKY
    # Research/strategy/build-prompt/feasibility/"which AI" → route via the Model Router.
    ROUTE_RX = (r"research|strateg|what do you think|review this|summar|build (a )?prompt|"
                r"run (this|it) on|mac ?mini|local hardware|which (ai|model|resource)|feasib")
    route_request = bool(re.search(ROUTE_RX, cmd.lower())) and category not in RISKY

    if category in RISKY:
        action = RISKY[category]
        if agent_policy.requires_approval(agent, action) or True:
            st, row = sb.insert("approvals", {
                "lane": "hermes", "item_type": f"hermes_{action}", "status": "pending",
                "title": f"Hermes requests approval: {action}",
                "summary": f"Command: {cmd[:160]}", "payload": {"action": action, "command": cmd, "category": category},
            })
            approval = row[0]["id"] if isinstance(row, list) and row else "created"
    elif intake_request and agent.get("can_create_jobs"):
        jt = "service_opportunity_extract" if "service opportunity" in cmd.lower() else "transcript_intake_review"
        st, row = sb.insert("agent_jobs", {
            "lane": "hermes", "job_type": jt, "status": "queued",
            "input": {"source": "hermes_command", "text": cmd, "title": cmd[:80]},
        })
        queued_job = row[0]["id"] if isinstance(row, list) and row else "queued"
        category = jt
    elif route_request and agent.get("can_create_jobs"):
        st, row = sb.insert("agent_jobs", {
            "lane": "hermes", "job_type": "hermes_model_route_decision", "status": "queued",
            "input": {"source": "hermes_command", "prompt": cmd},
        })
        queued_job = row[0]["id"] if isinstance(row, list) and row else "queued"
        category = "model_route_request"
    elif category in JOB_FOR and agent.get("can_create_jobs"):
        jt = JOB_FOR[category]
        st, row = sb.insert("agent_jobs", {
            "lane": "hermes", "job_type": jt, "status": "queued",
            "input": {"source": "hermes_command", "command": cmd, "campaign_key": "goclear_funding_readiness_review"},
        })
        queued_job = row[0]["id"] if isinstance(row, list) and row else "queued"

    allowed = ("research, recommend, and queue allowlisted jobs; create approvals for risky/public actions. "
               "Cannot publish/send/trade/deploy without Ray approval + runner gates.")
    note = (f"I read this as a '{category}' request. {allowed} ")
    if approval:
        note += f"Because it asks for a public/risky action, I created a PENDING approval (id {approval}) and did nothing else. "
    elif queued_job:
        qjt = ("hermes_model_route_decision" if category == "model_route_request"
               else category if category in ("transcript_intake_review", "service_opportunity_extract")
               else JOB_FOR.get(category, "follow_up"))
        note += f"I queued a safe '{qjt}' job (id {queued_job}) for the runner to execute under gates (dry-run, no external model call). "
    else:
        note += "No executable job applies yet — recommend reviewing or routing. "
    note += "No live model route was called."

    return ok({"category": category, "queued_job": queued_job, "approval_id": approval,
               "did_not_do": did_not, "response": note})


def model_route_decision(job, ctx) -> dict:
    """Run the Hermes model-route decision (DRY-RUN). No external model call."""
    prompt = (job.get("input") or {}).get("prompt") or (job.get("input") or {}).get("command") or "(no prompt)"
    r = run_script("scripts/hermes/request_model_route.py", ["--agent", "hermes_advisor", "--prompt", prompt, "--dry-run"])
    return ok({"script": "request_model_route", "dry_run": True, **r})


def intake_stub(job, ctx) -> dict:
    return ok({"note": "Intake/orientation acknowledged. No external research/model call performed.",
               "job_type": job.get("job_type")})
