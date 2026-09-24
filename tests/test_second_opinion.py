"""
Unit tests for Second Opinion Intelligence layer:
- Comparator (FareIndex tiers, Google range tiers, raw price_level disagreement, signal gap, divergence classification)
- Explanations (deterministic templates, absence of speculative claims, numerical context)
- Insights Builder (structured payload, API readiness)
"""
import unittest

from app.intelligence.comparator import (
    compare_signals,
    determine_fareindex_tier,
    determine_google_range_tier,
)
from app.intelligence.explanations import generate_explanation
from app.intelligence.insights import build_second_opinion


class TestSecondOpinionIntelligence(unittest.TestCase):
    """Test suite for deterministic Second Opinion intelligence layer."""

    def test_1_regression_hyd_del_low_vs_high_full_divergence(self):
        """
        Regression test with empirical HYD-DEL experiment data:
        Live fare = ₹7,542
        FareIndex: P25=₹8,288, Median=₹8,559, P75=₹10,162
        Google: price_level='high', typical_price_range=[6400, 7500]
        Expected: FareIndex=LOW, Google Raw=HIGH, Google Range=HIGH, Status=FULL_DIVERGENCE, gap ~ -20.4%
        """
        live_price = 7542.0
        fareindex_baseline = {"p25": 8288.0, "median": 8559.0, "p75": 10162.0}
        serpapi_insights = {
            "lowest_price": 7542.0,
            "price_level": "high",
            "typical_price_range": [6400.0, 7500.0]
        }

        res = compare_signals(live_price, fareindex_baseline, serpapi_insights)

        self.assertEqual(res["fareindex"]["tier"], "LOW")
        self.assertEqual(res["google"]["price_level"], "high")
        self.assertEqual(res["google"]["range_tier"], "HIGH")
        self.assertEqual(res["comparison"]["status"], "FULL_DIVERGENCE")
        self.assertTrue(res["comparison"]["raw_level_disagreement"])

        # Check numerical values
        self.assertAlmostEqual(res["fareindex"]["pct_deviation"], -11.88, places=1)
        self.assertAlmostEqual(res["google"]["pct_deviation"], 8.52, places=1)
        self.assertAlmostEqual(res["comparison"]["signal_gap"], -20.40, places=1)

    def test_2_low_fareindex_vs_typical_google_divergence(self):
        """Live fare is LOW by FareIndex, but TYPICAL by Google Flights."""
        live_price = 3994.0
        fareindex_baseline = {"p25": 5359.0, "median": 6712.0, "p75": 8433.0}
        serpapi_insights = {
            "lowest_price": 3994.0,
            "price_level": "typical",
            "typical_price_range": {"low": 3450.0, "high": 6200.0}
        }

        res = compare_signals(live_price, fareindex_baseline, serpapi_insights)

        self.assertEqual(res["fareindex"]["tier"], "LOW")
        self.assertEqual(res["google"]["range_tier"], "TYPICAL")
        self.assertTrue(res["comparison"]["raw_level_disagreement"])
        self.assertIn(res["comparison"]["status"], ["PARTIAL_DIVERGENCE", "FULL_DIVERGENCE"])

    def test_3_typical_vs_typical_with_small_gap_agreement(self):
        """Both signals classify as TYPICAL with signal gap < 10% -> AGREEMENT."""
        live_price = 8500.0
        fareindex_baseline = {"p25": 8000.0, "median": 8500.0, "p75": 9500.0}
        serpapi_insights = {
            "lowest_price": 8500.0,
            "price_level": "typical",
            "typical_price_range": [8000.0, 9000.0]
        }

        res = compare_signals(live_price, fareindex_baseline, serpapi_insights)

        self.assertEqual(res["fareindex"]["tier"], "TYPICAL")
        self.assertEqual(res["google"]["range_tier"], "TYPICAL")
        self.assertAlmostEqual(res["fareindex"]["pct_deviation"], 0.0, places=1)
        self.assertAlmostEqual(res["google"]["pct_deviation"], 0.0, places=1)
        self.assertAlmostEqual(res["comparison"]["signal_gap"], 0.0, places=1)
        self.assertEqual(res["comparison"]["status"], "AGREEMENT")
        self.assertFalse(res["comparison"]["raw_level_disagreement"])

    def test_4_high_vs_high_with_small_gap_agreement(self):
        """Both signals classify as HIGH with signal gap < 10% -> AGREEMENT."""
        live_price = 11500.0
        fareindex_baseline = {"p25": 8000.0, "median": 9000.0, "p75": 10000.0}
        serpapi_insights = {
            "lowest_price": 11500.0,
            "price_level": "high",
            "typical_price_range": [8500.0, 9500.0]
        }

        res = compare_signals(live_price, fareindex_baseline, serpapi_insights)

        self.assertEqual(res["fareindex"]["tier"], "HIGH")
        self.assertEqual(res["google"]["range_tier"], "HIGH")
        # FareIndex pct = (11500-9000)/9000 = +27.78%
        # SerpApi pct = (11500-9000)/9000 = +27.78%
        # Signal gap = 0% -> AGREEMENT
        self.assertEqual(res["comparison"]["status"], "AGREEMENT")

    def test_5_adjacent_tiers_partial_divergence(self):
        """Adjacent tiers with gap between 10% and 25% -> PARTIAL_DIVERGENCE."""
        live_price = 5500.0
        fareindex_baseline = {"p25": 5000.0, "median": 6000.0, "p75": 7000.0}  # live is TYPICAL (-8.33%)
        serpapi_insights = {
            "lowest_price": 5500.0,
            "price_level": "high",
            "typical_price_range": [4000.0, 5000.0]  # midpoint 4500, live is HIGH (+22.22%)
        }
        # Signal gap = -8.33 - 22.22 = -30.55% (diff == 1, abs_gap >= 25 -> FULL_DIVERGENCE)
        res1 = compare_signals(live_price, fareindex_baseline, serpapi_insights)
        self.assertEqual(res1["comparison"]["status"], "FULL_DIVERGENCE")

        # Test case specifically in 10-24% range
        # FareIndex: median 6000, live 5700 -> -5.0% (TYPICAL)
        # SerpApi: mid 5000, live 5700 -> +14.0% (HIGH, range 4500-5500)
        # Gap = -5.0 - 14.0 = -19.0% -> PARTIAL_DIVERGENCE
        serpapi_insights_2 = {
            "lowest_price": 5700.0,
            "price_level": "high",
            "typical_price_range": [4500.0, 5500.0]
        }
        res2 = compare_signals(5700.0, fareindex_baseline, serpapi_insights_2)
        self.assertEqual(res2["fareindex"]["tier"], "TYPICAL")
        self.assertEqual(res2["google"]["range_tier"], "HIGH")
        self.assertEqual(res2["comparison"]["status"], "PARTIAL_DIVERGENCE")

    def test_6_missing_price_insights_returns_insufficient_data(self):
        """Missing SerpApi price_insights returns INSUFFICIENT_DATA."""
        res = compare_signals(7500.0, {"p25": 7000, "median": 8000, "p75": 9000}, None)
        self.assertEqual(res["comparison"]["status"], "INSUFFICIENT_DATA")
        self.assertEqual(res["google"]["range_tier"], "UNKNOWN")
        self.assertIsNone(res["comparison"]["signal_gap"])

    def test_7_missing_typical_price_range(self):
        """Missing typical_price_range leaves Google range tier UNKNOWN."""
        serpapi_insights = {
            "lowest_price": 7500.0,
            "price_level": "high",
            # typical_price_range missing
        }
        res = compare_signals(7500.0, {"p25": 7000, "median": 8000, "p75": 9000}, serpapi_insights)
        self.assertEqual(res["google"]["range_tier"], "UNKNOWN")
        self.assertEqual(res["google"]["price_level"], "high")
        self.assertEqual(res["comparison"]["status"], "INSUFFICIENT_DATA")

    def test_8_missing_fareindex_quantiles(self):
        """Missing FareIndex quantiles leaves FareIndex tier UNKNOWN."""
        serpapi_insights = {"lowest_price": 7500.0, "typical_price_range": [7000, 8000]}
        res = compare_signals(7500.0, None, serpapi_insights)
        self.assertEqual(res["fareindex"]["tier"], "UNKNOWN")
        self.assertEqual(res["comparison"]["status"], "INSUFFICIENT_DATA")

    def test_9_missing_median_leaves_signal_gap_none(self):
        """Missing FareIndex median leaves signal_gap None."""
        baseline = {"p25": 7000, "median": None, "p75": 9000}
        serpapi_insights = {"lowest_price": 7500.0, "typical_price_range": [7000, 8000]}
        res = compare_signals(7500.0, baseline, serpapi_insights)
        self.assertIsNone(res["comparison"]["signal_gap"])
        self.assertEqual(res["comparison"]["status"], "INSUFFICIENT_DATA")

    def test_10_raw_google_price_level_disagreement_tracked_separately(self):
        """Verifies raw_level_disagreement is distinct from range tier."""
        # Live 7500: FareIndex is LOW (P25=8000). Google raw is 'typical', but typical range is [6000, 7000] (range tier HIGH).
        baseline = {"p25": 8000, "median": 8500, "p75": 9500}
        serpapi_insights = {
            "lowest_price": 7500.0,
            "price_level": "typical",  # raw says typical
            "typical_price_range": [6000.0, 7000.0]  # range says high
        }
        res = compare_signals(7500.0, baseline, serpapi_insights)
        self.assertEqual(res["fareindex"]["tier"], "LOW")
        self.assertEqual(res["google"]["price_level"], "typical")
        self.assertEqual(res["google"]["range_tier"], "HIGH")
        # FareIndex (LOW) vs Raw (TYPICAL) -> Disagreement is True
        self.assertTrue(res["comparison"]["raw_level_disagreement"])

    def test_11_explanation_neutrality_and_factual_integrity(self):
        """Verifies explanation contains no speculation and includes factual transparency statement."""
        baseline = {"p25": 8288.0, "median": 8559.0, "p75": 10162.0}
        serpapi_insights = {
            "lowest_price": 7542.0,
            "price_level": "high",
            "typical_price_range": [6400.0, 7500.0]
        }
        res = compare_signals(7542.0, baseline, serpapi_insights)
        explanation = generate_explanation(res)

        # Must contain transparency sentence
        self.assertIn("The two signals use different reference datasets and methodologies", explanation)
        # Must contain exact numerical context
        self.assertIn("8,559", explanation)
        self.assertIn("6,400", explanation)
        self.assertIn("7,500", explanation)
        # Must NOT make unverified assertions about Google's internal training data
        self.assertNotIn("global baseline", explanation.lower())
        self.assertNotIn("google uses a global", explanation.lower())

    def test_12_zero_invalid_and_boundary_handling(self):
        """Verifies safe handling of 0, negative, and extreme values."""
        # Zero price
        res_zero = compare_signals(0.0, {"p25": 1000, "median": 2000, "p75": 3000}, {"typical_price_range": [1500, 2500]})
        self.assertEqual(res_zero["fareindex"]["tier"], "LOW")
        self.assertEqual(res_zero["google"]["range_tier"], "LOW")

        # None price
        res_none = compare_signals(None, None, None)
        self.assertEqual(res_none["comparison"]["status"], "INSUFFICIENT_DATA")

        # Invalid types
        res_invalid = compare_signals("invalid", {"p25": "bad", "median": "bad", "p75": "bad"}, {"typical_price_range": "bad"})
        self.assertEqual(res_invalid["comparison"]["status"], "INSUFFICIENT_DATA")

    def test_13_no_api_key_in_insights_output(self):
        """Verifies build_second_opinion payload never exposes any API key."""
        raw_serpapi_response = {
            "search_parameters": {
                "engine": "google_flights",
                "api_key": "super_secret_test_key_xyz",
                "departure_id": "HYD",
                "arrival_id": "DEL"
            },
            "price_insights": {
                "lowest_price": 7542,
                "price_level": "high",
                "typical_price_range": [6400, 7500]
            },
            "best_flights": [
                {
                    "price": 7542,
                    "flights": [{"departure_airport": {"id": "HYD"}, "arrival_airport": {"id": "DEL"}, "airline": "IndiGo"}]
                }
            ]
        }
        baseline = {"p25": 8288.0, "median": 8559.0, "p75": 10162.0}

        insight_payload = build_second_opinion(
            live_price=None,
            route="HYD-DEL",
            fareindex_baseline=baseline,
            serpapi_data=raw_serpapi_response
        )

        payload_str = str(insight_payload)
        self.assertNotIn("super_secret_test_key_xyz", payload_str)
        self.assertEqual(insight_payload["comparison"]["status"], "FULL_DIVERGENCE")
        self.assertEqual(insight_payload["live_price"], 7542.0)
        self.assertEqual(insight_payload["route"], "HYD-DEL")
        self.assertIn("explanation", insight_payload)
        self.assertIn("methodology", insight_payload)


if __name__ == "__main__":
    unittest.main()
