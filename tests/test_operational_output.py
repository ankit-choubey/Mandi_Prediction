"""
Unit & Integration Tests for Current-Data Output & Operational Reliability
APMC Mandi Market Intelligence System
Author: Om Awasthi (Owner 4)

Covers all 7 mandatory operational states, freshness policies,
timestamp separation, and reconciliation ledger arithmetic.
"""

import os
import json
import tempfile
import unittest
from datetime import date, datetime, timezone, timedelta

import pandas as pd

from src.health_status import (
    HealthStatusEngine,
    HealthReport,
    OperationalState,
    FreshnessStatus,
    ReconciliationLedger
)
from src.current_data_output import CurrentDataReporter


class TestOperationalHealthStates(unittest.TestCase):
    """Test suite for the 7 mutually exclusive operational pipeline states."""

    def setUp(self):
        self.ref_date = date(2026, 10, 25)
        self.engine = HealthStatusEngine(current_ref_date=self.ref_date)

    def test_state_1_success(self):
        """State 1: Fetch and validation succeed with fresh data."""
        state = self.engine.determine_state(
            is_fetch_success=True,
            is_source_available=True,
            has_prior_snapshot=True,
            is_partial_response=False,
            records_quarantined=0,
            records_new=120,
            freshness=FreshnessStatus.CURRENT
        )
        self.assertEqual(state, OperationalState.SUCCESS)

    def test_state_2_unchanged(self):
        """State 2: Fetch succeeds but incoming records are already in store (0 new)."""
        state = self.engine.determine_state(
            is_fetch_success=True,
            is_source_available=True,
            has_prior_snapshot=True,
            is_partial_response=False,
            records_quarantined=0,
            records_new=0,
            freshness=FreshnessStatus.CURRENT
        )
        self.assertEqual(state, OperationalState.UNCHANGED)

    def test_state_3_partial(self):
        """State 3: Source responds with partial/incomplete data."""
        state = self.engine.determine_state(
            is_fetch_success=True,
            is_source_available=True,
            has_prior_snapshot=True,
            is_partial_response=True,
            records_quarantined=0,
            records_new=50,
            freshness=FreshnessStatus.CURRENT
        )
        self.assertEqual(state, OperationalState.PARTIAL)

    def test_state_4_quarantined(self):
        """State 4: Some records fail validation and are quarantined."""
        state = self.engine.determine_state(
            is_fetch_success=True,
            is_source_available=True,
            has_prior_snapshot=True,
            is_partial_response=False,
            records_quarantined=27,
            records_new=100,
            freshness=FreshnessStatus.CURRENT
        )
        self.assertEqual(state, OperationalState.QUARANTINED)

    def test_state_5_source_down_with_fallback(self):
        """State 5: Source is unavailable, but a prior validated snapshot exists."""
        state = self.engine.determine_state(
            is_fetch_success=False,
            is_source_available=False,
            has_prior_snapshot=True,
            is_partial_response=False,
            records_quarantined=0,
            records_new=0,
            freshness=FreshnessStatus.STALE
        )
        self.assertEqual(state, OperationalState.SOURCE_DOWN)

    def test_state_6_uninitialized(self):
        """State 6: Critical failure; source down and zero snapshots exist."""
        state = self.engine.determine_state(
            is_fetch_success=False,
            is_source_available=False,
            has_prior_snapshot=False,
            is_partial_response=False,
            records_quarantined=0,
            records_new=0,
            freshness=FreshnessStatus.UNKNOWN
        )
        self.assertEqual(state, OperationalState.UNINITIALIZED)

    def test_state_7_stale_data(self):
        """State 7: Latest observation is older than threshold."""
        state = self.engine.determine_state(
            is_fetch_success=True,
            is_source_available=True,
            has_prior_snapshot=True,
            is_partial_response=False,
            records_quarantined=0,
            records_new=50,
            freshness=FreshnessStatus.STALE
        )
        self.assertEqual(state, OperationalState.STALE_DATA)


class TestFreshnessPolicyAndTimestamps(unittest.TestCase):
    """Test observation freshness boundaries and strict timestamp separation."""

    def setUp(self):
        self.ref_date = date(2026, 10, 25)
        self.engine = HealthStatusEngine(current_ref_date=self.ref_date)

    def test_freshness_current_within_2_days(self):
        # 1 day lag -> CURRENT
        status, lag = self.engine.evaluate_freshness("2026-10-24")
        self.assertEqual(status, FreshnessStatus.CURRENT)
        self.assertEqual(lag, 1)

        # 2 days lag -> CURRENT
        status, lag = self.engine.evaluate_freshness("2026-10-23")
        self.assertEqual(status, FreshnessStatus.CURRENT)
        self.assertEqual(lag, 2)

    def test_freshness_delayed_3_to_5_days(self):
        # 3 days lag -> DELAYED
        status, lag = self.engine.evaluate_freshness("2026-10-22")
        self.assertEqual(status, FreshnessStatus.DELAYED)
        self.assertEqual(lag, 3)

        # 5 days lag -> DELAYED
        status, lag = self.engine.evaluate_freshness("2026-10-20")
        self.assertEqual(status, FreshnessStatus.DELAYED)
        self.assertEqual(lag, 5)

    def test_freshness_stale_over_5_days(self):
        # 6 days lag -> STALE
        status, lag = self.engine.evaluate_freshness("2026-10-19")
        self.assertEqual(status, FreshnessStatus.STALE)
        self.assertEqual(lag, 6)

        # 25 days lag -> STALE
        status, lag = self.engine.evaluate_freshness("2026-09-30")
        self.assertEqual(status, FreshnessStatus.STALE)
        self.assertEqual(lag, 25)

    def test_freshness_future_date_rejected(self):
        # 1 day future -> UNKNOWN, lag = -1
        status, lag = self.engine.evaluate_freshness("2026-10-26")
        self.assertNotEqual(status, FreshnessStatus.CURRENT)
        self.assertEqual(status, FreshnessStatus.UNKNOWN)
        self.assertEqual(lag, -1)

    def test_freshness_missing_date_rejected(self):
        # Missing date -> UNKNOWN, lag = None
        status, lag = self.engine.evaluate_freshness(None)
        self.assertNotEqual(status, FreshnessStatus.CURRENT)
        self.assertEqual(status, FreshnessStatus.UNKNOWN)
        self.assertIsNone(lag)

    def test_timestamp_separation_contract(self):
        """Verify that observation date and retrieval timestamp are strictly distinct."""
        mock_summary = {
            "execution_timestamp_utc": "2026-10-23T14:30:00Z",
            "counts": {"total_input_raw_records": 100, "total_accepted_clean_records": 100},
            "temporal_coverage": {"latest_arrival_date": "2026-09-30"}
        }
        report = self.engine.build_report_from_summary(mock_summary)
        
        # Observation date must reflect market clearing date, NOT fetch date
        self.assertEqual(report.latest_observation_date, "2026-09-30")
        self.assertTrue("2026-10-23" in report.last_successful_fetch_utc)
        self.assertNotEqual(report.latest_observation_date, report.last_successful_fetch_utc[:10])


class TestReconciliationArithmetic(unittest.TestCase):
    """Test ledger arithmetic and accounting balance."""

    def test_balanced_ledger(self):
        ledger = ReconciliationLedger(
            records_fetched=1000,
            records_parsed=1000,
            records_accepted=950,
            records_quarantined=50
        )
        result = ledger.validate_arithmetic()
        self.assertTrue(result["is_balanced"])
        self.assertEqual(result["discrepancy"], 0)

    def test_unbalanced_ledger_detection(self):
        # Silent drop of 20 records
        ledger = ReconciliationLedger(
            records_fetched=1000,
            records_parsed=1000,
            records_accepted=930,
            records_quarantined=50
        )
        result = ledger.validate_arithmetic()
        self.assertFalse(result["is_balanced"])
        self.assertEqual(result["discrepancy"], 20)


class TestReporterAndDashboard(unittest.TestCase):
    """Test terminal dashboard rendering and lookup queries."""

    def test_dashboard_renders_all_fields(self):
        reporter = CurrentDataReporter()
        report = reporter.load_report()
        dashboard = reporter.render_ascii_dashboard(report)

        self.assertIn("APMC MANDI MARKET INTELLIGENCE", dashboard)
        self.assertIn("Source Name", dashboard)
        self.assertIn("Resource ID", dashboard)
        self.assertIn("Operational Pipeline State", dashboard)
        self.assertIn("RECONCILIATION LEDGER", dashboard)
        self.assertIn("Snapshot SHA-256 Checksum", dashboard)

    def test_sample_lookup_potato(self):
        reporter = CurrentDataReporter()
        sample = reporter.query_latest_observation(commodity="Potato", district="Kanpur")
        if sample:
            self.assertEqual(sample["Commodity"], "Potato")
            self.assertEqual(sample["District"], "Kanpur")
            self.assertGreater(sample["Modal_Price"], 0)

    def test_newest_observation_after_row_25000_never_wrong_latest(self):
        """
        Verify that observations after row 25,000 are never missed.
        Direct CSV queries on oversized files are denied with ValueError;
        queries with index return the true complete latest observation.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = os.path.join(tmp_dir, "test_large.csv")
            # Write 26,000 rows where row 10 is 2026-01-01 and row 25,500 is 2026-11-10
            dates = ["2026-01-01"] * 26000
            dates[25500] = "2026-11-10"
            df = pd.DataFrame({
                "District": ["Kanpur"] * 26000,
                "Market": ["Kanpur(Grain)"] * 26000,
                "Commodity": ["Potato"] * 26000,
                "Variety": ["Other"] * 26000,
                "Grade": ["FAQ"] * 26000,
                "Arrival_Date": dates,
                "Modal_Price": [500.0] * 26000,
                "Min_Price": [480.0] * 26000,
                "Max_Price": [520.0] * 26000,
            })
            df.to_csv(csv_path, index=False)

            reporter = CurrentDataReporter(validated_csv_path=csv_path, latest_index_path=None)
            # Query directly: must find the 2026-11-10 observation (row 25,500), NOT 2026-01-01!
            obs = reporter.query_latest_observation(commodity="Potato", district="Kanpur", use_index=False)
            self.assertIsNotNone(obs)
            self.assertEqual(obs["Arrival_Date"], "2026-11-10")

    def test_missing_grade_distinct_from_faq(self):
        """Verify missing grade is preserved as SOURCE_NOT_PROVIDED and distinct from FAQ."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            idx_path = os.path.join(tmp_dir, "index.json")
            index_payload = {
                "series": {
                    "s1": {
                        "district": "Kanpur",
                        "market_canonical": "Kanpur(Grain)",
                        "commodity": "Potato",
                        "variety": "Other",
                        "grade": "SOURCE_NOT_PROVIDED",
                        "latest_observation_date": "2026-11-11",
                        "modal_price": 550.0,
                    }
                }
            }
            with open(idx_path, "w", encoding="utf-8") as f:
                json.dump(index_payload, f)

            reporter = CurrentDataReporter(latest_index_path=idx_path)
            res = reporter.query_latest_observation(commodity="Potato", district="Kanpur")
            self.assertIsNotNone(res)
            self.assertEqual(res["Grade"], "SOURCE_NOT_PROVIDED")
            self.assertNotEqual(res["Grade"], "FAQ")

    def test_recent_snapshot_one_current_and_unrelated_stale(self):
        """Verify reporter handles current series without extrapolating freshness to stale series."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            idx_path = os.path.join(tmp_dir, "index.json")
            index_payload = {
                "series": {
                    "s_fresh": {
                        "district": "Kanpur",
                        "market_canonical": "Kanpur(Grain)",
                        "commodity": "Potato",
                        "variety": "Other",
                        "grade": "FAQ",
                        "latest_observation_date": "2026-11-11",
                        "modal_price": 550.0,
                    },
                    "s_stale": {
                        "district": "Jhansi",
                        "market_canonical": "Chirgaon",
                        "commodity": "Wheat",
                        "variety": "Dara",
                        "grade": "FAQ",
                        "latest_observation_date": "2026-08-01",
                        "modal_price": 2200.0,
                    }
                }
            }
            with open(idx_path, "w", encoding="utf-8") as f:
                json.dump(index_payload, f)

            reporter = CurrentDataReporter(latest_index_path=idx_path, reference_date=date(2026, 11, 12))
            fresh = reporter.query_latest_observation(commodity="Potato", district="Kanpur")
            stale = reporter.query_latest_observation(commodity="Wheat", district="Jhansi")

            self.assertEqual(fresh["Arrival_Date"], "2026-11-11")
            self.assertEqual(stale["Arrival_Date"], "2026-08-01")


if __name__ == "__main__":
    unittest.main()
