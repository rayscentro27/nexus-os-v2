"""Execution Truth layer (Section 30A) — additive status/view over the existing registries.

Does NOT create a new registry. It distinguishes, per execution method:
  REGISTERED (name in a registry) vs INSTALLED (binary/app present) vs AUTHENTICATED vs
  HEALTH vs EXECUTABLE (has produced work) vs TESTED vs ROUTABLE (safe for the router to pick).

The router must never select a method merely because its name exists in a registry. ROUTABLE
requires: installed + health READY + not unhealthy + (tested OR deterministic native). Unknown
stays UNKNOWN; a registered-but-unverified method reports EXECUTION_VERIFIED=NO (never READY).
"""
from __future__ import annotations
import shutil
from pathlib import Path

EXECUTION_TYPES = {"CLI", "HARNESS", "NATIVE_WORKER", "MCP", "API", "REMOTE_AGENT", "SCRIPT", "OTHER"}

# Observed facts (this task's live probe + Section 28/29 evidence). binary=None => not a CLI.
_METHODS = [
    # id, display, type, env, binary, registered, authenticated, health, compatibility, tested, executed, cost_class, notes
    ("codex_cli", "Codex CLI", "CLI", "mac_mini", "codex", True, "YES", "DEGRADED", "GOOD", True, True, "PAID_METERED",
     "codex-cli 0.167.0 installed; live R16 deep engine; quota exhaustion observed (429) -> DEGRADED, routable when quota resets"),
    ("antigravity_cli", "Antigravity CLI", "CLI", "mac_mini", "agy", True, "YES", "READY", "GOOD", True, True, "INCLUDED_SUBSCRIPTION",
     "agy 1.5.5, Google AI Pro; launch/read/write/boundary + bounded build test PASS (Funding Ready page)"),
    ("antigravity_desktop", "Antigravity Desktop/Full Harness", "HARNESS", "mac_mini", None, True, "YES", "UNHEALTHY", "POOR", True, False, "INCLUDED_SUBSCRIPTION",
     "Installed (/Applications/Antigravity.app) but ~10-min startup + repeated errors on Mac mini; ROUTING DISABLED"),
    ("opencode_cli", "OpenCode CLI", "CLI", "mac_mini", "opencode", True, "UNKNOWN", "UNKNOWN", "UNKNOWN", False, "UNKNOWN", "UNKNOWN",
     "Binary installed (/usr/local/bin/opencode); not tested this task -> EXECUTION_VERIFIED=NO, not routable"),
    ("kilo_cli", "Kilo CLI", "CLI", "mac_mini", "kilo", True, "UNKNOWN", "UNKNOWN", "UNKNOWN", False, "UNKNOWN", "UNKNOWN",
     "Binary installed (/usr/local/bin/kilo); not tested -> EXECUTION_VERIFIED=NO, not routable"),
    ("claude_code", "Claude Code CLI", "CLI", "mac_mini", "claude", True, "UNKNOWN", "UNKNOWN", "GOOD", False, "UNKNOWN", "PAID_METERED",
     "Binary installed (~/.local/bin/claude); not bounded-tested this task -> not routable until verified"),
    ("deepseek_harness", "DeepSeek Harness", "HARNESS", "surface_pro", "deepseek", True, "UNKNOWN", "UNKNOWN", "UNKNOWN", False, False, "UNKNOWN",
     "REGISTERED in harness registry but binary NOT_FOUND on Mac mini -> EXECUTION_VERIFIED=NO, not routable"),
    ("hermes", "Hermes", "HARNESS", "oracle", None, True, "YES", "READY", "PARTIAL", True, True, "INCLUDED_SUBSCRIPTION",
     "Oracle reasoning/coordination; Nova-facing profile allowlist-restricted (PARTIAL native worker); control-plane only, not heavy work"),
    ("nova", "Nova", "NATIVE_WORKER", "oracle", None, True, "YES", "READY", "GOOD", True, True, "INCLUDED_SUBSCRIPTION",
     "Oracle operator/coordination; active"),
    ("nexus_mcp", "Nexus MCP", "MCP", "mac_mini", None, True, "YES", "READY", "GOOD", True, True, "FREE",
     "MCP bridge healthy (401 auth gate = healthy)"),
    ("netlify_cli", "Netlify CLI", "CLI", "netlify", "netlify", True, "YES", "READY", "GOOD", False, "UNKNOWN", "INCLUDED_SUBSCRIPTION",
     "Installed; deploy/publish is governed (approval required)"),
    ("gh_cli", "GitHub CLI", "CLI", "github", "gh", True, "YES", "READY", "GOOD", True, True, "INCLUDED_SUBSCRIPTION", "Installed; source control"),
    ("supabase_cli", "Supabase CLI", "CLI", "supabase", "supabase", True, "UNKNOWN", "UNKNOWN", "GOOD", False, "UNKNOWN", "INCLUDED_SUBSCRIPTION",
     "Installed; project changes governed"),
    ("deterministic_scripts", "Deterministic Python workers", "SCRIPT", "mac_mini", None, True, "N/A", "READY", "GOOD", True, True, "FREE",
     "Venture kernel + opportunities/marketing/creative/funnel engines; $0 deterministic"),
    ("kaggle", "Kaggle notebook", "REMOTE_AGENT", "kaggle", None, True, "YES", "READY", "GOOD", True, True, "FREE",
     "bounded GPU; session-limited; research/data permitted; CREATIVE_MEDIA_ROUTING=DISABLED (prior media stabilization unstable)"),
    ("colab", "Colab", "REMOTE_AGENT", "colab", None, True, "YES", "UNKNOWN", "GOOD", False, "UNKNOWN", "INCLUDED_SUBSCRIPTION", "compute units UNKNOWN"),
    ("modal", "Modal", "REMOTE_AGENT", "modal", None, True, "YES", "READY", "GOOD", False, False, "FREE_CREDIT_THEN_PAID_METERED",
     "Modal profile goclearonline configured in ~/.modal.toml; CLI not in PATH; credit remaining UNKNOWN; WAITING_FOR_RAY_APPROVAL before any metered compute"),
    ("higgsfield", "Higgsfield AI", "API", "remote_saas", None, True, "NO", "UNCONFIGURED", "GOOD", False, False, "PAID_METERED",
     "Higgsfield skills/CLI not installed; unauthenticated; zero-spend policy active -> NOT_ROUTABLE until configured and approval granted"),
    ("meta_ai_browser_creative", "Meta.ai Creative Browser Surface", "BROWSER_AUTOMATION", "mac_mini", None, True, "YES", "READY", "GOOD", True, True, "INCLUDED_SUBSCRIPTION",
     "ALLOWED_ENVIRONMENTS=mac_mini; PROHIBITED_ENVIRONMENTS=oracle. Certified on Mac mini dedicated Chrome profile (port 9222). Real execution VERIFIED: image_generation=READY (1920x1280 WebP), text_to_video=READY (1152x768 10s MP4). image_to_video=NO (unsupported by UI). vertical_video=UNPROVEN. ROUTABLE=YES."),
    ("deterministic_media", "Deterministic Media Composer (PIL+ffmpeg+say)", "SCRIPT", "mac_mini", None, True, "N/A", "READY", "GOOD", True, True, "FREE",
     "PIL image composition + ffmpeg inspection + macOS say; $0. DETERMINISTIC_MEDIA_PRODUCTION_ROUTABLE=NO (diagnostics/QA/inspection only; production creative generation routing prohibited; LOCAL_CREATIVE_SUBSTITUTE_ALLOWED=NO)."),
]

_HEALTHY = {"READY"}
_UNHEALTHY = {"UNHEALTHY", "OFFLINE", "DEPRECATED", "RETIRED"}


def methods(live_probe: bool = True) -> list[dict]:
    out = []
    for (mid, name, typ, env, binary, registered, auth, health, compat, tested, executed, cost, notes) in _METHODS:
        installed = True
        if binary is not None and live_probe:
            installed = shutil.which(binary) is not None
        execution_verified = bool(tested) and str(health) in _HEALTHY
        routable = (installed and str(health) in _HEALTHY and str(health) not in _UNHEALTHY
                    and (bool(tested) or typ in ("NATIVE_WORKER", "SCRIPT", "MCP")))
        out.append({
            "execution_id": mid, "display_name": name, "execution_type": typ, "environment": env,
            "installed": ("YES" if installed else "NO") if binary is not None else "N/A",
            "registered": "YES" if registered else "NO", "authenticated": auth, "health": health,
            "compatibility": compat, "tested": "YES" if tested else "NO",
            "actually_executed_work": ("YES" if executed is True else "NO" if executed is False else "UNKNOWN"),
            "execution_verified": "YES" if execution_verified else "NO",
            "routing_enabled": "YES" if routable else "NO", "cost_class": cost,
            "notes": notes,
        })
    return out


def routable(execution_id: str) -> bool:
    m = next((x for x in methods() if x["execution_id"] == execution_id), None)
    return bool(m and m["routing_enabled"] == "YES")


def routable_methods() -> list[str]:
    return [m["execution_id"] for m in methods() if m["routing_enabled"] == "YES"]


def summary() -> dict:
    ms = methods()
    return {"found": len(ms), "routable": [m["execution_id"] for m in ms if m["routing_enabled"] == "YES"],
            "unhealthy": [m["execution_id"] for m in ms if m["health"] in _UNHEALTHY],
            "registered_not_verified": [m["execution_id"] for m in ms if m["execution_verified"] == "NO"]}
