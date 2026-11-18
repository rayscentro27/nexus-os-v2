"""Nexus Creative Provider Router & Failure Rerouter.

Implements governed provider selection and failure rerouting across certified Creative providers.
Enforces:
- Meta.ai is primary for proven image & text-to-video generation ($0, low Mac impact).
- Modal is governed under FREE_CREDIT_THEN_PAID_METERED (requires Ray approval when credit UNKNOWN).
- Higgsfield is audited / unconfigured (requires CLI/credentials before routing).
- Kaggle is strictly DISABLED for Creative media generation.
- Disallows coding-agent local substitute media (no Pillow/SVG/canvas/slideshow/say to fake provider success).
- Preserves CREATIVE_REQUEST_ID and campaign lineage on reroute.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent.parent

DETERMINISTIC_MEDIA_PRODUCTION_ROUTABLE = False
LOCAL_CREATIVE_SUBSTITUTE_ALLOWED = False

# Category-specific provider rankings based on actual Section 30C certification
# ONLY verified quality-capable AI providers are permitted in production creative routing.
# Local deterministic media tools (PIL/FFmpeg/say) are strictly prohibited as production creative generators.
CREATIVE_ROUTING_TABLE = {
    "PRODUCT_IMAGES": {
        "primary": "meta_ai_browser_creative",
        "secondary": "modal",
        "fallback": None,
        "cost_policy": "prefer_free_included"
    },
    "MARKETPLACE_IMAGES": {
        "primary": "meta_ai_browser_creative",
        "secondary": "modal",
        "fallback": None,
        "cost_policy": "prefer_free_included"
    },
    "SOCIAL_IMAGES": {
        "primary": "meta_ai_browser_creative",
        "secondary": "modal",
        "fallback": None,
        "cost_policy": "prefer_free_included"
    },
    "THUMBNAILS": {
        "primary": "meta_ai_browser_creative",
        "secondary": "modal",
        "fallback": None,
        "cost_policy": "prefer_free_included"
    },
    "TEXT_TO_VIDEO": {
        "primary": "meta_ai_browser_creative",
        "secondary": "modal",
        "fallback": None,
        "cost_policy": "prefer_free_included"
    },
    "VERTICAL_SHORTS": {
        "primary": "modal",
        "secondary": "meta_ai_browser_creative",
        "fallback": None,
        "cost_policy": "requires_approval_if_paid"
    },
    "FACELESS_VIDEO": {
        "primary": "modal",
        "secondary": "meta_ai_browser_creative",
        "fallback": None,
        "cost_policy": "requires_approval_if_paid"
    },
    "BRAND_ASSET": {
        "primary": "meta_ai_browser_creative",
        "secondary": "modal",
        "fallback": None,
        "cost_policy": "prefer_free_included"
    }
}

DISALLOWED_CREATIVE_PROVIDERS = {
    "deterministic_media": "DETERMINISTIC_MEDIA_PRODUCTION_ROUTABLE=NO (diagnostics/QA/inspection only; production creative generation routing prohibited)",
    "kaggle": "KAGGLE_CREATIVE_MEDIA_ROUTING=DISABLED (prior attempts unstable; research/data only)",
    "coding_agent_substitute": "Production Creative media must NOT fall back to coding-agent local media",
    "pillow_substitute": "DISALLOWED as production creative generator",
    "svg_substitute": "DISALLOWED as production creative generator",
    "canvas_substitute": "DISALLOWED as production creative generator",
    "say_voice_substitute": "DISALLOWED as production voice provider",
    "slideshow_substitute": "DISALLOWED as production creative video",
    "local_ffmpeg_substitute": "DISALLOWED as production creative generator"
}

def select_creative_provider(category: str, *, approved_spend: float = 0.0, failed_providers: Optional[List[str]] = None) -> Dict[str, Any]:
    failed = set(failed_providers or [])
    cat_cfg = CREATIVE_ROUTING_TABLE.get(category.upper(), CREATIVE_ROUTING_TABLE["PRODUCT_IMAGES"])
    
    candidates = [c for c in [cat_cfg.get("primary"), cat_cfg.get("secondary"), cat_cfg.get("fallback")] if c]
    viable = [c for c in candidates if c not in failed and c not in DISALLOWED_CREATIVE_PROVIDERS]
    
    if not viable:
        return {
            "status": "PROVIDER_UNAVAILABLE",
            "category": category,
            "selected_provider": None,
            "reason": "All certified quality-capable creative providers have been attempted or disqualified. Fallback to local/deterministic media is prohibited."
        }
    
    selected = viable[0]
    
    # Governance check for Modal / paid compute
    if selected == "modal" and approved_spend <= 0.0:
        return {
            "status": "WAITING_FOR_RAY_APPROVAL",
            "category": category,
            "selected_provider": "modal",
            "approval_reason": "Modal is classified as FREE_CREDIT_THEN_PAID_METERED; credit remaining is UNKNOWN. Ray approval required before running metered compute.",
            "candidates": candidates
        }
        
    return {
        "status": "ROUTED",
        "category": category,
        "selected_provider": selected,
        "cost_policy": cat_cfg["cost_policy"],
        "candidates": candidates
    }

def handle_provider_failure(creative_request_id: str, category: str, failed_provider: str, error_reason: str, failed_history: Optional[List[str]] = None) -> Dict[str, Any]:
    history = list(failed_history or [])
    history.append(failed_provider)
    
    now_iso = datetime.now(timezone.utc).isoformat()
    reroute = select_creative_provider(category, failed_providers=history)
    
    return {
        "creative_request_id": creative_request_id,
        "timestamp": now_iso,
        "failed_provider": failed_provider,
        "failure_reason": error_reason,
        "attempted_providers": history,
        "reroute_decision": reroute,
        "local_agent_substitute_permitted": False
    }
