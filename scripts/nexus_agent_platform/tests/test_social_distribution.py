import unittest

from scripts.nexus_agent_platform.social_distribution import (
    SocialAccount,
    SocialAccountProvisioningRequest,
    SocialAccountReadiness,
    SocialAccountRegistry,
    SocialDistributionRequest,
    SocialDistributionRouter,
    build_attribution,
    build_platform_packages,
    build_queue_record,
)


def account(account_id, business, brand, platform="INSTAGRAM", status="READY", posting=True):
    return SocialAccount(account_id, "tenant_" + business, business, brand, platform, "PAGE", "@" + account_id,
                         platform_account_id=account_id, credential_ref="credential_ref:" + account_id,
                         status=status, posting_allowed=posting, analytics_allowed=True)


def request(account_ids, business="GOCLEAR", brand="GOCLEAR", **kwargs):
    return SocialDistributionRequest(
        distribution_request_id="dist_1", tenant_id="tenant_" + business, business_id=business, brand_id=brand,
        campaign_id="goclear-funding-readiness-r20b", variant_id="v1", creative_asset_ids=["asset_1"],
        platform_targets=["INSTAGRAM"], social_account_ids=account_ids, headline="Prepare before you apply",
        caption="Turn uncertainty into a clearer readiness path.", cta="Review readiness", landing_url="https://goclearonline.cc",
        utm_config={"utm_source": "instagram", "utm_medium": "organic", "utm_campaign": "goclear-readiness", "utm_content": "v1"},
        hashtags=["fundingreadiness"], **kwargs)


class SocialDistributionTests(unittest.TestCase):
    def setUp(self):
        self.goclear_ig = account("gc_ig", "GOCLEAR", "GOCLEAR")
        self.goclear_fb = account("gc_fb", "GOCLEAR", "GOCLEAR", "FACEBOOK")
        self.apex_ig = account("apex_ig", "APEX", "APEX")
        self.registry = SocialAccountRegistry([self.goclear_ig, self.goclear_fb, self.apex_ig])
        self.router = SocialDistributionRouter(self.registry)

    def test_scope_isolation(self):
        req = request(["apex_ig"])
        result = self.router.route(req, compliance_approved=True, approval_approved=True)
        self.assertEqual(result["results"][0]["reason"], "POST_BLOCKED_CROSS_TENANT")

    def test_same_tenant_cross_business_isolation(self):
        shared = account("shared_apex", "APEX", "APEX")
        shared.tenant_id = "tenant_nexus"
        self.registry.register(shared)
        req = request(["shared_apex"])
        req.tenant_id = "tenant_nexus"
        result = self.router.route(req, compliance_approved=True, approval_approved=True)
        self.assertEqual(result["results"][0]["reason"], "POST_BLOCKED_CROSS_BUSINESS")

    def test_business_and_brand_isolation(self):
        req = request(["gc_ig"], business="GOCLEAR", brand="APEX")
        result = self.router.route(req, compliance_approved=True, approval_approved=True)
        self.assertEqual(result["results"][0]["reason"], "POST_BLOCKED_CROSS_BRAND")

    def test_matching_draft_requires_gates_but_does_not_publish(self):
        req = request(["gc_ig"], approval_ref="approval_1", compliance_receipt_ref="compliance_1")
        result = self.router.route(req, compliance_approved=True, approval_approved=True)
        self.assertEqual(result["status"], "READY_FOR_REVIEW")
        self.assertFalse(result["publication_executed"])
        self.assertFalse(result["external_mutation"])

    def test_compliance_and_approval_block(self):
        req = request(["gc_ig"], approval_ref="approval_1")
        self.assertEqual(self.router.route(req, approval_approved=True)["results"][0]["reason"], "POST_BLOCKED_COMPLIANCE")
        req = request(["gc_ig"], compliance_receipt_ref="compliance_1")
        self.assertEqual(self.router.route(req, compliance_approved=True)["results"][0]["reason"], "POST_BLOCKED_APPROVAL")

    def test_wrong_brand_asset_block(self):
        req = request(["gc_ig"], approval_ref="a", compliance_receipt_ref="c")
        result = self.router.route(req, asset_context={"asset_1": {"brand_id": "APEX"}}, compliance_approved=True, approval_approved=True)
        self.assertEqual(result["results"][0]["reason"], "POST_BLOCKED_CROSS_BRAND_ASSET")

    def test_same_business_cross_platform_is_allowed_as_drafts(self):
        req = request(["gc_ig", "gc_fb"], approval_ref="a", compliance_receipt_ref="c")
        req.platform_targets = ["INSTAGRAM", "FACEBOOK"]
        result = self.router.route(req, compliance_approved=True, approval_approved=True)
        self.assertEqual(result["status"], "READY_FOR_REVIEW")
        self.assertEqual({item["platform"] for item in result["platform_packages"]}, {"INSTAGRAM", "FACEBOOK"})

    def test_unhealthy_and_unknown_accounts_block(self):
        unhealthy = account("gc_bad", "GOCLEAR", "GOCLEAR", status="AUTH_REQUIRED", posting=False)
        self.registry.register(unhealthy)
        req = request(["gc_bad"])
        self.assertEqual(self.router.route(req)["results"][0]["reason"], "POST_BLOCKED_ACCOUNT_NOT_READY")
        req = request(["missing"])
        self.assertEqual(self.router.route(req)["results"][0]["reason"], "POST_BLOCKED_UNKNOWN_ACCOUNT")

    def test_attribution_queue_and_provisioning_contracts(self):
        req = request(["gc_ig"])
        attr = build_attribution(req, "INSTAGRAM", "gc_ig", "asset_1")
        self.assertEqual(attr["business_id"], "GOCLEAR")
        self.assertEqual(build_queue_record(req)["publication_enabled"], False)
        provisioning = SocialAccountProvisioningRequest("LATER", "LATER", "LINKEDIN", "later", [], "Later", "bio", "desc", "https://example.com", None, None, None)
        readiness = SocialAccountReadiness(True, True, True, True, True, True, True, True, True, True, True, False)
        self.assertEqual(provisioning.status, "DRAFT")
        self.assertFalse(readiness.verification_requirement_known)

    def test_platform_packages_are_not_identical_copy(self):
        req = request(["gc_ig"])
        instagram = build_platform_packages(req, self.goclear_ig)["INSTAGRAM"]
        facebook = build_platform_packages(req, self.goclear_fb)["FACEBOOK"]
        self.assertNotEqual(instagram["format"], facebook["format"])
        self.assertIn("landing_url", facebook)


if __name__ == "__main__":
    unittest.main()
