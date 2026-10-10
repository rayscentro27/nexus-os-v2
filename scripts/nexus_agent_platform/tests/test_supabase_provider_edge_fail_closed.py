from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DISABLED_PROVIDER_FUNCTIONS = {
    "hermes-chat",
    "create-guest-invitation",
    "create-invited-checkout",
    "create-stripe-checkout",
    "goclear-followup-trigger",
    "goclear-marketing-send",
    "send-client-email",
}


def test_supabase_provider_edge_endpoints_fail_closed_without_loading_credentials():
    for function_name in DISABLED_PROVIDER_FUNCTIONS:
        source = (ROOT / "supabase/functions" / function_name / "index.ts").read_text()
        assert "Deno.serve" in source
        assert "status: 503" in source
        assert "Deno.env.get" not in source
        assert "api.resend.com" not in source
        assert "api.stripe.com" not in source
        assert "openrouter.ai" not in source
        assert "generativelanguage.googleapis.com" not in source


def test_provider_action_denials_keep_options_preflight_non_mutating():
    for function_name in DISABLED_PROVIDER_FUNCTIONS:
        source = (ROOT / "supabase/functions" / function_name / "index.ts").read_text()
        assert 'request.method === "OPTIONS"' in source
        assert "status: 204" in source
        assert "fetch(" not in source
