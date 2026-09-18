import unittest

from scripts.nexus_agent_platform.customer_service_engine import (
    CustomerContext,
    CustomerServiceEngine,
    CustomerServiceStore,
    ProductSupportPack,
    certify_goclear_scenarios,
    goclear_support_pack,
    identify_support_intent,
)


class CustomerServiceEngineTest(unittest.TestCase):
    def setUp(self):
        self.store = CustomerServiceStore()
        self.store.register_pack(goclear_support_pack())
        self.engine = CustomerServiceEngine(self.store)
        self.context = CustomerContext("tenant-1", "goclear", "brand-1", "customer-1", "readiness_review_97", verified=True)

    def test_context_and_product_isolation(self):
        self.assertTrue(self.engine.identify_customer_context(self.context)["cross_scope_allowed"])
        other = CustomerContext("tenant-1", "other-business", "brand-1", "customer-1", "readiness_review_97", verified=True)
        response = self.engine.determine_allowed_response("Show me the other business's documents.", other)
        self.assertEqual(response["decision"], "ESCALATE")

    def test_support_pack_and_intents(self):
        self.assertEqual(self.engine.load_support_pack(self.context).status, "READY_FOR_REVIEW")
        self.assertEqual(identify_support_intent("Where do I upload my bank statement?"), "DOCUMENT_REQUIREMENT")
        self.assertEqual(identify_support_intent("What is my next step?"), "NEXT_STEP")

    def test_goclear_support_behavior(self):
        response = self.engine.determine_allowed_response("What documents am I missing?", self.context)
        self.assertIn(response["decision"], {"ALLOWED", "QUALIFIED_WITH_QUALIFIER"})
        guarantee = self.engine.determine_allowed_response("If I upload these, will I get approved?", self.context)
        self.assertIn("approval", guarantee["qualifier"])
        self.assertFalse(self.engine.determine_allowed_action("APPROVE_FUNDING", self.context)["allowed"])

    def test_high_risk_cases_escalate(self):
        for message in ("I want to make a formal complaint.", "I need a refund exception.", "I have a privacy issue."):
            response = self.engine.determine_allowed_response(message, self.context)
            self.assertEqual(response["decision"], "ESCALATE")

    def test_case_and_voc_lifecycle(self):
        case = self.engine.create_case("Where do I upload documents?", self.context)
        self.assertEqual(case.status, "OPEN")
        signal = self.engine.emit_voice_of_customer_signal(case, "Where do I upload documents?")
        self.assertEqual(signal["source_case_id"], case.case_id)
        self.assertEqual(len(self.store.cases), 1)

    def test_all_goclear_certification_scenarios_are_internal(self):
        result = certify_goclear_scenarios()
        self.assertEqual(set(result["scenarios"]), set("ABCDEFGH"))
        self.assertEqual(result["scenarios"]["E"]["decision"], "ESCALATE")
        self.assertEqual(result["scenarios"]["F"]["decision"], "ESCALATE")
        self.assertEqual(result["scenarios"]["G"]["decision"], "ESCALATE")
        self.assertEqual(result["scenarios"]["H"]["decision"], "ESCALATE")
        self.assertFalse(result["customer_contact"])
        self.assertFalse(result["external_mutations"])

    def test_second_product_registers_without_engine_change(self):
        second = ProductSupportPack("support_saas_v1", "nexus", "saas", "1", "READY_FOR_REVIEW", ["technical help"], [], [], [], ["EXPLAIN_PROCESS"], [], [], [], [], [], None, None, [], {}, [], [], "compliance_pack:saas")
        self.store.register_pack(second)
        context = CustomerContext("tenant-1", "nexus", "brand-1", "customer-1", "saas", verified=True)
        self.assertEqual(self.engine.load_support_pack(context).product_id, "saas")


if __name__ == "__main__":
    unittest.main()
