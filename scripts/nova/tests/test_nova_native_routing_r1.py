"""NOVA_OBJECTIVE_INTAKE_AND_NATIVE_ROUTING_REPAIR_R1 routing contract.

Loads the EFFECTIVE (last) definition of `_resolve_opportunities_read_request` from a Nova
worker file and checks which requests the Business Opportunities pre-read may capture.
Anything it does not capture falls through to Hermes native reasoning + MCP tool selection.

    NOVA_WORKER_UNDER_TEST=<path to nova_telegram_worker.py>  (defaults to the patched release copy)
    NOVA_WORKER_EXPECT=FIXED | DEFECT
"""
from __future__ import annotations

import ast
import os
import re
from pathlib import Path

import pytest

WORKER = Path(os.environ.get("NOVA_WORKER_UNDER_TEST", ""))
EXPECT = os.environ.get("NOVA_WORKER_EXPECT", "FIXED")
TOOLS = [{"name": n} for n in ("opportunities_get", "opportunities_list", "opportunities_latest", "opportunities_needs_research",
                               "opportunities_search", "opportunities_top", "nexus_get_project", "nexus_get_projects", "nexus_get_reviews")]

BLACK_BOX_1 = ("Take one currently supported low-cost commerce opportunity from existing Research and move it as far as Nexus can "
               "autonomously through Research, Marketing, Creative, Commerce, Distribution, measurement, analysis, and continuation "
               "using only currently approved tools, providers, policies, and verified facts.")
BLACK_BOX_2 = ("DO NOT SELECT A NEW BUSINESS OPPORTUNITY. Resume PROJECT_ID=proj_98ef515bccee4b58 VENTURE_ID=vnt_holiday_commerce_pilot_2026 "
               "OPPORTUNITY_ID=opp_holiday_ceramic_mug_2026 and continue the existing project.")

NATIVE = [  # must NOT be captured by the opportunities pre-read
    "Resume project proj_98ef515bccee4b58.",
    "Do not select a new business opportunity. Continue project proj_98ef515bccee4b58.",
    "What did Creative make for the Holiday mug project?",
    "What approvals are waiting for me?",
    "What is Trading doing today?",
    "lol thanks Nova, have a good night",
    BLACK_BOX_1,
    BLACK_BOX_2,
    "Continue the existing project for the mug opportunity.",
]
DISCOVERY = [  # explicit opportunity-discovery reads may still use the register
    "Show me current commercial opportunities.",
    "What are the top business opportunities right now?",
    "Which opportunities need more research?",
    "Tell me about the Mobile DNA testing opportunity.",
]


def _load(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    defs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_resolve_opportunities_read_request"]
    assert defs, "resolver not found"
    ns: dict = {"re": re}
    exec(compile(ast.Module(body=[defs[-1]], type_ignores=[]), str(path), "exec"), ns)  # effective (last) definition
    return ns["_resolve_opportunities_read_request"]


@pytest.fixture(scope="module")
def resolve():
    if not WORKER.is_file():
        pytest.skip("NOVA_WORKER_UNDER_TEST not set")
    return _load(WORKER)


@pytest.mark.parametrize("text", NATIVE)
def test_natural_language_reaches_native_reasoning(resolve, text):
    captured = resolve(text, TOOLS)
    if EXPECT == "DEFECT" and text in (BLACK_BOX_1, BLACK_BOX_2):
        assert captured is not None  # proves the original intercept
    elif EXPECT == "FIXED":
        assert captured is None, f"pre-read hijacked: {text!r} -> {captured}"


@pytest.mark.parametrize("text", DISCOVERY)
def test_explicit_opportunity_discovery_still_uses_register(resolve, text):
    r = resolve(text, TOOLS)
    assert r is not None and r["tool_name"].startswith("opportunities_")
