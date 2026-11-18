from __future__ import annotations

import unittest

from nexus_agent_platform.research_room.execution_modes import (
    build_execution_strategy, classify_execution_mode, depth_for_mode,
    information_value_decision,
)


class ExecutionModeTests(unittest.TestCase):
    def test_execution_modes_classify(self):
        self.assertEqual(classify_execution_mode("top businesses to pursue"), "BUSINESS_OPPORTUNITY_MODE")
        self.assertEqual(classify_execution_mode("Trading strategy paper test"), "TRADING_STRATEGY_MODE")
        self.assertEqual(classify_execution_mode("Review OpenCode technology"), "NEXUS_ENHANCEMENT_MODE")

    def test_depth_budget_cannot_stop(self):
        self.assertEqual(depth_for_mode("DEEP_RESEARCH_MODE"), "DEEP")
        result = information_value_decision("unknown question", {})
        self.assertEqual(result["decision"], "PRESERVE_AS_UNCERTAINTY")
        self.assertTrue(result["continue_root_objective"])

    def test_needle_more_information_and_low_confidence_cannot_stop(self):
        case = {"original_request": "Trading strategy", "metadata": {"execution_mode": "TRADING_STRATEGY_MODE", "domain_sections": {}},
                "unresolved_items": [{"kind": "LOW_CONFIDENCE"}], "questions": [{"question": "more?", "status": "OPEN"}]}
        strategy = build_execution_strategy(case)
        self.assertIn("next_action", strategy)
        self.assertIn("library_additions", strategy)
        self.assertEqual(strategy["execution_mode"], "TRADING_STRATEGY_MODE")

    def test_business_mode_cannot_end_as_generic_summary_and_requires_nova(self):
        case = {"original_request": "What are the top 3 online businesses Nexus should pursue and how can Nova automate each one?",
                "metadata": {"execution_mode": "BUSINESS_OPPORTUNITY_MODE"}, "unresolved_items": [{"kind": "SOURCE_UNAVAILABLE"}]}
        strategy = build_execution_strategy(case)
        self.assertEqual(strategy["execution_mode"], "BUSINESS_OPPORTUNITY_MODE")
        self.assertTrue(strategy["top_businesses"])
        self.assertIn("how_nova_runs_it", strategy)
        self.assertTrue(strategy["next_action"])

    def test_negative_backtest_poor_economics_and_source_or_advisor_failure_continue(self):
        for issue in ("NEGATIVE_BACKTEST", "POOR_ECONOMICS", "SOURCE_UNAVAILABLE", "ADVISOR_UNAVAILABLE", "SOFT_COST_LIMIT"):
            case = {"original_request": "TradingView trading strategy", "metadata": {"execution_mode": "TRADING_STRATEGY_MODE"},
                    "unresolved_items": [{"kind": issue}]}
            strategy = build_execution_strategy(case)
            self.assertTrue(strategy.get("next_action"), issue)
            self.assertEqual(strategy["execution_mode"], "TRADING_STRATEGY_MODE")

    def test_enhancement_requires_implementation_plan(self):
        strategy = build_execution_strategy({"original_request": "Review OpenCode", "metadata": {"execution_mode": "NEXUS_ENHANCEMENT_MODE"}})
        self.assertTrue(strategy["implementation_plan"])
        self.assertTrue(strategy["library_additions"])
        self.assertTrue(strategy["next_action"])

    def test_library_extraction_and_information_value(self):
        strategy = build_execution_strategy({"original_request": "Review OpenCode", "metadata": {"execution_mode": "NEXUS_ENHANCEMENT_MODE"},
            "questions": [{"question": "Could permissions change adoption?", "decision_impacts": {"implementation": True}}]})
        self.assertTrue(strategy["library_additions"])
        self.assertEqual(strategy["information_value_decisions"][0]["decision"], "ANSWER_NOW")


if __name__ == "__main__":
    unittest.main()
