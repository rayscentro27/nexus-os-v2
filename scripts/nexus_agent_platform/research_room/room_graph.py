"""LangGraph participant router; each invocation executes exactly one turn."""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from .handoff import proposed_handoff
from .knowledge_adapter import KnowledgeAdapter
from .participants import (DomainAdvisor, FactChecker, FinalSynthesizer,
    FollowupResearcher, Needle, QuestionGenerator, ResearchLead, SourceAnalyst)

PARTICIPANTS = ("RESEARCH_LEAD", "SOURCE_ANALYST", "KNOWLEDGE_RECONCILIATION",
    "DOMAIN_ADVISOR", "QUESTION_GENERATOR", "FOLLOWUP_RESEARCH", "FACT_CHECKER",
    "NEEDLE", "FINAL_STRATEGIST", "HANDOFF")


class RoomGraph:
    """Build a LangGraph over injected participants, with one node per turn."""
    def __init__(self, *, source_tools: Any, advisor_router: Any,
                 knowledge_adapter: Any = None, verifier: Any = None):
        self.source = SourceAnalyst(source_tools)
        self.advisor = DomainAdvisor(advisor_router)
        self.knowledge = knowledge_adapter or KnowledgeAdapter()
        self.verifier = verifier
        self.lead, self.questions, self.followup = ResearchLead(), QuestionGenerator(), FollowupResearcher()
        self.fact_checker, self.needle, self.synthesizer = FactChecker(verifier), Needle(), FinalSynthesizer()
        self._compiled = None

    def _execute(self, participant: str, state: dict[str, Any]) -> dict[str, Any]:
        state = dict(state)
        prior_status = state.get("status")
        state["status"] = "WORKING"
        if participant == "RESEARCH_LEAD":
            self.lead.contribute(state)
        elif participant == "SOURCE_ANALYST":
            self.source.contribute(state)
        elif participant == "KNOWLEDGE_RECONCILIATION":
            subject = str((state.get("source_report") or {}).get("title") or state["original_request"])
            recon = self.knowledge.reconcile(subject, state.get("findings", []))
            state["knowledge_reconciliation"] = recon
            state["prior_nexus_knowledge"] = recon.get("prior_knowledge", [])
            from .participants import append_message
            append_message(state, "RESEARCH_LEAD", f"Existing-knowledge relationship: {recon.get('relationship')}; continuing with current evidence.", "KNOWLEDGE_RECONCILIATION")
            state["next_participant"] = "DOMAIN_ADVISOR"
        elif participant == "DOMAIN_ADVISOR":
            self.advisor.contribute(state)
        elif participant == "QUESTION_GENERATOR":
            self.questions.generate(state)
        elif participant == "FOLLOWUP_RESEARCH":
            self.followup.research(state)
        elif participant == "FACT_CHECKER":
            self.fact_checker.contribute(state)
        elif participant == "NEEDLE":
            state["needle_result"] = self.needle.review(state)
            state["next_participant"] = "FINAL_STRATEGIST"
        elif participant in {"FINAL_STRATEGIST", "FINAL_SYNTHESIZER"}:
            state["status"] = "SYNTHESIZING"
            self.synthesizer.synthesize(state)
        elif participant == "HANDOFF":
            proposed_handoff(state)
        else:
            raise ValueError(f"UNKNOWN_RESEARCH_ROOM_PARTICIPANT:{participant}")
        state["next_participant"] = self.lead.select_next_participant(state)
        history = state.setdefault("status_history", ["OPEN"])
        if prior_status != "WORKING" and "WORKING" not in history:
            history.append("WORKING")
        if state.get("status") != prior_status and state.get("status") not in history:
            history.append(state["status"])
        state["turn_count"] = int(state.get("turn_count", 0)) + 1
        return state

    def _graph(self):
        if self._compiled is None:
            from langgraph.graph import END, StateGraph
            graph = StateGraph(dict)
            graph.add_node("dispatch", self._dispatch)
            for role in PARTICIPANTS:
                graph.add_node(role, lambda state, _role=role: self._execute(_role, state))
                graph.add_edge(role, END)
            graph.set_entry_point("dispatch")
            graph.add_conditional_edges("dispatch", self._route,
                {role: role for role in PARTICIPANTS} | {"DONE": END})
            self._compiled = graph.compile()
        return self._compiled

    @staticmethod
    def _route(state: dict[str, Any]) -> str:
        next_role = str(state.get("next_participant") or "RESEARCH_LEAD").upper()
        if next_role == "FINAL_SYNTHESIZER":  # persisted-state compatibility
            next_role = "FINAL_STRATEGIST"
        if next_role == "ADVISOR_FOLLOWUP":  # durable production follow-up maps to the room's bounded follow-up node
            next_role = "FOLLOWUP_RESEARCH"
        return next_role if next_role in PARTICIPANTS else "DONE"

    @staticmethod
    def _dispatch(state: dict[str, Any]) -> dict[str, Any]:
        return state

    def turn(self, state: dict[str, Any], *, production_case_binding: dict[str, str] | None = None) -> dict[str, Any]:
        """Route one bounded turn in shadow mode or under exact case lineage.

        The graph itself never persists production state. The MCP production
        controller supplies and validates this binding, then writes projections
        through the existing Research Case Engine.
        """
        if state.get("metadata", {}).get("shadow_mode") is not True:
            binding = production_case_binding or {}
            required = ("objective_id", "project_id", "case_id", "job_id")
            if (any(not str(binding.get(key) or "").strip() for key in required)
                    or str(binding.get("case_id")) != str(state.get("case_id"))):
                raise ValueError("RESEARCH_ROOM_EXACT_PRODUCTION_CASE_BINDING_REQUIRED")
        try:
            return self._graph().invoke(state)
        except ModuleNotFoundError as exc:
            if exc.name != "langgraph" and not str(exc.name or "").startswith("langgraph."):
                raise
            # The graph's contract is one persisted participant turn. In
            # minimal Nova runtimes without the optional LangGraph package,
            # execute the same selected node directly rather than blocking
            # shadow Research intake on an orchestration library install.
            participant = str(state.get("next_participant") or "RESEARCH_LEAD").upper()
            if participant == "FINAL_SYNTHESIZER":
                participant = "FINAL_STRATEGIST"
            if participant not in PARTICIPANTS:
                return {**state, "next_participant": "DONE"}
            return self._execute(participant, state)


@lru_cache(maxsize=1)
def langgraph_version() -> str | None:
    try:
        from importlib.metadata import version
        return version("langgraph")
    except Exception:
        return None
