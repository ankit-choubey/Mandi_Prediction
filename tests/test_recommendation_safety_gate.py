"""
Comprehensive Test Suite for Farmer-Facing Recommendation Safety Gate
APMC Mandi Market Intelligence System — Phase 1 Trust & Evaluation Gate

Verifies all 12 mandatory specification requirements:
 1. CURRENT data permits normal evaluation.
 2. DELAYED data displays an explicit delay warning.
 3. STALE data blocks active storage recommendations.
 4. STALE data cannot be labeled LIVE or TODAY.
 5. SOURCE_DOWN without a valid fresh alternative blocks recommendations.
 6. UNINITIALIZED data blocks recommendations.
 7. Missing observation date cannot be classified as CURRENT.
 8. Future-dated observations are rejected or explicitly flagged.
 9. Historical analysis remains available when safe, but is clearly labeled historical.
 10. Demo output cannot masquerade as a real market observation.
 11. Every downstream recommendation path applies the safety gate.
 12. Existing economic calculations remain unchanged for valid fresh inputs.
"""

import unittest
from datetime import date, datetime
import pandas as pd
import numpy as np

from src.health_status import (
    HealthStatusEngine,
    HealthReport,
    OperationalState,
    FreshnessStatus,
    RecommendationStatus,
    RecommendationSafetyGate,
    SafetyGateDecision,
    BLOCKED_RECOMMENDATION_MESSAGE
)
from src.economic_model import (
    EconomicParameters,
    evaluate_sell_vs_store,
    evaluate_farmer_storage_recommendation
)
from src.current_data_output import CurrentDataReporter
from src.intelligence_system import MandiMarketIntelligenceEngine
from src.feature_engineering import FEATURE_COLUMNS


class MockPredictor:
    """Mock ML classifier for testing intelligence engine output."""
    def predict(self, X):
        return np.array([2])  # 2 corresponds to Favorable in CLASS_NAMES

    def predict_proba(self, X):
        return np.array([[0.10, 0.20, 0.70]])


class TestRecommendationSafetyGate(unittest.TestCase):
    """Test suite covering all 12 mandatory safety gate requirements."""

    def setUp(self):
        # Deterministic fixed reference date: 2026-10-25
        self.ref_date = date(2026, 10, 25)
        self.gate = RecommendationSafetyGate(current_ref_date=self.ref_date)
        self.params = EconomicParameters(
            storage_cost_per_quintal=50.0,
            quantity_loss_fraction=0.02,
            annual_carrying_rate=0.0,
            holding_period_days=7,
            carrying_cost_type='none'
        )

    # -------------------------------------------------------------------------
    # Requirement 1: CURRENT data permits normal evaluation
    # -------------------------------------------------------------------------
    def test_01_current_data_permits_normal_evaluation(self):
        """CURRENT data (1 day old) permits normal evaluation and displays observation date."""
        obs_date = "2026-10-24"  # 1 day lag
        decision = self.gate.evaluate_gate(observation_date=obs_date)

        self.assertTrue(decision.is_permitted)
        self.assertEqual(decision.recommendation_status, RecommendationStatus.ACTIVE.value)
        self.assertEqual(decision.freshness_status, FreshnessStatus.CURRENT.value)
        self.assertEqual(decision.observation_date, obs_date)
        self.assertEqual(decision.lag_days, 1)

        # Economic model evaluation permitted
        res = evaluate_sell_vs_store(
            quantity_quintals=10.0,
            current_price=2500.0,
            future_price=2650.0,
            params=self.params,
            observation_date=obs_date,
            reference_date=self.ref_date
        )
        self.assertNotEqual(res["action"], "BLOCKED")
        self.assertEqual(res["action"], "STORE")
        self.assertEqual(res["recommendation_status"], "ACTIVE")

    # -------------------------------------------------------------------------
    # Requirement 2: DELAYED data displays an explicit delay warning
    # -------------------------------------------------------------------------
    def test_02_delayed_data_displays_explicit_delay_warning(self):
        """DELAYED data (4 days old) allows evaluation but discloses the delay."""
        obs_date = "2026-10-21"  # 4 days lag
        decision = self.gate.evaluate_gate(observation_date=obs_date)

        self.assertTrue(decision.is_permitted)
        self.assertEqual(decision.recommendation_status, RecommendationStatus.DELAYED.value)
        self.assertEqual(decision.freshness_status, FreshnessStatus.DELAYED.value)
        self.assertEqual(decision.lag_days, 4)
        self.assertIn("delayed by 4 days", decision.message)
        self.assertIn("Not a live or today's price", decision.message)

        # Economic evaluation reflects DELAYED status
        res = evaluate_sell_vs_store(
            quantity_quintals=10.0,
            current_price=2500.0,
            future_price=2650.0,
            params=self.params,
            observation_date=obs_date,
            reference_date=self.ref_date
        )
        self.assertEqual(res["recommendation_status"], "DELAYED")
        self.assertEqual(res["action"], "STORE")
        self.assertIn("delayed", res["message"].lower())

    # -------------------------------------------------------------------------
    # Requirement 3: STALE data blocks active storage recommendations
    # -------------------------------------------------------------------------
    def test_03_stale_data_blocks_active_storage_recommendations(self):
        """STALE data (>5 days lag) must block active storage recommendations."""
        obs_date = "2026-09-30"  # 25 days lag
        decision = self.gate.evaluate_gate(observation_date=obs_date)

        self.assertFalse(decision.is_permitted)
        self.assertEqual(decision.recommendation_status, RecommendationStatus.BLOCKED.value)
        self.assertEqual(decision.freshness_status, FreshnessStatus.STALE.value)
        self.assertEqual(decision.message, BLOCKED_RECOMMENDATION_MESSAGE)
        self.assertIn("stale", decision.blocked_reason.lower())

        # Economic evaluation must return action = BLOCKED
        res = evaluate_sell_vs_store(
            quantity_quintals=10.0,
            current_price=2500.0,
            future_price=2650.0,
            params=self.params,
            observation_date=obs_date,
            reference_date=self.ref_date
        )
        self.assertEqual(res["action"], "BLOCKED")
        self.assertEqual(res["recommendation_status"], "BLOCKED")
        self.assertEqual(res["message"], BLOCKED_RECOMMENDATION_MESSAGE)
        self.assertIn("blocked_reason", res)

    # -------------------------------------------------------------------------
    # Requirement 4: STALE data cannot be labeled LIVE or TODAY
    # -------------------------------------------------------------------------
    def test_04_stale_data_cannot_be_labeled_live_or_today(self):
        """Stale output rendered in dashboard must clearly say NOT A CURRENT PRICE."""
        reporter = CurrentDataReporter(reference_date=self.ref_date)
        report = reporter.load_report(simulated_state=OperationalState.STALE_DATA)
        report.freshness_status = FreshnessStatus.STALE
        report.freshness_lag_days = 25
        report.latest_observation_date = "2026-09-30"

        dashboard = reporter.render_ascii_dashboard(report)

        self.assertIn("STALE DATA WARNING — NOT A CURRENT PRICE", dashboard)
        self.assertIn("BLOCKED", dashboard)
        self.assertNotIn("LIVE PRICE", dashboard)
        self.assertNotIn("TODAY'S PRICE", dashboard)

    # -------------------------------------------------------------------------
    # Requirement 5: SOURCE_DOWN without fresh alternative blocks recommendations
    # -------------------------------------------------------------------------
    def test_05_source_down_without_fresh_alternative_blocks_recommendations(self):
        """SOURCE_DOWN without fresh alternative must block recommendations."""
        decision = self.gate.evaluate_gate(
            observation_date="2026-10-24",
            operational_state=OperationalState.SOURCE_DOWN,
            source_available=False,
            has_verified_fresh_alternative=False
        )

        self.assertFalse(decision.is_permitted)
        self.assertEqual(decision.recommendation_status, RecommendationStatus.BLOCKED.value)
        self.assertEqual(decision.message, BLOCKED_RECOMMENDATION_MESSAGE)
        self.assertIn("source is down", decision.blocked_reason.lower())

    # -------------------------------------------------------------------------
    # Requirement 6: UNINITIALIZED data blocks recommendations
    # -------------------------------------------------------------------------
    def test_06_uninitialized_data_blocks_recommendations(self):
        """UNINITIALIZED operational state must block recommendations."""
        decision = self.gate.evaluate_gate(
            observation_date="2026-10-24",
            operational_state=OperationalState.UNINITIALIZED
        )

        self.assertFalse(decision.is_permitted)
        self.assertEqual(decision.recommendation_status, RecommendationStatus.BLOCKED.value)
        self.assertEqual(decision.message, BLOCKED_RECOMMENDATION_MESSAGE)
        self.assertIn("uninitialized", decision.blocked_reason.lower())

    # -------------------------------------------------------------------------
    # Requirement 7: Missing observation date cannot be classified as CURRENT
    # -------------------------------------------------------------------------
    def test_07_missing_observation_date_cannot_be_classified_as_current(self):
        """Missing or None observation date cannot be CURRENT and must block advice."""
        decision = self.gate.evaluate_gate(observation_date=None)

        self.assertFalse(decision.is_permitted)
        self.assertEqual(decision.recommendation_status, RecommendationStatus.BLOCKED.value)
        self.assertNotEqual(decision.freshness_status, FreshnessStatus.CURRENT.value)
        self.assertEqual(decision.freshness_status, FreshnessStatus.UNKNOWN.value)
        self.assertEqual(decision.message, BLOCKED_RECOMMENDATION_MESSAGE)
        self.assertIn("missing or invalid", decision.blocked_reason.lower())

        # Empty string observation date
        decision_empty = self.gate.evaluate_gate(observation_date="")
        self.assertFalse(decision_empty.is_permitted)
        self.assertEqual(decision_empty.recommendation_status, RecommendationStatus.BLOCKED.value)

    # -------------------------------------------------------------------------
    # Requirement 8: Future-dated observations are rejected or explicitly flagged
    # -------------------------------------------------------------------------
    def test_08_future_dated_observations_rejected(self):
        """Future-dated observation (e.g. 2026-10-29 vs ref 2026-10-25) must be rejected."""
        future_obs = "2026-10-29"  # 4 days in future
        decision = self.gate.evaluate_gate(observation_date=future_obs)

        self.assertFalse(decision.is_permitted)
        self.assertEqual(decision.recommendation_status, RecommendationStatus.BLOCKED.value)
        self.assertNotEqual(decision.freshness_status, FreshnessStatus.CURRENT.value)
        self.assertEqual(decision.freshness_status, FreshnessStatus.UNKNOWN.value)
        self.assertIn("future", decision.blocked_reason.lower())

    # -------------------------------------------------------------------------
    # Requirement 9: Historical analysis remains available and clearly labeled
    # -------------------------------------------------------------------------
    def test_09_historical_analysis_remains_available_and_labeled_historical(self):
        """Historical research/backtest mode allows retrospective evaluation with explicit labeling."""
        obs_date = "2024-05-10"  # Years in past
        decision = self.gate.evaluate_gate(
            observation_date=obs_date,
            is_historical_analysis=True
        )

        self.assertTrue(decision.is_permitted)
        self.assertEqual(decision.recommendation_status, RecommendationStatus.HISTORICAL_ONLY.value)
        self.assertTrue(decision.is_historical)
        self.assertIn("Historical analysis only", decision.message)

        # Economic model in historical analysis mode computes metrics and flags status
        res = evaluate_sell_vs_store(
            quantity_quintals=10.0,
            current_price=2500.0,
            future_price=2650.0,
            params=self.params,
            observation_date=obs_date,
            reference_date=self.ref_date,
            is_historical_analysis=True
        )
        self.assertEqual(res["action"], "STORE")
        self.assertEqual(res["recommendation_status"], "HISTORICAL_ONLY")
        self.assertFalse(res["is_actionable_advisory"])
        self.assertIn("historical", res["message"].lower())

    def test_09b_historical_mode_blocks_missing_or_malformed_or_future_dates(self):
        """Historical mode must reject missing, malformed, or future dates, but permit valid past dates."""
        # Missing date in historical mode
        dec_missing = self.gate.evaluate_gate(
            observation_date=None,
            is_historical_analysis=True
        )
        self.assertFalse(dec_missing.is_permitted)
        self.assertEqual(dec_missing.recommendation_status, RecommendationStatus.BLOCKED.value)
        self.assertIn("missing or malformed", dec_missing.blocked_reason.lower())

        # Empty string date in historical mode
        dec_empty = self.gate.evaluate_gate(
            observation_date="",
            is_historical_analysis=True
        )
        self.assertFalse(dec_empty.is_permitted)
        self.assertEqual(dec_empty.recommendation_status, RecommendationStatus.BLOCKED.value)

        # Malformed date in historical mode
        dec_malformed = self.gate.evaluate_gate(
            observation_date="invalid-date-format",
            is_historical_analysis=True
        )
        self.assertFalse(dec_malformed.is_permitted)
        self.assertEqual(dec_malformed.recommendation_status, RecommendationStatus.BLOCKED.value)
        self.assertIn("missing or malformed", dec_malformed.blocked_reason.lower())

        # Future-dated observation in historical mode
        dec_future = self.gate.evaluate_gate(
            observation_date="2026-10-30",  # 5 days ahead of ref_date (2026-10-25)
            is_historical_analysis=True
        )
        self.assertFalse(dec_future.is_permitted)
        self.assertEqual(dec_future.recommendation_status, RecommendationStatus.BLOCKED.value)
        self.assertIn("future", dec_future.blocked_reason.lower())

        # Economic model with missing historical date
        res_missing = evaluate_sell_vs_store(
            quantity_quintals=10.0,
            current_price=2500.0,
            future_price=2650.0,
            params=self.params,
            observation_date=None,
            reference_date=self.ref_date,
            is_historical_analysis=True
        )
        self.assertEqual(res_missing["action"], "BLOCKED")
        self.assertEqual(res_missing["recommendation_status"], "BLOCKED")
        self.assertFalse(res_missing["is_actionable_advisory"])

        # Economic model with future historical date
        res_future = evaluate_sell_vs_store(
            quantity_quintals=10.0,
            current_price=2500.0,
            future_price=2650.0,
            params=self.params,
            observation_date="2026-10-30",
            reference_date=self.ref_date,
            is_historical_analysis=True
        )
        self.assertEqual(res_future["action"], "BLOCKED")
        self.assertEqual(res_future["recommendation_status"], "BLOCKED")
        self.assertFalse(res_future["is_actionable_advisory"])

    def test_09c_partial_and_quarantined_states_block_recommendations(self):
        """OperationalState.PARTIAL and QUARANTINED must block recommendations even with fresh dates."""
        fresh_date = "2026-10-24"  # 1 day lag

        # Test PARTIAL state
        dec_partial = self.gate.evaluate_gate(
            observation_date=fresh_date,
            operational_state=OperationalState.PARTIAL
        )
        self.assertFalse(dec_partial.is_permitted)
        self.assertEqual(dec_partial.recommendation_status, RecommendationStatus.BLOCKED.value)
        self.assertIn("partial", dec_partial.blocked_reason.lower())

        res_partial_econ = evaluate_sell_vs_store(
            quantity_quintals=10.0,
            current_price=2500.0,
            future_price=2650.0,
            params=self.params,
            observation_date=fresh_date,
            reference_date=self.ref_date,
            operational_state=OperationalState.PARTIAL
        )
        self.assertEqual(res_partial_econ["action"], "BLOCKED")
        self.assertEqual(res_partial_econ["recommendation_status"], RecommendationStatus.BLOCKED.value)
        self.assertFalse(res_partial_econ["is_actionable_advisory"])

        res_partial_farmer = evaluate_farmer_storage_recommendation(
            quantity_quintals=10.0,
            current_price=2500.0,
            future_price=2650.0,
            params=self.params,
            observation_date=fresh_date,
            reference_date=self.ref_date,
            operational_state=OperationalState.PARTIAL
        )
        self.assertEqual(res_partial_farmer["action"], "BLOCKED")
        self.assertEqual(res_partial_farmer["recommendation_status"], RecommendationStatus.BLOCKED.value)
        self.assertFalse(res_partial_farmer["is_actionable_advisory"])

        # Test QUARANTINED state
        dec_quarantined = self.gate.evaluate_gate(
            observation_date=fresh_date,
            operational_state=OperationalState.QUARANTINED
        )
        self.assertFalse(dec_quarantined.is_permitted)
        self.assertEqual(dec_quarantined.recommendation_status, RecommendationStatus.BLOCKED.value)
        self.assertIn("quarantined", dec_quarantined.blocked_reason.lower())

        res_quar_econ = evaluate_sell_vs_store(
            quantity_quintals=10.0,
            current_price=2500.0,
            future_price=2650.0,
            params=self.params,
            observation_date=fresh_date,
            reference_date=self.ref_date,
            operational_state=OperationalState.QUARANTINED
        )
        self.assertEqual(res_quar_econ["action"], "BLOCKED")
        self.assertEqual(res_quar_econ["recommendation_status"], RecommendationStatus.BLOCKED.value)
        self.assertFalse(res_quar_econ["is_actionable_advisory"])

        res_quar_farmer = evaluate_farmer_storage_recommendation(
            quantity_quintals=10.0,
            current_price=2500.0,
            future_price=2650.0,
            params=self.params,
            observation_date=fresh_date,
            reference_date=self.ref_date,
            operational_state=OperationalState.QUARANTINED
        )
        self.assertEqual(res_quar_farmer["action"], "BLOCKED")
        self.assertEqual(res_quar_farmer["recommendation_status"], RecommendationStatus.BLOCKED.value)
        self.assertFalse(res_quar_farmer["is_actionable_advisory"])

    # -------------------------------------------------------------------------
    # Requirement 10: Demo output cannot masquerade as real market observation
    # -------------------------------------------------------------------------
    def test_10_demo_output_cannot_masquerade_as_real_market_observation(self):
        """Demo output must be isolated and explicitly flagged as simulated demo."""
        decision = self.gate.evaluate_gate(
            observation_date="2026-10-24",
            is_demo=True
        )

        self.assertFalse(decision.is_permitted)
        self.assertEqual(decision.recommendation_status, RecommendationStatus.DEMO.value)
        self.assertTrue(decision.is_demo)
        self.assertIn("DEMO MODE", decision.message)

        # Dashboard rendering under demo mode
        reporter = CurrentDataReporter(reference_date=self.ref_date)
        report = reporter.load_report()
        dashboard = reporter.render_ascii_dashboard(report, is_demo=True)

        self.assertIn("[DEMO MODE] SIMULATED INTEGRATION DEMONSTRATION RUN", dashboard)
        self.assertIn("NOT a real mandi market data feed", dashboard)

    # -------------------------------------------------------------------------
    # Requirement 11: Every downstream recommendation path applies safety gate
    # -------------------------------------------------------------------------
    def test_11_every_downstream_recommendation_path_applies_safety_gate(self):
        """Verify all major downstream recommendation paths apply the safety gate on stale data."""
        stale_date = "2026-09-30"  # 25 days behind ref_date (2026-10-25)

        # Path A: evaluate_sell_vs_store with stale observation
        res_econ = evaluate_sell_vs_store(
            quantity_quintals=10.0,
            current_price=2500.0,
            future_price=2650.0,
            params=self.params,
            observation_date=stale_date,
            reference_date=self.ref_date
        )
        self.assertEqual(res_econ["action"], "BLOCKED")
        self.assertEqual(res_econ["recommendation_status"], "BLOCKED")
        self.assertEqual(res_econ["message"], BLOCKED_RECOMMENDATION_MESSAGE)

        # Path B: evaluate_farmer_storage_recommendation
        res_farmer = evaluate_farmer_storage_recommendation(
            quantity_quintals=10.0,
            current_price=2500.0,
            future_price=2650.0,
            params=self.params,
            observation_date=stale_date,
            reference_date=self.ref_date
        )
        self.assertEqual(res_farmer["action"], "BLOCKED")
        self.assertEqual(res_farmer["recommendation_status"], "BLOCKED")

        # Path C: MandiMarketIntelligenceEngine
        row = {
            "Arrival_Date": pd.to_datetime(stale_date),
            "District": "Kanpur",
            "Market": "Choubepur",
            "Commodity": "Potato",
            "Variety": "Other",
            "Modal_Price": 2000.0,
            "Min_Price": 1900.0,
            "Max_Price": 2100.0,
            "Price_Intraday_Spread": 200.0,
            "Price_Change_1d": 0.0,
            "Price_Change_3d": 1.0,
            "Price_Change_7d": 2.0,
            "Roll_Mean_Price_7": 1980.0,
            "Roll_Std_Price_7": 25.0,
            "District_Commodity_MeanPrice": 2000.0,
            "District_Commodity_MandiCount": 2,
            "Neighbor_Commodity_MeanPrice": 2020.0,
            "Price_Diff_Target_vs_Neighbor": -20.0,
            "Modal_Price_T7": 2150.0,
            "Pct_Change_T7": 7.5,
            "Market_Condition": "Favorable"
        }
        for col in FEATURE_COLUMNS:
            if col not in row:
                row[col] = 1.0

        df_mock = pd.DataFrame([row])
        engine = MandiMarketIntelligenceEngine(MockPredictor(), df_mock, default_ref_date=self.ref_date)
        intel = engine.generate_intelligence(district="Kanpur", commodity="Potato")

        self.assertEqual(intel["recommendation_status"], "BLOCKED")
        self.assertEqual(intel["actionable_recommendation"], "BLOCKED")
        self.assertEqual(intel["blocked_reason"], f"Market data is stale (25 calendar days lag > threshold 5 days).")

        card = engine.format_terminal_card(intel)
        self.assertIn("STALE DATA WARNING — NOT A CURRENT PRICE", card)
        self.assertIn("ACTIVE ADVISORY BLOCKED", card)
        self.assertIn(BLOCKED_RECOMMENDATION_MESSAGE, card)

        # Path D: CurrentDataReporter
        reporter = CurrentDataReporter(reference_date=self.ref_date)
        report = reporter.load_report()
        gate_dec = reporter.evaluate_safety_gate(report=report)
        self.assertEqual(gate_dec.recommendation_status, "BLOCKED")
        self.assertFalse(gate_dec.is_permitted)

    # -------------------------------------------------------------------------
    # Requirement 12: Existing economic calculations remain unchanged for fresh inputs
    # -------------------------------------------------------------------------
    def test_12_existing_economic_calculations_remain_unchanged_for_valid_fresh_inputs(self):
        """Pure mathematical calculations remain bit-for-bit identical for fresh inputs."""
        # Unconstrained mathematical mode (backtesting / simulation)
        res_pure = evaluate_sell_vs_store(
            quantity_quintals=10.0,
            current_price=2500.0,
            future_price=2650.0,
            params=self.params
        )
        self.assertAlmostEqual(res_pure["r_sell_net"], 25000.0, places=2)
        self.assertAlmostEqual(res_pure["r_store_net"], 25470.0, places=2)
        self.assertAlmostEqual(res_pure["incremental_benefit"], 470.0, places=2)
        self.assertEqual(res_pure["action"], "STORE")
        # Critical architectural check: missing observation context MUST NOT produce ACTIVE
        self.assertEqual(res_pure["recommendation_status"], RecommendationStatus.SIMULATION_ONLY.value)
        self.assertFalse(res_pure["is_actionable_advisory"])

        # Gated mode with fresh observation date (1 day lag)
        res_fresh = evaluate_sell_vs_store(
            quantity_quintals=10.0,
            current_price=2500.0,
            future_price=2650.0,
            params=self.params,
            observation_date="2026-10-24",
            reference_date=self.ref_date
        )
        self.assertAlmostEqual(res_fresh["r_sell_net"], 25000.0, places=2)
        self.assertAlmostEqual(res_fresh["r_store_net"], 25470.0, places=2)
        self.assertAlmostEqual(res_fresh["incremental_benefit"], 470.0, places=2)
        self.assertEqual(res_fresh["action"], "STORE")
        self.assertEqual(res_fresh["recommendation_status"], "ACTIVE")
        self.assertTrue(res_fresh["is_actionable_advisory"])

    # -------------------------------------------------------------------------
    # Requirement 13: Farmer-facing recommendation requires observation context
    # -------------------------------------------------------------------------
    def test_13_farmer_facing_recommendation_requires_observation_context(self):
        """Farmer-facing wrapper without observation date must be BLOCKED, never ACTIVE."""
        res_no_date = evaluate_farmer_storage_recommendation(
            quantity_quintals=10.0,
            current_price=2500.0,
            future_price=2650.0,
            params=self.params,
            observation_date=None,
            reference_date=self.ref_date
        )
        self.assertEqual(res_no_date["action"], "BLOCKED")
        self.assertEqual(res_no_date["recommendation_status"], "BLOCKED")
        self.assertFalse(res_no_date["is_actionable_advisory"])
        self.assertEqual(res_no_date["message"], BLOCKED_RECOMMENDATION_MESSAGE)

        # Farmer-facing with fresh observation produces ACTIVE
        res_with_date = evaluate_farmer_storage_recommendation(
            quantity_quintals=10.0,
            current_price=2500.0,
            future_price=2650.0,
            params=self.params,
            observation_date="2026-10-24",
            reference_date=self.ref_date
        )
        self.assertEqual(res_with_date["action"], "STORE")
        self.assertEqual(res_with_date["recommendation_status"], "ACTIVE")
        self.assertTrue(res_with_date["is_actionable_advisory"])


if __name__ == "__main__":
    unittest.main()
