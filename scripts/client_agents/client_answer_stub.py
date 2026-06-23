#!/usr/bin/env python3
"""Nexus OS v2 — controlled client-agent answer stub. Proves client AI is DIFFERENT from Hermes.

A client_agent answers ONLY from Supabase approved_knowledge. No web, no external API. It
refuses guarantee/out-of-scope questions with compliance-safe language. Writes a nexus_event.

    python3 scripts/client_agents/client_answer_stub.py --agent client_funding_assistant \
        --question "Can you guarantee I will get business funding?"
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))           # agent_policy
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "social"))  # _supabase
import agent_policy  # noqa: E402
from _supabase import configured, get, event, q  # noqa: E402

DISCLAIMER = "This is education and readiness guidance — no guaranteed funding, approval, or credit outcome."
GUARANTEE_RX = r"guarantee|will i (get|be)|do you promise|100%|for sure"
IN_SCOPE_RX = r"fund|credit|readiness|loan|lender|approval|business|ein|bank|entity|naics"


def answer(agent: dict, question: str) -> dict:
    if not agent_policy.is_client_agent(agent):
        return {"refused": True, "answer": "This controlled stub only serves client-facing agents."}

    # 1) Never guarantee outcomes.
    if re.search(GUARANTEE_RX, question.lower()):
        return {"refused": True, "answer": (
            "I can't guarantee that you'll get business funding or approval — no one honestly can. "
            "What I can do is help you understand your funding readiness: the signals lenders check "
            "(entity/EIN consistency, business phone/address, web presence, bank statements, NAICS, "
            "credit readiness) so you walk in prepared. " + DISCLAIMER)}

    # 2) Out of scope → stay in lane.
    if not re.search(IN_SCOPE_RX, question.lower()):
        return {"refused": True, "answer": (
            "I can only help with approved funding and credit-readiness topics. " + DISCLAIMER)}

    # 3) Answer from approved_knowledge only.
    st, rows = get("approved_knowledge", "status=eq.approved&select=title,body,category&limit=20")
    kb = rows if isinstance(rows, list) else []
    ql = question.lower()
    match = next((k for k in kb if any(w in (k.get("body", "") + k.get("title", "")).lower()
                                       for w in re.findall(r"[a-z]{4,}", ql))), kb[0] if kb else None)
    if not match:
        return {"refused": False, "answer": "I don't have approved knowledge on that yet. " + DISCLAIMER}
    return {"refused": False, "answer": f"{match['body']}\n\n{DISCLAIMER}", "source": match["title"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="client_funding_assistant")
    ap.add_argument("--question", required=True)
    args = ap.parse_args()
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2

    agent = agent_policy.load_agent(args.agent)
    if not agent:
        print(f"agent '{args.agent}' not found"); return 1

    res = answer(agent, args.question)
    event("communication", "client_agent_answer", "success",
          f"Client agent answered ({args.agent})",
          f"refused={res.get('refused')} · approved_knowledge_only · no web/external API",
          payload={"agent": args.agent, "refused": res.get("refused")})
    print(f"[{args.agent}] (approved-knowledge only, no web/external API)")
    print("Q:", args.question)
    print("A:", res["answer"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
