#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent.parent
sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import *  # noqa:F401,F403,E402

TABLES=[
 "client_profiles","client_tasks","client_documents","readiness_scores","credit_workflow_items","dispute_cases",
 "dispute_letter_drafts","business_profile_requirements","funding_readiness_scores","business_opportunities","partner_offers",
 "approval_cards","admin_review_queue","approved_client_guidance","client_questions","client_escalations","proof_events",
 "connector_health","engine_runs","youtube_sources","youtube_review_items","social_drafts","subscription_memberships","payments_status"
]

FILE_TABLE_MAP={
 "client_profiles_latest.json":"client_profiles","client_tasks_latest.json":"client_tasks","client_documents_latest.json":"client_documents",
 "credit_profile_readiness_scores_latest.json":"readiness_scores","business_profile_readiness_scores_latest.json":"readiness_scores",
 "funding_readiness_scores_latest.json":"funding_readiness_scores","credit_repair_workflow_latest.json":"credit_workflow_items",
 "dispute_workflow_test_latest.json":"dispute_cases","dispute_letter_drafts_latest.json":"dispute_letter_drafts",
 "business_profile_requirements_latest.json":"business_profile_requirements","business_opportunities_latest.json":"business_opportunities",
 "partner_offers_latest.json":"partner_offers","approval_cards_latest.json":"approval_cards","admin_review_queue_latest.json":"admin_review_queue",
 "approved_client_guidance_latest.json":"approved_client_guidance","client_questions_latest.json":"client_questions",
 "client_escalations_latest.json":"client_escalations","proof_events_latest.json":"proof_events","connector_health_latest.json":"connector_health",
 "youtube_video_metadata_latest.json":"youtube_sources","youtube_review_items_latest.json":"youtube_review_items","social_drafts_latest.json":"social_drafts",
 "subscription_membership_model_latest.json":"subscription_memberships","payment_status_latest.json":"payments_status"
}
