"""
Unit & Integration Tests for Current-Data Output & Operational Reliability
APMC Mandi Market Intelligence System
Author: Om Awasthi (Owner 4)

Covers all 7 mandatory operational states, freshness policies,
timestamp separation, and reconciliation ledger arithmetic.
"""

import os
import json
import unittest
from datetime import date, datetime, timezone, timedelta

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


if __name__ == "__main__":
    unittest.main()
