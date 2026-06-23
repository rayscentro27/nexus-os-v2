"""Creative-design + design-inspiration job handlers (Day 9). Deterministic subprocess calls
to the Day 9 scripts. No external image/model calls, no publishing."""
from __future__ import annotations

from ._base import run_script, ok, fail


def _run(rel, args, label):
    r = run_script(rel, args)
    return ok({"script": label, **r}) if r["returncode"] == 0 else fail(f"{label} failed", r)


def _brief_args(job):
    bid = (job.get("input") or {}).get("brief_id")
    return ["--brief-id", str(bid)] if bid else ["--sample"]


def create_design_brief(job, ctx):
    return _run("scripts/creative/create_design_brief.py", ["--sample"], "create_design_brief")


def generate_design_variants(job, ctx):
    return _run("scripts/creative/generate_design_variants.py", _brief_args(job), "generate_design_variants")


def score_design_variants(job, ctx):
    return _run("scripts/creative/score_design_variants.py", _brief_args(job), "score_design_variants")


def compare_design_variants(job, ctx):
    return _run("scripts/creative/compare_design_variants.py", _brief_args(job), "compare_design_variants")


def register_inspiration(job, ctx):
    inp = job.get("input") or {}
    if inp.get("source_name"):
        args = ["--source-name", str(inp["source_name"]), "--source-type", str(inp.get("source_type", "reference")),
                "--category", str(inp.get("category", "reference")), "--summary", str(inp.get("summary", ""))]
        return _run("scripts/design/register_design_inspiration.py", args, "register_design_inspiration")
    return fail("no source_name in job input")


def extract_patterns(job, ctx):
    return _run("scripts/design/extract_design_patterns.py", ["--sample"], "extract_design_patterns")


def create_feature_packet(job, ctx):
    return _run("scripts/design/create_feature_design_packet.py", ["--sample"], "create_feature_design_packet")


def review_ui_quality(job, ctx):
    inp = job.get("input") or {}
    args = ["--title", str(inp["title"])] if inp.get("title") else ["--sample"]
    return _run("scripts/design/review_ui_quality.py", args, "review_ui_quality")
